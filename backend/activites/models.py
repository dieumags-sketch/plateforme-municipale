from django.db import models

# activites/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from django_ckeditor_5.fields import CKEditor5Field
import uuid

Utilisateur = get_user_model()

class CategorieActivite(models.Model):
    """Catégorie d'activité"""
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, default="fas fa-calendar-alt")
    couleur = models.CharField(max_length=20, default="#667eea")
    ordre = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return self.nom

class Activite(models.Model):
    """Activité principale"""
    
    TYPE_CHOICES = (
        ('sante', '🏥 Campagne de santé'),
        ('formation', '📚 Formation'),
        ('culturel', '🎭 Événement culturel'),
        ('sportif', '⚽ Événement sportif'),
        ('social', '🤝 Action sociale'),
        ('environnement', '🌱 Environnement'),
        ('citoyen', '🗳️ Réunion citoyenne'),
        ('autre', '📌 Autre'),
    )
    
    STATUT_CHOICES = (
        ('brouillon', 'Brouillon'),
        ('publie', 'Publié'),
        ('complet', 'Complet'),
        ('annule', 'Annulé'),
        ('termine', 'Terminé'),
    )
    
    # Informations générales
    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)
    type_activite = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre')
    categorie = models.ForeignKey(CategorieActivite, on_delete=models.SET_NULL, null=True)
    description_courte = models.CharField(max_length=300)
    description_longue = CKEditor5Field()
    
    # Images et médias
    image_principale = models.ImageField(upload_to='activites/%Y/%m/')
    images_galerie = models.JSONField(default=list, blank=True)  # URLs des images supplémentaires
    video_url = models.URLField(blank=True, help_text="Lien YouTube/Vimeo")
    
    # Dates
    date_debut = models.DateTimeField()
    date_fin = models.DateTimeField()
    date_limite_inscription = models.DateTimeField()
    date_publication = models.DateTimeField(default=timezone.now)
    
    # Capacité et prix
    capacite_max = models.PositiveIntegerField(default=0, help_text="0 = illimité")
    prix = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    est_gratuit = models.BooleanField(default=True)
    
    # Lieu
    lieu = models.CharField(max_length=300)
    adresse = models.TextField()
    ville = models.CharField(max_length=100)
    coordonnees_gps = models.CharField(max_length=100, blank=True, help_text="Latitude,Longitude")
    
    # Organisation
    organisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='activites_organisees')
    partenaires = models.TextField(blank=True, help_text="Liste des partenaires")
    
    # Statut et visibilité
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    est_a_la_une = models.BooleanField(default=False)
    est_recommandee = models.BooleanField(default=False)
    
    # Compteurs
    vue_count = models.PositiveIntegerField(default=0)
    partage_count = models.PositiveIntegerField(default=0)
    
    # Dates système
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Activité"
        verbose_name_plural = "Activités"
        ordering = ['-date_debut']
        indexes = [
            models.Index(fields=['statut', 'date_debut']),
            models.Index(fields=['type_activite']),
            models.Index(fields=['est_a_la_une']),
        ]
    
    def __str__(self):
        return self.titre
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.titre)
            # Éviter les doublons
            if Activite.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{uuid.uuid4().hex[:4]}"
        self.est_gratuit = self.prix == 0
        super().save(*args, **kwargs)
    
    @property
    def places_restantes(self):
        if self.capacite_max == 0:
            return -1  # Illimité
        inscrits = self.inscriptions.filter(statut='confirmee').count()
        return self.capacite_max - inscrits
    
    @property
    def est_complet(self):
        if self.capacite_max == 0:
            return False
        return self.places_restantes <= 0
    
    @property
    def nb_inscrits(self):
        return self.inscriptions.filter(statut='confirmee').count()
    
    @property
    def nb_en_attente(self):
        return self.inscriptions.filter(statut='en_attente_paiement').count()
    
    def increment_vue(self):
        self.vue_count += 1
        self.save(update_fields=['vue_count'])

class Inscription(models.Model):
    """Inscription d'un citoyen à une activité"""
    
    STATUT_CHOICES = (
        ('en_attente_paiement', 'En attente de paiement'),
        ('confirmee', 'Confirmée'),
        ('annulee', 'Annulée'),
        ('present', 'Présent'),
        ('absent', 'Absent'),
    )
    
    # Identifiant unique
    reference = models.CharField(max_length=50, unique=True, blank=True)
    
    # Liens
    activite = models.ForeignKey(Activite, on_delete=models.CASCADE, related_name='inscriptions')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='inscriptions_activites')
    
    # Informations inscription
    nom_complet = models.CharField(max_length=200)
    email = models.EmailField()
    telephone = models.CharField(max_length=50)
    date_naissance = models.DateField(null=True, blank=True)
    adresse = models.TextField(blank=True)
    commentaire = models.TextField(blank=True)
    
    # Nombre de places (pour inscriptions groupées)
    nombre_places = models.PositiveIntegerField(default=1)
    noms_accompagnants = models.TextField(blank=True, help_text="Noms des personnes accompagnantes")
    
    # Paiement
    montant_total = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    moyen_paiement = models.CharField(max_length=50, blank=True, choices=[
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
        ('carte', 'Carte bancaire'),
        ('especes', 'Espèces'),
        ('virement', 'Virement bancaire'),
    ])
    reference_paiement = models.CharField(max_length=100, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    
    # Statut
    statut = models.CharField(max_length=30, choices=STATUT_CHOICES, default='en_attente_paiement')
    
    # QR Code pour entrée
    qr_code = models.TextField(blank=True)  # Base64 du QR code
    
    # Dates
    date_inscription = models.DateTimeField(auto_now_add=True)
    date_annulation = models.DateTimeField(null=True, blank=True)
    date_presence = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Inscription"
        verbose_name_plural = "Inscriptions"
        ordering = ['-date_inscription']
        unique_together = ['activite', 'utilisateur']  # Un utilisateur ne peut s'inscrire qu'une fois
    
    def save(self, *args, **kwargs):
        if not self.reference:
            # Générer une référence unique
            prefix = "INS"
            date_str = timezone.now().strftime("%Y%m%d")
            random_part = uuid.uuid4().hex[:6].upper()
            self.reference = f"{prefix}-{date_str}-{random_part}"
        
        self.montant_total = self.activite.prix * self.nombre_places
        
        # Générer QR code si confirmation
        if self.statut == 'confirmee' and not self.qr_code:
            self.generate_qr_code()
        
        super().save(*args, **kwargs)
    
    def generate_qr_code(self):
        """Génère un QR code pour l'entrée"""
        import qrcode
        from io import BytesIO
        import base64
        
        qr_data = f"{self.reference}|{self.activite.slug}|{self.utilisateur.email}"
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        self.qr_code = base64.b64encode(buffer.getvalue()).decode()
    
    def __str__(self):
        return f"{self.reference} - {self.utilisateur.email} - {self.activite.titre}"

class PaiementActivite(models.Model):
    """Suivi des paiements pour les activités"""
    
    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('paye', 'Payé'),
        ('echoue', 'Échoué'),
        ('rembourse', 'Remboursé'),
    )
    
    MOYEN_CHOICES = (
        ('mtn', 'MTN Mobile Money'),
        ('orange', 'Orange Money'),
        ('carte', 'Carte bancaire'),
        ('especes', 'Espèces'),
        ('virement', 'Virement bancaire'),
    )
    
    inscription = models.OneToOneField(Inscription, on_delete=models.CASCADE, related_name='paiement')
    montant = models.DecimalField(max_digits=10, decimal_places=0)
    moyen_paiement = models.CharField(max_length=20, choices=MOYEN_CHOICES)
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    # Infos transaction
    transaction_id = models.CharField(max_length=100, blank=True)
    numero_telephone = models.CharField(max_length=50, blank=True)
    operator = models.CharField(max_length=20, blank=True)
    
    # Dates
    date_demande = models.DateTimeField(auto_now_add=True)
    date_validation = models.DateTimeField(null=True, blank=True)
    
    # Réponse API
    api_response = models.JSONField(default=dict, blank=True)
    
    def __str__(self):
        return f"Paiement {self.transaction_id or self.id} - {self.montant} FCFA"

class NotificationActivite(models.Model):
    """Notifications pour les inscriptions"""
    
    TYPE_CHOICES = (
        ('inscription', 'Confirmation d\'inscription'),
        ('rappel', 'Rappel d\'événement'),
        ('annulation', 'Annulation'),
        ('modification', 'Modification'),
        ('info', 'Information'),
    )
    
    CANAL_CHOICES = (
        ('email', 'Email'),
        ('sms', 'SMS'),
        ('push', 'Notification push'),
    )
    
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='notifications_activites')
    activite = models.ForeignKey(Activite, on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    canal = models.CharField(max_length=10, choices=CANAL_CHOICES)
    sujet = models.CharField(max_length=200)
    message = models.TextField()
    est_envoyee = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(null=True, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.type} - {self.utilisateur.email} - {self.est_envoyee}"

class AvisActivite(models.Model):
    """Avis et commentaires des participants"""
    
    inscription = models.ForeignKey(Inscription, on_delete=models.CASCADE, related_name='avis')
    note = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField()
    est_approuve = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
    
    def __str__(self):
        return f"Avis {self.note}/5 - {self.inscription.utilisateur.email}"
