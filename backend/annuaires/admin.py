from django.contrib import admin

# annuaires/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CategorieStructure, Structure, Elu, 
    FavoriStructure, AvisStructure, ContactStructure
)

@admin.register(CategorieStructure)
class CategorieStructureAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'icon', 'couleur_affichee', 'ordre']
    list_editable = ['ordre']
    prepopulated_fields = {'slug': ('nom',)}
    
    def couleur_affichee(self, obj):
        return format_html(f'<span style="background:{obj.couleur}; padding:5px 10px; border-radius:5px;">{obj.couleur}</span>')
    couleur_affichee.short_description = "Couleur"

@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ['nom', 'type_structure', 'ville', 'telephone', 'statut', 'est_populaire', 'vue_count']
    list_filter = ['type_structure', 'statut', 'ville', 'est_populaire']
    search_fields = ['nom', 'adresse', 'quartier', 'ville', 'telephone']
    prepopulated_fields = {'slug': ('nom',)}
    readonly_fields = ['vue_count', 'contact_count', 'favori_count', 'date_creation']
    list_editable = ['statut', 'est_populaire']
    
    fieldsets = (
        ('Informations générales', {
            'fields': ('nom', 'slug', 'type_structure', 'categorie', 'description')
        }),
        ('Adresse et géolocalisation', {
            'fields': ('adresse', 'quartier', 'ville', 'code_postal', 'latitude', 'longitude')
        }),
        ('Contacts', {
            'fields': ('telephone', 'telephone2', 'email', 'whatsapp', 'site_web', 'facebook')
        }),
        ('Horaires', {
            'fields': ('horaires_lundi', 'horaires_mardi', 'horaires_mercredi', 'horaires_jeudi',
                      'horaires_vendredi', 'horaires_samedi', 'horaires_dimanche', 'horaires_speciaux'),
            'classes': ('collapse',)
        }),
        ('Images', {
            'fields': ('image_principale', 'images_galerie'),
            'classes': ('collapse',)
        }),
        ('Statut et visibilité', {
            'fields': ('statut', 'est_populaire', 'est_verifie')
        }),
        ('Statistiques', {
            'fields': ('vue_count', 'contact_count', 'favori_count', 'date_creation'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['verifier_structures', 'marquer_populaires']
    
    def verifier_structures(self, request, queryset):
        queryset.update(est_verifie=True)
    verifier_structures.short_description = "Vérifier les structures sélectionnées"
    
    def marquer_populaires(self, request, queryset):
        queryset.update(est_populaire=True)
    marquer_populaires.short_description = "Marquer comme populaires"

@admin.register(Elu)
class EluAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prenom', 'fonction', 'commission', 'telephone', 'est_actif']
    list_filter = ['fonction', 'commission', 'est_actif']
    search_fields = ['nom', 'prenom', 'commission']
    list_editable = ['est_actif']
    
    fieldsets = (
        ('Identité', {
            'fields': ('nom', 'prenom', 'fonction', 'titre', 'photo')
        }),
        ('Biographie', {
            'fields': ('biographie',)
        }),
        ('Contacts', {
            'fields': ('telephone', 'email')
        }),
        ('Mandat', {
            'fields': ('commission', 'delegation', 'parti', 'date_debut_mandat', 'date_fin_mandat')
        }),
        ('Ordre et visibilité', {
            'fields': ('ordre', 'est_actif')
        }),
    )

@admin.register(AvisStructure)
class AvisStructureAdmin(admin.ModelAdmin):
    list_display = ['structure', 'utilisateur', 'note', 'commentaire_court', 'est_approuve', 'date_creation']
    list_filter = ['note', 'est_approuve']
    search_fields = ['structure__nom', 'utilisateur__email', 'commentaire']
    list_editable = ['est_approuve']
    
    def commentaire_court(self, obj):
        return obj.commentaire[:50] + "..." if len(obj.commentaire) > 50 else obj.commentaire
    commentaire_court.short_description = "Commentaire"

@admin.register(ContactStructure)
class ContactStructureAdmin(admin.ModelAdmin):
    list_display = ['structure', 'nom', 'sujet', 'email', 'est_traite', 'date_creation']
    list_filter = ['sujet', 'est_traite']
    search_fields = ['structure__nom', 'nom', 'email', 'message']
    list_editable = ['est_traite']
