# backend/apps/signature_electronique/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('certificats', views.CertificatViewSet, basename='certificat')
router.register('signatures', views.SignatureViewSet, basename='signature')
router.register('demandes', views.DemandeSignatureViewSet, basename='demande-signature')
router.register('configuration', views.ConfigurationSignatureViewSet, basename='configuration-signature')

urlpatterns = [
    path('', include(router.urls)),
]