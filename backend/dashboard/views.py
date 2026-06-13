from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Count, Sum, Q, Avg, F, Value, IntegerField
from django.db.models.functions import ExtractMonth, ExtractYear, TruncMonth
from django.utils import timezone
from datetime import timedelta, datetime
from django.contrib.auth import get_user_model
from rest_framework import status
from django.contrib.admin.views.decorators import staff_member_required
import logging
from calendar import month_name

logger = logging.getLogger(__name__)
User = get_user_model()


class DashboardStatsView(APIView):
    """Tableau de bord avec statistiques globales ultra-détaillées"""
    permission_classes = [IsAdminUser]

    def get(self, request):
        today = timezone.now().date()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        year_ago = today - timedelta(days=365)

        # ============================================
        # 1. STATISTIQUES UTILISATEURS
        # ============================================
        users_stats = {
            'total': User.objects.count(),
            'active': User.objects.filter(is_active=True).count(),
            'staff': User.objects.filter(is_staff=True).count(),
            'new_week': User.objects.filter(date_joined__date__gte=week_ago).count(),
            'new_month': User.objects.filter(date_joined__date__gte=month_ago).count(),
            'new_year': User.objects.filter(date_joined__date__gte=year_ago).count(),
            'by_role': dict(User.objects.values('role').annotate(count=Count('id'))),
            'evolution_mensuelle': [],
        }
        
        for i in range(11, -1, -1):
            date_start = (today.replace(day=1) - timedelta(days=30*i))
            date_end = (date_start + timedelta(days=32)).replace(day=1)
            count = User.objects.filter(
                date_joined__date__gte=date_start,
                date_joined__date__lt=date_end
            ).count()
            users_stats['evolution_mensuelle'].append({
                'mois': date_start.strftime('%B %Y'),
                'count': count
            })

        # ============================================
        # 2. STATISTIQUES ÉTAT CIVIL
        # ============================================
        try:
            from etat_civil.models import DemandeActe, ConfigurationTarif
            etat_civil_stats = {
                'total': DemandeActe.objects.count(),
                'en_attente': DemandeActe.objects.filter(statut='en_attente').count(),
                'en_cours': DemandeActe.objects.filter(statut='en_cours').count(),
                'valide_agent': DemandeActe.objects.filter(statut='valide_agent').count(),
                'valide_citoyen': DemandeActe.objects.filter(statut='valide_citoyen').count(),
                'signe': DemandeActe.objects.filter(statut='signe').count(),
                'delivre': DemandeActe.objects.filter(statut='delivre').count(),
                'rejete': DemandeActe.objects.filter(statut='rejete').count(),
                'by_type': dict(DemandeActe.objects.values('type_acte').annotate(count=Count('id'))),
                'by_month': [],
                'tarifs': list(ConfigurationTarif.objects.filter(est_actif=True).values('type_acte', 'tarif_normal', 'tarif_retard')),
                'taux_traitement': 0,
            }
            
            total_traitees = etat_civil_stats['delivre'] + etat_civil_stats['signe'] + etat_civil_stats['rejete']
            if etat_civil_stats['total'] > 0:
                etat_civil_stats['taux_traitement'] = round((total_traitees / etat_civil_stats['total']) * 100, 1)
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                count = DemandeActe.objects.filter(
                    date_creation__date__gte=date_start,
                    date_creation__date__lt=date_end
                ).count()
                etat_civil_stats['by_month'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
                
        except Exception as e:
            logger.error(f"Erreur état civil: {e}")
            etat_civil_stats = {'error': str(e)}

        # ============================================
        # 3. STATISTIQUES ANNUAIRES
        # ============================================
        try:
            from annuaires.models import Structure, Elu, AvisStructure, ContactStructure
            annuaires_stats = {
                'total_structures': Structure.objects.filter(statut='actif').count(),
                'total_elus': Elu.objects.filter(est_actif=True).count(),
                'categories': dict(Structure.objects.values('type_structure').annotate(count=Count('id'))),
                'structures_par_ville': dict(Structure.objects.values('ville').annotate(count=Count('id')).order_by('-count')[:5]),
                'note_moyenne': round(AvisStructure.objects.filter(est_approuve=True).aggregate(avg=Avg('note'))['avg'] or 0, 1),
                'total_avis': AvisStructure.objects.filter(est_approuve=True).count(),
                'total_contacts': ContactStructure.objects.count(),
                'structures_populaires': list(Structure.objects.filter(statut='actif').order_by('-vue_count')[:5].values('nom', 'vue_count')),
                'elus_par_fonction': dict(Elu.objects.values('fonction').annotate(count=Count('id'))),
            }
        except Exception as e:
            logger.error(f"Erreur annuaires: {e}")
            annuaires_stats = {'error': str(e)}

        # ============================================
        # 4. STATISTIQUES ACTIVITÉS
        # ============================================
        try:
            from activites.models import Activite, Inscription, AvisActivite
            activites_stats = {
                'total_activites': Activite.objects.filter(statut='publie').count(),
                'a_venir': Activite.objects.filter(date_debut__gte=timezone.now(), statut='publie').count(),
                'en_cours': Activite.objects.filter(date_debut__lte=timezone.now(), date_fin__gte=timezone.now(), statut='publie').count(),
                'terminees': Activite.objects.filter(date_fin__lt=timezone.now(), statut='publie').count(),
                'annulees': Activite.objects.filter(statut='annule').count(),
                'total_inscriptions': Inscription.objects.filter(statut='confirme').count(),
                'by_category': dict(Activite.objects.values('categorie__nom').annotate(count=Count('id'))),
                'activites_populaires': list(Activite.objects.filter(statut='publie').order_by('-vue_count')[:5].values('titre', 'vue_count', 'date_debut')),
                'note_moyenne': AvisActivite.objects.filter(est_approuve=True).aggregate(avg=Avg('note'))['avg'] or 0,
                'evolution_mensuelle': [],
            }
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                count = Activite.objects.filter(
                    date_creation__date__gte=date_start,
                    date_creation__date__lt=date_end,
                    statut='publie'
                ).count()
                activites_stats['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
                
        except Exception as e:
            logger.error(f"Erreur activités: {e}")
            activites_stats = {'error': str(e)}

        # ============================================
        # 5. STATISTIQUES ACTUALITÉS
        # ============================================
        try:
            from actualites.models import Publication, CategorieActualite, Commentaire, Reaction, HistoriqueConsultation
            
            actualites_stats = {
                'total': Publication.objects.filter(statut='publie').count(),
                'brouillons': Publication.objects.filter(statut='brouillon').count(),
                'archives': Publication.objects.filter(statut='archive').count(),
                'a_la_une': Publication.objects.filter(est_a_la_une=True, statut='publie').count(),
                'this_week': Publication.objects.filter(date_publication__date__gte=week_ago, statut='publie').count(),
                'this_month': Publication.objects.filter(date_publication__date__gte=month_ago, statut='publie').count(),
                'this_year': Publication.objects.filter(date_publication__date__gte=year_ago, statut='publie').count(),
                'vues_totales': Publication.objects.aggregate(total=Sum('vue_count'))['total'] or 0,
                'vues_moyenne': round(Publication.objects.filter(vue_count__gt=0).aggregate(avg=Avg('vue_count'))['avg'] or 0, 1),
                'partages_totaux': Publication.objects.aggregate(total=Sum('partage_count'))['total'] or 0,
                'top_actualites': list(
                    Publication.objects.filter(statut='publie')
                    .order_by('-vue_count')[:5]
                    .values('id', 'titre', 'vue_count', 'partage_count', 'date_publication')
                ),
                'par_categorie': [],
                'commentaires': {
                    'total': Commentaire.objects.filter(est_approuve=True).count(),
                    'en_attente': Commentaire.objects.filter(est_approuve=False).count(),
                    'this_week': Commentaire.objects.filter(est_approuve=True, date_creation__date__gte=week_ago).count(),
                    'this_month': Commentaire.objects.filter(est_approuve=True, date_creation__date__gte=month_ago).count(),
                    'moyenne_par_article': 0,
                },
                'reactions': {
                    'total': Reaction.objects.count(),
                    'this_month': Reaction.objects.filter(date_creation__date__gte=month_ago).count(),
                    'par_type': dict(Reaction.objects.values('type_reaction').annotate(count=Count('id'))),
                },
                'consultations': {
                    'total': HistoriqueConsultation.objects.count(),
                    'this_month': HistoriqueConsultation.objects.filter(date_consultation__date__gte=month_ago).count(),
                },
                'evolution_mensuelle': [],
            }
            
            total_publications = Publication.objects.filter(statut='publie').count()
            if total_publications > 0:
                actualites_stats['commentaires']['moyenne_par_article'] = round(
                    actualites_stats['commentaires']['total'] / total_publications, 1
                )
            
            for cat in CategorieActualite.objects.all():
                count = Publication.objects.filter(categorie=cat, statut='publie').count()
                vues = Publication.objects.filter(categorie=cat, statut='publie').aggregate(total=Sum('vue_count'))['total'] or 0
                if count > 0:
                    actualites_stats['par_categorie'].append({
                        'nom': cat.nom,
                        'count': count,
                        'vues': vues
                    })
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                count = Publication.objects.filter(
                    date_publication__date__gte=date_start,
                    date_publication__date__lt=date_end,
                    statut='publie'
                ).count()
                actualites_stats['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
            
        except Exception as e:
            logger.error(f"Erreur actualités: {e}")
            actualites_stats = {'error': str(e)}

        # ============================================
        # 6. STATISTIQUES ARCHIVES (CORRIGÉE)
        # ============================================
        try:
            from archives.models import Archive, CategorieArchive, DemandeAccesArchive, PretArchive, AvisArchive, LogArchive
            
            archives_stats = {
                'total_archives': Archive.objects.count(),
                'disponibles': Archive.objects.filter(statut='disponible').count(),
                'en_pret': Archive.objects.filter(statut='pret').count(),
                'en_restauration': Archive.objects.filter(statut='restauration').count(),
                'perdues': Archive.objects.filter(statut='perdu').count(),
                'numerisees': Archive.objects.filter(statut='numerise').count(),
                'vues_totales': Archive.objects.aggregate(total=Sum('vues'))['total'] or 0,
                'telechargements_totaux': Archive.objects.aggregate(total=Sum('telechargements'))['total'] or 0,
                'vues_moyenne': round(Archive.objects.filter(vues__gt=0).aggregate(avg=Avg('vues'))['avg'] or 0, 1),
                'top_archives': list(
                    Archive.objects.filter(statut='disponible')
                    .order_by('-vues')[:5]
                    .values('titre', 'reference', 'vues', 'telechargements')
                ),
                'top_telechargees': list(
                    Archive.objects.filter(statut='disponible')
                    .order_by('-telechargements')[:5]
                    .values('titre', 'reference', 'telechargements')
                ),
                'par_niveau_acces': dict(Archive.objects.values('niveau_acces').annotate(count=Count('id'))),
                'par_statut': dict(Archive.objects.values('statut').annotate(count=Count('id'))),
                'par_categorie': [],
                'par_periode': [],
                'demandes': {
                    'total': DemandeAccesArchive.objects.count(),
                    'en_attente': DemandeAccesArchive.objects.filter(statut='en_attente').count(),
                    'en_cours': DemandeAccesArchive.objects.filter(statut='en_cours').count(),
                    'validees': DemandeAccesArchive.objects.filter(statut='valide').count(),
                    'payees': DemandeAccesArchive.objects.filter(statut='paye').count(),
                    'rejetees': DemandeAccesArchive.objects.filter(statut='rejetee').count(),
                    'cloturees': DemandeAccesArchive.objects.filter(statut='cloturee').count(),
                    'this_month': DemandeAccesArchive.objects.filter(date_demande__date__gte=month_ago).count(),
                    'evolution_mensuelle': [],
                },
                'prets': {
                    'en_cours': PretArchive.objects.filter(statut='en_cours').count(),
                    'en_retard': PretArchive.objects.filter(statut='retard').count(),
                    'retournes': PretArchive.objects.filter(statut='retourne').count(),
                    'this_month': PretArchive.objects.filter(date_emprunt__date__gte=month_ago).count(),
                },
                'avis': {
                    'total': AvisArchive.objects.filter(est_approuve=True).count(),
                    'note_moyenne': round(AvisArchive.objects.filter(est_approuve=True).aggregate(avg=Avg('note'))['avg'] or 0, 1),
                    'repartition_notes': dict(
                        AvisArchive.objects.filter(est_approuve=True)
                        .values('note').annotate(count=Count('id'))
                    ),
                },
                'logs': {
                    'total': LogArchive.objects.count(),
                    'this_month': LogArchive.objects.filter(date_action__date__gte=month_ago).count(),
                },
                'evolution_mensuelle': [],
            }
            
            # Par catégorie
            for cat in CategorieArchive.objects.filter(est_actif=True):
                count = Archive.objects.filter(categorie=cat).count()
                vues = Archive.objects.filter(categorie=cat).aggregate(total=Sum('vues'))['total'] or 0
                if count > 0:
                    archives_stats['par_categorie'].append({
                        'nom': cat.nom,
                        'count': count,
                        'vues': vues
                    })
            
            # Par période (décennies) - CORRIGÉ
            periodes = []
            for year in range(1950, 2031, 10):
                count = Archive.objects.filter(
                    date_document__year__gte=year,
                    date_document__year__lt=year+10
                ).count()
                if count > 0:
                    periodes.append({
                        'periode': f"{year}-{year+9}",
                        'count': count
                    })
            archives_stats['par_periode'] = periodes
            
            # Évolution des demandes - CORRIGÉ (utilisation de datetime)
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                # Convertir en datetime pour éviter l'erreur
                start_datetime = datetime.combine(date_start, datetime.min.time())
                end_datetime = datetime.combine(date_end, datetime.min.time())
                count = DemandeAccesArchive.objects.filter(
                    date_demande__gte=start_datetime,
                    date_demande__lt=end_datetime
                ).count()
                archives_stats['demandes']['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
            
            # Évolution des archives - CORRIGÉ
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                start_datetime = datetime.combine(date_start, datetime.min.time())
                end_datetime = datetime.combine(date_end, datetime.min.time())
                count = Archive.objects.filter(
                    date_archivage__gte=start_datetime,
                    date_archivage__lt=end_datetime
                ).count()
                archives_stats['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
            
        except Exception as e:
            logger.error(f"Erreur archives: {e}")
            archives_stats = {'error': str(e)}

        # ============================================
        # 7. STATISTIQUES DÉCHETS
        # ============================================
        try:
            from dechets.models import (
                Quartier, PointCollecte, CalendrierCollecte, Signalement,
                DemandeEncombrant, Tournee, StatsCollecte, NotificationDechet
            )
            
            dechets_stats = {
                'quartiers': {
                    'total': Quartier.objects.count(),
                    'avec_points': Quartier.objects.filter(points_collecte__isnull=False).distinct().count(),
                },
                'points_collecte': {
                    'total': PointCollecte.objects.count(),
                    'actifs': PointCollecte.objects.filter(statut='actif').count(),
                    'pleins': PointCollecte.objects.filter(statut='plein').count(),
                    'casses': PointCollecte.objects.filter(statut='casse').count(),
                    'en_maintenance': PointCollecte.objects.filter(statut='en_maintenance').count(),
                    'par_type': dict(PointCollecte.objects.values('type').annotate(count=Count('id'))),
                    'par_quartier': dict(PointCollecte.objects.values('quartier__nom').annotate(count=Count('id')).order_by('-count')[:5]),
                    'taux_remplissage_moyen': round(PointCollecte.objects.aggregate(avg=Avg('niveau_remplissage'))['avg'] or 0, 1),
                    'points_critiques': PointCollecte.objects.filter(niveau_remplissage__gte=80).count(),
                },
                'signalements': {
                    'total': Signalement.objects.count(),
                    'en_attente': Signalement.objects.filter(statut='en_attente').count(),
                    'en_cours': Signalement.objects.filter(statut='en_cours').count(),
                    'traites': Signalement.objects.filter(statut='traite').count(),
                    'rejetes': Signalement.objects.filter(statut='rejete').count(),
                    'par_type': dict(Signalement.objects.values('type_signalement').annotate(count=Count('id'))),
                    'par_priorite': dict(Signalement.objects.values('priorite').annotate(count=Count('id'))),
                    'par_quartier': list(
                        Signalement.objects.values('point_collecte__quartier__nom')
                        .annotate(count=Count('id'))
                        .order_by('-count')[:5]
                    ),
                    'this_week': Signalement.objects.filter(date_signalement__date__gte=week_ago).count(),
                    'this_month': Signalement.objects.filter(date_signalement__date__gte=month_ago).count(),
                    'evolution_mensuelle': [],
                },
                'demandes_encombrants': {
                    'total': DemandeEncombrant.objects.count(),
                    'en_attente': DemandeEncombrant.objects.filter(statut='en_attente').count(),
                    'planifiees': DemandeEncombrant.objects.filter(statut='planifiee').count(),
                    'effectuees': DemandeEncombrant.objects.filter(statut='effectuee').count(),
                    'annulees': DemandeEncombrant.objects.filter(statut='annulee').count(),
                    'par_type': dict(DemandeEncombrant.objects.values('type_encombrant').annotate(count=Count('id'))),
                    'this_month': DemandeEncombrant.objects.filter(date_demande__date__gte=month_ago).count(),
                },
                'tournees': {
                    'total': Tournee.objects.count(),
                    'planifiees': Tournee.objects.filter(statut='planifiee').count(),
                    'en_cours': Tournee.objects.filter(statut='en_cours').count(),
                    'terminees': Tournee.objects.filter(statut='terminee').count(),
                    'annulees': Tournee.objects.filter(statut='annulee').count(),
                    'aujourdhui': Tournee.objects.filter(date=today).count(),
                    'this_week': Tournee.objects.filter(date__gte=week_ago).count(),
                    'distance_totale': round(Tournee.objects.aggregate(total=Sum('distance_totale'))['total'] or 0, 1),
                    'duree_totale': Tournee.objects.aggregate(total=Sum('duree_estimee'))['total'] or 0,
                },
                'collectes': {
                    'tonnes_total': round(StatsCollecte.objects.aggregate(total=Sum('tonnes_collectees'))['total'] or 0, 1),
                    'tonnes_mois': round(StatsCollecte.objects.filter(date__gte=month_ago).aggregate(total=Sum('tonnes_collectees'))['total'] or 0, 1),
                    'tonnes_annee': round(StatsCollecte.objects.filter(date__gte=year_ago).aggregate(total=Sum('tonnes_collectees'))['total'] or 0, 1),
                    'bacs_vides_total': StatsCollecte.objects.aggregate(total=Sum('bacs_vides'))['total'] or 0,
                    'bacs_vides_mois': StatsCollecte.objects.filter(date__gte=month_ago).aggregate(total=Sum('bacs_vides'))['total'] or 0,
                    'signalements_traites': StatsCollecte.objects.aggregate(total=Sum('signalements_traites'))['total'] or 0,
                    'evolution_mensuelle': [],
                    'meilleur_mois': None,
                },
                'notifications': {
                    'total': NotificationDechet.objects.count(),
                    'envoyees': NotificationDechet.objects.filter(est_envoyee=True).count(),
                    'this_month': NotificationDechet.objects.filter(date_envoi__date__gte=month_ago).count(),
                },
                'calendrier': {
                    'collectes_par_jour': dict(CalendrierCollecte.objects.values('jour_semaine').annotate(count=Count('id'))),
                },
                'performance': {
                    'traitement_signalements': 0,
                    'taux_remplissage_moyen_bacs': 0,
                },
            }
            
            total_signalements = dechets_stats['signalements']['total']
            traites = dechets_stats['signalements']['traites']
            if total_signalements > 0:
                dechets_stats['performance']['traitement_signalements'] = round((traites / total_signalements) * 100, 1)
            
            dechets_stats['performance']['taux_remplissage_moyen_bacs'] = dechets_stats['points_collecte']['taux_remplissage_moyen']
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                count = Signalement.objects.filter(
                    date_signalement__date__gte=date_start,
                    date_signalement__date__lt=date_end
                ).count()
                dechets_stats['signalements']['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                stats = StatsCollecte.objects.filter(
                    date__gte=date_start,
                    date__lt=date_end
                ).aggregate(
                    tonnes=Sum('tonnes_collectees'),
                    bacs=Sum('bacs_vides')
                )
                dechets_stats['collectes']['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'tonnes': round(stats['tonnes'] or 0, 1),
                    'bacs': stats['bacs'] or 0
                })
            
            if dechets_stats['collectes']['evolution_mensuelle']:
                dechets_stats['collectes']['meilleur_mois'] = max(
                    dechets_stats['collectes']['evolution_mensuelle'],
                    key=lambda x: x['tonnes']
                )
            
        except Exception as e:
            logger.error(f"Erreur déchets: {e}")
            dechets_stats = {'error': str(e)}

        # ============================================
        # 8. STATISTIQUES PAIEMENTS
        # ============================================
        try:
            from paiements.models import TransactionPaiement, PortefeuilleCitoyen
            paiements_stats = {
                'total': TransactionPaiement.objects.filter(statut='confirme').count(),
                'montant_total': float(TransactionPaiement.objects.filter(statut='confirme').aggregate(total=Sum('montant_total'))['total'] or 0),
                'montant_mois': float(TransactionPaiement.objects.filter(statut='confirme', date_creation__date__gte=month_ago).aggregate(total=Sum('montant_total'))['total'] or 0),
                'today': TransactionPaiement.objects.filter(date_creation__date=today).count(),
                'this_week': TransactionPaiement.objects.filter(date_creation__date__gte=week_ago).count(),
                'this_month': TransactionPaiement.objects.filter(date_creation__date__gte=month_ago).count(),
                'by_mode': dict(TransactionPaiement.objects.values('mode').annotate(count=Count('id'))),
                'by_statut': dict(TransactionPaiement.objects.values('statut').annotate(count=Count('id'))),
                'portefeuilles_actifs': PortefeuilleCitoyen.objects.filter(solde__gt=0).count(),
                'solde_total_portefeuilles': float(PortefeuilleCitoyen.objects.aggregate(total=Sum('solde'))['total'] or 0),
                'evolution_mensuelle': [],
            }
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                count = TransactionPaiement.objects.filter(
                    date_creation__date__gte=date_start,
                    date_creation__date__lt=date_end,
                    statut='confirme'
                ).count()
                montant = TransactionPaiement.objects.filter(
                    date_creation__date__gte=date_start,
                    date_creation__date__lt=date_end,
                    statut='confirme'
                ).aggregate(total=Sum('montant_total'))['total'] or 0
                paiements_stats['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count,
                    'montant': float(montant)
                })
                
        except Exception as e:
            logger.error(f"Erreur paiements: {e}")
            paiements_stats = {'error': str(e)}

        # ============================================
        # 9. STATISTIQUES SIGNATURES ÉLECTRONIQUES
        # ============================================
        try:
            from signature_electronique.models import SignatureElectronique, DemandeSignature, CertificatNumerique
            signatures_stats = {
                'total': SignatureElectronique.objects.count(),
                'valides': SignatureElectronique.objects.filter(est_valide=True).count(),
                'by_module': dict(SignatureElectronique.objects.values('module_source').annotate(count=Count('id'))),
                'en_attente': DemandeSignature.objects.filter(statut='en_attente').count(),
                'signe': DemandeSignature.objects.filter(statut='signe').count(),
                'expirees': DemandeSignature.objects.filter(statut='expire').count(),
                'annulees': DemandeSignature.objects.filter(statut='annule').count(),
                'this_month': SignatureElectronique.objects.filter(timestamp_signature__date__gte=month_ago).count(),
                'certificats_actifs': CertificatNumerique.objects.filter(est_valide=True, est_revoque=False).count(),
                'certificats_expires': CertificatNumerique.objects.filter(date_expiration__lt=timezone.now()).count(),
                'evolution_mensuelle': [],
            }
            
            for i in range(11, -1, -1):
                date_start = (today.replace(day=1) - timedelta(days=30*i))
                date_end = (date_start + timedelta(days=32)).replace(day=1)
                count = SignatureElectronique.objects.filter(
                    timestamp_signature__date__gte=date_start,
                    timestamp_signature__date__lt=date_end
                ).count()
                signatures_stats['evolution_mensuelle'].append({
                    'mois': date_start.strftime('%B %Y'),
                    'count': count
                })
                
        except Exception as e:
            logger.error(f"Erreur signatures: {e}")
            signatures_stats = {'error': str(e)}

        return Response({
            'success': True,
            'period': {
                'today': today,
                'week_ago': week_ago,
                'month_ago': month_ago,
                'year_ago': year_ago,
            },
            'users': users_stats,
            'etat_civil': etat_civil_stats,
            'annuaires': annuaires_stats,
            'activites': activites_stats,
            'actualites': actualites_stats,
            'archives': archives_stats,
            'dechets': dechets_stats,
            'paiements': paiements_stats,
            'signatures': signatures_stats,
            'summary': {
                'total_publications': actualites_stats.get('total', 0),
                'total_archives': archives_stats.get('total_archives', 0),
                'total_signalements': dechets_stats.get('signalements', {}).get('total', 0),
                'total_demandes_dechets': dechets_stats.get('demandes_encombrants', {}).get('total', 0),
                'total_demandes_archives': archives_stats.get('demandes', {}).get('total', 0),
                'tonnes_collectees': dechets_stats.get('collectes', {}).get('tonnes_annee', 0),
            }
        })


@staff_member_required
def dashboard_home(request):
    """Page d'accueil du tableau de bord"""
    return render(request, 'dashboard/index.html')