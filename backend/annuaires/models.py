from django.db import models

# annuaires/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator
from django_ckeditor_5.fields import CKEditor5Field

Utilisateur = get_user_model()

class CategorieStructure(models.Model):
    """Catégorie de structure municipale"""
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = CKEditor5Field(blank=True)
    icon = models.CharField(max_length=50, default="fas fa-building")
    couleur = models.CharField(max_length=20, default="#667eea")
    ordre = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Catégorie"
        verbose_name_plural = "Catégories"
        ordering = ['ordre', 'nom']
    
    def __str__(self):
        return self.nom

class Structure(models.Model):
    """Structure municipale (mairie, école, hôpital, marché, etc.)"""
    
    TYPE_CHOICES = (
        ('mairie', '🏛️ Mairie / Mairie annexe'),
        ('ecole', '🏫 École / Université'),
        ('hopital', '🏥 Hôpital / Centre de santé'),
        ('marche', '🛒 Marché / Commerce'),
        ('police', '👮 Commissariat / Gendarmerie'),
        ('transport', '🚌 Transport / Gare'),
        ('culture', '🎭 Centre culturel / Bibliothèque'),
        ('sport', '⚽ Complexe sportif'),
        ('social', '🤝 Centre social'),
        ('religion', '⛪ Lieu de culte'),
        ('autre', '📌 Autre'),
    )
    
    STATUT_CHOICES = (
        ('actif', 'Actif'),
        ('ferme', 'Fermé temporairement'),
        ('en_construction', 'En construction'),
        ('inactif', 'Inactif'),
    )
    
    # Informations générales
    nom = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, max_length=250)
    type_structure = models.CharField(max_length=20, choices=TYPE_CHOICES, default='autre')
    categorie = models.ForeignKey(CategorieStructure, on_delete=models.SET_NULL, null=True, blank=True)
    description = CKEditor5Field(blank=True)
    
    # Adresse et géolocalisation
    adresse = models.TextField()
    quartier = models.CharField(max_length=100, blank=True)
    ville = models.CharField(max_length=100, default='Douala')
    code_postal = models.CharField(max_length=10, blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Contacts
    telephone = models.CharField(max_length=50, blank=True)
    telephone2 = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    whatsapp = models.CharField(max_length=50, blank=True, help_text="Numéro WhatsApp")
    site_web = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    
    # Horaires
    horaires_lundi = models.CharField(max_length=200, blank=True)
    horaires_mardi = models.CharField(max_length=200, blank=True)
    horaires_mercredi = models.CharField(max_length=200, blank=True)
    horaires_jeudi = models.CharField(max_length=200, blank=True)
    horaires_vendredi = models.CharField(max_length=200, blank=True)
    horaires_samedi = models.CharField(max_length=200, blank=True)
    horaires_dimanche = models.CharField(max_length=200, blank=True)
    horaires_speciaux = models.TextField(blank=True, help_text="Horaires spéciaux (jours fériés, etc.)")
    
    # Images
    image_principale = models.ImageField(upload_to='annuaire/%Y/%m/', null=True, blank=True)
    images_galerie = models.JSONField(default=list, blank=True)
    
    # Métadonnées
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    est_populaire = models.BooleanField(default=False)
    est_verifie = models.BooleanField(default=False)
    
    # Compteurs
    vue_count = models.PositiveIntegerField(default=0)
    contact_count = models.PositiveIntegerField(default=0)
    favori_count = models.PositiveIntegerField(default=0)
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Structure"
        verbose_name_plural = "Structures"
        ordering = ['nom']
        indexes = [
            models.Index(fields=['type_structure', 'ville']),
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['est_populaire']),
        ]
    
    def __str__(self):
        return f"{self.nom} - {self.ville}"
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nom)
            if Structure.objects.filter(slug=self.slug).exists():
                self.slug = f"{self.slug}-{self.id or ''}"
        super().save(*args, **kwargs)
    
    @property
    def horaires_par_jour(self):
        """Retourne les horaires formatés par jour"""
        jours = ['lundi', 'mardi', 'mercredi', 'jeudi', 'vendredi', 'samedi', 'dimanche']
        horaires = {}
        for jour in jours:
            horaire = getattr(self, f'horaires_{jour}')
            if horaire:
                horaires[jour] = horaire
        return horaires
    
    @property
    def est_ouvert(self):
        """Vérifie si la structure est ouverte actuellement (simplifié)"""
        import datetime
        now = datetime.datetime.now()
        jour_semaine = now.strftime('%A').lower()
        horaire_aujourdhui = getattr(self, f'horaires_{jour_semaine}', '')
        if 'fermé' in horaire_aujourdhui.lower() or 'ferme' in horaire_aujourdhui.lower():
            return False
        return bool(horaire_aujourdhui)

class Elu(models.Model):
    """Élu municipal"""
    
    FONCTION_CHOICES = (
        ('maire', 'Maire'),
        ('adjoint', 'Adjoint au maire'),
        ('conseiller', 'Conseiller municipal'),
        ('president', 'Président de commission'),
        ('autre', 'Autre'),
    )
    
    # Informations personnelles
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100)
    fonction = models.CharField(max_length=50, choices=FONCTION_CHOICES, default='conseiller')
    titre = models.CharField(max_length=200, blank=True, help_text="Titre spécifique (ex: Maire de Douala)")
    
    # Détails
    photo = models.ImageField(upload_to='elus/%Y/', null=True, blank=True)
    biographie = CKEditor5Field(blank=True)
    
    # Contacts
    telephone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)
    
    # Commission / Délégation
    commission = models.CharField(max_length=200, blank=True, help_text="Commission rattachée")
    delegation = models.CharField(max_length=200, blank=True)
    
    # Politique
    parti = models.CharField(max_length=100, blank=True)
    date_debut_mandat = models.DateField(null=True, blank=True)
    date_fin_mandat = models.DateField(null=True, blank=True)
    
    # Visibilité
    ordre = models.IntegerField(default=0)
    est_actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Élu"
        verbose_name_plural = "Élus"
        ordering = ['ordre', 'fonction', 'nom']
    
    def __str__(self):
        return f"{self.prenom} {self.nom} - {self.get_fonction_display()}"
    
    @property
    def nom_complet(self):
        return f"{self.prenom} {self.nom}"

class FavoriStructure(models.Model):
    """Structures favorites des utilisateurs"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='favoris_annuaire')
    structure = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='favoris')
    date_ajout = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['utilisateur', 'structure']
        ordering = ['-date_ajout']
    
    def __str__(self):
        return f"{self.utilisateur.email} - {self.structure.nom}"

class AvisStructure(models.Model):
    """Avis des citoyens sur une structure"""
    structure = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='avis')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='avis_structures')
    note = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    commentaire = models.TextField()
    est_approuve = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Avis"
        verbose_name_plural = "Avis"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Avis {self.note}/5 - {self.structure.nom}"

class ContactStructure(models.Model):
    """Prise de contact avec une structure"""
    SUJET_CHOICES = (
        ('information', 'Demande d\'information'),
        ('rdv', 'Prise de rendez-vous'),
        ('reclamation', 'Réclamation'),
        ('suggestion', 'Suggestion'),
        ('autre', 'Autre'),
    )
    
    structure = models.ForeignKey(Structure, on_delete=models.CASCADE, related_name='contacts')
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True)
    sujet = models.CharField(max_length=50, choices=SUJET_CHOICES)
    message = models.TextField()
    nom = models.CharField(max_length=100)
    email = models.EmailField()
    telephone = models.CharField(max_length=50, blank=True)
    est_traite = models.BooleanField(default=False)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Contact {self.structure.nom} - {self.nom}"