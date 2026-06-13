from django.contrib import admin
from django.utils.html import format_html
from .models import (
    CategorieActualite, Publication, Reaction, Commentaire, 
    HistoriqueConsultation, PropositionCitoyenne, Partage
)

@admin.register(CategorieActualite)
class CategorieActualiteAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'ordre', 'couleur']
    search_fields = ['nom', 'description']
    prepopulated_fields = {'slug': ('nom',)}
    ordering = ['ordre', 'nom']

@admin.register(Publication)
class PublicationAdmin(admin.ModelAdmin):
    list_display = ['titre', 'categorie', 'auteur', 'statut', 'date_publication', 
                    'est_epingle', 'est_a_la_une', 'vue_count', 'apercu_thumbnail']
    list_filter = ['statut', 'categorie', 'est_epingle', 'est_a_la_une', 'date_publication']
    search_fields = ['titre', 'accroche', 'contenu']
    #prepopulated_fields = {'slug': ('titre',)}
    raw_id_fields = ['auteur', 'moderateur']
    readonly_fields = ['vue_count', 'partage_count', 'slug', 'date_creation', 'date_modification']
    
    def apercu_thumbnail(self, obj):
        if obj.thumbnail:
            return format_html('<img src="{}" width="50" height="50" style="object-fit:cover;" />', obj.thumbnail.url)
        return "Pas d'image"
    apercu_thumbnail.short_description = 'Aperçu'
    
    actions = ['publier_selectionnes', 'depublier_selectionnes']
    
    def publier_selectionnes(self, request, queryset):
        queryset.update(statut='publie')
    publier_selectionnes.short_description = "Publier les sélections"
    
    def depublier_selectionnes(self, request, queryset):
        queryset.update(statut='brouillon')
    depublier_selectionnes.short_description = "Dépublier les sélections"

@admin.register(Commentaire)
class CommentaireAdmin(admin.ModelAdmin):
    list_display = ['id', 'publication', 'utilisateur', 'contenu_court', 'like_count', 
                    'est_approuve', 'date_creation']
    list_filter = ['est_approuve', 'date_creation']
    search_fields = ['contenu', 'utilisateur__username', 'publication__titre']
    actions = ['approuver_commentaires', 'desapprouver_commentaires']
    
    def contenu_court(self, obj):
        return obj.contenu[:50] + '...' if len(obj.contenu) > 50 else obj.contenu
    contenu_court.short_description = 'Contenu'
    
    def approuver_commentaires(self, request, queryset):
        queryset.update(est_approuve=True)
    approuver_commentaires.short_description = "Approuver les commentaires"
    
    def desapprouver_commentaires(self, request, queryset):
        queryset.update(est_approuve=False)
    desapprouver_commentaires.short_description = "Désapprouver les commentaires"

@admin.register(Reaction)
class ReactionAdmin(admin.ModelAdmin):
    list_display = ['publication', 'utilisateur', 'type_reaction', 'date_creation']
    list_filter = ['type_reaction', 'date_creation']
    search_fields = ['publication__titre', 'utilisateur__username']
    readonly_fields = ['date_creation']

@admin.register(PropositionCitoyenne)
class PropositionCitoyenneAdmin(admin.ModelAdmin):
    list_display = ['titre', 'auteur', 'statut', 'date_soumission']
    list_filter = ['statut', 'date_soumission']
    search_fields = ['titre', 'contenu', 'auteur__username']
    readonly_fields = ['date_soumission']
    fieldsets = (
        ('Proposition', {
            'fields': ('titre', 'contenu', 'auteur')
        }),
        ('Statut et réponse', {
            'fields': ('statut', 'commentaire_reponse')
        }),
        ('Dates', {
            'fields': ('date_soumission',),
            'classes': ('collapse',)
        })
    )

@admin.register(HistoriqueConsultation)
class HistoriqueConsultationAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'publication', 'date_consultation']
    list_filter = ['date_consultation']
    search_fields = ['utilisateur__username', 'publication__titre']
    readonly_fields = ['date_consultation']

@admin.register(Partage)
class PartageAdmin(admin.ModelAdmin):
    list_display = ['publication', 'plateforme', 'utilisateur', 'date_partage']
    list_filter = ['plateforme', 'date_partage']
    search_fields = ['publication__titre', 'utilisateur__username']
    readonly_fields = ['date_partage']