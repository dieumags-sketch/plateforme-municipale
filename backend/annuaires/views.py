# annuaires/views.py
from django.shortcuts import render

# annuaires/views.py
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from geopy.distance import geodesic
from rest_framework.exceptions import ValidationError  # AJOUTÉ
from .models import Structure, Elu, CategorieStructure, FavoriStructure, AvisStructure, ContactStructure
from .serializers import (
    StructureListSerializer, StructureDetailSerializer, EluSerializer,
    CategorieStructureSerializer, FavoriStructureSerializer,
    AvisStructureSerializer, ContactStructureSerializer
)
from .permissions import IsAdminOrReadOnly


class CategorieStructureViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les catégories de structures"""
    queryset = CategorieStructure.objects.all()
    serializer_class = CategorieStructureSerializer
    permission_classes = [AllowAny]
    # ReadOnlyModelViewSet a déjà un queryset → pas besoin de basename


class StructureViewSet(viewsets.ModelViewSet):
    """ViewSet pour les structures municipales"""
    queryset = Structure.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_structure', 'ville', 'statut', 'est_populaire']
    search_fields = ['nom', 'adresse', 'quartier', 'ville', 'description']
    ordering_fields = ['nom', 'vue_count', 'est_populaire']
    ordering = ['nom']
    
    def get_serializer_class(self):
        if self.action == 'list':
            return StructureListSerializer
        return StructureDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAdminOrReadOnly()]
        return [IsAuthenticatedOrReadOnly()]
    
    def get_queryset(self):
        """Récupère les structures actives avec filtrage par distance"""
        queryset = Structure.objects.filter(statut='actif')
        
        # Géolocalisation : filtrer par distance
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 10)  # km par défaut
        
        if lat and lng:
            try:
                user_location = (float(lat), float(lng))
            except (ValueError, TypeError):
                return queryset
            
            # Calculer la distance pour chaque structure
            structures_with_distance = []
            for structure in queryset:
                if structure.latitude and structure.longitude:
                    try:
                        struct_location = (float(structure.latitude), float(structure.longitude))
                        distance = geodesic(user_location, struct_location).kilometers
                        if distance <= float(radius):
                            # Ajouter dynamiquement l'attribut distance
                            structure.distance = round(distance, 2)
                            structures_with_distance.append(structure)
                    except (ValueError, TypeError):
                        continue
            
            # Trier par distance
            structures_with_distance.sort(key=lambda x: getattr(x, 'distance', float('inf')))
            return structures_with_distance
        
        return queryset
    
    def retrieve(self, request, *args, **kwargs):
        """Incrémente le compteur de vues lors de la consultation"""
        instance = self.get_object()
        instance.vue_count += 1
        instance.save(update_fields=['vue_count'])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def contact(self, request, pk=None):
        """Prise de contact avec une structure"""
        structure = self.get_object()
        
        # Vérifier les tentatives trop fréquentes (optionnel)
        from django.utils import timezone
        recent_contacts = ContactStructure.objects.filter(
            structure=structure,
            date_creation__gte=timezone.now() - timezone.timedelta(minutes=5)
        )
        
        if request.user.is_authenticated:
            recent_contacts = recent_contacts.filter(utilisateur=request.user)
        
        if recent_contacts.count() >= 3:
            return Response(
                {'error': 'Trop de messages envoyés. Veuillez réessayer dans 5 minutes.'},
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        serializer = ContactStructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        # Sauvegarder le contact
        contact = serializer.save(
            structure=structure,
            utilisateur=request.user if request.user.is_authenticated else None
        )
        
        # Incrémenter compteur de contacts
        structure.contact_count += 1
        structure.save(update_fields=['contact_count'])
        
        # TODO: Envoyer notification par email ou SMS
        # from .notifications import notifier_nouveau_contact
        # notifier_nouveau_contact(contact)
        
        return Response(
            {'message': 'Votre message a été envoyé avec succès. Vous recevrez une réponse dans les plus brefs délais.'},
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def ajouter_favori(self, request, pk=None):
        """Ajouter aux favoris"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentification requise pour ajouter aux favoris'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        structure = self.get_object()
        
        # Vérifier que la structure est active
        if structure.statut != 'actif':
            return Response(
                {'error': 'Cette structure n\'est pas active'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        favori, created = FavoriStructure.objects.get_or_create(
            utilisateur=request.user,
            structure=structure
        )
        
        if created:
            structure.favori_count += 1
            structure.save(update_fields=['favori_count'])
            return Response(
                {'message': 'Ajouté aux favoris', 'is_favorite': True},
                status=status.HTTP_201_CREATED
            )
        
        return Response(
            {'message': 'Déjà dans les favoris', 'is_favorite': True},
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def retirer_favori(self, request, pk=None):
        """Retirer des favoris"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentification requise'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        structure = self.get_object()
        
        deleted_count, _ = FavoriStructure.objects.filter(
            utilisateur=request.user,
            structure=structure
        ).delete()
        
        if deleted_count > 0:
            structure.favori_count = max(0, structure.favori_count - 1)
            structure.save(update_fields=['favori_count'])
            return Response(
                {'message': 'Retiré des favoris', 'is_favorite': False},
                status=status.HTTP_200_OK
            )
        
        return Response(
            {'message': 'Non trouvé dans les favoris', 'is_favorite': False},
            status=status.HTTP_404_NOT_FOUND
        )
    
    @action(detail=True, methods=['post'])
    def ajouter_avis(self, request, pk=None):
        """Ajouter un avis sur une structure"""
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentification requise pour laisser un avis'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        structure = self.get_object()
        
        # Vérifier si la structure est active
        if structure.statut != 'actif':
            return Response(
                {'error': 'Impossible de laisser un avis sur une structure inactive'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier si l'utilisateur a déjà laissé un avis
        avis_existant = AvisStructure.objects.filter(
            structure=structure,
            utilisateur=request.user
        ).first()
        
        if avis_existant:
            return Response(
                {'error': 'Vous avez déjà laissé un avis. Vous pouvez le modifier.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = AvisStructureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        avis = serializer.save(
            structure=structure,
            utilisateur=request.user,
            est_approuve=False  # Par défaut non approuvé (modération)
        )
        
        # Mettre à jour la note moyenne de la structure
        structure.update_moyenne_notes()
        
        return Response(
            {
                'message': 'Votre avis a été soumis et sera publié après modération.',
                'avis': serializer.data
            },
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['get'])
    def est_favori(self, request, pk=None):
        """Vérifier si la structure est dans les favoris de l'utilisateur"""
        if not request.user.is_authenticated:
            return Response({'is_favorite': False})
        
        structure = self.get_object()
        is_favorite = FavoriStructure.objects.filter(
            utilisateur=request.user,
            structure=structure
        ).exists()
        
        return Response({'is_favorite': is_favorite})
    
    @action(detail=True, methods=['get'])
    def avis(self, request, pk=None):
        """Récupérer les avis d'une structure"""
        structure = self.get_object()
        avis = structure.avis.filter(est_approuve=True).order_by('-date_creation')
        
        page = self.paginate_queryset(avis)
        if page is not None:
            serializer = AvisStructureSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = AvisStructureSerializer(avis, many=True)
        return Response(serializer.data)


class EluViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les élus (lecture seule)"""
    queryset = Elu.objects.filter(est_actif=True)
    serializer_class = EluSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['fonction', 'commission']
    search_fields = ['nom', 'prenom', 'fonction', 'commission', 'delegation']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtrer par commission si spécifié
        commission = self.request.query_params.get('commission')
        if commission:
            queryset = queryset.filter(commission__icontains=commission)
        
        # Filtrer par fonction
        fonction = self.request.query_params.get('fonction')
        if fonction:
            queryset = queryset.filter(fonction__icontains=fonction)
        
        return queryset


class FavoriViewSet(viewsets.ModelViewSet):  # CHANGÉ: ReadOnlyModelViewSet → ModelViewSet
    """ViewSet pour les favoris (CRUD complet)"""
    serializer_class = FavoriStructureSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return FavoriStructure.objects.filter(utilisateur=self.request.user)
    
    def perform_create(self, serializer):
        """Ajouter un favori"""
        serializer.save(utilisateur=self.request.user)
    
    def destroy(self, request, *args, **kwargs):
        """Supprimer un favori"""
        favori = self.get_object()
        
        # Décrémenter le compteur de favoris de la structure
        structure = favori.structure
        structure.favori_count = max(0, structure.favori_count - 1)
        structure.save(update_fields=['favori_count'])
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=False, methods=['delete'])
    def clear_all(self, request):
        """Supprimer tous les favoris de l'utilisateur"""
        deleted_count, _ = self.get_queryset().delete()
        return Response(
            {'message': f'{deleted_count} favoris supprimés'},
            status=status.HTTP_200_OK
        )


class RechercheProximiteView(generics.ListAPIView):
    """Recherche de structures à proximité géographique"""
    serializer_class = StructureListSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        lat = self.request.query_params.get('lat')
        lng = self.request.query_params.get('lng')
        radius = self.request.query_params.get('radius', 5)
        type_structure = self.request.query_params.get('type')
        limit = self.request.query_params.get('limit', 50)
        
        # Validation des paramètres
        if not lat or not lng:
            return Structure.objects.none()
        
        try:
            radius = float(radius)
            limit = int(limit)
            user_location = (float(lat), float(lng))
        except (ValueError, TypeError):
            return Structure.objects.none()
        
        if radius <= 0 or radius > 100:  # Limite à 100km max
            radius = 5
        
        structures = Structure.objects.filter(statut='actif')
        
        if type_structure:
            structures = structures.filter(type_structure=type_structure)
        
        resultats = []
        for structure in structures:
            if structure.latitude and structure.longitude:
                try:
                    struct_location = (float(structure.latitude), float(structure.longitude))
                    distance = geodesic(user_location, struct_location).kilometers
                    if distance <= radius:
                        structure.distance = round(distance, 2)
                        resultats.append(structure)
                except (ValueError, TypeError):
                    continue
        
        # Trier par distance et limiter
        resultats.sort(key=lambda x: getattr(x, 'distance', float('inf')))
        return resultats[:limit]
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        
        return Response({
            'count': len(queryset),
            'radius': request.query_params.get('radius', 5),
            'center': {
                'lat': request.query_params.get('lat'),
                'lng': request.query_params.get('lng')
            },
            'results': serializer.data
        })


class StatistiquesView(generics.GenericAPIView):
    """Statistiques pour le dashboard administratif"""
    permission_classes = [IsAdminOrReadOnly]
    
    def get(self, request):
        from django.utils import timezone
        from datetime import timedelta
        
        # Statistiques générales
        total_structures = Structure.objects.count()
        total_structures_actives = Structure.objects.filter(statut='actif').count()
        total_structures_inactives = Structure.objects.filter(statut='inactif').count()
        total_elus = Elu.objects.filter(est_actif=True).count()
        total_avis = AvisStructure.objects.filter(est_approuve=True).count()
        total_avis_en_attente = AvisStructure.objects.filter(est_approuve=False).count()
        total_contacts = ContactStructure.objects.count()
        
        # Statistiques par type
        structures_par_type = list(Structure.objects.values('type_structure').annotate(count=Count('id')))
        
        # Top villes
        structures_par_ville = list(Structure.objects.values('ville')
                                   .annotate(count=Count('id'))
                                   .order_by('-count')[:10])
        
        # Meilleures structures (par note)
        meilleures_structures = Structure.objects.annotate(
            note_moyenne=Avg('avis__note')
        ).filter(note_moyenne__isnull=False, statut='actif').order_by('-note_moyenne')[:10]
        
        # Activité récente (7 derniers jours)
        semaine_derniere = timezone.now() - timedelta(days=7)
        nouveaux_contacts = ContactStructure.objects.filter(
            date_creation__gte=semaine_derniere
        ).count()
        
        nouveaux_avis = AvisStructure.objects.filter(
            date_creation__gte=semaine_derniere
        ).count()
        
        # Structures les plus consultées
        structures_populaires = Structure.objects.filter(statut='actif').order_by('-vue_count')[:5]
        
        return Response({
            'total_structures': total_structures,
            'total_structures_actives': total_structures_actives,
            'total_structures_inactives': total_structures_inactives,
            'total_elus': total_elus,
            'total_avis': total_avis,
            'total_avis_en_attente': total_avis_en_attente,
            'total_contacts': total_contacts,
            'structures_par_type': structures_par_type,
            'structures_par_ville': structures_par_ville,
            'meilleures_structures': [
                {'id': s.id, 'nom': s.nom, 'note': round(s.note_moyenne, 1)} 
                for s in meilleures_structures
            ],
            'structures_populaires': [
                {'id': s.id, 'nom': s.nom, 'vues': s.vue_count}
                for s in structures_populaires
            ],
            'activite_recente': {
                'nouveaux_contacts': nouveaux_contacts,
                'nouveaux_avis': nouveaux_avis
            }
        })