from django.db import models

# dashboard_agent/models.py
from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

User = get_user_model()

class TacheAgent(models.Model):
    """Tâches assignées aux agents"""
    
    PRIORITE_CHOICES = [
        ('haute', '🔴 Haute'),
        ('moyenne', '🟠 Moyenne'),
        ('basse', '🟢 Basse'),
    ]
    
    STATUT_CHOICES = [
        ('en_attente', 'En attente'),
        ('en_cours', 'En cours'),
        ('terminee', 'Terminée'),
        ('annulee', 'Annulée'),
    ]
    
    TYPE_CHOICES = [
        ('etat_civil', 'État Civil'),
        ('dechets', 'Déchets'),
        ('archives', 'Archives'),
        ('paiements', 'Paiements'),
        ('signature', 'Signature'),
    ]
    
    titre = models.CharField(max_length=200)
    description = models.TextField()
    type_tache = models.CharField(max_length=20, choices=TYPE_CHOICES)
    priorite = models.CharField(max_length=10, choices=PRIORITE_CHOICES, default='moyenne')
    statut = models.CharField(max_length=20, choices=STATUT_CHOICES, default='en_attente')
    
    assigne_a = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taches')
    cree_par = models.ForeignKey(User, on_delete=models.CASCADE, related_name='taches_crees')
    
    reference_id = models.CharField(max_length=100, blank=True, help_text="ID de la demande liée")
    lien_demande = models.CharField(max_length=500, blank=True)
    
    date_creation = models.DateTimeField(auto_now_add=True)
    date_echeance = models.DateTimeField()
    date_traitement = models.DateTimeField(null=True, blank=True)
    
    commentaire_traitement = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-priorite', 'date_echeance']
    
    def __str__(self):
        return f"{self.get_type_tache_display()} - {self.titre}"


class NotificationAgent(models.Model):
    """Notifications pour les agents"""
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications_agent')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    est_lue = models.BooleanField(default=False)
    lien = models.CharField(max_length=500, blank=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date_creation']
