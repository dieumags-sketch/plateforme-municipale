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
    list_display = ['nom', 'code', 'chef_lieu', 'population']
    search_fields = ['nom', 'code']
    ordering = ['nom']


@admin.register(Departement)
class DepartementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'region', 'chef_lieu']
    list_filter = ['region']
    search_fields = ['nom', 'code']


@admin.register(Arrondissement)
class ArrondissementAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'departement', 'chef_lieu']
    list_filter = ['departement']
    search_fields = ['nom', 'code']


@admin.register(DistrictSante)
class DistrictSanteAdmin(admin.ModelAdmin):
    list_display = ['nom', 'code', 'arrondissement']
    list_filter = ['arrondissement']
    search_fields = ['nom', 'code']


@admin.register(ConfigurationTarif)
class ConfigurationTarifAdmin(admin.ModelAdmin):
    """Administration des configurations tarifaires"""
    list_display = ['type_acte', 'tarif_normal', 'tarif_retard', 'delai_normal_jours', 'est_actif']
    list_filter = ['type_acte', 'est_actif']
    list_editable = ['tarif_normal', 'tarif_retard', 'delai_normal_jours', 'est_actif']
    search_fields = ['type_acte']


@admin.register(DemandeActe)
class DemandeActeAdmin(admin.ModelAdmin):
    list_display = ['reference', 'type_acte', 'demandeur', 'statut', 'date_creation']
    list_filter = ['type_acte', 'statut', 'date_creation']
    search_fields = ['reference', 'demandeur__email']
    readonly_fields = ['reference', 'date_creation', 'date_modification']
    date_hierarchy = 'date_creation'


@admin.register(HistoriqueStatut)
class HistoriqueStatutAdmin(admin.ModelAdmin):
    list_display = ['demande', 'ancien_statut', 'nouveau_statut', 'utilisateur', 'date']
    list_filter = ['ancien_statut', 'nouveau_statut']
    search_fields = ['demande__reference']


@admin.register(NotificationActe)
class NotificationActeAdmin(admin.ModelAdmin):
    list_display = ['titre', 'demande', 'est_lue', 'date_envoi']
    list_filter = ['est_lue', 'date_envoi']
    search_fields = ['titre']


@admin.register(CertificatVie)
class CertificatVieAdmin(admin.ModelAdmin):
    list_display = ['beneficiaire', 'date_validite', 'numero_pension']
    search_fields = ['beneficiaire', 'numero_pension']


@admin.register(CopieActe)
class CopieActeAdmin(admin.ModelAdmin):
    list_display = ['acte_original', 'nombre_copies']
    search_fields = ['acte_original']