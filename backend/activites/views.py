# activites/views.py
from django.shortcuts import render

# activites/views.py
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.utils import timezone
from django.db.models import Count, Sum, Q
from .models import Activite, Inscription, CategorieActivite, PaiementActivite, AvisActivite
from .serializers import (
    ActiviteListSerializer, ActiviteDetailSerializer, ActiviteCreateUpdateSerializer,
    InscriptionSerializer, InscriptionCreateSerializer, CategorieActiviteSerializer,
    PaiementActiviteSerializer, PaiementInitSerializer, AvisActiviteSerializer
)
from .permissions import EstOrganisateurOuAdmin, EstProprietaireInscription, PeutGererActivites
from .payment import PaiementHandler
from .filters import ActiviteFilter
from rest_framework import serializers  # AJOUTÉ pour l'exception dans AvisViewSet


class CategorieActiviteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les catégories"""
    queryset = CategorieActivite.objects.all()
    serializer_class = CategorieActiviteSerializer
    permission_classes = [AllowAny]
    # Plus besoin de basename car ReadOnlyModelViewSet a un queryset


class ActiviteViewSet(viewsets.ModelViewSet):
    """ViewSet pour les activités"""
    queryset = Activite.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_class = ActiviteFilter
    search_fields = ['titre', 'description_courte', 'description_longue', 'lieu']
    ordering_fields = ['date_debut', 'prix', 'vue_count', 'date_creation']
    ordering = ['-est_a_la_une', '-est_recommandee', 'date_debut']
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ActiviteCreateUpdateSerializer
        if self.action == 'list':
            return ActiviteListSerializer
        return ActiviteDetailSerializer
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated(), PeutGererActivites()]
        return [IsAuthenticatedOrReadOnly()]
    
    def get_queryset(self):
        queryset = Activite.objects.all()
        
        # Filtrer par date
        now = timezone.now()
        
        # Les non-authentifiés voient seulement les activités publiées à venir
        if not self.request.user.is_authenticated:
            return queryset.filter(
                statut='publie',
                date_debut__gte=now
            )
        
        # Les admins voient tout
        if self.request.user.role in ['admin', 'moderateur', 'agent']:
            return queryset
        
        # Les citoyens voient les activités publiées (passées et futures)
        return queryset.filter(statut='publie')
    
    def perform_create(self, serializer):
        serializer.save(organisateur=self.request.user)
    
    @action(detail=True, methods=['post'])
    def increment_vue(self, request, pk=None):
        """Incrémenter le compteur de vues"""
        activite = self.get_object()
        activite.increment_vue()
        return Response({'vue_count': activite.vue_count})
    
    @action(detail=True, methods=['get'])
    def inscriptions(self, request, pk=None):
        """Liste des inscriptions à une activité"""
        activite = self.get_object()
        
        # Vérifier les permissions
        if not (request.user.role in ['admin', 'moderateur', 'agent'] or activite.organisateur == request.user):
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        
        inscriptions = activite.inscriptions.all()
        serializer = InscriptionSerializer(inscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def est_inscrit(self, request, pk=None):
        """Vérifier si l'utilisateur est inscrit"""
        activite = self.get_object()
        if not request.user.is_authenticated:
            return Response({'inscrit': False})
        
        inscrit = activite.inscriptions.filter(
            utilisateur=request.user,
            statut__in=['en_attente_paiement', 'confirmee']
        ).exists()
        
        return Response({'inscrit': inscrit})


class InscriptionViewSet(viewsets.ModelViewSet):
    """ViewSet pour les inscriptions"""
    serializer_class = InscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['admin', 'moderateur', 'agent']:
            return Inscription.objects.all()
        return Inscription.objects.filter(utilisateur=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return InscriptionCreateSerializer
        return InscriptionSerializer
    
    def perform_create(self, serializer):
        inscription = serializer.save(
            utilisateur=self.request.user,
            nom_complet=self.request.user.get_full_name() or self.request.user.username,
            email=self.request.user.email,
            telephone=str(self.request.user.telephone) if self.request.user.telephone else '',
            statut='en_attente_paiement'
        )
        
        # Si l'activité est gratuite, confirmer directement
        if inscription.activite.est_gratuit:
            inscription.statut = 'confirmee'
            inscription.save()
            # Générer QR code
            inscription.generate_qr_code()
            inscription.save()
            # Envoyer notification
            from .notifications import NotificationService
            NotificationService.envoyer_confirmation_inscription(inscription)
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une inscription"""
        inscription = self.get_object()
        
        # Vérifier que l'inscription appartient à l'utilisateur ou que l'utilisateur est admin
        if inscription.utilisateur != request.user and request.user.role not in ['admin', 'moderateur']:
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        
        if inscription.statut in ['annulee', 'termine']:
            return Response({'error': 'Inscription déjà annulée'}, status=status.HTTP_400_BAD_REQUEST)
        
        if inscription.activite.date_debut < timezone.now():
            return Response({'error': 'Impossible d\'annuler une activité passée'}, status=status.HTTP_400_BAD_REQUEST)
        
        inscription.statut = 'annulee'
        inscription.date_annulation = timezone.now()
        inscription.save()
        
        # Envoyer notification d'annulation
        from .notifications import NotificationService
        NotificationService.notifier_annulation(inscription, "Annulation demandée par l'utilisateur")
        
        return Response({'message': 'Inscription annulée avec succès'})
    
    @action(detail=False, methods=['get'])
    def mes_inscriptions(self, request):
        """Mes inscriptions (utilisateur connecté)"""
        inscriptions = self.get_queryset().filter(utilisateur=request.user)
        
        # Filtrer par statut
        statut = request.query_params.get('statut')
        if statut:
            inscriptions = inscriptions.filter(statut=statut)
        
        serializer = self.get_serializer(inscriptions, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def prochaines(self, request):
        """Prochaines inscriptions à venir"""
        inscriptions = self.get_queryset().filter(
            utilisateur=request.user,
            statut='confirmee',
            activite__date_debut__gte=timezone.now()
        ).order_by('activite__date_debut')[:10]
        
        serializer = self.get_serializer(inscriptions, many=True)
        return Response(serializer.data)


class PaiementViewSet(viewsets.ViewSet):
    """ViewSet pour les paiements"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'])
    def initier(self, request):
        """Initier un paiement"""
        serializer = PaiementInitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        inscription_id = serializer.validated_data['inscription_id']
        moyen_paiement = serializer.validated_data['moyen_paiement']
        telephone = serializer.validated_data['numero_telephone']
        
        # Vérifier que l'inscription appartient à l'utilisateur
        try:
            inscription = Inscription.objects.get(
                id=inscription_id,
                utilisateur=request.user
            )
        except Inscription.DoesNotExist:
            return Response({'error': 'Inscription non trouvée'}, status=status.HTTP_404_NOT_FOUND)
        
        # Traiter le paiement
        result = PaiementHandler.traiter_paiement(inscription_id, moyen_paiement, telephone)
        
        if result.get('success'):
            return Response(result)
        else:
            return Response({'error': result.get('error')}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def confirmer(self, request):
        """Confirmer un paiement"""
        paiement_id = request.data.get('paiement_id')
        transaction_id = request.data.get('transaction_id')
        
        result = PaiementHandler.confirmer_paiement(paiement_id, transaction_id)
        
        if result.get('success'):
            return Response(result)
        else:
            return Response({'error': result.get('error')}, status=status.HTTP_400_BAD_REQUEST)


class AvisViewSet(viewsets.ModelViewSet):
    """ViewSet pour les avis"""
    serializer_class = AvisActiviteSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        if self.request.user.role in ['admin', 'moderateur']:
            return AvisActivite.objects.all()
        return AvisActivite.objects.filter(est_approuve=True)
    
    def perform_create(self, serializer):
        # Vérifier que l'utilisateur a participé à l'activité
        inscription_id = self.request.data.get('inscription')
        
        if not inscription_id:
            raise serializers.ValidationError("L'ID de l'inscription est requis")
        
        try:
            inscription = Inscription.objects.get(
                id=inscription_id,
                utilisateur=self.request.user,
                statut='confirmee'
            )
        except Inscription.DoesNotExist:
            raise serializers.ValidationError(
                "Vous ne pouvez laisser un avis que pour une activité à laquelle vous avez participé et qui est confirmée"
            )
        
        # Vérifier que l'activité est terminée
        if inscription.activite.date_fin and inscription.activite.date_fin > timezone.now():
            raise serializers.ValidationError("Vous ne pouvez laisser un avis qu'après la fin de l'activité")
        
        # Vérifier que l'utilisateur n'a pas déjà laissé un avis
        if AvisActivite.objects.filter(inscription=inscription).exists():
            raise serializers.ValidationError("Vous avez déjà laissé un avis pour cette activité")
        
        serializer.save(inscription=inscription)


class DashboardStatsView(generics.GenericAPIView):
    """Statistiques pour le dashboard admin"""
    permission_classes = [IsAuthenticated, PeutGererActivites]
    
    def get(self, request):
        now = timezone.now()
        
        # Statistiques globales
        total_activites = Activite.objects.count()
        total_inscriptions = Inscription.objects.count()
        total_inscriptions_confirmees = Inscription.objects.filter(statut='confirmee').count()
        chiffre_affaires = Inscription.objects.filter(
            statut='confirmee'
        ).aggregate(total=Sum('montant_total'))['total'] or 0
        
        # Activités par statut
        activites_par_statut = list(Activite.objects.values('statut').annotate(count=Count('id')))
        
        # Inscriptions par mois (6 derniers mois)
        inscriptions_par_mois = []
        for i in range(5, -1, -1):  # Du plus vieux au plus récent
            mois = now - timezone.timedelta(days=30*i)
            debut_mois = mois.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Calculer la fin du mois
            if debut_mois.month == 12:
                fin_mois = debut_mois.replace(year=debut_mois.year + 1, month=1, day=1)
            else:
                fin_mois = debut_mois.replace(month=debut_mois.month + 1, day=1)
            
            count = Inscription.objects.filter(
                date_inscription__gte=debut_mois,
                date_inscription__lt=fin_mois
            ).count()
            
            inscriptions_par_mois.append({
                'mois': debut_mois.strftime('%B %Y'),
                'count': count
            })
        
        # Top activités
        top_activites = Activite.objects.annotate(
            nb_inscriptions=Count('inscriptions')
        ).filter(nb_inscriptions__gt=0).order_by('-nb_inscriptions')[:5]
        
        top_activites_data = [
            {'titre': a.titre, 'inscriptions': a.nb_inscriptions}
            for a in top_activites
        ]
        
        return Response({
            'total_activites': total_activites,
            'total_inscriptions': total_inscriptions,
            'total_inscriptions_confirmees': total_inscriptions_confirmees,
            'chiffre_affaires': float(chiffre_affaires),  # Convertir en float pour JSON
            'activites_par_statut': activites_par_statut,
            'inscriptions_par_mois': inscriptions_par_mois,
            'top_activites': top_activites_data
        })