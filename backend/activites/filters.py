# activites/filters.py
from django_filters import rest_framework as filters
from django.db import models
from .models import Activite

class ActiviteFilter(filters.FilterSet):
    """Filtres avancés pour les activités"""
    
    type_activite = filters.ChoiceFilter(choices=Activite.TYPE_CHOICES)
    categorie = filters.CharFilter(field_name='categorie__slug')
    ville = filters.CharFilter(lookup_expr='iexact')
    prix_min = filters.NumberFilter(field_name='prix', lookup_expr='gte')
    prix_max = filters.NumberFilter(field_name='prix', lookup_expr='lte')
    est_gratuit = filters.BooleanFilter()
    date_debut_apres = filters.DateFilter(field_name='date_debut', lookup_expr='gte')
    date_debut_avant = filters.DateFilter(field_name='date_debut', lookup_expr='lte')
    search = filters.CharFilter(method='recherche_personnalisee')
    
    class Meta:
        model = Activite
        fields = [
            'type_activite', 'categorie', 'ville', 'prix_min', 'prix_max',
            'est_gratuit', 'statut', 'est_a_la_une', 'est_recommandee'
        ]
    
    def recherche_personnalisee(self, queryset, name, value):
        return queryset.filter(
            models.Q(titre__icontains=value) |
            models.Q(description_courte__icontains=value) |
            models.Q(description_longue__icontains=value) |
            models.Q(lieu__icontains=value) |
            models.Q(ville__icontains=value)
        )