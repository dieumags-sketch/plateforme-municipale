# actualites/filters.py
from django_filters import rest_framework as filters
from .models import Publication, CategorieActualite

class PublicationFilter(filters.FilterSet):
    """Filtres avancés pour les publications"""
    categorie = filters.ModelChoiceFilter(
        queryset=CategorieActualite.objects.all(),
        field_name='categorie__slug',
        to_field_name='slug'
    )
    date_min = filters.DateFilter(field_name='date_publication', lookup_expr='gte')
    date_max = filters.DateFilter(field_name='date_publication', lookup_expr='lte')
    search = filters.CharFilter(method='recherche_personnalisee')
    auteur = filters.CharFilter(field_name='auteur__username', lookup_expr='icontains')
    est_a_la_une = filters.BooleanFilter()
    est_epingle = filters.BooleanFilter()
    
    class Meta:
        model = Publication
        fields = ['categorie', 'statut', 'date_min', 'date_max', 'auteur', 
                  'est_a_la_une', 'est_epingle']
    
    def recherche_personnalisee(self, queryset, name, value):
        """Recherche personnalisée dans titre, accroche et contenu"""
        return queryset.filter(
            models.Q(titre__icontains=value) |
            models.Q(accroche__icontains=value) |
            models.Q(contenu__icontains=value) |
            models.Q(tags__name__icontains=value)
        ).distinct()