from django.db import models
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django_ckeditor_5.fields import CKEditor5Field
from taggit.managers import TaggableManager

Utilisateur = get_user_model()

class CategorieActualite(models.Model):
    """Catégories d'actualités"""
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Classe FontAwesome")
    couleur = models.CharField(max_length=20, default="#2563eb", help_text="Couleur hexadécimale")
    ordre = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return self.nom

class Publication(models.Model):
    """Publication d'actualité principale"""
    
    STATUT_CHOICES = (
        ('brouillon', 'Brouillon'),
        ('soumis', 'Soumis à modération'),
        ('en_correction', 'En correction'),
        ('publie', 'Publié'),
        ('rejete', 'Rejeté'),
        ('archive', 'Archivé'),
    )
    
    TYPEMEDIA_CHOICES = (
        ('image', 'Image'),
        ('video', 'Vidéo'),
        ('aucun', 'Aucun média'),
    )
    
    # Informations de base
    titre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)
    accroche = models.CharField(max_length=300, help_text="Résumé accrocheur de l'article")
    contenu = CKEditor5Field(config_name='default', help_text="Contenu complet de l'actualité")
    
    # Médias
    type_media = models.CharField(max_length=10, choices=TYPEMEDIA_CHOICES, default='image')
    media = models.FileField(upload_to='actualites/media/%Y/%m/', null=True, blank=True)
    media_url = models.URLField(blank=True, help_text="URL externe pour vidéo (YouTube, Vimeo)")
    thumbnail = models.ImageField(upload_to='actualites/thumbnails/%Y/%m/', null=True, blank=True)
    
    # Catégorie et tags
    categorie = models.ForeignKey(CategorieActualite, on_delete=models.SET_NULL, null=True, related_name='publications')
    tags = TaggableManager(blank=True)
    
    # Métadonnées
    auteur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='publications')
    moderateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='publications_moderees')
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_publication = models.DateTimeField(default=timezone.now)
    date_moderation = models.DateTimeField(null=True, blank=True)
    
    # Statut et visibilité
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='brouillon')
    est_epingle = models.BooleanField(default=False)
    est_a_la_une = models.BooleanField(default=False)
    vue_count = models.PositiveIntegerField(default=0)
    partage_count = models.PositiveIntegerField(default=0)
    
    # Modération
    commentaire_moderation = models.TextField(blank=True, help_text="Commentaire du modérateur")
    
    # SEO
    meta_description = models.CharField(max_length=160, blank=True)
    mots_cles_seo = models.CharField(max_length=200, blank=True)
    
    class Meta:
        verbose_name = "Publication"
        verbose_name_plural = "Publications"
        ordering = ['-est_epingle', '-date_publication']
        indexes = [
            models.Index(fields=['statut', 'date_publication']),
            models.Index(fields=['categorie', 'statut']),
            models.Index(fields=['-date_publication']),
        ]
    
    def __str__(self):
        return self.titre
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.titre)
        super().save(*args, **kwargs)
    
    def increment_vue(self):
        self.vue_count += 1
        self.save(update_fields=['vue_count'])
    
    @property
    def is_published(self):
        return self.statut == 'publie' and self.date_publication <= timezone.now()
    
    @property
    def temps_lecture(self):
        """Calcule le temps de lecture estimé (200 mots par minute)"""
        mots = len(self.contenu.split())
        return max(1, round(mots / 200))

class Reaction(models.Model):
    """Réactions des citoyens (like, love, etc.)"""
    TYPE_CHOICES = (
        ('like', '👍 J\'aime'),
        ('love', '❤️ J\'adore'),
        ('laugh', '😄 Ha ha'),
        ('wow', '😮 Wow'),
        ('sad', '😢 Triste'),
        ('angry', '😠 En colère'),
    )
    
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='reactions')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='reactions')
    type_reaction = models.CharField(max_length=10, choices=TYPE_CHOICES)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['publication', 'utilisateur']
        indexes = [models.Index(fields=['publication', 'type_reaction'])]
    
    def __str__(self):
        return f"{self.utilisateur.username} - {self.type_reaction}"

class Commentaire(models.Model):
    """Commentaires des citoyens"""
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='commentaires')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='commentaires_actualites')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='reponses')
    contenu = models.TextField(max_length=1000)
    est_approuve = models.BooleanField(default=False)
    like_count = models.PositiveIntegerField(default=0)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Commentaire de {self.utilisateur.username}"

class HistoriqueConsultation(models.Model):
    """Historique de consultation des citoyens"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='historique_actualites')
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE)
    date_consultation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['utilisateur', 'publication']
        ordering = ['-date_consultation']
    
    def __str__(self):
        return f"{self.utilisateur.username} - {self.publication.titre}"

class PropositionCitoyenne(models.Model):
    """Proposition de sujet par les citoyens"""
    commentaire_reponse = models.TextField(blank=True, null=True)
    STATUT_CHOICES = (
        ('en_attente', 'En attente de modération'),
        ('acceptee', 'Acceptée'),
        ('refusee', 'Refusée'),
        ('publiee', 'Publiée'),
    )
    
    titre = models.CharField(max_length=200)
    contenu = models.TextField()
    auteur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='propositions')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    commentaire_moderation = models.TextField(blank=True)
    publication_associee = models.OneToOneField(Publication, on_delete=models.SET_NULL, null=True, blank=True)
    date_soumission = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Proposition citoyenne"
        verbose_name_plural = "Propositions citoyennes"
        ordering = ['-date_soumission']
    
    def __str__(self):
        return self.titre

class Partage(models.Model):
    """Partages de publications"""
    publication = models.ForeignKey(Publication, on_delete=models.CASCADE, related_name='partages')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='partages')
    plateforme = models.CharField(max_length=50, choices=[
        ('facebook', 'Facebook'),
        ('twitter', 'Twitter/X'),
        ('linkedin', 'LinkedIn'),
        ('whatsapp', 'WhatsApp'),
        ('email', 'Email'),
        ('lien', 'Lien externe'),
    ])
    date_partage = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['publication', 'utilisateur', 'plateforme']
