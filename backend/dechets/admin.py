# dechets/admin.py
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from .models import (
    Quartier, PointCollecte, CalendrierCollecte, Signalement,
    DemandeEncombrant, Tournee, TourneePoint, NotificationDechet, StatsCollecte
)


@admin.register(Quartier)
class QuartierAdmin(admin.ModelAdmin):
    """Administration des quartiers"""
    list_display = ['nom', 'slug', 'ordre', 'code_postal', 'population_estimee']
    list_editable = ['ordre']
    list_filter = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}
    search_fields = ['nom', 'code_postal']
    readonly_fields = ['slug']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'slug', 'code_postal', 'description')
        }),
        ('Géolocalisation', {
            'fields': ('latitude', 'longitude'),
            'classes': ('collapse',)
        }),
        ('Statistiques', {
            'fields': ('population_estimee', 'couleur', 'ordre'),
            'classes': ('collapse',)
        }),
    )


class TourneePointInline(admin.TabularInline):
    """Inline pour les points de collecte dans une tournée"""
    model = TourneePoint
    extra = 1
    fields = ['point', 'ordre', 'est_vide', 'heure_passage', 'commentaire']
    readonly_fields = ['heure_passage']
    ordering = ['ordre']
    show_change_link = True
    classes = ['collapse']


@admin.register(Tournee)
class TourneeAdmin(admin.ModelAdmin):
    """Administration des tournées de collecte"""
    list_display = ['date', 'quartier', 'agent', 'statut', 'distance_totale', 'progression_display']
    list_filter = ['date', 'statut', 'quartier']
    search_fields = ['quartier__nom', 'agent__username', 'agent__email']
    readonly_fields = ['debut_reel', 'fin_reelle', 'distance_totale', 'duree_estimee', 'heure_debut', 'heure_fin_estimee']
    
    # Au lieu de filter_horizontal (incompatible avec through), on utilise inlines
    inlines = [TourneePointInline]
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('date', 'quartier', 'agent', 'statut')
        }),
        ('Horaires', {
            'fields': ('heure_debut', 'heure_fin_estimee', 'debut_reel', 'fin_reelle'),
            'classes': ('collapse',)
        }),
        ('Itinéraire', {
            'fields': ('ordre_points', 'distance_totale', 'duree_estimee'),
            'classes': ('collapse',)
        }),
    )
    
    def progression_display(self, obj):
        """Affiche la progression de la tournée"""
        total = obj.tourneepoint_set.count()
        if total == 0:
            return format_html('<span style="color: gray;">0%</span>')
        valides = obj.tourneepoint_set.filter(est_vide=True).count()
        progression = round((valides / total) * 100)
        
        if progression == 100:
            color = "green"
        elif progression >= 50:
            color = "orange"
        else:
            color = "red"
        
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}% ({}/{})</span>',
            color, progression, valides, total
        )
    progression_display.short_description = "Progression"


@admin.register(PointCollecte)
class PointCollecteAdmin(admin.ModelAdmin):
    """Administration des points de collecte"""
    list_display = ['code', 'type', 'quartier', 'adresse_reference', 'statut', 'niveau_remplissage_display', 'dernier_vidage']
    list_filter = ['type', 'statut', 'quartier']
    search_fields = ['code', 'adresse_reference']
    list_editable = ['statut']
    readonly_fields = ['code', 'signalements_count', 'collectes_count']
    
    fieldsets = (
        ('Identification', {
            'fields': ('code', 'type', 'quartier')
        }),
        ('Localisation', {
            'fields': ('adresse_reference', 'latitude', 'longitude', 'photo')
        }),
        ('État', {
            'fields': ('statut', 'niveau_remplissage', 'dernier_vidage', 'prochain_vidage')
        }),
        ('Statistiques', {
            'fields': ('signalements_count', 'collectes_count', 'capacite_kg'),
            'classes': ('collapse',)
        }),
    )
    
    def niveau_remplissage_display(self, obj):
        """Affiche le niveau de remplissage avec une barre de progression"""
        niveau = obj.niveau_remplissage
        if niveau >= 80:
            color = "red"
        elif niveau >= 50:
            color = "orange"
        else:
            color = "green"
        
        return format_html(
            '<div style="background-color: #f0f0f0; border-radius: 5px; width: 100px;">'
            '<div style="background-color: {}; width: {}%; border-radius: 5px; text-align: center; color: white;">{}%</div>'
            '</div>',
            color, niveau, niveau
        )
    niveau_remplissage_display.short_description = "Niveau de remplissage"
    
    actions = ['marquer_comme_plein', 'marquer_comme_vide']
    
    def marquer_comme_plein(self, request, queryset):
        """Action pour marquer les points comme pleins"""
        updated = queryset.update(niveau_remplissage=100, statut='plein')
        self.message_user(request, f'{updated} point(s) marqué(s) comme plein(s)')
    marquer_comme_plein.short_description = "Marquer comme plein"
    
    def marquer_comme_vide(self, request, queryset):
        """Action pour marquer les points comme vides"""
        updated = queryset.update(niveau_remplissage=0, statut='actif')
        self.message_user(request, f'{updated} point(s) marqué(s) comme vide(s)')
    marquer_comme_vide.short_description = "Marquer comme vide"


@admin.register(CalendrierCollecte)
class CalendrierCollecteAdmin(admin.ModelAdmin):
    """Administration du calendrier des collectes"""
    list_display = ['quartier', 'jour_semaine_display', 'heure_passage', 'type_dechet', 'est_actif']
    list_filter = ['quartier', 'jour_semaine', 'est_actif', 'type_dechet']
    search_fields = ['quartier__nom']
    list_editable = ['est_actif', 'heure_passage']
    
    def jour_semaine_display(self, obj):
        jours = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
        return jours[obj.jour_semaine]
    jour_semaine_display.short_description = "Jour de collecte"
    
    fieldsets = (
        ('Informations', {
            'fields': ('quartier', 'jour_semaine', 'heure_passage', 'type_dechet')
        }),
        ('Options', {
            'fields': ('est_actif', 'est_semaine_impaire', 'date_debut', 'date_fin'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Signalement)
class SignalementAdmin(admin.ModelAdmin):
    """Administration des signalements citoyens"""
    list_display = ['type_signalement', 'adresse_description', 'quartier_affiche', 'statut', 'priorite_display', 'date_signalement']
    list_filter = ['type_signalement', 'statut', 'priorite', 'date_signalement']
    search_fields = ['adresse_description', 'nom_citoyen', 'telephone', 'email']
    list_editable = ['statut']
    readonly_fields = ['date_signalement', 'temps_attente']
    
    fieldsets = (
        ('Signalement', {
            'fields': ('type_signalement', 'point_collecte', 'description', 'photo')
        }),
        ('Localisation', {
            'fields': ('adresse_description', 'latitude', 'longitude')
        }),
        ('Auteur', {
            'fields': ('citoyen', 'nom_citoyen', 'telephone', 'email')
        }),
        ('Traitement', {
            'fields': ('statut', 'priorite', 'commentaire_traitement', 'agent_traitement', 'date_traitement')
        }),
        ('Métadonnées', {
            'fields': ('date_signalement', 'temps_attente'),
            'classes': ('collapse',)
        }),
    )
    
    def quartier_affiche(self, obj):
        if obj.point_collecte and obj.point_collecte.quartier:
            return obj.point_collecte.quartier.nom
        return "-"
    quartier_affiche.short_description = "Quartier"
    
    def priorite_display(self, obj):
        couleurs = {
            'basse': 'gray',
            'normale': 'blue',
            'haute': 'orange',
            'urgente': 'red'
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleurs.get(obj.priorite, 'black'),
            obj.get_priorite_display()
        )
    priorite_display.short_description = "Priorité"
    
    def temps_attente(self, obj):
        if obj.date_traitement:
            delta = obj.date_traitement - obj.date_signalement
            heures = delta.total_seconds() / 3600
            return f"{heures:.1f} heures"
        return "En attente"
    temps_attente.short_description = "Temps d'attente"
    
    actions = ['marquer_en_cours', 'marquer_traite', 'marquer_urgent']
    
    def marquer_en_cours(self, request, queryset):
        updated = queryset.update(statut='en_cours')
        self.message_user(request, f'{updated} signalement(s) marqué(s) "En cours"')
    marquer_en_cours.short_description = "Marquer comme 'En cours'"
    
    def marquer_traite(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(statut='traite', date_traitement=timezone.now())
        self.message_user(request, f'{updated} signalement(s) marqué(s) "Traité"')
    marquer_traite.short_description = "Marquer comme 'Traité'"
    
    def marquer_urgent(self, request, queryset):
        updated = queryset.update(priorite='urgente')
        self.message_user(request, f'{updated} signalement(s) marqué(s) comme "Urgent"')
    marquer_urgent.short_description = "Marquer comme 'Urgent'"


@admin.register(DemandeEncombrant)
class DemandeEncombrantAdmin(admin.ModelAdmin):
    """Administration des demandes d'encombrants"""
    list_display = ['citoyen_info', 'type_encombrant', 'adresse_courte', 'statut', 'date_souhaitee', 'date_demande']
    list_filter = ['type_encombrant', 'statut', 'date_souhaitee']
    search_fields = ['citoyen__email', 'citoyen__username', 'adresse', 'telephone']
    list_editable = ['statut']
    readonly_fields = ['date_demande']
    
    fieldsets = (
        ('Demandeur', {
            'fields': ('citoyen', 'adresse', 'point_repere', 'latitude', 'longitude')
        }),
        ('Encombrant', {
            'fields': ('type_encombrant', 'description', 'photo', 'quantite_estimee')
        }),
        ('Planification', {
            'fields': ('date_souhaitee', 'creneau_horaire', 'statut', 'agent_assignee')
        }),
        ('Dates', {
            'fields': ('date_demande', 'date_planification', 'date_realisation'),
            'classes': ('collapse',)
        }),
    )
    
    def citoyen_info(self, obj):
        if obj.citoyen:
            return format_html(
                '<a href="{}">{}</a><br/><span style="color: gray;">{}</span>',
                reverse('admin:auth_user_change', args=[obj.citoyen.id]),
                obj.citoyen.get_full_name() or obj.citoyen.username,
                obj.citoyen.email
            )
        return "-"
    citoyen_info.short_description = "Citoyen"
    
    def adresse_courte(self, obj):
        return obj.adresse[:50] + '...' if len(obj.adresse) > 50 else obj.adresse
    adresse_courte.short_description = "Adresse"
    
    actions = ['planifier', 'marquer_effectue']
    
    def planifier(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(statut='planifiee', date_planification=timezone.now())
        self.message_user(request, f'{updated} demande(s) planifiée(s)')
    planifier.short_description = "Planifier"
    
    def marquer_effectue(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(statut='effectuee', date_realisation=timezone.now())
        self.message_user(request, f'{updated} demande(s) marquée(s) comme effectuée(s)')
    marquer_effectue.short_description = "Marquer comme effectuée"


@admin.register(StatsCollecte)
class StatsCollecteAdmin(admin.ModelAdmin):
    """Administration des statistiques de collecte"""
    list_display = ['date', 'tonnes_collectees', 'bacs_vides', 'signalements_traites', 'encombrants_collectes', 'tournees_completees']
    list_filter = ['date']
    list_editable = ['tonnes_collectees', 'bacs_vides', 'signalements_traites', 'encombrants_collectes']
    search_fields = ['date']
    date_hierarchy = 'date'
    
    fieldsets = (
        ('Collectes', {
            'fields': ('date', 'tonnes_collectees', 'bacs_vides', 'tournees_completees')
        }),
        ('Traitements', {
            'fields': ('signalements_traites', 'encombrants_collectes')
        }),
        ('Métriques avancées', {
            'fields': ('carburant_consomme', 'kilometres_parcourus', 'agents_mobilises'),
            'classes': ('collapse',)
        }),
    )


@admin.register(NotificationDechet)
class NotificationDechetAdmin(admin.ModelAdmin):
    """Administration des notifications déchets"""
    list_display = ['titre', 'quartier', 'type', 'date_envoi', 'est_envoyee']
    list_filter = ['type', 'est_envoyee', 'quartier']
    search_fields = ['titre', 'message']
    list_editable = ['est_envoyee']
    readonly_fields = ['date_envoi']
    
    fieldsets = (
        ('Notification', {
            'fields': ('titre', 'message', 'type', 'quartier')
        }),
        ('Envoi', {
            'fields': ('est_envoyee', 'date_envoi', 'envoyer_sms', 'envoyer_email', 'envoyer_push')
        }),
        ('Planification', {
            'fields': ('date_planifiee',),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['envoyer_maintenant']
    
    def envoyer_maintenant(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(est_envoyee=True, date_envoi=timezone.now())
        self.message_user(request, f'{updated} notification(s) marquée(s) comme envoyée(s)')
    envoyer_maintenant.short_description = "Marquer comme envoyée"


# Admin pour TourneePoint (optionnel)
@admin.register(TourneePoint)
class TourneePointAdmin(admin.ModelAdmin):
    """Administration des points par tournée"""
    list_display = ['tournee', 'point', 'ordre', 'est_vide', 'heure_passage']
    list_filter = ['est_vide', 'tournee__date', 'tournee__quartier']
    search_fields = ['point__code', 'point__adresse_reference']
    list_editable = ['ordre', 'est_vide']
    readonly_fields = ['heure_passage']
    
    fieldsets = (
        ('Tournée', {
            'fields': ('tournee', 'point', 'ordre')
        }),
        ('Validation', {
            'fields': ('est_vide', 'heure_passage', 'photo_preuve', 'commentaire')
        }),
    )