from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count, Q, Sum, F
from django.utils import timezone
from datetime import timedelta
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from .models import TacheAgent, NotificationAgent
from .serializers import TacheAgentSerializer, NotificationAgentSerializer


def is_agent(user):
    return user.is_authenticated and (user.is_staff or getattr(user, 'role', '') in ['agent', 'admin'])


class AgentDashboardStatsView(APIView):
    """Statistiques pour le tableau de bord agent"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        today = timezone.now().date()
        
        # Vérifier si l'utilisateur est agent
        if not (user.is_staff or getattr(user, 'role', '') in ['agent', 'admin']):
            return Response({'error': 'Accès non autorisé'}, status=403)
        
        # ============================================
        # 1. TÂCHES DE L'AGENT
        # ============================================
        taches = TacheAgent.objects.filter(assigne_a=user)
        
        taches_stats = {
            'total': taches.count(),
            'en_attente': taches.filter(statut='en_attente').count(),
            'en_cours': taches.filter(statut='en_cours').count(),
            'terminees': taches.filter(statut='terminee').count(),
            'en_retard': taches.filter(statut__in=['en_attente', 'en_cours'], date_echeance__lt=timezone.now()).count(),
            'par_priorite': {
                'haute': taches.filter(priorite='haute', statut__in=['en_attente', 'en_cours']).count(),
                'moyenne': taches.filter(priorite='moyenne', statut__in=['en_attente', 'en_cours']).count(),
                'basse': taches.filter(priorite='basse', statut__in=['en_attente', 'en_cours']).count(),
            },
            'par_type': dict(taches.values('type_tache').annotate(count=Count('id'))),
            'prochaines_echeances': TacheAgentSerializer(
                taches.filter(statut__in=['en_attente', 'en_cours'], date_echeance__gte=timezone.now())
                .order_by('date_echeance')[:5], many=True
            ).data,
        }
        
        # ============================================
        # 2. STATISTIQUES ÉTAT CIVIL (agent)
        # ============================================
        try:
            from etat_civil.models import DemandeActe
            etat_civil_stats = {
                'a_traiter': DemandeActe.objects.filter(statut='en_attente').count(),
                'en_cours': DemandeActe.objects.filter(agent_traitant=user, statut='en_cours').count(),
                'traitees_mois': DemandeActe.objects.filter(
                    agent_traitant=user,
                    date_traitement__date__gte=today - timedelta(days=30)
                ).count(),
                'dernieres_demandes': list(
                    DemandeActe.objects.filter(agent_traitant=user)
                    .order_by('-date_creation')[:5]
                    .values('reference', 'type_acte', 'statut', 'date_creation')
                ),
            }
        except:
            etat_civil_stats = {'error': 'Module non disponible'}

        # ============================================
        # 3. STATISTIQUES DÉCHETS (agent)
        # ============================================
        try:
            from dechets.models import Signalement, Tournee
            dechets_stats = {
                'signalements_urgents': Signalement.objects.filter(priorite='urgente', statut='en_attente').count(),
                'signalements_a_traiter': Signalement.objects.filter(statut='en_attente').count(),
                'tournees_aujourdhui': Tournee.objects.filter(agent=user, date=timezone.now().date()).count(),
                'tournees_semaine': Tournee.objects.filter(agent=user, date__gte=today, date__lte=today+timedelta(days=7)).count(),
                'derniers_signalements': list(
                    Signalement.objects.filter(agent_traitement=user)
                    .order_by('-date_signalement')[:5]
                    .values('type_signalement', 'statut', 'date_signalement')
                ),
            }
        except:
            dechets_stats = {'error': 'Module non disponible'}

        # ============================================
        # 4. STATISTIQUES ARCHIVES (agent)
        # ============================================
        try:
            from archives.models import DemandeAccesArchive
            archives_stats = {
                'demandes_en_attente': DemandeAccesArchive.objects.filter(statut='en_attente').count(),
                'validees_mois': DemandeAccesArchive.objects.filter(
                    moderateur=user,
                    date_moderation__date__gte=today - timedelta(days=30)
                ).count(),
                'a_traiter': DemandeAccesArchive.objects.filter(statut='en_attente').count(),
            }
        except:
            archives_stats = {'error': 'Module non disponible'}

        # ============================================
        # 5. STATISTIQUES PAIEMENTS (agent)
        # ============================================
        try:
            from paiements.models import TransactionPaiement
            paiements_stats = {
                'encaissements_jour': TransactionPaiement.objects.filter(
                    encaisse_par=user,
                    date_creation__date=today,
                    statut='confirme'
                ).aggregate(total=Sum('montant_total'))['total'] or 0,
                'transactions_jour': TransactionPaiement.objects.filter(
                    encaisse_par=user,
                    date_creation__date=today
                ).count(),
                'a_verifier': TransactionPaiement.objects.filter(statut='en_attente').count(),
            }
        except:
            paiements_stats = {'error': 'Module non disponible'}

        # ============================================
        # 6. NOTIFICATIONS
        # ============================================
        notifications = NotificationAgent.objects.filter(utilisateur=user, est_lue=False)
        notifications_stats = {
            'non_lues': notifications.count(),
            'recentes': NotificationAgentSerializer(
                notifications.order_by('-date_creation')[:5], many=True
            ).data,
        }

        # ============================================
        # 7. PERFORMANCE AGENT
        # ============================================
        total_taches = taches.filter(statut='terminee').count()
        taches_dans_les_delais = taches.filter(
            statut='terminee',
            date_traitement__lte=F('date_echeance')
        ).count()
        
        performance_stats = {
            'taux_realisation': round((total_taches / taches.count() * 100) if taches.count() > 0 else 0, 1),
            'taux_delais': round((taches_dans_les_delais / total_taches * 100) if total_taches > 0 else 0, 1),
            'taches_realisees_mois': taches.filter(
                statut='terminee',
                date_traitement__date__gte=today - timedelta(days=30)
            ).count(),
        }

        return Response({
            'agent': {
                'nom': user.get_full_name() or user.username,
                'email': user.email,
                'role': getattr(user, 'role', 'agent'),
            },
            'taches': taches_stats,
            'etat_civil': etat_civil_stats,
            'dechets': dechets_stats,
            'archives': archives_stats,
            'paiements': paiements_stats,
            'notifications': notifications_stats,
            'performance': performance_stats,
            'date': today,
        })


class AgentTachesView(APIView):
    """Gestion des tâches de l'agent"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Lister les tâches de l'agent"""
        user = request.user
        statut = request.query_params.get('statut', 'en_attente')
        type_tache = request.query_params.get('type', '')
        
        taches = TacheAgent.objects.filter(assigne_a=user)
        
        if statut != 'all':
            taches = taches.filter(statut=statut)
        if type_tache:
            taches = taches.filter(type_tache=type_tache)
        
        serializer = TacheAgentSerializer(taches.order_by('-priorite', 'date_echeance'), many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Créer une nouvelle tâche (admin uniquement)"""
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'admin'):
            return Response({'error': 'Non autorisé'}, status=403)
        
        serializer = TacheAgentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(cree_par=request.user)
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)


class AgentTacheDetailView(APIView):
    """Détail et gestion d'une tâche"""
    permission_classes = [IsAuthenticated]
    
    def get_object(self, pk, user):
        try:
            return TacheAgent.objects.get(id=pk, assigne_a=user)
        except TacheAgent.DoesNotExist:
            return None
    
    def get(self, request, pk):
        tache = self.get_object(pk, request.user)
        if not tache:
            return Response({'error': 'Tâche non trouvée'}, status=404)
        serializer = TacheAgentSerializer(tache)
        return Response(serializer.data)
    
    def post(self, request, pk):
        tache = self.get_object(pk, request.user)
        if not tache:
            return Response({'error': 'Tâche non trouvée'}, status=404)
        
        action = request.data.get('action')
        
        if action == 'demarrer':
            tache.statut = 'en_cours'
            tache.save()
            return Response({'message': 'Tâche démarrée'})
        
        elif action == 'terminer':
            tache.statut = 'terminee'
            tache.date_traitement = timezone.now()
            tache.commentaire_traitement = request.data.get('commentaire', '')
            tache.save()
            return Response({'message': 'Tâche terminée'})
        
        elif action == 'annuler':
            tache.statut = 'annulee'
            tache.save()
            return Response({'message': 'Tâche annulée'})
        
        return Response({'error': 'Action inconnue'}, status=400)


class AgentNotificationsView(APIView):
    """Gestion des notifications"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        notifications = NotificationAgent.objects.filter(utilisateur=request.user)
        serializer = NotificationAgentSerializer(notifications, many=True)
        return Response(serializer.data)
    
    def post(self, request):
        """Marquer une notification comme lue"""
        notification_id = request.data.get('notification_id')
        try:
            notification = NotificationAgent.objects.get(id=notification_id, utilisateur=request.user)
            notification.est_lue = True
            notification.save()
            return Response({'message': 'Notification marquée comme lue'})
        except NotificationAgent.DoesNotExist:
            return Response({'error': 'Notification non trouvée'}, status=404)


@user_passes_test(is_agent)
def agent_dashboard_home(request):
    """Page HTML du tableau de bord agent"""
    return render(request, 'dashboard_agent/index.html')