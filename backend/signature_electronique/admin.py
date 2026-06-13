from django.contrib import admin

# backend/apps/signature_electronique/admin.py

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import *


@admin.register(CertificatNumerique)
class CertificatNumeriqueAdmin(admin.ModelAdmin):
    list_display = ['utilisateur_link', 'numero_serie', 'date_emission', 'date_expiration', 'niveau_confiance', 'statut_colore']
    list_filter = ['niveau_confiance', 'est_valide', 'est_revoque']
    search_fields = ['numero_serie', 'utilisateur__email']
    
    def utilisateur_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.utilisateur.id])
        return format_html('<a href="{}">{}</a>', url, obj.utilisateur.get_full_name())
    utilisateur_link.short_description = 'Utilisateur'
    
    def statut_colore(self, obj):
        if obj.est_revoque:
            return format_html('<span style="color: red;">Révoqué</span>')
        if obj.est_expire():
            return format_html('<span style="color: orange;">Expiré</span>')
        return format_html('<span style="color: green;">Valide</span>')
    statut_colore.short_description = 'Statut'


@admin.register(SignatureElectronique)
class SignatureElectroniqueAdmin(admin.ModelAdmin):
    list_display = ['id', 'document_titre', 'signataire_link', 'module_source', 'timestamp_signature', 'est_valide']
    list_filter = ['module_source', 'est_valide', 'timestamp_signature']
    search_fields = ['document_titre', 'signataire__email']
    
    def signataire_link(self, obj):
        url = reverse('admin:auth_user_change', args=[obj.signataire.id])
        return format_html('<a href="{}">{}</a>', url, obj.signataire.get_full_name())
    signataire_link.short_description = 'Signataire'


@admin.register(DemandeSignature)
class DemandeSignatureAdmin(admin.ModelAdmin):
    list_display = ['document_titre', 'destinataire', 'envoyeur', 'statut', 'date_creation']
    list_filter = ['statut', 'date_creation']
    search_fields = ['document_titre', 'destinataire__email']


@admin.register(ConfigurationSignature)
class ConfigurationSignatureAdmin(admin.ModelAdmin):
    list_display = ['id', 'niveau_requis_etat_civil', 'niveau_requis_archives', 'delai_validite_demande']
    
    def has_add_permission(self, request):
        return not ConfigurationSignature.objects.exists()
