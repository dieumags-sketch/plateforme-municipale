from django.contrib import admin

# backend/archives/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import *

@admin.register(CategorieArchive)
class CategorieArchiveAdmin(admin.ModelAdmin):
    list_display = ['nom', 'slug', 'couleur_preview', 'ordre', 'est_actif']
    list_editable = ['ordre', 'est_actif']
    prepopulated_fields = {'slug': ('nom',)}
    search_fields = ['nom']
    
    def couleur_preview(self, obj):
        return format_html(
            '<div style="background: {}; width: 30px; height: 30px; border-radius: 5px;"></div>',
            obj.couleur
        )
    couleur_preview.short_description = 'Couleur'

@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    list_display = ['reference', 'titre', 'categorie', 'date_document', 'niveau_acces_colore', 'statut_colore', 'vues']
    list_filter = ['categorie', 'niveau_acces', 'statut', 'date_document']
    search_fields = ['reference', 'titre', 'description', 'mots_cles']
    readonly_fields = ['vues', 'telechargements', 'demandes_acces', 'date_creation', 'date_modification']
    prepopulated_fields = {'reference': ('titre',)}
    
    fieldsets = (
        ('Identification', {
            'fields': ('reference', 'titre', 'categorie')
        }),
        ('Description', {
            'fields': ('description', 'mots_cles')
        }),
        ('Métadonnées', {
            'fields': ('date_document', 'auteur', 'source', 'periode_debut', 'periode_fin')
        }),
        ('Localisation', {
            'fields': ('emplacement_physique', 'numero_boite'),
            'classes': ('collapse',)
        }),
        ('Fichiers', {
            'fields': ('fichier_pdf', 'vignette', 'fichiers_annexes'),
            'classes': ('collapse',)
        }),
        ('Conservation', {
            'fields': ('duree_conservation', 'date_fin_conservation'),
            'classes': ('collapse',)
        }),
        ('Accès et tarifs', {
            'fields': ('niveau_acces', 'tarif_consultation', 'tarif_impression', 'tarif_copie', 'tarif_envoi')
        }),
        ('Statut', {
            'fields': ('statut',)
        }),
    )
    
    actions = ['marquer_disponible', 'marquer_restauration']
    
    def niveau_acces_colore(self, obj):
        couleurs = {
            'public': 'green',
            'restreint': 'orange',
            'confidentiel': 'red',
            'tres_confidentiel': 'darkred',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleurs.get(obj.niveau_acces, 'black'),
            obj.get_niveau_acces_display()
        )
    niveau_acces_colore.short_description = 'Niveau accès'
    
    def statut_colore(self, obj):
        couleurs = {
            'disponible': 'green',
            'pret': 'orange',
            'restauration': 'red',
            'perdu': 'darkred',
            'numerise': 'blue',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleurs.get(obj.statut, 'black'),
            obj.get_statut_display()
        )
    statut_colore.short_description = 'Statut'
    
    def marquer_disponible(self, request, queryset):
        queryset.update(statut='disponible')
        self.message_user(request, f"{queryset.count()} archive(s) marquée(s) disponible(s)")
    marquer_disponible.short_description = "Marquer comme disponible"
    
    def marquer_restauration(self, request, queryset):
        queryset.update(statut='restauration')
        self.message_user(request, f"{queryset.count()} archive(s) marquée(s) en restauration")
    marquer_restauration.short_description = "Marquer en restauration"

@admin.register(DemandeAccesArchive)
class DemandeAccesArchiveAdmin(admin.ModelAdmin):
    list_display = ['archive_link', 'demandeur_link', 'type_demande', 'statut_colore', 'montant_total', 'date_demande']
    list_filter = ['type_demande', 'statut', 'date_demande']
    search_fields = ['archive__titre', 'archive__reference', 'demandeur__email', 'demandeur__username']
    readonly_fields = ['date_demande', 'montant_total']
    
    fieldsets = (
        ('Demande', {
            'fields': ('archive', 'demandeur', 'type_demande')
        }),
        ('Motif', {
            'fields': ('motif', 'justificatif')
        }),
        ('Livraison', {
            'fields': ('adresse_livraison',),
            'classes': ('collapse',)
        }),
        ('Traitement', {
            'fields': ('statut', 'moderateur', 'commentaire_moderation', 'date_moderation')
        }),
        ('Paiement', {
            'fields': ('montant_total', 'paiement_effectue', 'reference_paiement', 'date_paiement')
        }),
        ('Accès', {
            'fields': ('token_acces', 'date_debut_acces', 'date_fin_acces', 'lien_acces'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['valider_demandes', 'rejeter_demandes', 'marquer_payees']
    
    def archive_link(self, obj):
        url = reverse('admin:archives_archive_change', args=[obj.archive.id])
        return format_html('<a href="{}">{}</a>', url, obj.archive.reference)
    archive_link.short_description = 'Archive'
    
    def demandeur_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.demandeur.id])
        return format_html('<a href="{}">{}</a>', url, obj.demandeur.get_full_name())
    demandeur_link.short_description = 'Demandeur'
    
    def statut_colore(self, obj):
        couleurs = {
            'en_attente': 'orange',
            'en_cours': 'blue',
            'valide': 'green',
            'paye': 'purple',
            'rejetee': 'red',
            'livree': 'teal',
            'cloturee': 'grey',
        }
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            couleurs.get(obj.statut, 'black'),
            obj.get_statut_display()
        )
    statut_colore.short_description = 'Statut'
    
    def valider_demandes(self, request, queryset):
        for demande in queryset:
            if demande.statut == 'en_attente':
                demande.statut = 'valide'
                demande.montant_total = demande.calculer_montant()
                demande.moderateur = request.user
                demande.date_moderation = timezone.now()
                demande.save()
        self.message_user(request, f"{queryset.count()} demande(s) validée(s)")
    valider_demandes.short_description = "Valider les demandes sélectionnées"
    
    def rejeter_demandes(self, request, queryset):
        queryset.update(statut='rejetee', moderateur=request.user, date_moderation=timezone.now())
        self.message_user(request, f"{queryset.count()} demande(s) rejetée(s)")
    rejeter_demandes.short_description = "Rejeter les demandes sélectionnées"
    
    def marquer_payees(self, request, queryset):
        now = timezone.now()
        for demande in queryset:
            demande.statut = 'paye'
            demande.paiement_effectue = True
            demande.date_paiement = now
            demande.save()
        self.message_user(request, f"{queryset.count()} demande(s) marquée(s) payée(s)")
    marquer_payees.short_description = "Marquer comme payées"