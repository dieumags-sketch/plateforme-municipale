# backend/archives/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('archives', views.ArchiveViewSet, basename='archive')
router.register('demandes', views.DemandeAccesArchiveViewSet, basename='demande-acces')
router.register('acces', views.AccesTokenViewSet, basename='acces')

urlpatterns = [
    path('', include(router.urls)),
]