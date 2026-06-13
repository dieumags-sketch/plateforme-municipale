# actualites/views.py
# ============================================
# VERSION CORRIGÉE : ACCÈS UNIQUEMENT AUX UTILISATEURS CONNECTÉS
# ============================================

from django.shortcuts import render
from django.db.models import Q
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated  # ✅ UNIQUEMENT IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import (
    Publication, Reaction, Commentaire, HistoriqueConsultation, 
    PropositionCitoyenne, Partage, CategorieActualite
)
from .serializers import (
    PublicationListSerializer, PublicationDetailSerializer, 
    PublicationCreateUpdateSerializer, ReactionSerializer, 
    CommentaireSerializer, PropositionCitoyenneSerializer,
    HistoriqueConsultationSerializer, PartageSerializer,
    CategorieActualiteSerializer
)
from .permissions import EstAuteurOuModerateur, EstModerateur, PeutModererCommentaires
from .filters import PublicationFilter
from .pagination import PublicationPagination, CommentairePagination


# ============================================
# CATÉGORIES - PROTÉGÉ
# ============================================

class CategorieActualiteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les catégories - Accessible uniquement aux utilisateurs connectés"""
    queryset = CategorieActualite.objects.all()
    serializer_class = CategorieActualiteSerializer
    permission_classes = [IsAuthenticated]


# ============================================
# PUBLICATIONS - PROTÉGÉ
# ============================================

class PublicationViewSet(viewsets.ModelViewSet):
    """ViewSet complet pour les publications - Accessible uniquement aux utilisateurs connectés"""
    queryset = Publication.objects.all()
    pagination_class = PublicationPagination
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = PublicationFilter
    search_fields = ['titre', 'accroche', 'contenu']
    ordering_fields = ['date_publication', 'vue_count', 'date_creation']
    ordering = ['-est_epingle', '-date_publication']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return PublicationCreateUpdateSerializer
        if self.action == 'list':
            return PublicationListSerializer
        return PublicationDetailSerializer
    
    def get_permissions(self):
        """
        Toutes les actions nécessitent une authentification.
        Les permissions spécifiques (auteur, modérateur) s'ajoutent par-dessus.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), EstAuteurOuModerateur()]
        if self.action in ['soumettre_moderation', 'moderer']:
            return [IsAuthenticated(), EstModerateur()]
        # list, retrieve, et toutes les autres actions : simple authentification requise
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """
        Filtre les publications selon le rôle de l'utilisateur connecté.
        """
        queryset = Publication.objects.all()
        user = self.request.user
        
        # Les admins et modérateurs voient tout
        if user.is_staff or getattr(user, 'role', '') in ['admin', 'moderateur']:
            return queryset
        
        # Les citoyens voient les publications publiées + leurs propres brouillons/soumis
        return queryset.filter(
            Q(statut='publie', date_publication__lte=timezone.now()) |
            Q(auteur=user, statut__in=['brouillon', 'soumis'])
        )
    
    def perform_create(self, serializer):
        """Création d'une publication - statut initial 'brouillon'"""
        serializer.save(auteur=self.request.user, statut='brouillon')
    
    @action(detail=True, methods=['post'])
    def soumettre_moderation(self, request, pk=None):
        """Soumettre une publication à la modération"""
        publication = self.get_object()
        
        if publication.auteur != request.user:
            return Response(
                {'error': 'Vous ne pouvez soumettre que vos propres publications'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if publication.statut != 'brouillon':
            return Response(
                {'error': f'Cette publication est déjà en statut {publication.statut}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        publication.statut = 'soumis'
        publication.save()
        
        return Response({'message': 'Publication soumise à la modération avec succès'})
    
    @action(detail=True, methods=['post'])
    def moderer(self, request, pk=None):
        """Modérer une publication (admin/moderateur uniquement)"""
        publication = self.get_object()
        action_moderation = request.data.get('action')
        commentaire = request.data.get('commentaire', '')
        
        if action_moderation not in ['publier', 'rejeter', 'demander_correction']:
            return Response(
                {'error': 'Action non valide. Choisir parmi : publier, rejeter, demander_correction'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if action_moderation == 'publier':
            publication.statut = 'publie'
            publication.date_publication = timezone.now()
            message = 'Publication publiée avec succès'
        elif action_moderation == 'rejeter':
            publication.statut = 'rejete'
            message = 'Publication rejetée'
        else:  # demander_correction
            publication.statut = 'en_correction'
            message = 'Demande de correction envoyée à l\'auteur'
        
        publication.moderateur = request.user
        publication.commentaire_moderation = commentaire
        publication.date_moderation = timezone.now()
        publication.save()
        
        return Response({'message': message})
    
    @action(detail=True, methods=['post'])
    def increment_vue(self, request, pk=None):
        """Incrémenter le compteur de vues"""
        publication = self.get_object()
        publication.increment_vue()
        
        # Enregistrer dans l'historique (utilisateur toujours connecté)
        HistoriqueConsultation.objects.get_or_create(
            utilisateur=request.user,
            publication=publication
        )
        
        return Response({'vue_count': publication.vue_count})
    
    @action(detail=True, methods=['get'])
    def reactions(self, request, pk=None):
        """Obtenir les réactions d'une publication"""
        publication = self.get_object()
        reactions = publication.reactions.all()
        serializer = ReactionSerializer(reactions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def ajouter_reaction(self, request, pk=None):
        """Ajouter ou modifier une réaction"""
        publication = self.get_object()
        type_reaction = request.data.get('type_reaction')
        
        if type_reaction not in dict(Reaction.TYPE_CHOICES).keys():
            return Response(
                {'error': 'Type de réaction invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reaction, created = Reaction.objects.update_or_create(
            publication=publication,
            utilisateur=request.user,
            defaults={'type_reaction': type_reaction}
        )
        
        return Response({'message': 'Réaction enregistrée', 'type': type_reaction})
    
    @action(detail=True, methods=['delete'])
    def supprimer_reaction(self, request, pk=None):
        """Supprimer sa réaction"""
        publication = self.get_object()
        reaction = publication.reactions.filter(utilisateur=request.user).first()
        
        if reaction:
            reaction.delete()
            return Response({'message': 'Réaction supprimée'})
        
        return Response(
            {'error': 'Aucune réaction trouvée'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def partager(self, request, pk=None):
        """Enregistrer un partage"""
        publication = self.get_object()
        plateforme = request.data.get('plateforme')
        
        if plateforme not in dict(Partage.PLATEFORME_CHOICES).keys():
            return Response(
                {'error': 'Plateforme invalide'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        Partage.objects.create(
            publication=publication,
            utilisateur=request.user,  # Utilisateur toujours connecté
            plateforme=plateforme
        )
        
        publication.partage_count += 1
        publication.save(update_fields=['partage_count'])
        
        return Response({
            'message': 'Partage enregistré',
            'partage_count': publication.partage_count
        })


# ============================================
# COMMENTAIRES - PROTÉGÉ
# ============================================

class CommentaireViewSet(viewsets.ModelViewSet):
    """ViewSet pour les commentaires - Accessible uniquement aux utilisateurs connectés"""
    queryset = Commentaire.objects.all()
    serializer_class = CommentaireSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = CommentairePagination
    
    def get_queryset(self):
        publication_id = self.request.query_params.get('publication')
        if publication_id:
            return Commentaire.objects.filter(
                publication_id=publication_id,
                parent=None,
                est_approuve=True
            )
        if self.request.user.is_staff:
            return Commentaire.objects.all()
        return Commentaire.objects.filter(est_approuve=True)
    
    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user, est_approuve=False)
    
    @action(detail=True, methods=['post'])
    def approuver(self, request, pk=None):
        """Approuver un commentaire (modération) - Admin/Modérateur uniquement"""
        if not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'moderateur']):
            return Response(
                {'error': 'Permission refusée'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        commentaire = self.get_object()
        commentaire.est_approuve = True
        commentaire.save()
        
        return Response({'message': 'Commentaire approuvé'})
    
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        """Liker un commentaire"""
        commentaire = self.get_object()
        commentaire.like_count += 1
        commentaire.save()
        
        return Response({'like_count': commentaire.like_count})


# ============================================
# RÉACTIONS - PROTÉGÉ
# ============================================

class ReactionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les réactions - Accessible uniquement aux utilisateurs connectés"""
    queryset = Reaction.objects.all()
    serializer_class = ReactionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Reaction.objects.all()
        return Reaction.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        publication_id = self.request.data.get('publication')
        type_reaction = self.request.data.get('type_reaction')
        
        # Mettre à jour ou créer
        reaction, created = Reaction.objects.update_or_create(
            utilisateur=self.request.user,
            publication_id=publication_id,
            defaults={'type_reaction': type_reaction}
        )
        if not created:
            serializer.instance = reaction
        else:
            serializer.save(utilisateur=self.request.user)


# ============================================
# PARTAGES - PROTÉGÉ
# ============================================

class PartageViewSet(viewsets.ModelViewSet):
    """ViewSet pour les partages - Accessible uniquement aux utilisateurs connectés"""
    queryset = Partage.objects.all()
    serializer_class = PartageSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff:
            return Partage.objects.all()
        return Partage.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(utilisateur=self.request.user)


# ============================================
# PROPOSITIONS CITOYENNES - PROTÉGÉ
# ============================================

class PropositionCitoyenneViewSet(viewsets.ModelViewSet):
    """ViewSet pour les propositions citoyennes - Accessible uniquement aux utilisateurs connectés"""
    queryset = PropositionCitoyenne.objects.all()
    serializer_class = PropositionCitoyenneSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, 'role', '') in ['admin', 'moderateur']:
            return PropositionCitoyenne.objects.all()
        return PropositionCitoyenne.objects.filter(auteur=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(auteur=self.request.user)
    
    @action(detail=False, methods=['get'])
    def mes_propositions(self, request):
        """Récupérer les propositions de l'utilisateur connecté"""
        propositions = self.get_queryset().filter(auteur=request.user)
        serializer = self.get_serializer(propositions, many=True)
        return Response(serializer.data)


# ============================================
# HISTORIQUE DE CONSULTATION - PROTÉGÉ
# ============================================

class HistoriqueConsultationViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour l'historique de consultation - Accessible uniquement aux utilisateurs connectés"""
    queryset = HistoriqueConsultation.objects.all()
    serializer_class = HistoriqueConsultationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return HistoriqueConsultation.objects.filter(utilisateur=self.request.user)


# ============================================
# VUES SPÉCIALES POUR ACCUEIL - PROTÉGÉES
# ============================================

class PublicationAfficheView(generics.ListAPIView):
    """Publications à la une - Accessible uniquement aux utilisateurs connectés"""
    queryset = Publication.objects.all()
    serializer_class = PublicationListSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = None
    
    def get_queryset(self):
        return Publication.objects.filter(
            statut='publie',
            est_a_la_une=True,
            date_publication__lte=timezone.now()
        )[:6]


class PublicationRecentView(generics.ListAPIView):
    """Publications récentes - Accessible uniquement aux utilisateurs connectés"""
    queryset = Publication.objects.all()
    serializer_class = PublicationListSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return Publication.objects.filter(
            statut='publie',
            date_publication__lte=timezone.now()
        ).order_by('-date_publication')[:10]