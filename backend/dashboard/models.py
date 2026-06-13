from django.db import models

# dashboard/models.py
from django.db import models
from django.utils import timezone

class DashboardStats(models.Model):
    """Statistiques globales de la plateforme"""
    date = models.DateField(auto_now_add=True)
    total_users = models.IntegerField(default=0)
    active_users = models.IntegerField(default=0)
    total_actes = models.IntegerField(default=0)
    total_inscriptions = models.IntegerField(default=0)
    total_signalements = models.IntegerField(default=0)
    total_transactions = models.IntegerField(default=0)
    total_archives = models.IntegerField(default=0)
    total_structures = models.IntegerField(default=0)
    total_actualites = models.IntegerField(default=0)
    total_signatures = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Statistique"
        verbose_name_plural = "Statistiques"
        ordering = ['-date']

    def __str__(self):
        return f"Stats du {self.date}"
