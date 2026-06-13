# backend/apps/etat_civil/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('regions', views.RegionViewSet, basename='region')
router.register('departements', views.DepartementViewSet, basename='departement')
router.register('arrondissements', views.ArrondissementViewSet, basename='arrondissement')
router.register('districts-sante', views.DistrictSanteViewSet, basename='district-sante')
router.register('demandes', views.DemandeActeViewSet, basename='demande-acte')

urlpatterns = [
    path('', include(router.urls)),
]