# dechets/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator  # AJOUTÉ
from django.core.exceptions import ValidationError  # AJOUTÉ
import uuid
from datetime import date, timedelta  # AJOUTÉ

Utilisateur = get_user_model()


class Quartier(models.Model):
    """Quartier de la commune (Bot-Makak)"""
    nom = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    ordre = models.IntegerField(default=0)
    
    # AJOUTÉ: Code postal
    code_postal = models.CharField(max_length=10, blank=True, help_text="Code postal du quartier")
    
    # AJOUTÉ: Population estimée
    population_estimee = models.PositiveIntegerField(default=0, help_text="Population estimée du quartier")
    
    # AJOUTÉ: Couleur pour affichage sur carte
    couleur = models.CharField(max_length=7, default="#28a745", help_text="Couleur hexadécimale")
    
    class Meta:
        verbose_name = "Quartier"
        verbose_name_plural = "Quartiers"
        ordering = ['ordre', 'nom']
        indexes = [  # AJOUTÉ
            models.Index(fields=['slug']),
            models.Index(fields=['nom']),
        ]
    
    def __str__(self):
        return self.nom
    
    def save(self, *args, **kwargs):
        """Auto-générer le slug si non fourni"""
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.nom)
        super().save(*args, **kwargs)
    
    @property
    def nombre_points_collecte(self):
        """Nombre de points de collecte dans le quartier"""
        return self.points_collecte.filter(statut='actif').count()
    
    @property
    def signalements_actifs(self):
        """Nombre de signalements actifs dans le quartier"""
        return Signalement.objects.filter(
            point_collecte__quartier=self,
            statut__in=['en_attente', 'en_cours']
        ).count()


class PointCollecte(models.Model):
    """Point de collecte / Bac à déchets"""
    
    TYPE_CHOICES = (
        ('bac_240', 'Bac 240L'),
        ('bac_660', 'Bac 660L'),
        ('bac_1100', 'Bac 1100L'),
        ('container', 'Container'),
        ('point_tri', 'Point de tri sélectif'),
    )
    
    STATUT_CHOICES = (
        ('actif', 'Actif'),
        ('plein', 'Plein - nécessite vidage'),
        ('casse', 'Cassé'),
        ('en_maintenance', 'En maintenance'),
        ('supprime', 'Supprimé'),
    )
    
    # Identification
    code = models.CharField(max_length=50, unique=True, blank=True)
    type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='bac_240')
    quartier = models.ForeignKey(Quartier, on_delete=models.CASCADE, related_name='points_collecte')
    
    # Localisation (adresse approximative pour zone périurbaine)
    adresse_reference = models.CharField(max_length=300, help_text="Ex: 'Près de l'église de Ndikinimeki'")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)  # MODIFIÉ: null=True
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)  # MODIFIÉ: null=True
    photo = models.ImageField(
        upload_to='dechets/bacs/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]  # AJOUTÉ
    )
    
    # AJOUTÉ: Capacité
    capacite_kg = models.PositiveIntegerField(default=240, help_text="Capacité en kg")
    
    # État
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='actif')
    dernier_vidage = models.DateTimeField(null=True, blank=True)
    prochain_vidage = models.DateTimeField(null=True, blank=True)
    
    # AJOUTÉ: Niveau de remplissage (estimation)
    niveau_remplissage = models.PositiveSmallIntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
        help_text="Pourcentage estimé de remplissage"
    )
    
    # Compteurs
    signalements_count = models.PositiveIntegerField(default=0)
    collectes_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        verbose_name = "Point de collecte"
        verbose_name_plural = "Points de collecte"
        indexes = [  # AJOUTÉ
            models.Index(fields=['code']),
            models.Index(fields=['statut', 'quartier']),
            models.Index(fields=['prochain_vidage']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.adresse_reference[:50]}"
    
    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f"BAC-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
    
    @property
    def est_plein(self):
        """Vérifie si le bac est considéré comme plein"""
        return self.niveau_remplissage >= 80
    
    def mettre_a_jour_prochain_vidage(self):
        """Met à jour la date du prochain vidage"""
        from .services import calculer_prochain_vidage
        self.prochain_vidage = calculer_prochain_vidage(self)
        self.save(update_fields=['prochain_vidage'])


class CalendrierCollecte(models.Model):
    """Calendrier des collectes par quartier"""
    
    JOURS = [
        (0, 'Lundi'), (1, 'Mardi'), (2, 'Mercredi'), (3, 'Jeudi'),
        (4, 'Vendredi'), (5, 'Samedi'), (6, 'Dimanche')
    ]
    
    TYPE_DECHET_CHOICES = [
        ('ordures_menageres', 'Ordures ménagères'),
        ('plastiques', 'Plastiques'),
        ('verre', 'Verre'),
        ('papiers', 'Papiers/Cartons'),
        ('dechets_verts', 'Déchets verts'),
        ('encombrants', 'Encombrants'),
    ]
    
    quartier = models.ForeignKey(Quartier, on_delete=models.CASCADE, related_name='calendriers')
    jour_semaine = models.IntegerField(choices=JOURS)
    heure_passage = models.TimeField()
    type_dechet = models.CharField(max_length=50, choices=TYPE_DECHET_CHOICES, default='ordures_menageres')
    
    # AJOUTÉ: Semaine paire/impaire
    est_semaine_impaire = models.BooleanField(default=False, help_text="Si True, collecte uniquement les semaines impaires")
    
    est_actif = models.BooleanField(default=True)
    
    # AJOUTÉ: Période de validité
    date_debut = models.DateField(null=True, blank=True)
    date_fin = models.DateField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Calendrier de collecte"
        verbose_name_plural = "Calendriers de collecte"
        unique_together = ['quartier', 'jour_semaine', 'type_dechet']
        ordering = ['quartier', 'jour_semaine', 'heure_passage']
        indexes = [  # AJOUTÉ
            models.Index(fields=['quartier', 'est_actif']),
            models.Index(fields=['jour_semaine', 'type_dechet']),
        ]
    
    def __str__(self):
        semaine = " (semaine impaire)" if self.est_semaine_impaire else ""
        return f"{self.quartier.nom} - {self.get_jour_semaine_display()} {self.heure_passage} - {self.get_type_dechet_display()}{semaine}"
    
    def prochaine_collecte(self):
        """Retourne la date de la prochaine collecte"""
        today = date.today()
        current_weekday = today.weekday()
        days_ahead = self.jour_semaine - current_weekday
        
        if days_ahead <= 0:
            days_ahead += 7
        
        prochaine_date = today + timedelta(days=days_ahead)
        
        # Vérifier la parité de semaine si nécessaire
        if self.est_semaine_impaire:
            week_number = prochaine_date.isocalendar()[1]
            if week_number % 2 == 0:  # Semaine paire
                prochaine_date += timedelta(days=7)
        
        return prochaine_date


class Signalement(models.Model):
    """Signalement citoyen (bac plein, débordant, cassé)"""
    
    TYPE_CHOICES = (
        ('bac_plein', '🗑️ Bac plein'),
        ('bac_debordant', '⚠️ Bac débordant'),
        ('bac_casse', '🔨 Bac cassé'),
        ('depot_sauvage', '🚯 Dépôt sauvage'),
        ('odeur', '👃 Nuisance odorante'),
        ('autre', '📌 Autre'),
    )
    
    STATUT_CHOICES = (
        ('en_attente', 'En attente de traitement'),
        ('en_cours', 'En cours de traitement'),
        ('traite', 'Traité'),
        ('rejete', 'Rejeté'),  # CORRIGÉ: 'refuse' → 'rejete'
        ('annule', 'Annulé'),  # AJOUTÉ
    )
    
    # Informations signalement
    type_signalement = models.CharField(max_length=20, choices=TYPE_CHOICES)
    point_collecte = models.ForeignKey(
        PointCollecte, 
        on_delete=models.SET_NULL,  # CORRIGÉ: CASCADE → SET_NULL
        null=True, 
        blank=True, 
        related_name='signalements'
    )
    description = models.TextField()
    photo = models.ImageField(
        upload_to='dechets/signalements/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    # Localisation
    adresse_description = models.CharField(max_length=300, help_text="Description du lieu (ex: 'près du grand arbre')")
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    
    # Auteur
    citoyen = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='signalements')
    nom_citoyen = models.CharField(max_length=100, blank=True)
    telephone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True)  # AJOUTÉ
    
    # Traitement
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    commentaire_traitement = models.TextField(blank=True)
    agent_traitement = models.ForeignKey(
        Utilisateur, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='signalements_traites'
    )
    date_traitement = models.DateTimeField(null=True, blank=True)
    
    # AJOUTÉ: Priorité
    priorite = models.CharField(
        max_length=10,
        choices=[('basse', 'Basse'), ('normale', 'Normale'), ('haute', 'Haute'), ('urgente', 'Urgente')],
        default='normale'
    )
    
    # Dates
    date_signalement = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Signalement"
        verbose_name_plural = "Signalements"
        ordering = ['-date_signalement']
        indexes = [  # AJOUTÉ
            models.Index(fields=['statut', '-date_signalement']),
            models.Index(fields=['type_signalement', 'statut']),
            models.Index(fields=['priorite']),
        ]
    
    def __str__(self):
        return f"{self.get_type_signalement_display()} - {self.date_signalement.strftime('%d/%m/%Y %H:%M')}"
    
    @property
    def temps_attente(self):
        """Temps d'attente en heures avant traitement"""
        if self.date_traitement:
            delta = self.date_traitement - self.date_signalement
            return delta.total_seconds() / 3600
        return None


class DemandeEncombrant(models.Model):
    """Demande d'enlèvement d'encombrants"""
    
    TYPE_CHOICES = (
        ('meuble', '🪑 Meuble'),
        ('electromenager', '🔌 Électroménager'),
        ('frigo', '❄️ Réfrigérateur'),
        ('matelas', '🛏️ Matelas'),
        ('dechets_vert', '🌿 Déchets verts'),
        ('gravats', '🏗️ Gravats'),
        ('autre', '📦 Autre'),
    )
    
    STATUT_CHOICES = (
        ('en_attente', 'En attente'),
        ('planifiee', 'Planifiée'),
        ('effectuee', 'Effectuée'),
        ('annulee', 'Annulée'),
        ('reportee', 'Reportée'),  # AJOUTÉ
    )
    
    citoyen = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='demandes_encombrants')
    type_encombrant = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description = models.TextField()
    photo = models.ImageField(
        upload_to='dechets/encombrants/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    
    # Localisation
    adresse = models.CharField(max_length=300)
    latitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    point_repere = models.CharField(max_length=200, blank=True, help_text="Point de repère (ex: 'devant la case jaune')")
    
    # Disponibilités
    date_souhaitee = models.DateField()
    creneau_horaire = models.CharField(max_length=100, blank=True)
    
    # AJOUTÉ: Quantité estimée
    quantite_estimee = models.CharField(
        max_length=20,
        choices=[('petit', 'Petit (1-2 objets)'), ('moyen', 'Moyen (3-5 objets)'), ('grand', 'Grand (6+ objets)')],
        default='moyen'
    )
    
    # Statut
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    date_planification = models.DateTimeField(null=True, blank=True)
    date_realisation = models.DateTimeField(null=True, blank=True)
    agent_assignee = models.ForeignKey(  # AJOUTÉ
        Utilisateur,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='encombrants_assignes'
    )
    
    date_demande = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Demande d'encombrant"
        verbose_name_plural = "Demandes d'encombrants"
        ordering = ['-date_demande']
        indexes = [  # AJOUTÉ
            models.Index(fields=['statut', '-date_demande']),
            models.Index(fields=['date_souhaitee']),
        ]
    
    def __str__(self):
        return f"{self.citoyen.get_full_name() or self.citoyen.username} - {self.get_type_encombrant_display()} ({self.date_souhaitee})"


class Tournee(models.Model):
    """Tournée de collecte programmée"""
    
    STATUT_CHOICES = (
        ('planifiee', 'Planifiée'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    )
    
    date = models.DateField()
    quartier = models.ForeignKey(Quartier, on_delete=models.CASCADE, related_name='tournees')
    agent = models.ForeignKey(Utilisateur, on_delete=models.SET_NULL, null=True, blank=True, related_name='tournees')
    
    # Points à visiter
    points_collecte = models.ManyToManyField(PointCollecte, through='TourneePoint')
    
    # Itinéraire (ordre optimisé)
    ordre_points = models.JSONField(default=list, blank=True, help_text="Liste des IDs dans l'ordre")
    distance_totale = models.FloatField(default=0, help_text="Distance en km")
    duree_estimee = models.IntegerField(default=0, help_text="Durée en minutes")
    
    # AJOUTÉ: Heures prévues
    heure_debut = models.TimeField(null=True, blank=True)
    heure_fin_estimee = models.TimeField(null=True, blank=True)
    
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='planifiee')
    
    debut_reel = models.DateTimeField(null=True, blank=True)
    fin_reelle = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        verbose_name = "Tournée"
        verbose_name_plural = "Tournées"
        ordering = ['-date']
        indexes = [  # AJOUTÉ
            models.Index(fields=['date', 'statut']),
            models.Index(fields=['quartier', 'date']),
        ]
    
    def __str__(self):
        return f"Tournée {self.quartier.nom} - {self.date}"
    
    @property
    def progression(self):
        """Progression de la tournée en pourcentage"""
        total = self.tourneepoint_set.count()
        if total == 0:
            return 0
        valides = self.tourneepoint_set.filter(est_vide=True).count()
        return round((valides / total) * 100, 1)
    
    def calculer_duree(self):
        """Calcule la durée de la tournée en minutes"""
        if self.debut_reel and self.fin_reelle:
            delta = self.fin_reelle - self.debut_reel
            return int(delta.total_seconds() / 60)
        return 0


class TourneePoint(models.Model):
    """Point de collecte dans une tournée"""
    tournee = models.ForeignKey(Tournee, on_delete=models.CASCADE, related_name='tourneepoint_set')
    point = models.ForeignKey(PointCollecte, on_delete=models.CASCADE)
    ordre = models.IntegerField()
    est_vide = models.BooleanField(default=False)
    photo_preuve = models.ImageField(
        upload_to='dechets/preuves/%Y/%m/',
        null=True,
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'webp'])]
    )
    heure_passage = models.DateTimeField(null=True, blank=True)
    commentaire = models.TextField(blank=True)
    
    class Meta:
        ordering = ['ordre']
        unique_together = ['tournee', 'point']
        indexes = [  # AJOUTÉ
            models.Index(fields=['tournee', 'ordre']),
        ]
    
    def __str__(self):
        return f"{self.tournee} - {self.point} (ordre {self.ordre})"


class NotificationDechet(models.Model):
    """Notifications pour les citoyens"""
    
    TYPE_CHOICES = (
        ('rappel_collecte', 'Rappel de collecte'),
        ('alerte_signalement', 'Alerte signalement traité'),
        ('info_tri', 'Information tri'),
        ('modification_horaire', 'Modification horaire'),
    )
    
    quartier = models.ForeignKey(Quartier, on_delete=models.CASCADE, related_name='notifications')
    type = models.CharField(max_length=30, choices=TYPE_CHOICES)
    titre = models.CharField(max_length=200)
    message = models.TextField()
    date_envoi = models.DateTimeField(auto_now_add=True)
    est_envoyee = models.BooleanField(default=False)
    
    # AJOUTÉ: Canaux d'envoi
    envoyer_sms = models.BooleanField(default=True)
    envoyer_email = models.BooleanField(default=False)
    envoyer_push = models.BooleanField(default=True)
    
    # AJOUTÉ: Planification
    date_planifiee = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_envoi']
        indexes = [  # AJOUTÉ
            models.Index(fields=['quartier', 'est_envoyee']),
            models.Index(fields=['date_planifiee']),
        ]
    
    def __str__(self):
        return f"{self.get_type_display()} - {self.quartier.nom} ({self.date_envoi.strftime('%d/%m/%Y')})"


class StatsCollecte(models.Model):
    """Statistiques des collectes"""
    date = models.DateField(unique=True)
    tonnes_collectees = models.FloatField(default=0, validators=[MinValueValidator(0)])
    bacs_vides = models.PositiveIntegerField(default=0)
    signalements_traites = models.PositiveIntegerField(default=0)
    encombrants_collectes = models.PositiveIntegerField(default=0)
    
    # AJOUTÉ: Autres métriques
    carburant_consomme = models.FloatField(default=0, help_text="Litres de carburant consommés")
    kilometres_parcourus = models.FloatField(default=0, help_text="Kilomètres parcourus")
    agents_mobilises = models.PositiveIntegerField(default=0)
    tournees_completees = models.PositiveIntegerField(default=0)  # AJOUTÉ
    
    class Meta:
        verbose_name = "Statistique collecte"
        verbose_name_plural = "Statistiques collectes"
        ordering = ['-date']
        indexes = [  # AJOUTÉ
            models.Index(fields=['date']),
        ]
    
    def __str__(self):
        return f"Stats du {self.date}"
    
    @property
    def moyenne_tonnes_par_jour(self):
        """Moyenne des tonnes collectées sur les 7 derniers jours"""
        dernieres_stats = StatsCollecte.objects.filter(date__lt=self.date).order_by('-date')[:7]
        if dernieres_stats.exists():
            return round(sum(s.tonnes_collectees for s in dernieres_stats) / dernieres_stats.count(), 2)
        return 0


# AJOUTÉ: Modèle pour les itinéraires optimisés
class ItineraireOptimise(models.Model):
    """Itinéraires optimisés pour les tournées"""
    quartier = models.ForeignKey(Quartier, on_delete=models.CASCADE, related_name='itineraires')
    points = models.ManyToManyField(PointCollecte, through='ItinerairePoint')
    distance_totale = models.FloatField(default=0, help_text="Distance en km")
    duree_estimee = models.IntegerField(default=0, help_text="Durée en minutes")
    date_creation = models.DateTimeField(auto_now_add=True)
    est_actif = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Itinéraire optimisé"
        verbose_name_plural = "Itinéraires optimisés"
        ordering = ['-date_creation']
    
    def __str__(self):
        return f"Itinéraire {self.quartier.nom} - {self.date_creation.strftime('%d/%m/%Y')}"


class ItinerairePoint(models.Model):
    """Points dans un itinéraire optimisé"""
    itineraire = models.ForeignKey(ItineraireOptimise, on_delete=models.CASCADE)
    point = models.ForeignKey(PointCollecte, on_delete=models.CASCADE)
    ordre = models.IntegerField()
    
    class Meta:
        ordering = ['ordre']
        unique_together = ['itineraire', 'point']
    
    def __str__(self):
        return f"Point {self.ordre}: {self.point.code}"