from django.contrib import admin

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import (
    Region, Departement, Arrondissement, DistrictSante,
    DemandeActe, ConfigurationTarif, HistoriqueStatut, 
    NotificationActe, CertificatVie, CopieActe
)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    """Administration des régions du Cameroun"""
    list_display = ['nom', 'code', 'chef_lieu', 'population']
    list_filter = ['nom']
    search_fields = ['nom', 'code', 'chef_lieu']
    ordering = ['nom']
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'code', 'chef_lieu')
        }),
        ('Statistiques', {
            'fields': ('population',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    """Administration des départements"""
    list_display = ['nom', 'code', 'region_affiche', 'chef_lieu']
    list_filter = ['region']
    search_fields = ['nom', 'code', 'chef_lieu']
    ordering = ['region__nom', 'nom']
    autocomplete_fields = ['region']
    
    def region_affiche(self, obj):
        return obj.region.nom if obj.region else "-"
    region_affiche.short_description = "Région"
    region_affiche.admin_order_field = 'region__nom'


@admin.register(Arrondissement)
class ArrondissementAdmin(admin.ModelAdmin):
    """Administration des arrondissements"""
    list_display = ['nom', 'code', 'departement_affiche', 'chef_lieu']
    list_filter = ['departement__region', 'departement']
    search_fields = ['nom', 'code', 'chef_lieu']
    ordering = ['departement__nom', 'nom']
    autocomplete_fields = ['departement']
    
    def departement_affiche(self, obj):
        return obj.departement.nom if obj.departement else "-"
    departement_affiche.short_description = "Département"
    departement_affiche.admin_order_field = 'departement__nom'


@admin.register(DistrictSante)
class DistrictSanteAdmin(admin.ModelAdmin):
    """Administration des districts de santé"""
    list_display = ['nom', 'code', 'arrondissement_affiche']
    list_filter = ['arrondissement__departement', 'arrondissement']
    search_fields = ['nom', 'code']
    ordering = ['arrondissement__nom', 'nom']
    autocomplete_fields = ['arrondissement']
    
    def arrondissement_affiche(self, obj):
        return obj.arrondissement.nom if obj.arrondissement else "-"
    arrondissement_affiche.short_description = "Arrondissement"


@admin.register(ConfigurationTarif)
class ConfigurationTarifAdmin(admin.ModelAdmin):
    """Administration des configurations tarifaires"""
    list_display = ["type_acte", "tarif_normal", "tarif_retard", "delai_normal_jours", "est_actif"]
    list_filter = ['type_acte', 'est_actif']
    list_editable = ['tarif_normal', 'tarif_retard', 'delai_normal_jours', 'est_actif']
    search_fields = ['type_acte']
    readonly_fields = ['date_modification']
    
    def type_acte_display(self, obj):
        return obj.get_type_acte_display()
    type_acte_display.short_description = "Type d'acte"
    type_acte_display.admin_order_field = 'type_acte'
    
    def tarif_normal_formate(self, obj):
        return f"{obj.tarif_normal:,.0f} FCFA"
    tarif_normal_formate.short_description = "Tarif normal"
    
    def tarif_retard_formate(self, obj):
        return f"{obj.tarif_retard:,.0f} FCFA"
    tarif_retard_formate.short_description = "Tarif retard"
    
    fieldsets = (
        ('Type d\'acte', {
            'fields': ('type_acte',)
        }),
        ('Tarification', {
            'fields': ('tarif_normal', 'tarif_retard', 'tarif_copie', 'tarif_extrait')
        }),
        ('Délais', {
            'fields': ('delai_normal_jours',)
        }),
        ('Statut', {
            'fields': ('est_actif', 'date_modification')
        }),
    )


class HistoriqueStatutInline(admin.TabularInline):
    """Inline pour l'historique des statuts"""
    model = HistoriqueStatut
    extra = 0
    fields = ['ancien_statut', 'nouveau_statut', 'commentaire', 'utilisateur', 'date']
    readonly_fields = ['date']
    can_delete = False
    max_num = 0


class NotificationActeInline(admin.TabularInline):
    """Inline pour les notifications"""
    model = NotificationActe
    extra = 0
    fields = ['titre', 'message', 'est_lue', 'date_envoi']
    readonly_fields = ['date_envoi']
    can_delete = False
    max_num = 10


@admin.register(DemandeActe)
class DemandeActeAdmin(admin.ModelAdmin):
    """Administration des demandes d'actes d'état civil"""
    list_display = ['reference', 'type_acte_display', 'demandeur_info', 'statut_display', 
                    'tarif_applique_formate', 'paiement_status', 'date_creation_formatee']
    list_filter = ['type_acte', 'statut', 'paiement_effectue', 'date_creation']
    search_fields = ['reference', 'demandeur__email', 'demandeur__username', 'demandeur__first_name']
    readonly_fields = ['reference', 'date_creation', 'date_modification']
    date_hierarchy = 'date_creation'
    list_select_related = ['demandeur', 'agent_traitant', 'autorite_signataire']
    inlines = [HistoriqueStatutInline, NotificationActeInline]
    
    def type_acte_display(self, obj):
        return obj.get_type_acte_display()
    type_acte_display.short_description = "Type d'acte"
    type_acte_display.admin_order_field = 'type_acte'
    
    def demandeur_info(self, obj):
        if obj.demandeur:
            return format_html(
                '<a href="{}">{}</a><br/><span style="color:gray;">{}</span>',
                reverse('admin:auth_user_change', args=[obj.demandeur.id]),
                obj.demandeur.get_full_name() or obj.demandeur.username,
                obj.demandeur.email
            )
        return "-"
    demandeur_info.short_description = "Demandeur"
    
    def statut_display(self, obj):
        colors = {
            'brouillon': 'gray',
            'en_attente': 'orange',
            'en_cours': 'blue',
            'valide_agent': 'green',
            'valide_citoyen': 'purple',
            'signe': 'teal',
            'rejete': 'red',
            'delivre': 'darkgreen',
        }
        color = colors.get(obj.statut, 'black')
        return format_html('<span style="color: {}; font-weight: bold;">{}</span>', 
                          color, obj.get_statut_display())
    statut_display.short_description = "Statut"
    statut_display.admin_order_field = 'statut'
    
    def tarif_applique_formate(self, obj):
        if obj.tarif_applique:
            return f"{obj.tarif_applique:,.0f} FCFA"
        return "-"
    tarif_applique_formate.short_description = "Tarif"
    
    def paiement_status(self, obj):
        if obj.paiement_effectue:
            return format_html('<span style="color: green;">✓ Payé</span>')
        return format_html('<span style="color: red;">✗ Non payé</span>')
    paiement_status.short_description = "Paiement"
    
    def date_creation_formatee(self, obj):
        return obj.date_creation.strftime('%d/%m/%Y %H:%M')
    date_creation_formatee.short_description = "Date de création"
    date_creation_formatee.admin_order_field = 'date_creation'
    
    fieldsets = (
        ('Identification', {
            'fields': ('reference', 'type_acte', 'statut')
        }),
        ('Demandeur', {
            'fields': ('demandeur', 'agent_traitant', 'autorite_signataire')
        }),
        ('Données de l\'acte', {
            'fields': ('data_acte',),
            'classes': ('wide',)
        }),
        ('Paiement', {
            'fields': ('tarif_applique', 'paiement_effectue', 'reference_paiement', 'date_paiement'),
            'classes': ('collapse',)
        }),
        ('Documents', {
            'fields': ('fichier_pdf', 'qr_code'),
            'classes': ('collapse',)
        }),
        ('Dates', {
            'fields': ('date_creation', 'date_modification', 'date_validation_agent', 
                      'date_validation_citoyen', 'date_signature', 'date_delivrance'),
            'classes': ('collapse',)
        }),
        ('Métadonnées', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['valider_agent', 'rejeter_demande', 'marquer_paye']
    
    def valider_agent(self, request, queryset):
        """Action pour valider les demandes"""
        from django.utils import timezone
        updated = queryset.filter(statut='en_attente').update(
            statut='valide_agent',
            date_validation_agent=timezone.now(),
            agent_traitant=request.user
        )
        self.message_user(request, f'{updated} demande(s) validée(s) par l\'agent')
    valider_agent.short_description = "Valider la demande (agent)"
    
    def rejeter_demande(self, request, queryset):
        """Action pour rejeter les demandes"""
        updated = queryset.filter(statut__in=['en_attente', 'en_cours']).update(statut='rejete')
        self.message_user(request, f'{updated} demande(s) rejetée(s)')
    rejeter_demande.short_description = "Rejeter la demande"
    
    def marquer_paye(self, request, queryset):
        """Action pour marquer comme payé"""
        from django.utils import timezone
        updated = queryset.filter(paiement_effectue=False).update(
            paiement_effectue=True,
            date_paiement=timezone.now()
        )
        self.message_user(request, f'{updated} demande(s) marquée(s) comme payée(s)')
    marquer_paye.short_description = "Marquer comme payé"


@admin.register(HistoriqueStatut)
class HistoriqueStatutAdmin(admin.ModelAdmin):
    """Administration de l'historique des statuts"""
    list_display = ['demande', 'ancien_statut', 'nouveau_statut', 'utilisateur', 'date_formatee']
    list_filter = ['ancien_statut', 'nouveau_statut', 'date']
    search_fields = ['demande__reference', 'utilisateur__email', 'commentaire']
    readonly_fields = ['date']
    date_hierarchy = 'date'
    
    def date_formatee(self, obj):
        return obj.date.strftime('%d/%m/%Y %H:%M:%S')
    date_formatee.short_description = "Date"
    date_formatee.admin_order_field = 'date'
    
    fieldsets = (
        ('Demande', {
            'fields': ('demande',)
        }),
        ('Changement de statut', {
            'fields': ('ancien_statut', 'nouveau_statut', 'commentaire')
        }),
        ('Utilisateur', {
            'fields': ('utilisateur',)
        }),
        ('Date', {
            'fields': ('date',)
        }),
    )


@admin.register(NotificationActe)
class NotificationActeAdmin(admin.ModelAdmin):
    """Administration des notifications"""
    list_display = ['titre_court', 'demande', 'est_lue_display', 'date_envoi_formatee']
    list_filter = ['est_lue', 'date_envoi']
    search_fields = ['titre', 'message', 'demande__reference']
    readonly_fields = ['date_envoi']
    date_hierarchy = 'date_envoi'
    
    def titre_court(self, obj):
        return obj.titre[:50] + '...' if len(obj.titre) > 50 else obj.titre
    titre_court.short_description = "Titre"
    
    def est_lue_display(self, obj):
        if obj.est_lue:
            return format_html('<span style="color: green;">✓ Lue</span>')
        return format_html('<span style="color: orange;">● Non lue</span>')
    est_lue_display.short_description = "Statut"
    
    def date_envoi_formatee(self, obj):
        return obj.date_envoi.strftime('%d/%m/%Y %H:%M')
    date_envoi_formatee.short_description = "Date d'envoi"
    
    actions = ['marquer_comme_lue']
    
    def marquer_comme_lue(self, request, queryset):
        updated = queryset.filter(est_lue=False).update(est_lue=True, date_lecture=timezone.now())
        self.message_user(request, f'{updated} notification(s) marquée(s) comme lue(s)')
    marquer_comme_lue.short_description = "Marquer comme lue"


@admin.register(CertificatVie)
class CertificatVieAdmin(admin.ModelAdmin):
    """Administration des certificats de vie"""
    list_display = ['beneficiaire', 'date_naissance', 'numero_pension', 'date_validite', 'est_valide_display']
    list_filter = ['date_validite']
    search_fields = ['beneficiaire', 'numero_pension']
    date_hierarchy = 'date_validite'
    
    def est_valide_display(self, obj):
        if obj.est_valide():
            return format_html('<span style="color: green;">✓ Valide</span>')
        return format_html('<span style="color: red;">✗ Expiré</span>')
    est_valide_display.short_description = "Validité"
    
    fieldsets = (
        ('Bénéficiaire', {
            'fields': ('beneficiaire', 'date_naissance', 'lieu_naissance')
        }),
        ('Pension', {
            'fields': ('numero_pension',)
        }),
        ('Validité', {
            'fields': ('date_validite',)
        }),
        ('Demande associée', {
            'fields': ('demande',),
            'classes': ('collapse',)
        }),
    )


@admin.register(CopieActe)
class CopieActeAdmin(admin.ModelAdmin):
    """Administration des copies d'actes"""
    list_display = ['acte_original', 'nombre_copies', 'motif_court', 'demande_associee']
    list_filter = ['nombre_copies']
    search_fields = ['acte_original', 'motif']
    
    def motif_court(self, obj):
        return obj.motif[:50] + '...' if len(obj.motif) > 50 else obj.motif
    motif_court.short_description = "Motif"
    
    def demande_associee(self, obj):
        if obj.demande:
            return format_html(
                '<a href="{}">{}</a>',
                reverse('admin:etat_civil_demandeacte_change', args=[obj.demande.id]),
                obj.demande.reference
            )
        return "-"
    demande_associee.short_description = "Demande associée"
    
    fieldsets = (
        ('Acte original', {
            'fields': ('acte_original',)
        }),
        ('Copie', {
            'fields': ('nombre_copies', 'motif')
        }),
        ('Demande', {
            'fields': ('demande',),
            'classes': ('collapse',)
        }),
    )