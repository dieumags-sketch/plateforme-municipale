# backend/apps/paiements/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('configurations', views.ConfigurationPaiementViewSet, basename='configuration-paiement')
router.register('transactions', views.TransactionPaiementViewSet, basename='transaction-paiement')
router.register('portefeuille', views.PortefeuilleViewSet, basename='portefeuille')

urlpatterns = [
    path('', include(router.urls)),
]