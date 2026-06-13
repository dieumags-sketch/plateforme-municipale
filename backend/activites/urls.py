# activites/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategorieActiviteViewSet, basename='categorie')
router.register(r'activites', views.ActiviteViewSet, basename='activite')
router.register(r'inscriptions', views.InscriptionViewSet, basename='inscription')
router.register(r'paiements', views.PaiementViewSet, basename='paiement')
router.register(r'avis', views.AvisViewSet, basename='avis')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
]