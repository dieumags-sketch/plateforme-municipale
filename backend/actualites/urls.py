from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategorieActualiteViewSet, basename='categorie')
router.register(r'publications', views.PublicationViewSet, basename='publication')
router.register(r'commentaires', views.CommentaireViewSet, basename='commentaire')
router.register(r'propositions', views.PropositionCitoyenneViewSet, basename='proposition')
router.register(r'historique', views.HistoriqueConsultationViewSet, basename='historique')
router.register(r'reactions', views.ReactionViewSet, basename='reaction')
router.register(r'partages', views.PartageViewSet, basename='partage')

urlpatterns = [
    path('', include(router.urls)),
    path('a-la-une/', views.PublicationAfficheView.as_view(), name='a-la-une'),
    path('recentes/', views.PublicationRecentView.as_view(), name='recentes'),
]