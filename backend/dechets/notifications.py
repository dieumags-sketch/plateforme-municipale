# dechets/notifications.py
import requests
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from twilio.rest import Client
from .models import NotificationDechet, Quartier

class NotificationService:
    """Service de notifications pour le module déchets"""
    
    @staticmethod
    def envoyer_rappel_collecte(quartier_id, jour_semaine):
        """
        Envoie des rappels de collecte aux citoyens d'un quartier
        """
        try:
            quartier = Quartier.objects.get(id=quartier_id)
            
            # Récupérer les utilisateurs du quartier (via préférences)
            # Pour l'instant, simulation - à connecter avec le modèle User
            users = []  # À implémenter avec le modèle UserPreferences
            
            # Notification push via web push
            NotificationService._envoyer_push_collecte(quartier, jour_semaine)
            
            # Notification SMS pour ceux qui ont opt-in
            NotificationService._envoyer_sms_collecte(quartier, jour_semaine)
            
            # Enregistrer la notification
            NotificationDechet.objects.create(
                quartier=quartier,
                type='rappel_collecte',
                titre=f"Rappel collecte - {quartier.nom}",
                message=f"Demain {NotificationService._get_jour_nom(jour_semaine)} à partir de 7h, sortez vos poubelles !",
                est_envoyee=True
            )
            
            return True
        except Exception as e:
            print(f"Erreur envoi rappel: {e}")
            return False
    
    @staticmethod
    def _envoyer_push_collecte(quartier, jour_semaine):
        """Envoi de notification push via Firebase Cloud Messaging"""
        # Configuration FCM (à configurer dans settings)
        fcm_api_key = getattr(settings, 'FCM_API_KEY', '')
        if not fcm_api_key:
            return
        
        # Récupérer les tokens des utilisateurs du quartier
        # À implémenter avec un modèle UserDevice
        
        headers = {
            'Authorization': f'key={fcm_api_key}',
            'Content-Type': 'application/json'
        }
        
        payload = {
            'to': '/topics/collecte_' + str(quartier.id),
            'notification': {
                'title': f'🗑️ Collecte demain - {quartier.nom}',
                'body': f'Sortez vos poubelles demain matin !',
                'icon': '/static/images/logo.png',
                'click_action': '/pages/dechets/calendrier.html'
            },
            'data': {
                'quartier_id': quartier.id,
                'type': 'rappel_collecte'
            }
        }
        
        try:
            requests.post('https://fcm.googleapis.com/fcm/send', json=payload, headers=headers)
        except:
            pass
    
    @staticmethod
    def _envoyer_sms_collecte(quartier, jour_semaine):
        """Envoi de SMS via Twilio"""
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        if not all([twilio_sid, twilio_token, twilio_phone]):
            return
        
        client = Client(twilio_sid, twilio_token)
        
        # Récupérer les numéros des utilisateurs du quartier
        # À implémenter avec le modèle UserPreferences
        
        message = f"Bot-Makak Propre: Collecte des déchets demain ({NotificationService._get_jour_nom(jour_semaine)}). Sortez vos poubelles des la veille au soir. Merci !"
        
        # Envoi groupé (limité)
        # for phone in phones:
        #     client.messages.create(body=message, from_=twilio_phone, to=phone)
    
    @staticmethod
    def notifier_signalement_traite(signalement):
        """Notifie le citoyen que son signalement a été traité"""
        if signalement.telephone:
            NotificationService._envoyer_sms_signalement(signalement)
        
        if signalement.citoyen and signalement.citoyen.email:
            NotificationService._envoyer_email_signalement(signalement)
    
    @staticmethod
    def _envoyer_sms_signalement(signalement):
        """Envoi SMS pour signalement traité"""
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        if not all([twilio_sid, twilio_token, twilio_phone]):
            return
        
        client = Client(twilio_sid, twilio_token)
        
        message = f"Bot-Makak Propre: Votre signalement du {signalement.date_signalement.strftime('%d/%m')} a été traité. Merci pour votre vigilance !"
        
        try:
            client.messages.create(
                body=message,
                from_=twilio_phone,
                to=signalement.telephone
            )
        except Exception as e:
            print(f"Erreur envoi SMS: {e}")
    
    @staticmethod
    def _envoyer_email_signalement(signalement):
        """Envoi email pour signalement traité"""
        subject = f"Votre signalement a été traité - Bot-Makak Propre"
        message = f"""
Bonjour {signalement.nom_citoyen or signalement.citoyen.get_full_name()},

Vous aviez signalé un problème de type "{signalement.get_type_signalement_display()}" le {signalement.date_signalement.strftime('%d/%m/%Y %H:%M')}.

Nous vous informons que ce signalement a été traité par nos équipes.

Merci pour votre contribution à la propreté de notre commune !

Cordialement,
L'équipe Bot-Makak Propre
        """
        
        try:
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [signalement.citoyen.email],
                fail_silently=True
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")
    
    @staticmethod
    def notifier_nouveau_signalement_admin(signalement):
        """Notifie l'admin qu'un nouveau signalement a été créé"""
        # Webhook ou notification interne
        pass
    
    @staticmethod
    def _get_jour_nom(jour_semaine):
        """Convertit le numéro du jour en nom"""
        jours = {
            0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi',
            4: 'vendredi', 5: 'samedi', 6: 'dimanche'
        }
        return jours.get(jour_semaine, '')
    
    @staticmethod
    def envoyer_rappel_hebdomadaire():
        """
        Envoie des rappels hebdomadaires pour tous les quartiers
        À exécuter via cron job ou Celery periodic task
        """
        today = timezone.now().weekday()
        tomorrow = (today + 1) % 7
        
        # Quartiers qui ont collecte demain
        from .models import CalendrierCollecte
        collectes_demain = CalendrierCollecte.objects.filter(
            jour_semaine=tomorrow,
            est_actif=True
        ).select_related('quartier')
        
        for collecte in collectes_demain:
            NotificationService.envoyer_rappel_collecte(
                collecte.quartier.id,
                tomorrow
            )
    
    @staticmethod
    def envoyer_alerte_urgente(quartier_id, message):
        """Envoie une alerte urgente (modification horaire, incident)"""
        try:
            quartier = Quartier.objects.get(id=quartier_id)
            
            # Notification push urgente
            headers = {
                'Authorization': f'key={getattr(settings, "FCM_API_KEY", "")}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'to': '/topics/alerte_' + str(quartier_id),
                'notification': {
                    'title': f'⚠️ ALERTE - {quartier.nom}',
                    'body': message,
                    'icon': '/static/images/alert.png',
                    'sound': 'default',
                    'click_action': '/pages/dechets/index.html'
                },
                'data': {
                    'quartier_id': quartier_id,
                    'type': 'alerte_urgente',
                    'message': message
                }
            }
            
            requests.post('https://fcm.googleapis.com/fcm/send', json=payload, headers=headers)
            
            return True
        except Exception as e:
            print(f"Erreur envoi alerte: {e}")
            return False

class VoiceNotificationService:
    """Service de notifications vocales pour les zones avec faible alphabétisation"""
    
    @staticmethod
    def envoyer_notification_vocale(telephone, message):
        """
        Envoie une notification vocale (appel automatisé)
        Via Twilio Voice ou service équivalent
        """
        twilio_sid = getattr(settings, 'TWILIO_ACCOUNT_SID', '')
        twilio_token = getattr(settings, 'TWILIO_AUTH_TOKEN', '')
        twilio_phone = getattr(settings, 'TWILIO_PHONE_NUMBER', '')
        
        if not all([twilio_sid, twilio_token, twilio_phone]):
            return False
        
        client = Client(twilio_sid, twilio_token)
        
        # URL vers un fichier audio ou TwiML
        twiml_url = f"{settings.SITE_URL}/api/dechets/voice/twiml/?message={message}"
        
        try:
            call = client.calls.create(
                url=twiml_url,
                to=telephone,
                from_=twilio_phone
            )
            return call.sid
        except Exception as e:
            print(f"Erreur appel vocal: {e}")
            return None

class USSDService:
    """
    Service USSD pour les citoyens sans smartphone
    Numéro court: *123#
    """
    
    @staticmethod
    def traiter_requete_ussd(session_id, phone_number, text):
        """
        Traite une requête USSD
        Format: *123# pour menu principal
        """
        if not text:
            # Menu principal
            response = "CON Bienvenue sur Bot-Makak Propre\n"
            response += "1. Signaler un bac plein\n"
            response += "2. Demander enlèvement encombrant\n"
            response += "3. Prochain jour de collecte\n"
            response += "4. Info tri déchets\n"
            response += "0. Quitter"
            return response
        
        if text == "1":
            # Signalement
            return "CON Entrez le code du bac (ou description du lieu):"
        
        elif text.startswith("1*"):
            code = text.split("*")[1]
            # Enregistrer le signalement
            from .models import Signalement
            Signalement.objects.create(
                type_signalement='bac_plein',
                adresse_description=f"Signalement USSD - Bac {code}",
                nom_citoyen=f"Citoyen {phone_number}",
                telephone=phone_number,
                statut='en_attente'
            )
            return "END ✅ Signalement enregistré. Nos équipes interviendront rapidement."
        
        elif text == "2":
            return "CON Type d'encombrant:\n1. Meuble\n2. Électroménager\n3. Matelas\n4. Autre"
        
        elif text.startswith("2*"):
            types = {'1': 'meuble', '2': 'electromenager', '3': 'matelas', '4': 'autre'}
            choix = text.split("*")[1]
            from .models import DemandeEncombrant
            # Créer demande sans utilisateur connecté
            DemandeEncombrant.objects.create(
                type_encombrant=types.get(choix),
                description=f"Demande USSD - {types.get(choix)}",
                nom_citoyen=f"Citoyen {phone_number}",
                telephone=phone_number,
                statut='en_attente'
            )
            return "END ✅ Demande enregistrée. Un agent vous contactera."
        
        elif text == "3":
            # Prochaine collecte
            return "CON Entrez le nom de votre quartier:"
        
        elif text.startswith("3*"):
            quartier = text.split("*")[1]
            # Chercher le prochain jour de collecte
            return f"END 📅 Prochaine collecte à {quartier}: mercredi 7h"
        
        elif text == "4":
            return "END ♻️ INFOS TRI:\n- Vert: déchets organiques\n- Jaune: recyclables\n- Noir: non recyclables\nwww.botmakak-propre.cm/tri"
        
        return "END Option invalide"