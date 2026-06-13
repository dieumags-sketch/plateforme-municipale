# backend/archives/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator  # AJOUTÉ FileExtensionValidator
from django.utils import timezone  # AJOUTÉ
import uuid
from datetime import datetime, timedelta

User = get_user_model()


class CategorieArchive(models.Model):
    """Catégorie d'archive"""
    nom = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    couleur = models.CharField(max_length=7, default="#6c757d", help_text="Code hexadécimal (ex: #6c757d)")
    icone = models.CharField(max_length=50, default="archive", help_text="Nom de l'icône FontAwesome/Bootstrap")
    ordre = models.IntegerField(default=0)
    est_actif = models.BooleanField(default=True)
    
    # AJOUTÉ: métadonnées pour SEO
    meta_description = models.CharField(max_length=200, blank=True)
    meta_keywords = models.CharField(max_length=200, blank=True)
    
    class Meta:
        ordering = ['ordre', 'nom']
        verbose_name = "Catégorie d'archive"
        verbose_name_plural = "Catégories d'archives"
    
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        """Auto-générer le slug si non fourni"""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)


class Archive(models.Model):
    """Document d'archive"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    # Identification
    titre = models.CharField(max_length=200)
    reference = models.CharField(max_length=100, unique=True)
    categorie = models.ForeignKey(CategorieArchive, on_delete=models.CASCADE, related_name='archives')
    
    # Description
    description = models.TextField()
    mots_cles = models.CharField(max_length=500, blank=True, help_text="Mots-clés séparés par des virgules")
    
    # Métadonnées
    date_document = models.DateField(help_text="Date du document original")
    date_archivage = models.DateField(auto_now_add=True)
    periode_debut = models.DateField(null=True, blank=True)
    periode_fin = models.DateField(null=True, blank=True)
    
    # Auteur / Source
    auteur = models.CharField(max_length=200, blank=True)
    source = models.CharField(max_length=200, blank=True)
    
    # Localisation physique
    emplacement_physique = models.CharField(max_length=200, blank=True)
    numero_boite = models.CharField(max_length=50, blank=True)
    
    # Fichier numérique
    fichier_pdf = models.FileField(
        upload_to='archives/documents/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf'])]  # AJOUTÉ
    )
    vignette = models.ImageField(
        upload_to='archives/vignettes/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]  # AJOUTÉ
    )
    fichiers_annexes = models.JSONField(default=list, blank=True)
    
    # Taille du fichier (AJOUTÉ)
    taille_fichier = models.BigIntegerField(default=0, help_text="Taille en octets")
    nombre_pages = models.PositiveIntegerField(default=0, help_text="Nombre de pages du document")
    
    # Conservation
    DUREES = [
        ('permanent', 'Conservation permanente'),
        ('10_ans', '10 ans'),
        ('20_ans', '20 ans'),
        ('30_ans', '30 ans'),
        ('50_ans', '50 ans'),
        ('100_ans', '100 ans'),
    ]
    duree_conservation = models.CharField(max_length=20, choices=DUREES, default='permanent')
    date_fin_conservation = models.DateField(null=True, blank=True)
    
    # Confidentialité
    NIVEAUX = [
        ('public', 'Public - Accès libre'),
        ('restreint', 'Restreint - Sur demande'),
        ('confidentiel', 'Confidentiel - Autorisation requise'),
        ('tres_confidentiel', 'Très confidentiel - Cadres uniquement'),
    ]
    niveau_acces = models.CharField(max_length=20, choices=NIVEAUX, default='public')
    
    # Tarification pour consultation
    payant = models.BooleanField(default=False)  # AJOUTÉ: champ manquant
    tarif = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Tarif standard")  # AJOUTÉ: champ manquant
    tarif_consultation = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tarif_impression = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tarif_copie = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tarif_envoi = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Statut
    STATUTS = [
        ('disponible', 'Disponible'),
        ('pret', 'En prêt'),
        ('restauration', 'En restauration'),
        ('perdu', 'Perdu'),
        ('numerise', 'Numérisé'),
        ('archive', 'Archivé'),  # AJOUTÉ
    ]
    statut = models.CharField(max_length=20, choices=STATUTS, default='disponible')
    
    # Métriques
    vues = models.PositiveIntegerField(default=0)
    telechargements = models.PositiveIntegerField(default=0)
    demandes_acces = models.PositiveIntegerField(default=0)
    note_moyenne = models.DecimalField(max_digits=3, decimal_places=1, default=0, null=True, blank=True)  # AJOUTÉ
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_document']
        indexes = [
            models.Index(fields=['categorie', 'niveau_acces']),
            models.Index(fields=['reference']),
            models.Index(fields=['mots_cles']),
            models.Index(fields=['date_document']),
            models.Index(fields=['statut']),  # AJOUTÉ
            models.Index(fields=['-date_archivage']),  # AJOUTÉ
        ]
    
    def __str__(self):
        return f"{self.reference} - {self.titre[:50]}"
    
    def incrementer_vues(self):
        """Incrémenter le compteur de vues"""
        from django.db.models import F
        self.vues = F('vues') + 1
        self.save(update_fields=['vues'])
        self.refresh_from_db(fields=['vues'])
    
    def incrementer_telechargements(self):
        """Incrémenter le compteur de téléchargements"""
        from django.db.models import F
        self.telechargements = F('telechargements') + 1
        self.save(update_fields=['telechargements'])
        self.refresh_from_db(fields=['telechargements'])
    
    def update_moyenne_notes(self):
        """Met à jour la note moyenne des avis"""
        from django.db.models import Avg
        moyenne = self.avis.aggregate(Avg('note'))['note__avg'] if hasattr(self, 'avis') else None
        self.note_moyenne = round(moyenne, 1) if moyenne else None
        self.save(update_fields=['note_moyenne'])
    
    def est_public(self):
        """Vérifie si l'archive est accessible au public"""
        return self.niveau_acces == 'public'
    
    def est_disponible(self):
        """Vérifie si l'archive est disponible"""
        return self.statut == 'disponible'
    
    def peut_etre_consulte_par(self, user):
        """Vérifie si un utilisateur peut consulter l'archive"""
        if self.niveau_acces == 'public':
            return True
        if user and user.is_authenticated:
            if user.is_staff:
                return True
            # Vérifier si l'utilisateur a une demande approuvée
            return self.demandes.filter(
                demandeur=user,
                statut='paye',
                date_fin_acces__gte=timezone.now()
            ).exists()
        return False
    
    def save(self, *args, **kwargs):
        """Auto-générer la référence si non fournie"""
        if not self.reference:
            year = self.date_document.year if self.date_document else timezone.now().year
            self.reference = f"ARCH-{year}-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


class DemandeAccesArchive(models.Model):
    """Demande d'accès à une archive"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, related_name='demandes')
    demandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_archives')
    
    # Type de demande
    TYPES = [
        ('consultation', 'Consultation sur place'),
        ('copie', 'Copie numérique'),
        ('impression', 'Impression papier'),
        ('envoi', 'Envoi par courrier'),
    ]
    type_demande = models.CharField(max_length=20, choices=TYPES)
    
    # Justificatif
    motif = models.TextField()
    justificatif = models.FileField(
        upload_to='archives/justificatifs/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'jpg', 'jpeg', 'png'])]  # AJOUTÉ
    )
    
    # Adresse pour envoi
    adresse_livraison = models.TextField(blank=True)
    
    # Tarifs
    montant_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    # Statut
    STATUTS = [
        ('en_attente', 'En attente de validation'),
        ('en_cours', 'En cours de traitement'),
        ('valide', 'Validée - En attente de paiement'),
        ('paye', 'Payée - En traitement'),
        ('pret', 'Prête - Disponible'),
        ('rejetee', 'Rejetée'),
        ('livree', 'Livrée'),
        ('cloturee', 'Clôturée'),
        ('expiree', 'Expirée'),  # AJOUTÉ
    ]
    statut = models.CharField(max_length=20, choices=STATUTS, default='en_attente')
    
    # Validation
    moderateur = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='demandes_validees'
    )
    commentaire_moderation = models.TextField(blank=True)
    date_moderation = models.DateTimeField(null=True, blank=True)
    
    # Paiement
    paiement_effectue = models.BooleanField(default=False)
    reference_paiement = models.CharField(max_length=100, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    moyen_paiement = models.CharField(max_length=50, blank=True, help_text="Carte, Mobile Money, etc.")  # AJOUTÉ
    
    # Accès
    date_debut_acces = models.DateTimeField(null=True, blank=True)
    date_fin_acces = models.DateTimeField(null=True, blank=True)
    lien_acces = models.CharField(max_length=500, blank=True, help_text="Lien temporaire pour téléchargement")
    token_acces = models.CharField(max_length=100, blank=True, unique=True, null=True)
    
    # Métadonnées
    date_demande = models.DateTimeField(auto_now_add=True)
    date_traitement = models.DateTimeField(null=True, blank=True)
    telechargements_effectues = models.PositiveIntegerField(default=0)  # AJOUTÉ
    
    # Notification (AJOUTÉ)
    notification_envoyee = models.BooleanField(default=False)
    date_notification = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_demande']
        indexes = [
            models.Index(fields=['statut', 'date_demande']),  # AJOUTÉ
            models.Index(fields=['token_acces']),  # AJOUTÉ
            models.Index(fields=['demandeur', 'statut']),  # AJOUTÉ
        ]
    
    def __str__(self):
        return f"Demande de {self.demandeur.get_full_name() or self.demandeur.username} - {self.archive.titre[:50]}"
    
    def calculer_montant(self):
        """Calculer le montant selon le type de demande"""
        montant = 0
        if self.type_demande == 'consultation':
            montant = self.archive.tarif_consultation
        elif self.type_demande == 'copie':
            montant = self.archive.tarif_copie
        elif self.type_demande == 'impression':
            montant = self.archive.tarif_impression
        elif self.type_demande == 'envoi':
            montant = self.archive.tarif_envoi
        return float(montant)
    
    def est_expiree(self):
        """Vérifie si la demande est expirée"""
        if self.date_fin_acces:
            return timezone.now() > self.date_fin_acces
        return False
    
    def prolonger_acces(self, jours=30):
        """Prolonge l'accès de X jours"""
        self.date_fin_acces = timezone.now() + timedelta(days=jours)
        self.save(update_fields=['date_fin_acces'])
    
    def save(self, *args, **kwargs):
        """Auto-calcul du montant avant sauvegarde"""
        if not self.montant_total and self.archive:
            self.montant_total = self.calculer_montant()
        super().save(*args, **kwargs)


class HistoriqueConsultationArchive(models.Model):
    """Historique des consultations des archives"""
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, related_name='consultations')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='consultations_archives')
    date_consultation = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=500, blank=True)  # AJOUTÉ
    temps_consulte = models.PositiveIntegerField(default=0, help_text="Temps de consultation en secondes")  # AJOUTÉ
    
    class Meta:
        ordering = ['-date_consultation']
        indexes = [
            models.Index(fields=['archive', '-date_consultation']),  # AJOUTÉ
            models.Index(fields=['utilisateur', '-date_consultation']),  # AJOUTÉ
        ]
    
    def __str__(self):
        return f"{self.utilisateur.get_full_name() or self.utilisateur.username} - {self.archive.titre[:50]} - {self.date_consultation.strftime('%d/%m/%Y')}"


class LogArchive(models.Model):
    """Journal d'audit des archives"""
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, related_name='logs')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    action = models.CharField(max_length=50)
    details = models.JSONField(default=dict)
    ip_address = models.GenericIPAddressField()
    user_agent = models.CharField(max_length=500, blank=True)  # AJOUTÉ
    date_action = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_action']
        indexes = [
            models.Index(fields=['action', '-date_action']),  # AJOUTÉ
            models.Index(fields=['archive', '-date_action']),  # AJOUTÉ
        ]
        verbose_name = "Journal d'audit"
        verbose_name_plural = "Journaux d'audit"
    
    def __str__(self):
        return f"{self.action} - {self.archive.titre[:30]} - {self.date_action.strftime('%d/%m/%Y %H:%M')}"


# AJOUTÉ: Modèle pour les avis sur les archives
class AvisArchive(models.Model):
    """Avis et évaluations des archives"""
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, related_name='avis')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='avis_archives')
    note = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Note de 1 à 5"
    )
    commentaire = models.TextField(max_length=1000, blank=True)
    est_approuve = models.BooleanField(default=False, help_text="Approuvé par un modérateur")
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-date_creation']
        unique_together = [['archive', 'utilisateur']]  # Un seul avis par utilisateur par archive
        indexes = [
            models.Index(fields=['archive', 'est_approuve']),
            models.Index(fields=['utilisateur']),
        ]
    
    def __str__(self):
        return f"Avis de {self.utilisateur.username} - {self.archive.titre[:30]} - {self.note}/5"
    
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Mettre à jour la note moyenne de l'archive
        self.archive.update_moyenne_notes()


# AJOUTÉ: Modèle pour les prêts d'archives physiques
class PretArchive(models.Model):
    """Gestion des prêts d'archives physiques"""
    archive = models.ForeignKey(Archive, on_delete=models.CASCADE, related_name='prets')
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prets_archives')
    date_emprunt = models.DateTimeField(auto_now_add=True)
    date_retour_prevue = models.DateField()
    date_retour_effective = models.DateField(null=True, blank=True)
    statut = models.CharField(
        max_length=20,
        choices=[
            ('en_cours', 'En cours'),
            ('retard', 'En retard'),
            ('retourne', 'Retourné'),
            ('perdu', 'Perdu'),
        ],
        default='en_cours'
    )
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date_emprunt']
        verbose_name = "Prêt d'archive"
        verbose_name_plural = "Prêts d'archives"
    
    def __str__(self):
        return f"Prêt de {self.archive.titre[:30]} à {self.utilisateur.username}"
    
    def est_en_retard(self):
        """Vérifie si le prêt est en retard"""
        if not self.date_retour_effective and timezone.now().date() > self.date_retour_prevue:
            return True
        return False