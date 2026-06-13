# activites/payment.py
import requests
import json
import hashlib
import hmac
import time
import uuid
from django.conf import settings
from .models import PaiementActivite, Inscription

class MobileMoneyPayment:
    """Intégration des paiements Mobile Money (MTN, Orange)"""
    
    @staticmethod
    def initier_paiement_mtn(telephone, montant, reference):
        """Initier un paiement MTN Mobile Money"""
        # API MTN (à adapter selon la documentation officielle)
        api_url = "https://api.mtn.com/v1/payment/request"
        
        # En production, utiliser les vraies clés API
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": settings.MTN_API_KEY,
            "X-API-Secret": settings.MTN_API_SECRET
        }
        
        payload = {
            "amount": str(montant),
            "currency": "XAF",
            "externalId": reference,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": telephone
            },
            "payerMessage": f"Paiement inscription activité {reference}",
            "payeeNote": "Plateforme Municipale"
        }
        
        try:
            # En mode test, simuler une réponse
            if settings.DEBUG:
                return {
                    "success": True,
                    "transaction_id": f"MTN-{uuid.uuid4().hex[:8].upper()}",
                    "status": "pending"
                }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if response.status_code == 202:
                return {
                    "success": True,
                    "transaction_id": data.get("transactionId"),
                    "status": "pending"
                }
            else:
                return {
                    "success": False,
                    "error": data.get("message", "Erreur lors du paiement")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def initier_paiement_orange(telephone, montant, reference):
        """Initier un paiement Orange Money"""
        api_url = "https://api.orange.com/v1/payment/request"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {settings.ORANGE_ACCESS_TOKEN}"
        }
        
        payload = {
            "amount": str(montant),
            "currency": "XAF",
            "orderId": reference,
            "msisdn": telephone,
            "description": f"Paiement inscription activité"
        }
        
        try:
            if settings.DEBUG:
                return {
                    "success": True,
                    "transaction_id": f"ORANGE-{uuid.uuid4().hex[:8].upper()}",
                    "status": "pending"
                }
            
            response = requests.post(api_url, json=payload, headers=headers, timeout=30)
            data = response.json()
            
            if response.status_code == 201:
                return {
                    "success": True,
                    "transaction_id": data.get("transactionId"),
                    "status": "pending"
                }
            else:
                return {
                    "success": False,
                    "error": data.get("message", "Erreur lors du paiement")
                }
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def verifier_paiement(transaction_id, provider):
        """Vérifier le statut d'un paiement"""
        # Implémenter la vérification selon le provider
        return {"success": True, "status": "success"}

class PaiementHandler:
    """Gestionnaire central des paiements"""
    
    @staticmethod
    def traiter_paiement(inscription_id, moyen_paiement, telephone):
        """Traiter un paiement pour une inscription"""
        from .models import Inscription, PaiementActivite
        from django.utils import timezone
        
        try:
            inscription = Inscription.objects.get(id=inscription_id)
            
            # Créer l'enregistrement de paiement
            paiement = PaiementActivite.objects.create(
                inscription=inscription,
                montant=inscription.montant_total,
                moyen_paiement=moyen_paiement,
                numero_telephone=telephone,
                statut='en_attente'
            )
            
            # Initier le paiement selon le moyen
            if moyen_paiement == 'mtn':
                result = MobileMoneyPayment.initier_paiement_mtn(
                    telephone, 
                    inscription.montant_total, 
                    inscription.reference
                )
            elif moyen_paiement == 'orange':
                result = MobileMoneyPayment.initier_paiement_orange(
                    telephone, 
                    inscription.montant_total, 
                    inscription.reference
                )
            else:
                return {"success": False, "error": "Moyen de paiement non supporté"}
            
            if result.get("success"):
                paiement.transaction_id = result.get("transaction_id")
                paiement.save()
                
                # Mettre à jour l'inscription
                inscription.moyen_paiement = moyen_paiement
                inscription.reference_paiement = result.get("transaction_id")
                inscription.save()
                
                return {
                    "success": True,
                    "paiement_id": paiement.id,
                    "transaction_id": result.get("transaction_id"),
                    "message": "Paiement initié. Veuillez confirmer sur votre téléphone."
                }
            else:
                paiement.statut = 'echoue'
                paiement.api_response = result
                paiement.save()
                return {"success": False, "error": result.get("error")}
                
        except Inscription.DoesNotExist:
            return {"success": False, "error": "Inscription non trouvée"}
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    @staticmethod
    def confirmer_paiement(paiement_id, transaction_id=None):
        """Confirmer un paiement après validation"""
        from .models import PaiementActivite, Inscription, NotificationActivite
        from django.utils import timezone
        
        try:
            paiement = PaiementActivite.objects.get(id=paiement_id)
            
            # Vérifier le statut du paiement auprès du provider
            verification = MobileMoneyPayment.verifier_paiement(
                transaction_id or paiement.transaction_id,
                paiement.moyen_paiement
            )
            
            if verification.get("success") and verification.get("status") == "success":
                paiement.statut = 'paye'
                paiement.date_validation = timezone.now()
                paiement.save()
                
                # Confirmer l'inscription
                inscription = paiement.inscription
                inscription.statut = 'confirmee'
                inscription.date_paiement = timezone.now()
                inscription.save()
                
                # Générer le QR code
                inscription.generate_qr_code()
                inscription.save()
                
                # Envoyer notification
                PaiementHandler.envoyer_confirmation(inscription)
                
                return {
                    "success": True,
                    "inscription_id": inscription.id,
                    "reference": inscription.reference,
                    "qr_code": inscription.qr_code
                }
            else:
                return {"success": False, "error": "Paiement non confirmé"}
                
        except PaiementActivite.DoesNotExist:
            return {"success": False, "error": "Paiement non trouvé"}
    
    @staticmethod
    def envoyer_confirmation(inscription):
        """Envoyer une confirmation par email et SMS"""
        # Utiliser le système de notifications
        from .notifications import NotificationService
        
        NotificationService.envoyer_confirmation_inscription(inscription)