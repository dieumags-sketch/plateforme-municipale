# backend/apps/etat_civil/views.py
# ============================================
# VERSION CORRIGÉE : ACCÈS UNIQUEMENT AUX UTILISATEURS CONNECTÉS
# ============================================

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # ✅ UNIQUEMENT IsAuthenticated (supprimé IsAdminUser, AllowAny)
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q, Count
from django.core.mail import send_mail
from django.core.files.base import ContentFile
from django.http import FileResponse, HttpResponseNotFound
from .models import (
    Region, Departement, Arrondissement, DistrictSante,
    DemandeActe, HistoriqueStatut, NotificationActe
)
from .serializers import (
    RegionSerializer, DepartementSerializer, ArrondissementSerializer,
    DistrictSanteSerializer, DemandeActeSerializer,
    DemandeNaissanceSerializer, DemandeMariageSerializer, DemandeDecesSerializer,
    DemandeReconnaissanceSerializer, DemandeAdoptionSerializer,
    ValidationCitoyenSerializer, TraitementAgentSerializer,
    HistoriqueStatutSerializer, NotificationActeSerializer
)
from .permissions import EstAgentOuAdmin  # À créer si nécessaire


# ============================================
# RÉGIONS - PROTÉGÉ
# ============================================

class RegionViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des régions du Cameroun - Accessible uniquement aux utilisateurs connectés"""
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    permission_classes = [IsAuthenticated]
    
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom', 'code']


# ============================================
# DÉPARTEMENTS - PROTÉGÉ
# ============================================

class DepartementViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des départements - Accessible uniquement aux utilisateurs connectés"""
    queryset = Departement.objects.all()
    serializer_class = DepartementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        region_id = self.request.query_params.get('region')
        if region_id:
            queryset = queryset.filter(region_id=region_id)
        return queryset


# ============================================
# ARRONDISSEMENTS - PROTÉGÉ
# ============================================

class ArrondissementViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des arrondissements - Accessible uniquement aux utilisateurs connectés"""
    queryset = Arrondissement.objects.all()
    serializer_class = ArrondissementSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        departement_id = self.request.query_params.get('departement')
        if departement_id:
            queryset = queryset.filter(departement_id=departement_id)
        return queryset


# ============================================
# DISTRICTS DE SANTÉ - PROTÉGÉ
# ============================================

class DistrictSanteViewSet(viewsets.ReadOnlyModelViewSet):
    """Gestion des districts de santé - Accessible uniquement aux utilisateurs connectés"""
    queryset = DistrictSante.objects.all()
    serializer_class = DistrictSanteSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter]
    search_fields = ['nom']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        arrondissement_id = self.request.query_params.get('arrondissement')
        if arrondissement_id:
            queryset = queryset.filter(arrondissement_id=arrondissement_id)
        return queryset


# ============================================
# DEMANDES D'ACTES - PROTÉGÉ
# ============================================

class DemandeActeViewSet(viewsets.ModelViewSet):
    """Gestion des demandes d'actes d'état civil - Accessible uniquement aux utilisateurs connectés"""
    serializer_class = DemandeActeSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['reference']
    ordering_fields = ['date_demande', 'statut']
    ordering = ['-date_demande']
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff or getattr(user, 'role', '') in ['admin', 'agent']:
            return DemandeActe.objects.all()
        return DemandeActe.objects.filter(demandeur=user)
    
    def perform_create(self, serializer):
        """Création manuelle d'une demande (admin uniquement)"""
        if not self.request.user.is_staff:
            raise PermissionError("Seuls les administrateurs peuvent créer des demandes manuellement")
        serializer.save()
    
    # ============================================
    # DÉCLARATIONS PAR TYPE D'ACTE
    # ============================================
    
    @action(detail=False, methods=['post'])
    def naissance(self, request):
        """Déclaration de naissance"""
        serializer = DemandeNaissanceSerializer(data=request.data)
        if serializer.is_valid():
            demande = DemandeActe.objects.create(
                type_acte='naissance',
                demandeur=request.user,
                data_acte=serializer.validated_data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            tarif = demande.calculer_tarif()
            demande.tarif_applique = tarif
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut='brouillon',
                nouveau_statut='en_attente',
                commentaire='Déclaration de naissance créée',
                utilisateur=request.user
            )
            
            NotificationActe.objects.create(
                demande=demande,
                titre='Demande enregistrée',
                message=f'Votre demande d\'acte de naissance a été enregistrée. Référence: {demande.reference}'
            )
            
            return Response({
                'id': str(demande.id),
                'reference': demande.reference,
                'tarif': float(tarif),
                'message': 'Demande enregistrée avec succès'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def mariage(self, request):
        """Déclaration de mariage"""
        serializer = DemandeMariageSerializer(data=request.data)
        if serializer.is_valid():
            demande = DemandeActe.objects.create(
                type_acte='mariage',
                demandeur=request.user,
                data_acte=serializer.validated_data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            tarif = demande.calculer_tarif()
            demande.tarif_applique = tarif
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut='brouillon',
                nouveau_statut='en_attente',
                commentaire='Déclaration de mariage créée',
                utilisateur=request.user
            )
            
            return Response({
                'id': str(demande.id),
                'reference': demande.reference,
                'tarif': float(tarif),
                'message': 'Demande de mariage enregistrée'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def deces(self, request):
        """Déclaration de décès"""
        serializer = DemandeDecesSerializer(data=request.data)
        if serializer.is_valid():
            demande = DemandeActe.objects.create(
                type_acte='deces',
                demandeur=request.user,
                data_acte=serializer.validated_data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            tarif = demande.calculer_tarif()
            demande.tarif_applique = tarif
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut='brouillon',
                nouveau_statut='en_attente',
                commentaire='Déclaration de décès créée',
                utilisateur=request.user
            )
            
            return Response({
                'id': str(demande.id),
                'reference': demande.reference,
                'tarif': float(tarif),
                'message': 'Demande de décès enregistrée'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def reconnaissance(self, request):
        """Déclaration de reconnaissance"""
        serializer = DemandeReconnaissanceSerializer(data=request.data)
        if serializer.is_valid():
            demande = DemandeActe.objects.create(
                type_acte='reconnaissance',
                demandeur=request.user,
                data_acte=serializer.validated_data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            tarif = demande.calculer_tarif()
            demande.tarif_applique = tarif
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut='brouillon',
                nouveau_statut='en_attente',
                commentaire='Déclaration de reconnaissance créée',
                utilisateur=request.user
            )
            
            return Response({
                'id': str(demande.id),
                'reference': demande.reference,
                'tarif': float(tarif),
                'message': 'Demande de reconnaissance enregistrée'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def adoption(self, request):
        """Demande d'adoption"""
        serializer = DemandeAdoptionSerializer(data=request.data)
        if serializer.is_valid():
            demande = DemandeActe.objects.create(
                type_acte='adoption',
                demandeur=request.user,
                data_acte=serializer.validated_data,
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
            )
            tarif = demande.calculer_tarif()
            demande.tarif_applique = tarif
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut='brouillon',
                nouveau_statut='en_attente',
                commentaire='Demande d\'adoption créée',
                utilisateur=request.user
            )
            
            return Response({
                'id': str(demande.id),
                'reference': demande.reference,
                'tarif': float(tarif),
                'message': 'Demande d\'adoption enregistrée'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    # ============================================
    # WORKFLOW DE TRAITEMENT
    # ============================================
    
    @action(detail=True, methods=['post'])
    def valider_citoyen(self, request, pk=None):
        """Validation par le citoyen"""
        demande = self.get_object()
        
        if demande.demandeur != request.user:
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.statut != 'valide_agent':
            return Response(
                {'error': f'Demande non validée par l\'agent (statut actuel: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = ValidationCitoyenSerializer(data=request.data)
        if serializer.is_valid():
            if serializer.validated_data['valide']:
                demande.statut = 'valide_citoyen'
                demande.date_validation_citoyen = timezone.now()
                message = 'Informations validées par le citoyen'
            else:
                demande.statut = 'brouillon'
                message = 'Le citoyen demande des modifications'
            
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut='valide_agent',
                nouveau_statut=demande.statut,
                commentaire=message,
                utilisateur=request.user
            )
            
            NotificationActe.objects.create(
                demande=demande,
                titre='Validation citoyenne',
                message=f'Vous avez {message.lower()}'
            )
            
            return Response({'message': message})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def traiter_agent(self, request, pk=None):
        """Traitement par l'agent municipal"""
        demande = self.get_object()
        
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'agent']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        serializer = TraitementAgentSerializer(data=request.data)
        if serializer.is_valid():
            action = serializer.validated_data['action']
            commentaire = serializer.validated_data.get('commentaire', '')
            
            ancien_statut = demande.statut
            
            if action == 'valider':
                demande.statut = 'valide_agent'
                demande.agent_traitant = request.user
                demande.date_validation_agent = timezone.now()
                message = 'validée par l\'agent'
            else:
                demande.statut = 'rejete'
                demande.commentaire_rejet = commentaire
                message = 'rejetée'
            
            demande.save()
            
            HistoriqueStatut.objects.create(
                demande=demande,
                ancien_statut=ancien_statut,
                nouveau_statut=demande.statut,
                commentaire=commentaire,
                utilisateur=request.user
            )
            
            NotificationActe.objects.create(
                demande=demande,
                titre='Mise à jour de votre demande',
                message=f'Votre demande a été {message}'
            )
            
            if demande.demandeur and demande.demandeur.email:
                try:
                    send_mail(
                        subject=f"État de votre demande - {demande.reference}",
                        message=f"Bonjour,\n\nVotre demande d'acte d'état civil a été {message}.\n\nRéférence: {demande.reference}\n\nService État Civil - Commune de Bot-Makak",
                        from_email='etat-civil@botmatmakak.net',
                        recipient_list=[demande.demandeur.email],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Erreur envoi email: {e}")
            
            return Response({'message': f'Demande {message}'})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def signer(self, request, pk=None):
        """Signature par l'autorité supérieure"""
        demande = self.get_object()
        
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.statut != 'valide_citoyen':
            return Response(
                {'error': f'Demande non validée par le citoyen (statut actuel: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demande.statut = 'signe'
        demande.autorite_signataire = request.user
        demande.date_signature = timezone.now()
        demande.date_expiration_copie = timezone.now() + timezone.timedelta(days=180)
        demande.save(update_fields=['statut', 'autorite_signataire', 'date_signature', 'date_expiration_copie'])
        
        try:
            from .utils import generer_pdf_acte
            pdf_content = generer_pdf_acte(demande)
            if pdf_content:
                demande.fichier_pdf.save(f"acte_{demande.reference}.pdf", pdf_content)
            
            from .utils import generer_qr_code
            qr_content = generer_qr_code(demande)
            if qr_content:
                demande.qr_code.save(f"qr_{demande.reference}.png", qr_content)
                
            demande.save()
        except Exception as e:
            print(f"Erreur génération PDF/QR: {e}")
        
        HistoriqueStatut.objects.create(
            demande=demande,
            ancien_statut='valide_citoyen',
            nouveau_statut='signe',
            commentaire='Acte signé électroniquement',
            utilisateur=request.user
        )
        
        NotificationActe.objects.create(
            demande=demande,
            titre='Votre acte est signé !',
            message=f'Votre acte {demande.reference} a été signé et est disponible au téléchargement.'
        )
        
        if demande.demandeur and demande.demandeur.email:
            try:
                send_mail(
                    subject=f"Votre acte est prêt - {demande.reference}",
                    message=f"Bonjour,\n\nVotre acte a été signé électroniquement et est disponible dans votre espace citoyen.\n\nRéférence: {demande.reference}\n\nService État Civil - Commune de Bot-Makak",
                    from_email='etat-civil@botmatmakak.net',
                    recipient_list=[demande.demandeur.email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Erreur envoi email: {e}")
        
        pdf_url = demande.fichier_pdf.url if demande.fichier_pdf else None
        return Response({
            'message': 'Acte signé avec succès',
            'pdf_url': pdf_url
        })
    
    @action(detail=True, methods=['post'])
    def delivrer(self, request, pk=None):
        """Délivrance de l'acte"""
        demande = self.get_object()
        
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'agent']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.statut != 'signe':
            return Response(
                {'error': f'Acte non signé (statut actuel: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demande.statut = 'delivre'
        demande.date_delivrance = timezone.now()
        demande.save(update_fields=['statut', 'date_delivrance'])
        
        HistoriqueStatut.objects.create(
            demande=demande,
            ancien_statut='signe',
            nouveau_statut='delivre',
            commentaire='Acte délivré',
            utilisateur=request.user
        )
        
        NotificationActe.objects.create(
            demande=demande,
            titre='Acte disponible en mairie',
            message=f'Votre acte {demande.reference} est disponible au retrait à la mairie.'
        )
        
        return Response({'message': 'Acte délivré avec succès'})
    
    # ============================================
    # ACTIONS UTILITAIRES
    # ============================================
    
    @action(detail=True, methods=['get'])
    def historique(self, request, pk=None):
        """Historique des statuts"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'agent']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        historique = demande.historique.all()
        serializer = HistoriqueStatutSerializer(historique, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        """Télécharger le PDF"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'agent']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.statut not in ['signe', 'delivre']:
            return Response(
                {'error': f'PDF non disponible (statut: {demande.statut})'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if demande.fichier_pdf:
            return FileResponse(
                demande.fichier_pdf.open('rb'),
                content_type='application/pdf',
                filename=f"acte_{demande.reference}.pdf"
            )
        
        return Response({'error': 'PDF non disponible'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=True, methods=['get'])
    def notifications(self, request, pk=None):
        """Notifications de la demande"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'agent']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        notifications = demande.notifications.all()
        serializer = NotificationActeSerializer(notifications, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def stats(self, request):
        """Statistiques pour l'administration"""
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        stats_par_statut = {}
        for statut, _ in DemandeActe.STATUT_CHOICES:
            stats_par_statut[statut] = DemandeActe.objects.filter(statut=statut).count()
        
        stats_par_type = dict(
            DemandeActe.objects.values_list('type_acte', flat=False)
            .annotate(count=Count('id'))
        )
        
        from datetime import timedelta
        today = timezone.now().date()
        stats_mensuelles = []
        for i in range(6):
            debut_mois = today.replace(day=1) - timedelta(days=30*i)
            fin_mois = (debut_mois + timedelta(days=32)).replace(day=1)
            count = DemandeActe.objects.filter(
                date_demande__date__gte=debut_mois,
                date_demande__date__lt=fin_mois
            ).count()
            stats_mensuelles.append({
                'mois': debut_mois.strftime('%B %Y'),
                'count': count
            })
        
        return Response({
            'par_statut': stats_par_statut,
            'par_type': stats_par_type,
            'par_mois': stats_mensuelles,
            'total': DemandeActe.objects.count(),
            'en_attente': DemandeActe.objects.filter(statut='en_attente').count(),
            'valide_agent': DemandeActe.objects.filter(statut='valide_agent').count(),
            'valide_citoyen': DemandeActe.objects.filter(statut='valide_citoyen').count(),
            'signe': DemandeActe.objects.filter(statut='signe').count(),
            'rejete': DemandeActe.objects.filter(statut='rejete').count(),
            'delivre': DemandeActe.objects.filter(statut='delivre').count()
        })
    
    @action(detail=True, methods=['post'])
    def relancer(self, request, pk=None):
        """Relancer une demande en attente"""
        demande = self.get_object()
        
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.statut not in ['en_attente', 'en_cours']:
            return Response(
                {'error': f'Demande non relançable (statut: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        NotificationActe.objects.create(
            demande=demande,
            titre='Relance de votre demande',
            message='Votre demande est toujours en cours de traitement. Merci de votre patience.'
        )
        
        if demande.demandeur and demande.demandeur.email:
            try:
                send_mail(
                    subject=f"Relance - Demande {demande.reference}",
                    message=f"Bonjour,\n\nVotre demande d'acte d'état civil est toujours en cours de traitement.\n\nRéférence: {demande.reference}\n\nService État Civil - Commune de Bot-Makak",
                    from_email='etat-civil@botmatmakak.net',
                    recipient_list=[demande.demandeur.email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Erreur envoi email: {e}")
        
        return Response({'message': 'Relance envoyée avec succès'})
    
    # ============================================
    # MÉTHODE UTILITAIRE
    # ============================================
    
    def get_client_ip(self, request):
        """Récupère l'adresse IP du client"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip