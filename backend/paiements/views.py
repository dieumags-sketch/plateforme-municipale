# backend/apps/paiements/views.py
# ============================================
# VERSION CORRIGÉE : ACCÈS UNIQUEMENT AUX UTILISATEURS CONNECTÉS
# ============================================

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # ✅ UNIQUEMENT IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Sum, Count
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.http import FileResponse, HttpResponseNotFound
from .models import (
    ConfigurationPaiement, TransactionPaiement, PortefeuilleCitoyen,
    JournalPaiement, RecuPaiement
)
from .serializers import (
    ConfigurationPaiementSerializer, TransactionPaiementListSerializer,
    TransactionPaiementDetailSerializer, InitierPaiementSerializer,
    ConfirmerPaiementSerializer, PortefeuilleSerializer, RechargerPortefeuilleSerializer,
    UtiliserPortefeuilleSerializer  # AJOUTÉ pour éviter l'erreur
)
from .mobile_money import MTNMoneyAPI, OrangeMoneyAPI, VirementAPI
import secrets
import qrcode
from io import BytesIO


# ============================================
# CONFIGURATION DES PAIEMENTS - ADMIN UNIQUEMENT
# ============================================

class ConfigurationPaiementViewSet(viewsets.ModelViewSet):
    """Configuration des modes de paiement - Admin uniquement"""
    queryset = ConfigurationPaiement.objects.all()
    serializer_class = ConfigurationPaiementSerializer
    permission_classes = [IsAuthenticated]  # ✅ MODIFIÉ (était IsAdminUser)
    
    def get_permissions(self):
        """
        Surcharge pour vérifier le rôle admin
        """
        if self.request.user.is_staff or getattr(self.request.user, 'role', '') == 'admin':
            return [IsAuthenticated()]
        return [IsAuthenticated()]  # La vérification se fait dans la méthode
    
    def dispatch(self, request, *args, **kwargs):
        """Vérification admin avant toute action"""
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'admin'):
            return Response(
                {'error': 'Accès réservé aux administrateurs'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().dispatch(request, *args, **kwargs)
    
    filter_backends = [filters.SearchFilter]
    search_fields = ['mode', 'nom']


# ============================================
# TRANSACTIONS DE PAIEMENT - PROTÉGÉ
# ============================================

class TransactionPaiementViewSet(viewsets.ModelViewSet):
    """Gestion des transactions de paiement - Accessible uniquement aux utilisateurs connectés"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference', 'numero_transaction']
    ordering_fields = ['date_creation', 'montant_total']
    ordering = ['-date_creation']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return TransactionPaiementDetailSerializer
        return TransactionPaiementListSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') in ['admin']:
            return TransactionPaiement.objects.all()
        return TransactionPaiement.objects.filter(utilisateur=user)
    
    @action(detail=False, methods=['post'])
    def initier(self, request):
        """Initier un paiement"""
        serializer = InitierPaiementSerializer(data=request.data)
        if serializer.is_valid():
            montant = serializer.validated_data['montant']
            mode = serializer.validated_data['mode']
            telephone = serializer.validated_data.get('telephone', '')
            module_source = serializer.validated_data['module_source']
            source_id = serializer.validated_data.get('source_id', '')
            description = serializer.validated_data.get('description', '')
            
            # Vérifier le montant minimum
            try:
                config = ConfigurationPaiement.objects.get(mode=mode, est_actif=True)
                if montant < config.montant_min:
                    return Response({
                        'error': f'Montant minimum: {config.montant_min} FCFA'
                    }, status=status.HTTP_400_BAD_REQUEST)
                if montant > config.montant_max:
                    return Response({
                        'error': f'Montant maximum: {config.montant_max} FCFA'
                    }, status=status.HTTP_400_BAD_REQUEST)
            except ConfigurationPaiement.DoesNotExist:
                pass
            
            # Créer la transaction
            transaction = TransactionPaiement.objects.create(
                utilisateur=request.user,
                montant_net=montant,
                mode=mode,
                telephone=telephone,
                module_source=module_source,
                source_id=source_id,
                description=description,
                ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            # Calculer frais et taxe
            transaction.frais = transaction.calculer_frais()
            transaction.taxe = transaction.calculer_taxe()
            transaction.montant_total = transaction.montant_net + transaction.frais + transaction.taxe
            transaction.save()
            
            # Journal
            JournalPaiement.objects.create(
                transaction=transaction,
                action='initier',
                nouveau_statut='initie',
                message=f'Paiement de {montant} FCFA initié en {mode}',
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            # Si Mobile Money, initier le paiement
            if mode in ['mtn', 'orange']:
                if not telephone:
                    return Response({
                        'error': 'Numéro de téléphone requis pour le paiement Mobile Money'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    if mode == 'mtn':
                        api = MTNMoneyAPI()
                        result = api.initier_paiement(telephone, float(transaction.montant_total), transaction.reference)
                    else:
                        api = OrangeMoneyAPI()
                        result = api.initier_paiement(telephone, float(transaction.montant_total), transaction.reference)
                    
                    if result.get('success'):
                        transaction.statut = 'en_attente'
                        transaction.code_validation = result.get('code', '')
                        transaction.save(update_fields=['statut', 'code_validation'])
                        
                        return Response({
                            'transaction_id': str(transaction.id),
                            'reference': transaction.reference,
                            'montant_total': float(transaction.montant_total),
                            'mode': mode,
                            'code_envoye': True,
                            'message': result.get('message', 'Code de validation envoyé')
                        }, status=status.HTTP_201_CREATED)
                    else:
                        transaction.statut = 'echoue'
                        transaction.save(update_fields=['statut'])
                        return Response({
                            'error': result.get('message', 'Erreur lors de l\'initiation du paiement')
                        }, status=status.HTTP_400_BAD_REQUEST)
                        
                except Exception as e:
                    transaction.statut = 'echoue'
                    transaction.save(update_fields=['statut'])
                    return Response({
                        'error': f'Erreur technique: {str(e)}'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Pour virement ou cash
            return Response({
                'transaction_id': str(transaction.id),
                'reference': transaction.reference,
                'montant_total': float(transaction.montant_total),
                'mode': mode,
                'message': 'Paiement en attente de confirmation'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def confirmer(self, request):
        """Confirmer un paiement"""
        serializer = ConfirmerPaiementSerializer(data=request.data)
        if serializer.is_valid():
            reference = serializer.validated_data['reference']
            code = serializer.validated_data.get('code', '')
            preuve_virement = serializer.validated_data.get('preuve_virement')
            
            transaction = get_object_or_404(TransactionPaiement, reference=reference)
            
            # Vérifier les permissions
            if transaction.utilisateur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
                return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
            
            # Vérifier si déjà confirmé
            if transaction.statut == 'confirme':
                return Response({'message': 'Paiement déjà confirmé'}, status=status.HTTP_200_OK)
            
            # Mobile Money
            if transaction.mode in ['mtn', 'orange']:
                if not code:
                    return Response({'error': 'Code de validation requis'}, status=status.HTTP_400_BAD_REQUEST)
                
                try:
                    if transaction.mode == 'mtn':
                        api = MTNMoneyAPI()
                        result = api.confirmer_paiement(reference, code)
                    else:
                        api = OrangeMoneyAPI()
                        result = api.confirmer_paiement(reference, code)
                    
                    if result.get('success'):
                        transaction.statut = 'confirme'
                        transaction.numero_transaction = result.get('transaction_id', '')
                        transaction.date_confirmation = timezone.now()
                        transaction.save(update_fields=['statut', 'numero_transaction', 'date_confirmation'])
                        
                        # Générer le reçu
                        try:
                            generer_recu(transaction)
                        except Exception as e:
                            print(f"Erreur génération reçu: {e}")
                        
                        # Mettre à jour le module source
                        try:
                            mettre_a_jour_module_source(transaction)
                        except Exception as e:
                            print(f"Erreur mise à jour module source: {e}")
                        
                        # Envoyer notification
                        try:
                            envoyer_notification_paiement(transaction)
                        except Exception as e:
                            print(f"Erreur envoi notification: {e}")
                        
                        # Journal
                        JournalPaiement.objects.create(
                            transaction=transaction,
                            action='confirmer',
                            ancien_statut='en_attente',
                            nouveau_statut='confirme',
                            message='Paiement confirmé avec succès',
                            ip_address=request.META.get('REMOTE_ADDR', '')
                        )
                        
                        return Response({
                            'message': 'Paiement confirmé avec succès',
                            'recu_url': transaction.recu.fichier_pdf.url if hasattr(transaction, 'recu') and transaction.recu and transaction.recu.fichier_pdf else None
                        })
                    else:
                        transaction.statut = 'echoue'
                        transaction.save(update_fields=['statut'])
                        return Response({'error': result.get('message', 'Code invalide ou expiré')}, status=status.HTTP_400_BAD_REQUEST)
                        
                except Exception as e:
                    return Response({'error': f'Erreur de confirmation: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            # Virement bancaire
            elif transaction.mode == 'virement':
                if preuve_virement:
                    transaction.preuve_virement = preuve_virement
                    transaction.save(update_fields=['preuve_virement'])
                
                transaction.statut = 'en_attente'
                transaction.save(update_fields=['statut'])
                
                JournalPaiement.objects.create(
                    transaction=transaction,
                    action='confirmer',
                    ancien_statut='initie',
                    nouveau_statut='en_attente',
                    message='Preuve de virement reçue, en attente de validation',
                    ip_address=request.META.get('REMOTE_ADDR', '')
                )
                
                return Response({
                    'message': 'Preuve de virement reçue. En attente de validation par nos services.'
                })
            
            # Paiement en espèces
            elif transaction.mode == 'cash':
                transaction.statut = 'confirme'
                transaction.date_confirmation = timezone.now()
                transaction.save(update_fields=['statut', 'date_confirmation'])
                
                try:
                    generer_recu(transaction)
                except Exception as e:
                    print(f"Erreur génération reçu: {e}")
                
                return Response({'message': 'Paiement en espèces enregistré avec succès'})
            
            return Response({'error': 'Mode de paiement non supporté'}, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def recu(self, request, pk=None):
        """Télécharger le reçu PDF"""
        transaction = self.get_object()
        
        # Vérifier permissions
        if transaction.utilisateur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier statut
        if transaction.statut != 'confirme':
            return Response({'error': 'Reçu disponible uniquement pour les paiements confirmés'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si reçu existe
        if not hasattr(transaction, 'recu') or not transaction.recu or not transaction.recu.fichier_pdf:
            try:
                generer_recu(transaction)
                transaction.refresh_from_db()
            except Exception as e:
                return Response({'error': f'Erreur génération reçu: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if transaction.recu and transaction.recu.fichier_pdf:
            return FileResponse(
                transaction.recu.fichier_pdf.open('rb'),
                content_type='application/pdf',
                filename=f"recu_{transaction.reference}.pdf"
            )
        
        return Response({'error': 'Reçu non disponible'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une transaction en attente"""
        transaction = self.get_object()
        
        # Vérifier permissions
        if transaction.utilisateur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier si annulable
        if transaction.statut not in ['initie', 'en_attente']:
            return Response({
                'error': f'Transaction non annulable (statut actuel: {transaction.statut})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        ancien_statut = transaction.statut
        transaction.statut = 'annule'
        transaction.save(update_fields=['statut'])
        
        JournalPaiement.objects.create(
            transaction=transaction,
            action='annuler',
            ancien_statut=ancien_statut,
            nouveau_statut='annule',
            message='Transaction annulée par l\'utilisateur',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({'message': 'Transaction annulée avec succès'})
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques des paiements (Admin uniquement)"""
        user = request.user
        if not (user.is_staff or getattr(user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        # Statistiques globales
        total_transactions = TransactionPaiement.objects.count()
        total_confirmees = TransactionPaiement.objects.filter(statut='confirme').count()
        total_montant = TransactionPaiement.objects.filter(
            statut='confirme'
        ).aggregate(total=Sum('montant_total'))['total'] or 0
        
        # Par mode de paiement
        par_mode = list(TransactionPaiement.objects.values('mode').annotate(
            count=Count('id'),
            total=Sum('montant_total')
        ))
        
        # Par statut
        par_statut = list(TransactionPaiement.objects.values('statut').annotate(count=Count('id')))
        
        # Par module source
        par_module = list(TransactionPaiement.objects.values('module_source').annotate(
            count=Count('id'),
            total=Sum('montant_total')
        ))
        
        # Transactions aujourd'hui
        aujourd_hui = TransactionPaiement.objects.filter(
            date_creation__date=timezone.now().date()
        ).count()
        
        # Montant aujourd'hui
        montant_aujourd_hui = TransactionPaiement.objects.filter(
            date_creation__date=timezone.now().date(),
            statut='confirme'
        ).aggregate(total=Sum('montant_total'))['total'] or 0
        
        # Transactions ce mois
        debut_mois = timezone.now().replace(day=1, hour=0, minute=0, second=0)
        transactions_mois = TransactionPaiement.objects.filter(
            date_creation__gte=debut_mois,
            statut='confirme'
        ).count()
        montant_mois = TransactionPaiement.objects.filter(
            date_creation__gte=debut_mois,
            statut='confirme'
        ).aggregate(total=Sum('montant_total'))['total'] or 0
        
        return Response({
            'total_transactions': total_transactions,
            'total_confirmees': total_confirmees,
            'total_montant': float(total_montant),
            'par_mode': par_mode,
            'par_statut': par_statut,
            'par_module': par_module,
            'aujourd_hui': {
                'count': aujourd_hui,
                'montant': float(montant_aujourd_hui)
            },
            'ce_mois': {
                'count': transactions_mois,
                'montant': float(montant_mois)
            }
        })
    
    @action(detail=True, methods=['post'])
    def valider_virement(self, request, pk=None):
        """Valider un virement bancaire (Admin uniquement)"""
        transaction = self.get_object()
        
        # Vérifier permissions admin
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier si c'est un virement
        if transaction.mode != 'virement':
            return Response({'error': 'Cette action est réservée aux virements bancaires'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier statut
        if transaction.statut != 'en_attente':
            return Response({
                'error': f'Transaction non valable (statut: {transaction.statut})'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        action = request.data.get('action', 'valider')
        commentaire = request.data.get('commentaire', '')
        
        if action == 'valider':
            transaction.statut = 'confirme'
            transaction.date_confirmation = timezone.now()
            transaction.save(update_fields=['statut', 'date_confirmation'])
            
            # Générer reçu
            generer_recu(transaction)
            
            # Mettre à jour module source
            mettre_a_jour_module_source(transaction)
            
            # Notifier utilisateur
            envoyer_notification_paiement(transaction)
            
            message = 'Virement validé avec succès'
        else:
            transaction.statut = 'echoue'
            transaction.save(update_fields=['statut'])
            message = 'Virement rejeté'
        
        JournalPaiement.objects.create(
            transaction=transaction,
            action='valider_virement',
            ancien_statut='en_attente',
            nouveau_statut=transaction.statut,
            message=f'{message}. {commentaire}',
            ip_address=request.META.get('REMOTE_ADDR', '')
        )
        
        return Response({'message': message})
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================
# PORTEFEUILLE CITOYEN - PROTÉGÉ
# ============================================

class PortefeuilleViewSet(viewsets.GenericViewSet):
    """Gestion du portefeuille citoyen - Accessible uniquement aux utilisateurs connectés"""
    permission_classes = [IsAuthenticated]
    serializer_class = PortefeuilleSerializer
    
    def get_queryset(self):
        return PortefeuilleCitoyen.objects.filter(utilisateur=self.request.user)
    
    def list(self, request):
        """Obtenir le solde du portefeuille"""
        portefeuille, created = PortefeuilleCitoyen.objects.get_or_create(
            utilisateur=request.user,
            defaults={'solde': 0}
        )
        serializer = self.get_serializer(portefeuille)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def recharger(self, request):
        """Recharger le portefeuille"""
        serializer = RechargerPortefeuilleSerializer(data=request.data)
        if serializer.is_valid():
            montant = serializer.validated_data['montant']
            
            # Créer une transaction de recharge
            transaction = TransactionPaiement.objects.create(
                utilisateur=request.user,
                montant_net=montant,
                mode='portefeuille',
                module_source='portefeuille',
                description=f'Recharge portefeuille de {montant} FCFA',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            # Calculer frais (si applicable)
            transaction.frais = transaction.calculer_frais()
            transaction.taxe = transaction.calculer_taxe()
            transaction.montant_total = transaction.montant_net + transaction.frais + transaction.taxe
            transaction.save()
            
            return Response({
                'transaction_id': str(transaction.id),
                'reference': transaction.reference,
                'montant': float(montant),
                'frais': float(transaction.frais),
                'total': float(transaction.montant_total),
                'message': 'Redirection vers le paiement en cours'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def utiliser(self, request):
        """Utiliser le portefeuille pour payer"""
        serializer = UtiliserPortefeuilleSerializer(data=request.data)
        if serializer.is_valid():
            montant = serializer.validated_data['montant']
            module_source = serializer.validated_data['module_source']
            source_id = serializer.validated_data.get('source_id', '')
            
            portefeuille, created = PortefeuilleCitoyen.objects.get_or_create(
                utilisateur=request.user,
                defaults={'solde': 0}
            )
            
            # Vérifier le solde
            if portefeuille.solde < montant:
                return Response({
                    'error': 'Solde insuffisant',
                    'solde_actuel': float(portefeuille.solde),
                    'montant_requis': float(montant)
                }, status=status.HTTP_400_BAD_REQUEST)
            
            # Débiter le portefeuille
            portefeuille.solde -= montant
            portefeuille.save(update_fields=['solde'])
            
            # Créer la transaction
            transaction = TransactionPaiement.objects.create(
                utilisateur=request.user,
                montant_net=montant,
                mode='portefeuille',
                module_source=module_source,
                source_id=source_id,
                statut='confirme',
                date_confirmation=timezone.now(),
                description=f'Paiement via portefeuille pour {module_source}',
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            
            # Mettre à jour le module source
            mettre_a_jour_module_source(transaction)
            
            return Response({
                'message': 'Paiement effectué avec succès',
                'nouveau_solde': float(portefeuille.solde),
                'transaction_id': str(transaction.id),
                'reference': transaction.reference
            })
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['get'])
    def historique(self, request):
        """Historique des transactions du portefeuille"""
        transactions = TransactionPaiement.objects.filter(
            utilisateur=request.user,
            mode='portefeuille'
        ).order_by('-date_creation')[:50]
        
        serializer = TransactionPaiementListSerializer(transactions, many=True)
        return Response(serializer.data)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# ============================================
# FONCTIONS UTILITAIRES (inchangées)
# ============================================

def generer_recu(transaction):
    """Génère un reçu PDF pour la transaction"""
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    from reportlab.lib.units import cm
    from io import BytesIO
    
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)
    
    styles = getSampleStyleSheet()
    
    style_titre = ParagraphStyle(
        'Titre',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=1,
        textColor=colors.HexColor('#1a237e'),
        spaceAfter=20
    )
    
    style_soustitre = ParagraphStyle(
        'Soustitre',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=1,
        spaceAfter=15
    )
    
    style_normal = ParagraphStyle(
        'Normal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=5
    )
    
    style_bold = ParagraphStyle(
        'Bold',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=5,
        fontName='Helvetica-Bold'
    )
    
    story = []
    
    # En-tête
    story.append(Paragraph("RÉPUBLIQUE DU CAMEROUN", style_titre))
    story.append(Paragraph("Paix - Travail - Patrie", style_soustitre))
    story.append(Spacer(1, 10))
    story.append(Paragraph("MAIRIE DE BOT-MAKAK", style_titre))
    story.append(Paragraph("Service des Paiements", style_soustitre))
    story.append(Spacer(1, 20))
    
    story.append(Paragraph("REÇU DE PAIEMENT", style_titre))
    story.append(Spacer(1, 20))
    
    # Infos transaction
    story.append(Paragraph(f"<b>N° Reçu:</b> REC-{transaction.reference}", style_normal))
    story.append(Paragraph(f"<b>Date:</b> {(transaction.date_confirmation or timezone.now()).strftime('%d/%m/%Y à %H:%M')}", style_normal))
    story.append(Paragraph(f"<b>Citoyen:</b> {transaction.utilisateur.get_full_name() or transaction.utilisateur.username}", style_normal))
    story.append(Paragraph(f"<b>Email:</b> {transaction.utilisateur.email}", style_normal))
    if transaction.utilisateur.telephone:
        story.append(Paragraph(f"<b>Téléphone:</b> {transaction.utilisateur.telephone}", style_normal))
    
    story.append(Spacer(1, 20))
    
    # Détails paiement
    story.append(Paragraph("<b>DÉTAIL DU PAIEMENT</b>", style_bold))
    story.append(Spacer(1, 5))
    
    story.append(Paragraph(f"Référence transaction: {transaction.reference}", style_normal))
    story.append(Paragraph(f"Mode de paiement: {transaction.get_mode_display()}", style_normal))
    
    if transaction.numero_transaction:
        story.append(Paragraph(f"Numéro transaction: {transaction.numero_transaction}", style_normal))
    
    story.append(Spacer(1, 10))
    
    # Tableau des montants
    montants_data = [
        ["Montant net", f"{transaction.montant_net:,.0f} FCFA"],
        ["Frais de service", f"{transaction.frais:,.0f} FCFA"],
        ["Taxes", f"{transaction.taxe:,.0f} FCFA"],
        ["<b>TOTAL PAYÉ</b>", f"<b>{transaction.montant_total:,.0f} FCFA</b>"],
    ]
    
    montants_table = Table(montants_data, colWidths=[8*cm, 5*cm])
    montants_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
    ]))
    story.append(montants_table)
    
    story.append(Spacer(1, 20))
    
    # Module source
    if transaction.module_source:
        modules = {
            'etat_civil': "État Civil",
            'activites': "Activités Municipales",
            'dechets': "Gestion des Déchets",
            'archives': "Archives Municipales"
        }
        module_name = modules.get(transaction.module_source, transaction.module_source)
        story.append(Paragraph(f"<b>Service concerné:</b> {module_name}", style_normal))
        
        if transaction.description:
            story.append(Paragraph(f"<b>Description:</b> {transaction.description}", style_normal))
    
    story.append(Spacer(1, 30))
    
    # Signatures
    story.append(Paragraph("Cachet et signature de la Mairie", style_normal))
    story.append(Spacer(1, 20))
    story.append(Paragraph("_________________________", style_normal))
    story.append(Paragraph("Le Receveur Municipal", style_normal))
    
    # Mention légale
    story.append(Spacer(1, 20))
    story.append(Paragraph(
        "<i>Ce reçu fait foi du paiement effectué. Merci de le conserver.</i>",
        ParagraphStyle('Italic', parent=styles['Normal'], textColor=colors.grey, fontSize=8)
    ))
    
    doc.build(story)
    buffer.seek(0)
    
    # Sauvegarder le reçu
    numero_recu = f"REC-{transaction.reference}"
    recu, created = RecuPaiement.objects.get_or_create(
        transaction=transaction,
        defaults={'numero_recu': numero_recu}
    )
    recu.fichier_pdf.save(f"{numero_recu}.pdf", ContentFile(buffer.getvalue()), save=True)
    return recu


def envoyer_notification_paiement(transaction):
    """Envoie une notification après paiement"""
    from django.core.mail import send_mail
    
    # Email
    if transaction.utilisateur.email:
        try:
            send_mail(
                subject=f"Confirmation de paiement - {transaction.reference}",
                message=f"""
Bonjour {transaction.utilisateur.get_full_name() or transaction.utilisateur.username},

Votre paiement a été confirmé avec succès.

📋 Détails du paiement:
• Référence: {transaction.reference}
• Montant: {transaction.montant_total:,.0f} FCFA
• Date: {(transaction.date_confirmation or timezone.now()).strftime('%d/%m/%Y à %H:%M')}
• Mode: {transaction.get_mode_display()}

Vous pouvez télécharger votre reçu depuis votre espace citoyen.

Merci de votre confiance.

---
Mairie de Bot-Makak
Service des Paiements
Email: paiements@botmatmakak.net
Tel: +237 XXX XXX XXX
                """,
                from_email='paiements@botmatmakak.net',
                recipient_list=[transaction.utilisateur.email],
                fail_silently=True
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")
    
    # Notification dans la base de données
    try:
        from apps.notifications.models import Notification
        Notification.objects.create(
            utilisateur=transaction.utilisateur,
            titre="Paiement confirmé",
            message=f"Votre paiement de {transaction.montant_total:,.0f} FCFA (réf: {transaction.reference}) a été confirmé.",
            type_notification='paiement',
            lien=f"/paiements/recu/{transaction.id}/"
        )
    except Exception as e:
        print(f"Erreur création notification: {e}")


def mettre_a_jour_module_source(transaction):
    """Met à jour le module source après paiement"""
    if not transaction.module_source or not transaction.source_id:
        return
    
    try:
        # État Civil
        if transaction.module_source == 'etat_civil':
            from apps.etat_civil.models import DemandeActe
            demande = DemandeActe.objects.filter(id=transaction.source_id).first()
            if demande:
                demande.paiement_effectue = True
                demande.reference_paiement = transaction.reference
                demande.date_paiement = transaction.date_confirmation or timezone.now()
                demande.save(update_fields=['paiement_effectue', 'reference_paiement', 'date_paiement'])
                
                if demande.statut == 'en_attente':
                    demande.statut = 'en_cours'
                    demande.save(update_fields=['statut'])
        
        # Activités
        elif transaction.module_source == 'activites':
            from apps.activites.models import InscriptionActivite
            inscription = InscriptionActivite.objects.filter(id=transaction.source_id).first()
            if inscription:
                inscription.paiement_effectue = True
                inscription.reference_paiement = transaction.reference
                inscription.date_paiement = transaction.date_confirmation or timezone.now()
                inscription.statut = 'confirme'
                inscription.save(update_fields=['paiement_effectue', 'reference_paiement', 'date_paiement', 'statut'])
        
        # Déchets
        elif transaction.module_source == 'dechets':
            from apps.dechets.models import DemandeEncombrant
            demande = DemandeEncombrant.objects.filter(id=transaction.source_id).first()
            if demande:
                demande.paiement_effectue = True
                demande.save(update_fields=['paiement_effectue'])
        
        # Archives
        elif transaction.module_source == 'archives':
            from apps.archives.models import DemandeAccesArchive
            demande = DemandeAccesArchive.objects.filter(id=transaction.source_id).first()
            if demande:
                demande.paiement_effectue = True
                demande.reference_paiement = transaction.reference
                demande.date_paiement = transaction.date_confirmation or timezone.now()
                demande.save(update_fields=['paiement_effectue', 'reference_paiement', 'date_paiement'])
                
    except Exception as e:
        print(f"Erreur mise à jour module source {transaction.module_source}: {e}")