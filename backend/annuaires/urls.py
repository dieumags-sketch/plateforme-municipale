# annuaires/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategorieStructureViewSet, basename='categorie-structure')
router.register(r'structures', views.StructureViewSet, basename='structure')
router.register(r'elus', views.EluViewSet, basename='elu')
router.register(r'favoris', views.FavoriViewSet, basename='favori')

urlpatterns = [
    path('', include(router.urls)),
    path('recherche/proximite/', views.RechercheProximiteView.as_view(), name='recherche-proximite'),
    path('statistiques/', views.StatistiquesView.as_view(), name='statistiques'),
]