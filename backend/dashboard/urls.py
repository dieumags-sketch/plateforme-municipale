from django.urls import path
from . import views

urlpatterns = [
    # API endpoint pour les statistiques (JSON)
    path('stats/', views.DashboardStatsView.as_view(), name='dashboard-stats'),
    
    # Page HTML du tableau de bord
    path('', views.dashboard_home, name='dashboard-home'),
]