from django.contrib import admin

# activites/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CategorieActivite, Activite, Inscription, 
    PaiementActivite, NotificationActivite, AvisActivite
)

@admin.register(CategorieActivite)
class CategorieActiviteAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'icon', 'couleur_affichee', 'ordre']
    list_editable = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}
    
    def couleur_affichee(self, obj):
        return format_html(f'<span style="background:{obj.couleur}; padding:5px 10px; border-radius:5px;">{obj.couleur}</span>')
    couleur_affichee.short_description = "Couleur"

@admin.register(Activite)
class ActiviteAdmin(admin.ModelAdmin):
    list_display = ['titre', 'type_activite', 'date_debut', 'statut', 'prix', 'places_restantes', 'est_a_la_une']
    list_filter = ['type_activite', 'statut', 'est_a_la_une', 'date_debut']
    search_fields = ['titre', 'description_courte', 'lieu']
    prepopulated_fields = {'slug': ('titre',)}
    readonly_fields = ['vue_count', 'partage_count', 'date_creation', 'places_restantes_display']
    list_editable = ['statut', 'est_a_la_une']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('titre', 'slug', 'type_activite', 'categorie', 'description_courte', 'description_longue')
        }),
        ('Médias', {
            'fields': ('image_principale', 'images_galerie', 'video_url'),
            'classes': ('collapse',)
        }),
        ('Dates et lieu', {
            'fields': ('date_debut', 'date_fin', 'date_limite_inscription', 'lieu', 'adresse', 'ville', 'coordonnees_gps')
        }),
        ('Capacité et tarifs', {
            'fields': ('capacite_max', 'prix', 'est_gratuit')
        }),
        ('Organisation', {
            'fields': ('organisateur', 'partenaires')
        }),
        ('Publication', {
            'fields': ('statut', 'date_publication', 'est_a_la_une', 'est_recommandee')
        }),
        ('Statistiques', {
            'fields': ('vue_count', 'partage_count', 'date_creation', 'places_restantes_display'),
            'classes': ('collapse',)
        }),
    )
    
    def places_restantes_display(self, obj):
        if obj.capacite_max == 0:
            return "Illimité"
        return f"{obj.places_restantes} / {obj.capacite_max}"
    places_restantes_display.short_description = "Places restantes"

@admin.register(Inscription)
class InscriptionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'activite', 'utilisateur', 'statut', 'montant_total', 'date_inscription']
    list_filter = ['statut', 'moyen_paiement', 'date_inscription']
    search_fields = ['reference', 'utilisateur__email', 'nom_complet', 'telephone']
    readonly_fields = ['reference', 'montant_total', 'qr_code_preview']
    
    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html(f'<img src="data:image/png;base64,{obj.qr_code}" width="80" height="80">')
        return "-"
    qr_code_preview.short_description = "QR Code"
    
    actions = ['confirmer_inscriptions', 'annuler_inscriptions']
    
    def confirmer_inscriptions(self, request, queryset):
        queryset.update(statut='confirmee')
    confirmer_inscriptions.short_description = "Confirmer les inscriptions"
    
    def annuler_inscriptions(self, request, queryset):
        queryset.update(statut='annulee')
    annuler_inscriptions.short_description = "Annuler les inscriptions"

@admin.register(PaiementActivite)
class PaiementActiviteAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'montant', 'moyen_paiement', 'statut', 'transaction_id', 'date_demande']
    list_filter = ['statut', 'moyen_paiement', 'date_demande']
    search_fields = ['transaction_id', 'inscription__reference']

@admin.register(NotificationActivite)
class NotificationActiviteAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'type', 'canal', 'est_envoyee', 'date_creation']
    list_filter = ['type', 'canal', 'est_envoyee']

@admin.register(AvisActivite)
class AvisActiviteAdmin(admin.ModelAdmin):
    list_display = ['inscription', 'note', 'commentaire_court', 'est_approuve', 'date_creation']
    list_filter = ['note', 'est_approuve']
    list_editable = ['est_approuve']
    
    def commentaire_court(self, obj):
        return obj.commentaire[:50] + "..." if len(obj.commentaire) > 50 else obj.commentaire
    commentaire_court.short_description = "Commentaire"
