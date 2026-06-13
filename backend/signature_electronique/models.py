# backend/apps/signature_electronique/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
from datetime import timedelta

User = get_user_model()


class CertificatNumerique(models.Model):
    """Certificat numérique pour la signature électronique"""
    
    NIVEAUX = [
        (1, 'Signature simple'),
        (2, 'Signature avancée'),
        (3, 'Signature qualifiée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    utilisateur = models.OneToOneField(User, on_delete=models.CASCADE, related_name='certificat_signature')
    
    # Certificat
    certificat = models.TextField(help_text="Certificat X.509 au format PEM")
    cle_publique = models.TextField(help_text="Clé publique au format PEM")
    cle_privee_chiffree = models.TextField(help_text="Clé privée chiffrée (AES-256)")
    
    # Métadonnées
    numero_serie = models.CharField(max_length=100, unique=True)
    emetteur = models.CharField(max_length=200, default="Commune de Bot-Makak")
    
    # Informations du sujet
    sujet_nom = models.CharField(max_length=200, blank=True, help_text="Nom complet du titulaire")
    sujet_email = models.EmailField(blank=True)
    sujet_organisation = models.CharField(max_length=200, default="Commune de Bot-Makak", blank=True)
    
    # Validité
    date_emission = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField()
    date_revocation = models.DateTimeField(null=True, blank=True)
    
    # Statut
    est_valide = models.BooleanField(default=True)
    est_revoque = models.BooleanField(default=False)
    raison_revocation = models.TextField(blank=True)
    
    # Niveau de confiance
    niveau_confiance = models.IntegerField(choices=NIVEAUX, default=1)
    
    # AJOUTÉ: Empreinte du certificat (fingerprint)
    empreinte = models.CharField(max_length=64, blank=True, help_text="Empreinte SHA-256 du certificat")
    
    class Meta:
        verbose_name = "Certificat numérique"
        verbose_name_plural = "Certificats numériques"
        indexes = [
            models.Index(fields=['numero_serie']),
            models.Index(fields=['utilisateur', 'est_valide']),
            models.Index(fields=['date_expiration']),
        ]
    
    def __str__(self):
        return f"Certificat de {self.utilisateur.get_full_name() or self.utilisateur.username} - {self.numero_serie[:12]}..."
    
    def est_expire(self):
        """Vérifie si le certificat est expiré"""
        return timezone.now() > self.date_expiration
    
    def est_utilisable(self):
        """Vérifie si le certificat peut être utilisé pour signer"""
        return self.est_valide and not self.est_revoque and not self.est_expire()
    
    def revoquer(self, motif=""):
        """Révoque le certificat"""
        self.est_revoque = True
        self.est_valide = False
        self.date_revocation = timezone.now()
        self.raison_revocation = motif
        self.save(update_fields=['est_revoque', 'est_valide', 'date_revocation', 'raison_revocation'])
    
    def prolonger_validite(self, jours=365):
        """Prolonge la validité du certificat"""
        self.date_expiration = timezone.now() + timedelta(days=jours)
        self.save(update_fields=['date_expiration'])


class SignatureElectronique(models.Model):
    """Signature électronique d'un document"""
    
    MODULES = [
        ('etat_civil', 'État Civil'),
        ('archives', 'Archives'),
        ('activites', 'Activités'),
        ('dechets', 'Déchets'),
        ('deliberation', 'Délibération'),
        ('arrete', 'Arrêté'),
        ('paiements', 'Paiements'),  # AJOUTÉ
        ('marche_public', 'Marché Public'),  # AJOUTÉ
        ('contrat', 'Contrat'),  # AJOUTÉ
    ]
    
    TYPES_SIGNATURE = [
        ('manuscrite', 'Signature manuscrite'),
        ('electronique', 'Signature électronique simple'),
        ('avancee', 'Signature avancée'),
        ('qualifiee', 'Signature qualifiée'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Document signé
    module_source = models.CharField(max_length=50, choices=MODULES)
    source_id = models.CharField(max_length=100, blank=True)  # MODIFIÉ: blank=True
    document_titre = models.CharField(max_length=200)
    document_hash = models.CharField(max_length=64, help_text="Hash SHA-256 du document")
    
    # AJOUTÉ: Contenu du document (optionnel)
    document_contenu = models.TextField(blank=True, help_text="Contenu textuel du document signé")
    
    # Signataire
    signataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signatures')
    certificat_utilise = models.ForeignKey(CertificatNumerique, on_delete=models.CASCADE)
    
    # Signature
    signature_valeur = models.TextField(help_text="Valeur cryptographique de la signature")
    type_signature = models.CharField(max_length=20, choices=TYPES_SIGNATURE, default='electronique')
    timestamp_signature = models.DateTimeField(auto_now_add=True)
    horodatage = models.DateTimeField(default=timezone.now)  # CORRIGÉ: default
    
    # Position (pour signature graphique)
    position_x = models.IntegerField(default=0)
    position_y = models.IntegerField(default=0)
    largeur = models.IntegerField(default=200)
    hauteur = models.IntegerField(default=80)
    
    # AJOUTÉ: Image de la signature manuscrite
    signature_image = models.TextField(blank=True, help_text="Image de la signature (base64)")
    
    # Métadonnées
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    # Statut
    est_valide = models.BooleanField(default=True)
    date_validation = models.DateTimeField(auto_now_add=True)
    
    # AJOUTÉ: Raison de la signature
    raison_signature = models.CharField(max_length=255, blank=True, help_text="Raison de la signature")
    
    class Meta:
        ordering = ['-timestamp_signature']
        indexes = [
            models.Index(fields=['module_source', 'source_id']),
            models.Index(fields=['signataire', 'timestamp_signature']),
            models.Index(fields=['document_hash']),
            models.Index(fields=['timestamp_signature']),
        ]
        verbose_name = "Signature électronique"
        verbose_name_plural = "Signatures électroniques"
    
    def __str__(self):
        return f"Signature de {self.signataire.get_full_name() or self.signataire.username} - {self.document_titre[:50]}"
    
    def verifier(self, document=None):
        """Vérifie la validité de la signature"""
        from .utils import verifier_signature, calculer_hash_contenu
        
        doc_a_verifier = document or self.document_contenu
        if not doc_a_verifier:
            return False
        
        # Vérifier le hash
        hash_ok = calculer_hash_contenu(doc_a_verifier) == self.document_hash
        
        # Vérifier la signature cryptographique
        try:
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            signature_ok = verifier_signature(doc_a_verifier, self.signature_valeur, 
                                               self.certificat_utilise.cle_publique)
        except:
            signature_ok = False
        
        return hash_ok and signature_ok


class DemandeSignature(models.Model):
    """Demande de signature envoyée à un citoyen"""
    
    MODULES = SignatureElectronique.MODULES
    
    STATUTS = [
        ('en_attente', 'En attente de signature'),
        ('signe', 'Signé'),
        ('expire', 'Expiré'),
        ('annule', 'Annulé'),
        ('refuse', 'Refusé'),  # AJOUTÉ
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Document à signer
    module_source = models.CharField(max_length=50, choices=MODULES)
    source_id = models.CharField(max_length=100, blank=True)
    document_titre = models.CharField(max_length=200)
    document_contenu = models.TextField(help_text="Contenu du document à signer")
    
    # AJOUTÉ: Document original (fichier)
    document_fichier = models.FileField(upload_to='signatures/documents/%Y/%m/', null=True, blank=True)
    
    # Destinataire
    destinataire = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_signature')
    envoyeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='signatures_envoyees')
    
    # AJOUTÉ: Email du destinataire (pour envoi externe)
    destinataire_email = models.EmailField(blank=True)
    
    # Token unique pour signature
    token = models.CharField(max_length=100, unique=True)
    
    # AJOUTÉ: Message personnalisé
    message_personnalise = models.TextField(blank=True, help_text="Message joint à la demande")
    
    # Statut
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField()
    date_signature = models.DateTimeField(null=True, blank=True)
    
    # Signature associée
    signature = models.OneToOneField(SignatureElectronique, null=True, blank=True, on_delete=models.SET_NULL, related_name='demande')
    
    # AJOUTÉ: Nombre de relances
    nb_relances = models.PositiveIntegerField(default=0)
    derniere_relance = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['token']),
            models.Index(fields=['statut', 'date_expiration']),
            models.Index(fields=['destinataire', 'statut']),
        ]
        verbose_name = "Demande de signature"
        verbose_name_plural = "Demandes de signature"
    
    def __str__(self):
        return f"Demande de signature pour {self.destinataire.get_full_name() or self.destinataire.username} - {self.document_titre[:40]}"
    
    def est_expiree(self):
        """Vérifie si la demande est expirée"""
        return timezone.now() > self.date_expiration
    
    def peut_etre_signe(self):
        """Vérifie si la demande peut encore être signée"""
        return self.statut == 'en_attente' and not self.est_expiree()
    
    def expirer(self):
        """Marque la demande comme expirée"""
        if self.est_expiree() and self.statut == 'en_attente':
            self.statut = 'expire'
            self.save(update_fields=['statut'])
            return True
        return False


class JournalSignature(models.Model):
    """Journal d'audit des signatures"""
    
    ACTIONS = [
        ('creation', 'Création de signature'),
        ('validation', 'Validation de signature'),
        ('verification', 'Vérification de signature'),
        ('rejet', 'Rejet de signature'),
        ('revocation_certificat', 'Révocation de certificat'),
        ('demande_envoyee', 'Demande envoyée'),
        ('demande_annulee', 'Demande annulée'),
        ('relance', 'Relance envoyée'),
    ]
    
    signature = models.ForeignKey(SignatureElectronique, on_delete=models.CASCADE, related_name='journal', null=True, blank=True)
    demande = models.ForeignKey(DemandeSignature, on_delete=models.CASCADE, related_name='journal', null=True, blank=True)  # AJOUTÉ
    action = models.CharField(max_length=50, choices=ACTIONS)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    commentaire = models.TextField(blank=True)
    date_action = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)  # AJOUTÉ
    
    class Meta:
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['signature', 'action']),
            models.Index(fields=['date_action']),
            models.Index(fields=['utilisateur', 'date_action']),
        ]
        verbose_name = "Journal de signature"
        verbose_name_plural = "Journaux de signature"
    
    def __str__(self):
        return f"{self.get_action_display()} - {self.utilisateur.get_full_name() or self.utilisateur.username} - {self.date_action.strftime('%d/%m/%Y %H:%M')}"


class VerificationSignature(models.Model):
    """Historique des vérifications de signature"""
    
    signature = models.ForeignKey(SignatureElectronique, on_delete=models.CASCADE, related_name='verifications')
    verificateur = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)  # MODIFIÉ: null=True
    resultat = models.BooleanField()
    details = models.JSONField(default=dict)
    date_verification = models.DateTimeField(auto_now_add=True)
    adresse_ip = models.GenericIPAddressField(null=True, blank=True)  # AJOUTÉ
    
    class Meta:
        ordering = ['-date_verification']
        indexes = [
            models.Index(fields=['signature', 'date_verification']),
            models.Index(fields=['resultat']),
        ]
        verbose_name = "Vérification de signature"
        verbose_name_plural = "Vérifications de signature"
    
    def __str__(self):
        return f"Vérification de {self.signature.document_titre[:30]} - {'Valide' if self.resultat else 'Invalide'}"


class ConfigurationSignature(models.Model):
    """Configuration du module de signature électronique"""
    
    # Niveaux requis par module
    niveau_requis_etat_civil = models.IntegerField(choices=CertificatNumerique.NIVEAUX, default=1)
    niveau_requis_archives = models.IntegerField(choices=CertificatNumerique.NIVEAUX, default=2)
    niveau_requis_activites = models.IntegerField(choices=CertificatNumerique.NIVEAUX, default=1)
    niveau_requis_dechets = models.IntegerField(choices=CertificatNumerique.NIVEAUX, default=1)  # AJOUTÉ
    niveau_requis_marche_public = models.IntegerField(choices=CertificatNumerique.NIVEAUX, default=3)  # AJOUTÉ
    
    # Délais
    delai_validite_demande = models.IntegerField(default=7, help_text="Délai en jours avant expiration des demandes")
    delai_relance = models.IntegerField(default=2, help_text="Délai en jours avant relance")
    
    # AJOUTÉ: Clés système pour les signatures automatiques
    cle_privee_systeme = models.TextField(blank=True, help_text="Clé privée du système (chiffrée)")
    cle_publique_systeme = models.TextField(blank=True, help_text="Clé publique du système")
    
    # AJOUTÉ: Paramètres divers
    signature_automatique = models.BooleanField(default=False, help_text="Permet les signatures automatiques pour certains documents")
    stockage_preuve = models.BooleanField(default=True, help_text="Stockage des preuves de signature")
    horizon_archivage = models.IntegerField(default=10, help_text="Années d'archivage des signatures")
    
    # AJOUTÉ: Horodatage
    service_horodatage_url = models.URLField(blank=True, help_text="URL du service d'horodatage")
    service_horodatage_token = models.CharField(max_length=255, blank=True)
    
    # AJOUTÉ: Cachet électronique
    cachet_actif = models.BooleanField(default=True, help_text="Apposer un cachet électronique")
    cachet_image = models.ImageField(upload_to='signatures/cachets/', null=True, blank=True)
    
    class Meta:
        verbose_name = "Configuration de la signature"
        verbose_name_plural = "Configurations de la signature"
    
    def __str__(self):
        return "Configuration de la signature électronique"
    
    def save(self, *args, **kwargs):
        """Empêche la création de multiples configurations"""
        if not self.pk and ConfigurationSignature.objects.exists():
            # Mettre à jour la configuration existante au lieu d'en créer une nouvelle
            existing = ConfigurationSignature.objects.first()
            self.pk = existing.pk
            self.id = existing.id
        super().save(*args, **kwargs)


# AJOUTÉ: Modèle pour les cachets électroniques
class CachetElectronique(models.Model):
    """Cachet électronique pour authentification des documents"""
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nom = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='signatures/cachets/', null=True, blank=True)
    certificat = models.TextField(help_text="Certificat du cachet")
    cle_privee = models.TextField(help_text="Clé privée du cachet (chiffrée)")
    est_actif = models.BooleanField(default=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_expiration = models.DateTimeField()
    
    class Meta:
        verbose_name = "Cachet électronique"
        verbose_name_plural = "Cachets électroniques"
    
    def __str__(self):
        return f"Cachet: {self.nom}"


# AJOUTÉ: Modèle pour les preuves de signature
class PreuveSignature(models.Model):
    """Preuve de signature (horodatage et conservation)"""
    
    signature = models.OneToOneField(SignatureElectronique, on_delete=models.CASCADE, related_name='preuve')
    horodatage_externe = models.DateTimeField(help_text="Horodatage certifié par un tiers")
    jeton_horodatage = models.TextField(help_text="Jetons d'horodatage (RFC 3161)")
    empreinte_longue = models.CharField(max_length=255, help_text="Empreinte pour la conservation")
    preuve_conservation = models.FileField(upload_to='signatures/preuves/%Y/%m/', null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Preuve de signature"
        verbose_name_plural = "Preuves de signature"
    
    def __str__(self):
        return f"Preuve pour signature {self.signature.document_titre[:40]}"


# AJOUTÉ: Modèle pour les relances
class RelanceSignature(models.Model):
    """Historique des relances pour les demandes de signature"""
    
    demande = models.ForeignKey(DemandeSignature, on_delete=models.CASCADE, related_name='relances')
    date_relance = models.DateTimeField(auto_now_add=True)
    canal = models.CharField(max_length=20, choices=[('email', 'Email'), ('sms', 'SMS'), ('push', 'Notification push')])
    message = models.TextField()
    statut = models.CharField(max_length=20, choices=[('envoye', 'Envoyé'), ('echoue', 'Échoué')], default='envoye')
    
    class Meta:
        ordering = ['-date_relance']
    
    def __str__(self):
        return f"Relance pour {self.demande.document_titre[:40]} - {self.date_relance.strftime('%d/%m/%Y')}"