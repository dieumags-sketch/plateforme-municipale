# backend/apps/paiements/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone  # AJOUTÉ
import uuid
import secrets  # AJOUTÉ
from datetime import timedelta

User = get_user_model()


class ConfigurationPaiement(models.Model):
    """Configuration des modes de paiement"""
    MODES = [
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
        ('virement', 'Virement bancaire'),
        ('cash', 'Cash physique'),
        ('carte', 'Carte bancaire'),  # AJOUTÉ
        ('portefeuille', 'Portefeuille citoyen'),  # AJOUTÉ
    ]
    
    mode = models.CharField(max_length=20, choices=MODES, unique=True)
    nom = models.CharField(max_length=100, blank=True, help_text="Nom affiché")  # AJOUTÉ
    est_actif = models.BooleanField(default=True)
    ordre_affichage = models.PositiveIntegerField(default=0)  # AJOUTÉ
    
    # Configuration API Mobile Money
    api_url = models.URLField(blank=True, null=True)
    api_key = models.CharField(max_length=200, blank=True)
    api_secret = models.CharField(max_length=200, blank=True)
    merchant_code = models.CharField(max_length=50, blank=True)
    
    # Configuration bancaire
    rib = models.CharField(max_length=50, blank=True)
    iban = models.CharField(max_length=50, blank=True)
    bic = models.CharField(max_length=20, blank=True)
    titulaire_compte = models.CharField(max_length=200, blank=True)
    banque = models.CharField(max_length=100, blank=True)
    
    # Frais et taxes
    frais_fixe = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    frais_pourcentage = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    taxe = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    # Seuils
    montant_min = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_max = models.DecimalField(max_digits=10, decimal_places=2, default=1000000)
    
    # Délai d'expiration (minutes)
    expiration_minutes = models.PositiveIntegerField(default=30, help_text="Délai d'expiration en minutes")  # AJOUTÉ
    
    # AJOUTÉ: Logo/icône
    logo = models.ImageField(upload_to='paiements/logos/', null=True, blank=True)
    
    class Meta:
        ordering = ['ordre_affichage', 'mode']
        verbose_name = "Configuration de paiement"
        verbose_name_plural = "Configurations de paiement"
    
    def __str__(self):
        return f"{self.get_mode_display()} - {'Actif' if self.est_actif else 'Inactif'}"
    
    def save(self, *args, **kwargs):
        if not self.nom:
            self.nom = self.get_mode_display()
        super().save(*args, **kwargs)


class TransactionPaiement(models.Model):
    """Transaction de paiement"""
    MODES = [
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
        ('virement', 'Virement bancaire'),
        ('cash', 'Cash physique'),
        ('carte', 'Carte bancaire'),  # AJOUTÉ
        ('portefeuille', 'Portefeuille citoyen'),  # AJOUTÉ
    ]
    
    STATUTS = [
        ('initie', 'Initié'),
        ('en_attente', 'En attente'),
        ('confirme', 'Confirmé'),
        ('echoue', 'Échoué'),
        ('annule', 'Annulé'),
        ('rembourse', 'Remboursé'),
        ('expire', 'Expiré'),  # AJOUTÉ
    ]
    
    MODULES_SOURCE = [
        ('etat_civil', 'État Civil'),
        ('activites', 'Activités'),
        ('dechets', 'Déchets'),
        ('archives', 'Archives'),
        ('amendes', 'Amendes'),
        ('taxes', 'Taxes'),
        ('signatures', 'Signatures électroniques'),  # AJOUTÉ
        ('portefeuille', 'Portefeuille citoyen'),  # AJOUTÉ
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=100, unique=True)
    
    # Liens
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='transactions')
    module_source = models.CharField(max_length=50, choices=MODULES_SOURCE, default='etat_civil')
    source_id = models.CharField(max_length=100, blank=True)
    
    # Montants
    montant_net = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])  # AJOUTÉ validateur
    frais = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    taxe = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Mode et statut
    mode = models.CharField(max_length=20, choices=MODES)
    statut = models.CharField(max_length=20, choices=STATUTS, default='initie')
    
    # Informations de paiement
    telephone = models.CharField(max_length=20, blank=True)
    numero_transaction = models.CharField(max_length=100, blank=True)
    code_validation = models.CharField(max_length=10, blank=True)
    
    # Virement bancaire
    reference_bancaire = models.CharField(max_length=100, blank=True)
    preuve_virement = models.FileField(upload_to='preuves_virement/%Y/%m/', null=True, blank=True)  # CORRIGÉ: dossier
    
    # Cash
    recu_cash = models.FileField(upload_to='recus_cash/%Y/%m/', null=True, blank=True)  # CORRIGÉ: dossier
    encaisse_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='encaissements')
    
    # AJOUTÉ: Carte bancaire
    carte_masquee = models.CharField(max_length=19, blank=True, help_text="Numéro de carte masqué (ex: **** **** **** 1234)")
    carte_token = models.CharField(max_length=255, blank=True)
    
    # AJOUTÉ: Métadonnées supplémentaires
    message_erreur = models.TextField(blank=True)  # AJOUTÉ
    tentative_compteur = models.PositiveIntegerField(default=0)  # AJOUTÉ
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_confirmation = models.DateTimeField(null=True, blank=True)
    date_expiration = models.DateTimeField(null=True, blank=True)
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['statut', 'mode']),
            models.Index(fields=['utilisateur', 'date_creation']),
            models.Index(fields=['module_source', 'source_id']),  # AJOUTÉ
            models.Index(fields=['date_expiration']),  # AJOUTÉ
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.utilisateur.get_full_name() or self.utilisateur.username} - {self.montant_total} FCFA"
    
    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = f"PAY-{secrets.token_hex(8).upper()}"
        
        # Définir date d'expiration si non définie
        if not self.date_expiration and self.mode in ['mtn', 'orange']:
            try:
                config = ConfigurationPaiement.objects.get(mode=self.mode, est_actif=True)
                self.date_expiration = timezone.now() + timedelta(minutes=config.expiration_minutes)
            except ConfigurationPaiement.DoesNotExist:
                self.date_expiration = timezone.now() + timedelta(minutes=30)
        
        super().save(*args, **kwargs)
    
    def calculer_frais(self):
        """Calcule les frais selon le mode de paiement"""
        try:
            config = ConfigurationPaiement.objects.get(mode=self.mode, est_actif=True)
            frais = float(self.montant_net) * (float(config.frais_pourcentage) / 100) + float(config.frais_fixe)
            return round(frais, 2)
        except ConfigurationPaiement.DoesNotExist:
            return 0
    
    def calculer_taxe(self):
        """Calcule la taxe"""
        try:
            config = ConfigurationPaiement.objects.get(mode=self.mode, est_actif=True)
            taxe = (float(self.montant_net) + float(self.frais)) * (float(config.taxe) / 100)
            return round(taxe, 2)
        except ConfigurationPaiement.DoesNotExist:
            return 0
    
    def est_expiree(self):
        """Vérifie si la transaction est expirée"""
        if self.date_expiration and self.statut in ['initie', 'en_attente']:
            return timezone.now() > self.date_expiration
        return False
    
    def peut_etre_annulee(self):
        """Vérifie si la transaction peut être annulée"""
        return self.statut in ['initie', 'en_attente'] and not self.est_expiree()
    
    def peut_etre_rembourse(self):
        """Vérifie si la transaction peut être remboursée"""
        return self.statut == 'confirme' and (timezone.now() - self.date_confirmation).days < 14


class RecuPaiement(models.Model):
    """Reçu de paiement"""
    transaction = models.OneToOneField(TransactionPaiement, on_delete=models.CASCADE, related_name='recu')
    numero_recu = models.CharField(max_length=50, unique=True)
    fichier_pdf = models.FileField(upload_to='recus_pdf/%Y/%m/', null=True, blank=True)  # CORRIGÉ: dossier
    date_generation = models.DateTimeField(auto_now_add=True)
    
    # AJOUTÉ: QR code pour vérification
    qr_code = models.ImageField(upload_to='recus_qr/%Y/%m/', null=True, blank=True)
    
    class Meta:
        ordering = ['-date_generation']
        verbose_name = "Reçu de paiement"
        verbose_name_plural = "Reçus de paiement"
    
    def __str__(self):
        return f"Reçu {self.numero_recu}"
    
    def save(self, *args, **kwargs):
        if not self.numero_recu:
            import secrets
            self.numero_recu = f"REC-{secrets.token_hex(6).upper()}"
        super().save(*args, **kwargs)


class JournalPaiement(models.Model):
    """Journal d'audit des paiements"""
    transaction = models.ForeignKey(TransactionPaiement, on_delete=models.CASCADE, related_name='logs')
    action = models.CharField(max_length=50)
    ancien_statut = models.CharField(max_length=20, null=True, blank=True)
    nouveau_statut = models.CharField(max_length=20)
    message = models.TextField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)  # AJOUTÉ
    date_action = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['transaction', 'action']),
            models.Index(fields=['date_action']),
        ]
        verbose_name = "Journal de paiement"
        verbose_name_plural = "Journaux de paiement"
    
    def __str__(self):
        return f"{self.transaction.reference} - {self.action} - {self.date_action.strftime('%d/%m/%Y %H:%M')}"


class PortefeuilleCitoyen(models.Model):
    """Portefeuille virtuel du citoyen"""
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='portefeuille')
    solde = models.DecimalField(max_digits=10, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    points_fidelite = models.IntegerField(default=0)
    
    # AJOUTÉ: Plafond du portefeuille
    plafond = models.DecimalField(max_digits=10, decimal_places=2, default=500000, help_text="Plafond maximum du portefeuille")
    
    # AJOUTÉ: Statut
    est_active = models.BooleanField(default=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)  # AJOUTÉ
    date_derniere_mise_a_jour = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Portefeuille citoyen"
        verbose_name_plural = "Portefeuilles citoyens"
    
    def __str__(self):
        return f"Portefeuille de {self.utilisateur.get_full_name() or self.utilisateur.username} - {self.solde} FCFA"
    
    def crediter(self, montant):
        """Crédite le portefeuille"""
        nouveau_solde = self.solde + montant
        if nouveau_solde <= self.plafond:
            self.solde = nouveau_solde
            self.save(update_fields=['solde', 'date_derniere_mise_a_jour'])
            return True
        return False
    
    def debiter(self, montant):
        """Débite le portefeuille"""
        if self.solde >= montant:
            self.solde -= montant
            self.save(update_fields=['solde', 'date_derniere_mise_a_jour'])
            return True
        return False
    
    def ajouter_points_fidelite(self, points):
        """Ajoute des points de fidélité"""
        self.points_fidelite += points
        self.save(update_fields=['points_fidelite'])


class TransactionPortefeuille(models.Model):
    """Transactions du portefeuille"""
    TYPE_CHOICES = [
        ('credit', 'Crédit'),
        ('debit', 'Débit'),
    ]
    
    # AJOUTÉ: Catégories
    CATEGORIES = [
        ('recharge', 'Recharge'),
        ('paiement', 'Paiement'),
        ('remboursement', 'Remboursement'),
        ('cashback', 'Cashback'),
        ('bonus', 'Bonus'),
    ]
    
    portefeuille = models.ForeignKey(PortefeuilleCitoyen, on_delete=models.CASCADE, related_name='transactions')
    montant = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    type_transaction = models.CharField(max_length=20, choices=TYPE_CHOICES)
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='recharge')  # AJOUTÉ
    description = models.CharField(max_length=200)
    transaction_liee = models.ForeignKey(TransactionPaiement, null=True, blank=True, on_delete=models.SET_NULL)
    
    # AJOUTÉ: Solde après transaction
    solde_apres = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['portefeuille', '-date_creation']),
            models.Index(fields=['type_transaction', 'categorie']),
        ]
        verbose_name = "Transaction de portefeuille"
        verbose_name_plural = "Transactions de portefeuille"
    
    def __str__(self):
        return f"{self.get_type_transaction_display()} - {self.montant} FCFA - {self.description[:50]}"
    
    def save(self, *args, **kwargs):
        """Enregistre le solde après transaction"""
        if not self.solde_apres:
            if self.type_transaction == 'credit':
                self.solde_apres = self.portefeuille.solde
            else:
                self.solde_apres = self.portefeuille.solde
        super().save(*args, **kwargs)


# AJOUTÉ: Modèle pour les factures récurrentes
class FactureRecurrente(models.Model):
    """Factures récurrentes (taxes, impôts)"""
    
    PERIODES = [
        ('mensuel', 'Mensuel'),
        ('trimestriel', 'Trimestriel'),
        ('semestriel', 'Semestriel'),
        ('annuel', 'Annuel'),
    ]
    
    STATUTS = [
        ('active', 'Active'),
        ('suspendue', 'Suspendue'),
        ('terminee', 'Terminée'),
    ]
    
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='factures_recurrentes')
    libelle = models.CharField(max_length=200)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    periode = models.CharField(max_length=20, choices=PERIODES)
    jour_echeance = models.PositiveSmallIntegerField(help_text="Jour du mois pour l'échéance")
    prochaine_echeance = models.DateField()
    statut = models.CharField(max_length=20, choices=STATUTS, default='active')
    dernier_paiement = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['prochaine_echeance']
        verbose_name = "Facture récurrente"
        verbose_name_plural = "Factures récurrentes"
    
    def __str__(self):
        return f"{self.libelle} - {self.utilisateur.get_full_name()} - {self.montant} FCFA"


# AJOUTÉ: Modèle pour les remboursements
class Remboursement(models.Model):
    """Demandes de remboursement"""
    
    STATUTS = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('approuve', 'Approuvé'),
        ('rejete', 'Rejeté'),
        ('rembourse', 'Remboursé'),
    ]
    
    transaction = models.ForeignKey(TransactionPaiement, on_delete=models.CASCADE, related_name='remboursements')
    motif = models.TextField()
    montant_rembourse = models.DecimalField(max_digits=10, decimal_places=2)
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    commentaire_moderation = models.TextField(blank=True)
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    traite_par = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='remboursements_traites')
    
    class Meta:
        ordering = ['-date_demande']
        verbose_name = "Remboursement"
        verbose_name_plural = "Remboursements"
    
    def __str__(self):
        return f"Remboursement {self.transaction.reference} - {self.montant_rembourse} FCFA"


# AJOUTÉ: Modèle pour les webhooks de notification
class WebhookPaiement(models.Model):
    """Configuration des webhooks pour les notifications de paiement"""
    
    EVENEMENTS = [
        ('transaction.confirmee', 'Transaction confirmée'),
        ('transaction.echouee', 'Transaction échouée'),
        ('transaction.rembourse', 'Transaction remboursée'),
        ('portefeuille.credite', 'Portefeuille crédité'),
        ('portefeuille.debite', 'Portefeuille débité'),
    ]
    
    url = models.URLField()
    evenement = models.CharField(max_length=50, choices=EVENEMENTS)
    secret = models.CharField(max_length=255, blank=True)
    est_actif = models.BooleanField(default=True)
    tentative_compteur = models.PositiveIntegerField(default=0)
    dernier_envoi = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['url', 'evenement']
        verbose_name = "Webhook de paiement"
        verbose_name_plural = "Webhooks de paiement"
    
    def __str__(self):
        return f"{self.get_evenement_display()} -> {self.url}"


# AJOUTÉ: Modèle pour les logs de webhook
class WebhookLog(models.Model):
    """Journal des envois de webhook"""
    webhook = models.ForeignKey(WebhookPaiement, on_delete=models.CASCADE, related_name='logs')
    transaction = models.ForeignKey(TransactionPaiement, on_delete=models.CASCADE, null=True, blank=True)
    payload = models.JSONField(default=dict)
    reponse_status = models.IntegerField(null=True, blank=True)
    reponse_body = models.TextField(blank=True)
    erreur = models.TextField(blank=True)
    date_envoi = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_envoi']
        verbose_name = "Log de webhook"
        verbose_name_plural = "Logs de webhook"
    
    def __str__(self):
        return f"Webhook {self.webhook.id} - {self.date_envoi}"