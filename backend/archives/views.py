# backend/apps/archives/views.py
# ============================================
# VERSION CORRIGÉE : ACCÈS UNIQUEMENT AUX UTILISATEURS CONNECTÉS
# ============================================

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # ✅ UNIQUEMENT IsAuthenticated
from django.db.models import Q, Count
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.paginator import Paginator
from django.http import FileResponse, HttpResponseNotFound
from django.core.files.storage import default_storage
import secrets
from .models import *
from .serializers import *
import uuid


# ============================================
# ARCHIVES - PROTÉGÉ
# ============================================

class ArchiveViewSet(viewsets.ModelViewSet):
    """ViewSet pour la gestion des archives municipales - Accessible uniquement aux utilisateurs connectés"""
    queryset = Archive.objects.filter(statut='disponible')
    permission_classes = [IsAuthenticated]  # ✅ MODIFIÉ (était AllowAny)
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['titre', 'description', 'mots_cles', 'reference', 'auteur']
    ordering_fields = ['date_document', 'vues', 'date_archivage']
    ordering = ['-date_archivage']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ArchiveDetailSerializer
        return ArchiveListSerializer
    
    def get_queryset(self):
        """Filtrage avancé des archives"""
        queryset = super().get_queryset()
        
        # Recherche textuelle
        q = self.request.query_params.get('q')
        if q:
            queryset = queryset.filter(
                Q(titre__icontains=q) |
                Q(description__icontains=q) |
                Q(mots_cles__icontains=q) |
                Q(reference__icontains=q) |
                Q(auteur__icontains=q)
            )
        
        # Filtrer par catégorie
        categorie = self.request.query_params.get('categorie')
        if categorie:
            queryset = queryset.filter(categorie__slug=categorie)
        
        # Filtrer par type de document
        type_document = self.request.query_params.get('type_document')
        if type_document:
            queryset = queryset.filter(type_document=type_document)
        
        # Filtrer par période
        annee_debut = self.request.query_params.get('annee_debut')
        annee_fin = self.request.query_params.get('annee_fin')
        
        if annee_debut:
            try:
                queryset = queryset.filter(date_document__year__gte=int(annee_debut))
            except ValueError:
                pass
        
        if annee_fin:
            try:
                queryset = queryset.filter(date_document__year__lte=int(annee_fin))
            except ValueError:
                pass
        
        # Filtrer par niveau d'accès (utilisateur toujours connecté)
        if not self.request.user.is_staff:
            queryset = queryset.filter(niveau_acces='public')
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """Récupération d'une archive avec incrémentation des vues"""
        instance = self.get_object()
        
        # Vérifier le niveau d'accès (utilisateur toujours connecté)
        if instance.niveau_acces != 'public':
            # Vérifier si l'utilisateur a une demande approuvée
            from .models import DemandeAccesArchive
            demande_exists = DemandeAccesArchive.objects.filter(
                archive=instance,
                demandeur=request.user,
                statut='paye',
                date_fin_acces__gte=timezone.now()
            ).exists()
            
            if not demande_exists and not request.user.is_staff:
                return Response(
                    {'error': 'Accès restreint. Veuillez demander l\'accès à cette archive.'},
                    status=status.HTTP_403_FORBIDDEN
                )
        
        # Incrémenter les vues
        instance.incrementer_vues()
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def demander_acces(self, request, pk=None):
        """Demander l'accès à une archive"""
        archive = self.get_object()
        
        # Utilisateur toujours connecté (permission déjà vérifiée)
        # Vérifier si une demande existe déjà
        demande_existante = DemandeAccesArchive.objects.filter(
            archive=archive,
            demandeur=request.user,
            statut__in=['en_attente', 'valide', 'paye']
        ).first()
        
        if demande_existante:
            return Response({
                'error': 'Une demande existe déjà pour cette archive',
                'demande_id': str(demande_existante.id),
                'statut': demande_existante.statut
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = InitierDemandeArchiveSerializer(data=request.data)
        if serializer.is_valid():
            # Calculer le montant (si payant)
            montant_total = 0
            if archive.payant and archive.tarif:
                montant_total = archive.tarif
            
            # Créer la demande
            demande = DemandeAccesArchive.objects.create(
                archive=archive,
                demandeur=request.user,
                type_demande=serializer.validated_data['type_demande'],
                motif=serializer.validated_data['motif'],
                adresse_livraison=serializer.validated_data.get('adresse_livraison', ''),
                montant_total=montant_total
            )
            
            # Incrémenter le compteur de demandes
            archive.demandes_acces += 1
            archive.save(update_fields=['demandes_acces'])
            
            # Générer un token d'accès temporaire pour suivi
            token = secrets.token_urlsafe(32)
            demande.token_acces = token
            demande.save(update_fields=['token_acces'])
            
            # TODO: Envoyer notification par email
            
            return Response({
                'demande_id': str(demande.id),
                'token': token,
                'statut': demande.statut,
                'montant_total': float(montant_total),
                'message': 'Demande envoyée avec succès. Vous serez notifié de sa validation.'
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def incrementer_vues(self, request, pk=None):
        """Incrémenter le compteur de vues"""
        archive = self.get_object()
        archive.incrementer_vues()
        
        # Enregistrer l'historique (utilisateur toujours connecté)
        from .models import HistoriqueConsultationArchive
        HistoriqueConsultationArchive.objects.create(
            archive=archive,
            utilisateur=request.user,
            ip_address=request.META.get('HTTP_X_FORWARDED_FOR', request.META.get('REMOTE_ADDR', '')),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:255]
        )
        
        return Response({'vues': archive.vues})
    
    @action(detail=True, methods=['get'])
    def apercu(self, request, pk=None):
        """Aperçu du document (première page)"""
        archive = self.get_object()
        
        # Vérifier les permissions pour l'aperçu (utilisateur toujours connecté)
        if archive.niveau_acces != 'public':
            # L'utilisateur est déjà authentifié, pas besoin de vérification supplémentaire
            pass
        
        if archive.fichier_pdf and archive.niveau_acces == 'public':
            return Response({
                'url': archive.fichier_pdf.url,
                'type': 'pdf',
                'message': 'Aperçu disponible'
            })
        
        return Response(
            {'error': 'Aperçu non disponible pour cette archive'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['get'])
    def statut_acces(self, request, pk=None):
        """Vérifier le statut d'accès de l'utilisateur à une archive"""
        archive = self.get_object()
        
        # Utilisateur toujours connecté (permission déjà vérifiée)
        
        # Vérifier si l'utilisateur a une demande approuvée
        demande = DemandeAccesArchive.objects.filter(
            archive=archive,
            demandeur=request.user,
            statut='paye',
            date_fin_acces__gte=timezone.now()
        ).first()
        
        if demande:
            return Response({
                'acces': True,
                'date_expiration': demande.date_fin_acces,
                'demande_id': str(demande.id)
            })
        
        # Vérifier si une demande est en attente
        demande_attente = DemandeAccesArchive.objects.filter(
            archive=archive,
            demandeur=request.user,
            statut__in=['en_attente', 'valide']
        ).first()
        
        if demande_attente:
            return Response({
                'acces': False,
                'statut': demande_attente.statut,
                'message': f'Demande en cours de traitement ({demande_attente.statut})'
            })
        
        return Response({'acces': False, 'message': 'Aucune demande trouvée'})


# ============================================
# DEMANDES D'ACCÈS - PROTÉGÉ
# ============================================

class DemandeAccesArchiveViewSet(viewsets.ModelViewSet):
    """ViewSet pour les demandes d'accès aux archives - Accessible uniquement aux utilisateurs connectés"""
    serializer_class = DemandeAccesArchiveSerializer
    permission_classes = [IsAuthenticated]  # ✅ DÉJÀ BON
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return DemandeAccesArchive.objects.all().order_by('-date_demande')
        return DemandeAccesArchive.objects.filter(demandeur=self.request.user).order_by('-date_demande')
    
    def perform_create(self, serializer):
        """Création manuelle d'une demande (admin uniquement)"""
        if not self.request.user.is_staff:
            raise PermissionError("Seuls les administrateurs peuvent créer des demandes manuellement")
        serializer.save()
    
    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """Détails complets d'une demande"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(demande)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une demande"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if demande.statut not in ['en_attente', 'valide']:
            return Response(
                {'error': 'Cette demande ne peut pas être annulée car elle est déjà traitée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demande.statut = 'cloturee'
        demande.date_fin = timezone.now()
        demande.save(update_fields=['statut', 'date_fin'])
        
        archive = demande.archive
        if archive.demandes_acces > 0:
            archive.demandes_acces -= 1
            archive.save(update_fields=['demandes_acces'])
        
        return Response({'message': 'Demande annulée avec succès'})
    
    @action(detail=True, methods=['post'])
    def effectuer_paiement(self, request, pk=None):
        """Effectuer le paiement pour une demande validée"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if demande.statut != 'valide':
            return Response(
                {'error': f'Cette demande ne peut pas être payée (statut: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if demande.montant_total <= 0:
            # Gratuit, confirmer directement
            demande.statut = 'paye'
            demande.paiement_effectue = True
            demande.save(update_fields=['statut', 'paiement_effectue'])
            
            # Générer un lien d'accès
            token = secrets.token_urlsafe(32)
            demande.token_acces = token
            demande.lien_acces = f"/api/archives/acces/consulter/{token}"
            demande.date_debut_acces = timezone.now()
            demande.date_fin_acces = timezone.now() + timezone.timedelta(days=30)
            demande.save(update_fields=['token_acces', 'lien_acces', 'date_debut_acces', 'date_fin_acces'])
            
            return Response({
                'message': 'Accès gratuit confirmé',
                'lien_acces': demande.lien_acces,
                'date_expiration': demande.date_fin_acces
            })
        
        # Pour les paiements payants
        demande.statut = 'paye'
        demande.paiement_effectue = True
        demande.reference_paiement = f"ARCH-{uuid.uuid4().hex[:12].upper()}"
        demande.date_paiement = timezone.now()
        demande.save(update_fields=['statut', 'paiement_effectue', 'reference_paiement', 'date_paiement'])
        
        # Générer un lien d'accès
        token = secrets.token_urlsafe(32)
        demande.token_acces = token
        demande.lien_acces = f"/api/archives/acces/consulter/{token}"
        demande.date_debut_acces = timezone.now()
        demande.date_fin_acces = timezone.now() + timezone.timedelta(days=30)
        demande.save(update_fields=['token_acces', 'lien_acces', 'date_debut_acces', 'date_fin_acces'])
        
        return Response({
            'message': 'Paiement effectué avec succès',
            'lien_acces': demande.lien_acces,
            'date_expiration': demande.date_fin_acces,
            'reference_paiement': demande.reference_paiement
        })
    
    @action(detail=True, methods=['get'])
    def telecharger(self, request, pk=None):
        """Télécharger le document (si accès autorisé)"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if demande.statut != 'paye':
            return Response(
                {'error': 'Accès non autorisé - Paiement requis'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if demande.date_fin_acces and timezone.now() > demande.date_fin_acces:
            return Response(
                {'error': 'Lien expiré - Veuillez renouveler votre demande'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        archive = demande.archive
        
        if archive.fichier_pdf:
            try:
                if not default_storage.exists(archive.fichier_pdf.name):
                    return Response(
                        {'error': 'Fichier non trouvé sur le serveur'},
                        status=status.HTTP_404_NOT_FOUND
                    )
                
                archive.incrementer_telechargements()
                demande.telechargements_effectues += 1
                demande.save(update_fields=['telechargements_effectues'])
                
                response = FileResponse(
                    archive.fichier_pdf.open('rb'),
                    content_type='application/pdf',
                    filename=f"{archive.reference}.pdf"
                )
                response['Content-Disposition'] = f'attachment; filename="{archive.reference}.pdf"'
                return response
                
            except Exception as e:
                return Response(
                    {'error': f'Erreur lors du téléchargement: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(
            {'error': 'Fichier non disponible'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def renouveler(self, request, pk=None):
        """Renouveler une demande expirée"""
        demande = self.get_object()
        
        if demande.demandeur != request.user and not request.user.is_staff:
            return Response(
                {'error': 'Non autorisé'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if demande.date_fin_acces and timezone.now() <= demande.date_fin_acces:
            return Response(
                {'error': 'La demande n\'est pas encore expirée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demande.date_fin_acces = timezone.now() + timezone.timedelta(days=30)
        demande.token_acces = secrets.token_urlsafe(32)
        demande.lien_acces = f"/api/archives/acces/consulter/{demande.token_acces}"
        demande.save(update_fields=['date_fin_acces', 'token_acces', 'lien_acces'])
        
        return Response({
            'message': 'Accès renouvelé avec succès',
            'lien_acces': demande.lien_acces,
            'date_expiration': demande.date_fin_acces
        })


# ============================================
# TOKENS D'ACCÈS - AVEC ACCÈS PUBLIC POUR LE TÉLÉCHARGEMENT
# ============================================
# ⚠️ ATTENTION : Ces endpoints restent publics car ils sont utilisés via des liens
# partagés par email. Ne pas modifier les permissions ici.
# ============================================

from rest_framework.permissions import AllowAny  # Réimporté pour ces vues spécifiques


class AccesTokenViewSet(viewsets.ViewSet):
    """ViewSet pour la gestion des tokens d'accès aux archives"""
    permission_classes = [AllowAny]  # ✅ RESTE PUBLIC (liens partagés)
    
    @action(detail=False, methods=['get'], url_path='consulter/(?P<token>[^/.]+)')
    def verifier_token(self, request, token):
        """Vérifier un token d'accès et retourner le document"""
        try:
            from .models import DemandeAccesArchive
            
            demande = DemandeAccesArchive.objects.select_related('archive').get(token_acces=token)
            
            if demande.date_fin_acces and timezone.now() > demande.date_fin_acces:
                return Response(
                    {'error': 'Lien expiré (plus de 30 jours). Veuillez renouveler votre demande.'},
                    status=status.HTTP_410_GONE
                )
            
            if demande.statut != 'paye':
                return Response(
                    {'error': f'Accès non autorisé. Statut: {demande.statut}'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            archive = demande.archive
            
            if not archive.fichier_pdf:
                return Response(
                    {'error': 'Fichier non disponible'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if not default_storage.exists(archive.fichier_pdf.name):
                return Response(
                    {'error': 'Fichier non trouvé sur le serveur'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            archive.incrementer_telechargements()
            demande.telechargements_effectues += 1
            demande.save(update_fields=['telechargements_effectues'])
            
            response = FileResponse(
                archive.fichier_pdf.open('rb'),
                content_type='application/pdf',
                filename=f"{archive.reference}.pdf"
            )
            response['Content-Disposition'] = f'inline; filename="{archive.reference}.pdf"'
            return response
            
        except DemandeAccesArchive.DoesNotExist:
            return Response(
                {'error': 'Token invalide - Aucune demande trouvée'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de l\'accès: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'], url_path='info/(?P<token>[^/.]+)')
    def info_token(self, request, token):
        """Obtenir les informations d'un token sans télécharger"""
        try:
            from .models import DemandeAccesArchive
            
            demande = DemandeAccesArchive.objects.select_related('archive').get(token_acces=token)
            
            return Response({
                'archive_titre': demande.archive.titre,
                'archive_reference': demande.archive.reference,
                'type_demande': demande.type_demande,
                'date_demande': demande.date_demande,
                'date_expiration': demande.date_fin_acces,
                'est_expire': timezone.now() > demande.date_fin_acces if demande.date_fin_acces else False,
                'statut': demande.statut,
                'telechargements': demande.telechargements_effectues
            })
            
        except DemandeAccesArchive.DoesNotExist:
            return Response(
                {'error': 'Token invalide'},
                status=status.HTTP_404_NOT_FOUND
            )