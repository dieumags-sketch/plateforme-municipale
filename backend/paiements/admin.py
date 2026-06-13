from django.contrib import admin
from .models import (
    ConfigurationPaiement, TransactionPaiement, PortefeuilleCitoyen,
    RecuPaiement, JournalPaiement, TransactionPortefeuille,
    FactureRecurrente, Remboursement, WebhookPaiement
)


@admin.register(ConfigurationPaiement)
class ConfigurationPaiementAdmin(admin.ModelAdmin):
    list_display = ['mode', 'est_actif', 'montant_min', 'montant_max']
    list_filter = ['mode', 'est_actif']
    search_fields = ['mode']


@admin.register(TransactionPaiement)
class TransactionPaiementAdmin(admin.ModelAdmin):
    list_display = ['reference', 'utilisateur', 'montant_total', 'mode', 'statut', 'date_creation']
    list_filter = ['mode', 'statut', 'date_creation']
    search_fields = ['reference', 'utilisateur__email', 'utilisateur__username']
    readonly_fields = ['reference', 'date_creation', 'date_confirmation']


@admin.register(PortefeuilleCitoyen)
class PortefeuilleCitoyenAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'solde', 'points_fidelite', 'date_derniere_mise_a_jour']
    search_fields = ['utilisateur__email', 'utilisateur__username']
    readonly_fields = ['date_derniere_mise_a_jour']


@admin.register(RecuPaiement)
class RecuPaiementAdmin(admin.ModelAdmin):
    list_display = ['numero_recu', 'transaction', 'date_generation']
    search_fields = ['numero_recu', 'transaction__reference']


@admin.register(JournalPaiement)
class JournalPaiementAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'action', 'date_action']
    list_filter = ['action', 'date_action']
    search_fields = ['transaction__reference']


@admin.register(TransactionPortefeuille)
class TransactionPortefeuilleAdmin(admin.ModelAdmin):
    list_display = ['portefeuille', 'montant', 'type_transaction', 'date_creation']
    list_filter = ['type_transaction', 'date_creation']


@admin.register(FactureRecurrente)
class FactureRecurrenteAdmin(admin.ModelAdmin):
    list_display = ['libelle', 'utilisateur', 'montant', 'periode', 'statut']
    list_filter = ['periode', 'statut']


@admin.register(Remboursement)
class RemboursementAdmin(admin.ModelAdmin):
    list_display = ['transaction', 'montant_rembourse', 'statut', 'date_demande']
    list_filter = ['statut', 'date_demande']


@admin.register(WebhookPaiement)
class WebhookPaiementAdmin(admin.ModelAdmin):
    list_display = ['url', 'evenement', 'est_actif', 'date_creation']
    list_filter = ['est_actif', 'evenement']