# dashboard_agent/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # Pages HTML
    path('', views.agent_dashboard_home, name='agent-dashboard-home'),
    
    # API endpoints
    path('api/stats/', views.AgentDashboardStatsView.as_view(), name='agent-stats'),
    path('api/taches/', views.AgentTachesView.as_view(), name='agent-taches'),
    path('api/taches/<int:pk>/', views.AgentTacheDetailView.as_view(), name='agent-tache-detail'),
    path('api/notifications/', views.AgentNotificationsView.as_view(), name='agent-notifications'),
]