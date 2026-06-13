# dechets/views.py
from rest_framework import viewsets, generics, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Count, Sum, Q
from django.utils import timezone
from django.shortcuts import get_object_or_404  # AJOUTÉ
from datetime import timedelta, date
from .models import (
    Quartier, PointCollecte, CalendrierCollecte, Signalement,
    DemandeEncombrant, Tournee, StatsCollecte, TourneePoint  # AJOUTÉ TourneePoint
)
from .serializers import (
    QuartierSerializer, PointCollecteSerializer, CalendrierCollecteSerializer,
    SignalementListSerializer, SignalementCreateSerializer,
    DemandeEncombrantSerializer, DemandeEncombrantCreateSerializer,
    TourneeSerializer, TourneeUpdateSerializer, StatsCollecteSerializer
)
from .permissions import EstAgentOuAdmin, EstAdmin
from django.http import HttpResponse  # AJOUTÉ


class QuartierViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour les quartiers (lecture seule)"""
    queryset = Quartier.objects.all()
    serializer_class = QuartierSerializer
    permission_classes = [AllowAny]
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]  # AJOUTÉ
    search_fields = ['nom', 'code_postal']  # AJOUTÉ


class PointCollecteViewSet(viewsets.ModelViewSet):
    """ViewSet pour les points de collecte"""
    queryset = PointCollecte.objects.all()
    serializer_class = PointCollecteSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter]
    filterset_fields = ['quartier', 'type', 'statut']
    search_fields = ['adresse_reference', 'code']
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [EstAdmin()]
        return [AllowAny()]
    
    @action(detail=True, methods=['get'])
    def signalements(self, request, pk=None):
        """Récupérer les signalements pour ce point de collecte"""
        point = self.get_object()
        signalements = Signalement.objects.filter(point_collecte=point).order_by('-date_signalement')
        serializer = SignalementListSerializer(signalements, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def statistiques(self, request, pk=None):
        """Statistiques du point de collecte"""
        point = self.get_object()
        from django.db.models import Avg
        
        stats = {
            'total_signalements': Signalement.objects.filter(point_collecte=point).count(),
            'signalements_traites': Signalement.objects.filter(point_collecte=point, statut='traite').count(),
            'dernier_vidage': point.dernier_vidage,
            'collectes_count': point.collectes_count
        }
        return Response(stats)


class CalendrierCollecteViewSet(viewsets.ReadOnlyModelViewSet):
    """ViewSet pour le calendrier des collectes (lecture seule)"""
    queryset = CalendrierCollecte.objects.filter(est_actif=True)
    serializer_class = CalendrierCollecteSerializer
    filter_backends = [DjangoFilterBackend]
    filterset_fields = ['quartier', 'jour_semaine', 'type_dechet']
    
    @action(detail=False, methods=['get'])
    def prochaines(self, request):
        """Prochaines collectes à venir"""
        today = date.today()
        current_weekday = today.weekday()
        
        # Trouver les prochaines collectes
        prochaines = []
        calendriers = self.get_queryset()
        
        for cal in calendriers:
            jours_restants = (cal.jour_semaine - current_weekday) % 7
            if jours_restants == 0 and cal.jour_semaine != current_weekday:
                jours_restants = 7
            prochaine_date = today + timedelta(days=jours_restants)
            prochaines.append({
                'quartier': cal.quartier.nom,
                'jour': cal.get_jour_semaine_display(),
                'date': prochaine_date,
                'type_dechet': cal.get_type_dechet_display(),
                'est_semaine_impaire': cal.est_semaine_impaire
            })
        
        return Response(sorted(prochaines, key=lambda x: x['date']))


class SignalementViewSet(viewsets.ModelViewSet):
    """ViewSet pour les signalements citoyens"""
    serializer_class = SignalementListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['type_signalement', 'statut']
    search_fields = ['adresse_description', 'description']
    ordering_fields = ['date_signalement', 'date_traitement']
    ordering = ['-date_signalement']
    
    def get_queryset(self):
        if self.request.user.is_authenticated and (
            self.request.user.is_staff or 
            getattr(self.request.user, 'role', '') in ['admin', 'agent']
        ):
            return Signalement.objects.all()
        
        if self.request.user.is_authenticated:
            return Signalement.objects.filter(
                Q(citoyen=self.request.user) | Q(telephone=self.request.user.telephone)
            )
        
        return Signalement.objects.none()
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SignalementCreateSerializer
        return SignalementListSerializer
    
    def get_permissions(self):
        if self.action in ['update', 'partial_update', 'destroy']:
            return [EstAgentOuAdmin()]
        return [IsAuthenticatedOrReadOnly()]
    
    def perform_create(self, serializer):
        """Création d'un signalement"""
        extra_data = {}
        
        if self.request.user.is_authenticated:
            extra_data['citoyen'] = self.request.user
            extra_data['nom_citoyen'] = self.request.user.get_full_name() or self.request.user.username
            extra_data['telephone'] = str(self.request.user.telephone) if self.request.user.telephone else ''
        else:
            # Pour les non-authentifiés, les données viennent du formulaire
            extra_data['nom_citoyen'] = serializer.validated_data.get('nom_citoyen', '')
            extra_data['telephone'] = serializer.validated_data.get('telephone', '')
        
        signalement = serializer.save(**extra_data)
        
        # TODO: Envoyer notification aux agents
        # from .notifications import notifier_nouveau_signalement
        # notifier_nouveau_signalement(signalement)
        
        return signalement
    
    @action(detail=True, methods=['post'])
    def traiter(self, request, pk=None):
        """Marquer un signalement comme traité"""
        signalement = self.get_object()
        
        if signalement.statut == 'traite':
            return Response(
                {'error': 'Ce signalement est déjà traité'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        signalement.statut = 'traite'
        signalement.commentaire_traitement = request.data.get('commentaire', '')
        signalement.agent_traitement = request.user
        signalement.date_traitement = timezone.now()
        signalement.save(update_fields=['statut', 'commentaire_traitement', 'agent_traitement', 'date_traitement'])
        
        # TODO: Notifier le citoyen
        # from .notifications import notifier_signalement_traite
        # notifier_signalement_traite(signalement)
        
        return Response({'message': 'Signalement marqué comme traité'})
    
    @action(detail=True, methods=['post'])
    def rejeter(self, request, pk=None):
        """Rejeter un signalement"""
        signalement = self.get_object()
        
        if signalement.statut != 'en_attente':
            return Response(
                {'error': 'Seuls les signalements en attente peuvent être rejetés'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        motif = request.data.get('motif', '')
        if not motif:
            return Response(
                {'error': 'Un motif de rejet est requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        signalement.statut = 'rejete'
        signalement.commentaire_traitement = motif
        signalement.agent_traitement = request.user
        signalement.date_traitement = timezone.now()
        signalement.save(update_fields=['statut', 'commentaire_traitement', 'agent_traitement', 'date_traitement'])
        
        return Response({'message': 'Signalement rejeté'})


class DemandeEncombrantViewSet(viewsets.ModelViewSet):
    """ViewSet pour les demandes d'enlèvement d'encombrants"""
    serializer_class = DemandeEncombrantSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['statut', 'type_encombrant']
    ordering_fields = ['date_demande', 'date_souhaitee']
    ordering = ['-date_demande']
    
    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, 'role', '') in ['admin', 'agent']:
            return DemandeEncombrant.objects.all()
        return DemandeEncombrant.objects.filter(citoyen=self.request.user)
    
    def get_serializer_class(self):
        if self.action == 'create':
            return DemandeEncombrantCreateSerializer
        return DemandeEncombrantSerializer
    
    def perform_create(self, serializer):
        demande = serializer.save(citoyen=self.request.user)
        
        # TODO: Envoyer confirmation
        # from .notifications import notifier_demande_encombrant
        # notifier_demande_encombrant(demande)
        
        return demande
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une demande"""
        demande = self.get_object()
        
        if demande.statut not in ['en_attente', 'planifiee']:
            return Response(
                {'error': f'Cette demande ne peut pas être annulée (statut: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demande.statut = 'annulee'
        demande.save(update_fields=['statut'])
        
        return Response({'message': 'Demande annulée avec succès'})
    
    @action(detail=True, methods=['post'])
    def planifier(self, request, pk=None):
        """Planifier une demande (admin uniquement)"""
        if not EstAdmin().has_permission(request, self):
            return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        
        demande = self.get_object()
        date_planifiee = request.data.get('date_planifiee')
        agent_id = request.data.get('agent_id')
        
        if not date_planifiee:
            return Response({'error': 'Date planifiée requise'}, status=status.HTTP_400_BAD_REQUEST)
        
        demande.statut = 'planifiee'
        demande.date_planifiee = date_planifiee
        if agent_id:
            demande.agent_assignee_id = agent_id
        demande.save(update_fields=['statut', 'date_planifiee', 'agent_assignee'])
        
        # TODO: Notifier le citoyen
        # from .notifications import notifier_demande_planifiee
        # notifier_demande_planifiee(demande)
        
        return Response({'message': 'Demande planifiée avec succès'})


class TourneeViewSet(viewsets.ModelViewSet):
    """ViewSet pour les tournées de collecte"""
    queryset = Tournee.objects.all()
    serializer_class = TourneeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['date', 'quartier', 'statut', 'agent']
    ordering = ['date', 'heure_debut']
    permission_classes = [EstAgentOuAdmin]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return TourneeUpdateSerializer
        return TourneeSerializer
    
    @action(detail=True, methods=['post'])
    def commencer(self, request, pk=None):
        """Démarrer une tournée"""
        tournee = self.get_object()
        
        if tournee.statut != 'planifiee':
            return Response(
                {'error': f'Seules les tournées planifiées peuvent être démarrées (statut: {tournee.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tournee.statut = 'en_cours'
        tournee.debut_reel = timezone.now()
        tournee.save(update_fields=['statut', 'debut_reel'])
        
        return Response({'message': 'Tournée démarrée', 'debut_reel': tournee.debut_reel})
    
    @action(detail=True, methods=['post'])
    def terminer(self, request, pk=None):
        """Terminer une tournée"""
        tournee = self.get_object()
        
        if tournee.statut != 'en_cours':
            return Response(
                {'error': f'Seules les tournées en cours peuvent être terminées (statut: {tournee.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        tournee.statut = 'terminee'
        tournee.fin_reelle = timezone.now()
        tournee.save(update_fields=['statut', 'fin_reelle'])
        
        # Mettre à jour les stats
        today = date.today()
        stats, created = StatsCollecte.objects.get_or_create(date=today)
        
        bacs_vides = tournee.tourneepoint_set.filter(est_vide=True).count()
        stats.bacs_vides += bacs_vides
        stats.tournees_completees += 1
        stats.save(update_fields=['bacs_vides', 'tournees_completees'])
        
        return Response({
            'message': 'Tournée terminée',
            'bacs_vides': bacs_vides,
            'duree_minutes': tournee.calculer_duree()
        })
    
    @action(detail=True, methods=['post'])
    def valider_point(self, request, pk=None):
        """Valider qu'un point a été vidé"""
        tournee = self.get_object()
        point_id = request.data.get('point_id')
        photo = request.FILES.get('photo')
        
        if not point_id:
            return Response(
                {'error': 'point_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            tp = tournee.tourneepoint_set.get(point_id=point_id)
            
            if tp.est_vide:
                return Response(
                    {'error': 'Ce point a déjà été validé'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            tp.est_vide = True
            if photo:
                tp.photo_preuve = photo
            tp.heure_passage = timezone.now()
            tp.commentaire = request.data.get('commentaire', '')
            tp.save(update_fields=['est_vide', 'photo_preuve', 'heure_passage', 'commentaire'])
            
            # Mettre à jour le point de collecte
            point = tp.point
            point.dernier_vidage = timezone.now()
            point.collectes_count += 1
            point.save(update_fields=['dernier_vidage', 'collectes_count'])
            
            return Response({
                'message': 'Point validé avec succès',
                'point': {
                    'id': point.id,
                    'code': point.code,
                    'adresse': point.adresse_reference
                }
            })
            
        except TourneePoint.DoesNotExist:
            return Response(
                {'error': 'Point non trouvé dans cette tournée'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def progression(self, request, pk=None):
        """Progression de la tournée"""
        tournee = self.get_object()
        total_points = tournee.tourneepoint_set.count()
        points_valides = tournee.tourneepoint_set.filter(est_vide=True).count()
        
        progression = 0
        if total_points > 0:
            progression = round((points_valides / total_points) * 100, 1)
        
        return Response({
            'total_points': total_points,
            'points_valides': points_valides,
            'progression': progression,
            'statut': tournee.statut
        })


class DashboardStatsView(generics.GenericAPIView):
    """Statistiques pour le dashboard admin"""
    permission_classes = [EstAdmin]
    
    def get(self, request):
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Signalements
        signalements_en_attente = Signalement.objects.filter(statut='en_attente').count()
        signalements_mois = Signalement.objects.filter(date_signalement__date__gte=month_ago).count()
        signalements_par_type = Signalement.objects.values('type_signalement').annotate(count=Count('id'))
        
        # Collectes
        collectes_semaine = Tournee.objects.filter(date__gte=week_ago, statut='terminee').count()
        
        stats_collectes = StatsCollecte.objects.filter(date__gte=week_ago).aggregate(
            total_tonnes=Sum('tonnes_collectees'),
            total_bacs=Sum('bacs_vides')
        )
        tonnes_semaine = stats_collectes['total_tonnes'] or 0
        bacs_semaine = stats_collectes['total_bacs'] or 0
        
        # Demandes encombrants
        demandes_en_attente = DemandeEncombrant.objects.filter(statut='en_attente').count()
        
        # Top quartiers signalements
        top_quartiers = Signalement.objects.filter(
            point_collecte__isnull=False
        ).values('point_collecte__quartier__nom').annotate(
            count=Count('id')
        ).order_by('-count')[:5]
        
        # Efficacité agent (si agent connecté)
        efficacite = None
        if request.user.role == 'agent':
            tournees_agent = Tournee.objects.filter(agent=request.user, statut='terminee')
            total_points = 0
            points_vides = 0
            for t in tournees_agent:
                total_points += t.tourneepoint_set.count()
                points_vides += t.tourneepoint_set.filter(est_vide=True).count()
            if total_points > 0:
                efficacite = round((points_vides / total_points) * 100, 1)
        
        return Response({
            'signalements_en_attente': signalements_en_attente,
            'signalements_mois': signalements_mois,
            'signalements_par_type': list(signalements_par_type),
            'collectes_semaine': collectes_semaine,
            'tonnes_semaine': round(float(tonnes_semaine), 1),
            'bacs_semaine': bacs_semaine,
            'demandes_en_attente': demandes_en_attente,
            'top_quartiers': list(top_quartiers),
            'efficacite_agent': efficacite
        })


class TourneeDuJourView(generics.ListAPIView):
    """Tournée du jour pour l'agent connecté"""
    serializer_class = TourneeSerializer
    permission_classes = [EstAgentOuAdmin]
    
    def get_queryset(self):
        today = date.today()
        return Tournee.objects.filter(date=today, agent=self.request.user)


class RapprochementView(generics.ListAPIView):
    """Liste des collectes à venir pour un quartier (rappel)"""
    serializer_class = CalendrierCollecteSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        quartier_slug = self.request.query_params.get('quartier')
        if quartier_slug:
            return CalendrierCollecte.objects.filter(
                quartier__slug=quartier_slug,
                est_actif=True
            )
        return CalendrierCollecte.objects.none()


class VoiceTwiMLView(generics.GenericAPIView):
    """Génère le TwiML pour les appels vocaux (Twilio)"""
    permission_classes = [AllowAny]
    
    def get(self, request):
        message = request.query_params.get('message', 'Bienvenue sur le service de gestion des déchets de la municipalité.')
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="fr-FR">
        {message}
    </Say>
</Response>"""
        return HttpResponse(twiml, content_type='text/xml')
    
    def post(self, request):
        """Pour les interactions vocales plus complexes"""
        # Récupérer les données de l'appel
        from urllib.parse import parse_qs
        body = request.body.decode('utf-8')
        data = parse_qs(body)
        
        user_input = data.get('Digits', [None])[0]
        
        # Construire la réponse
        if user_input == '1':
            message = "Pour signaler un dépôt sauvage, veuillez utiliser notre application mobile."
        elif user_input == '2':
            message = "Pour connaître votre jour de collecte, consultez notre site web."
        else:
            message = "Merci de contacter notre service au 0800 123 456."
        
        twiml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="fr-FR">
        {message}
    </Say>
</Response>"""
        return HttpResponse(twiml, content_type='text/xml')


class USSDView(generics.GenericAPIView):
    """Endpoint USSD pour les numéros courts"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        session_id = request.data.get('sessionId')
        phone_number = request.data.get('phoneNumber')
        text = request.data.get('text', '')
        
        # Service USSD à implémenter
        response = self.traiter_requete_ussd(session_id, phone_number, text)
        
        return Response({'response': response})
    
    def traiter_requete_ussd(self, session_id, phone_number, text):
        """Traite la requête USSD"""
        levels = text.split('*')
        level = len(levels)
        
        if text == '':
            # Menu principal
            return """CON Bienvenue sur le service déchets
1. Signaler un dépôt sauvage
2. Calendrier des collectes
3. Demander un enlèvement
0. Quitter"""
        
        elif text == '1':
            return """CON Signaler un dépôt sauvage
Entrez l'adresse du dépôt:"""
        
        elif text.startswith('1*'):
            address = text.split('*')[1]
            # Sauvegarder le signalement
            return f"END Merci pour votre signalement à l'adresse: {address}. Un agent traitera votre demande sous 48h."
        
        elif text == '2':
            return """CON Calendrier des collectes
Entrez votre quartier:"""
        
        elif text.startswith('2*'):
            quartier = text.split('*')[1]
            return f"END Les collectes dans {quartier} ont lieu les lundis, mercredis et vendredis."
        
        elif text == '3':
            return """CON Demande d'enlèvement
1. Encombrants
2. Déchets verts
3. Déchets électroniques
0. Retour"""
        
        elif text == '3*1':
            return "END Pour les encombrants, veuillez contacter le 0800 123 456 ou utiliser notre application."
        
        elif text == '0':
            return "END Merci d'avoir utilisé le service déchets. Au revoir."
        
        else:
            return "END Option invalide. Veuillez réessayer."


class TestNotificationView(generics.GenericAPIView):
    """Endpoint de test pour les notifications"""
    permission_classes = [EstAdmin]
    
    def post(self, request):
        quartier_id = request.data.get('quartier_id')
        type_notif = request.data.get('type', 'rappel')
        
        if not quartier_id:
            return Response(
                {'error': 'quartier_id requis'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            quartier = Quartier.objects.get(id=quartier_id)
        except Quartier.DoesNotExist:
            return Response(
                {'error': 'Quartier non trouvé'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if type_notif == 'rappel':
            # Importer le service de notification
            from .notifications import NotificationService
            tomorrow = (date.today().weekday() + 1) % 7
            result = NotificationService.envoyer_rappel_collecte(quartier_id, tomorrow)
            return Response({
                'success': result,
                'message': f'Test de rappel envoyé pour {quartier.nom}'
            })
        
        elif type_notif == 'signalement':
            return Response({
                'success': True,
                'message': 'Test de notification de signalement simulé'
            })
        
        return Response(
            {'error': f'Type de notification non reconnu: {type_notif}'},
            status=status.HTTP_400_BAD_REQUEST
        )