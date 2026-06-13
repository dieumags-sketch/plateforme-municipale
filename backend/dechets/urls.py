# dechets/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'quartiers', views.QuartierViewSet, basename='quartier')
router.register(r'points', views.PointCollecteViewSet, basename='point-collecte')
router.register(r'calendrier', views.CalendrierCollecteViewSet, basename='calendrier-collecte')
router.register(r'signalements', views.SignalementViewSet, basename='signalement')
router.register(r'demandes', views.DemandeEncombrantViewSet, basename='demande-encombrant')
router.register(r'tournees', views.TourneeViewSet, basename='tournee')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    path('tournee-du-jour/', views.TourneeDuJourView.as_view(), name='tournee-du-jour'),
    path('rappel/', views.RapprochementView.as_view(), name='rappel'),
    path('voice/twiml/', views.VoiceTwiMLView.as_view(), name='voice-twiml'),
    path('ussd/', views.USSDView.as_view(), name='ussd'),
    path('test-notification/', views.TestNotificationView.as_view(), name='test-notification'),
]