"""
URL configuration for plateforme_municipale project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
"""

import sys
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView
from django.views.static import serve
from django.views.generic import RedirectView
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from rest_framework.schemas import get_schema_view
from rest_framework.documentation import include_docs_urls

# ============================================
# CONFIGURATION DU TITRE DE L'ADMIN
# ============================================

admin.site.site_header = "Administration de Bot-Makak"
admin.site.site_title = "Plateforme Municipale Bot-Makak"
admin.site.index_title = "Bienvenue sur la plateforme municipale"

# ============================================
# URLS PRINCIPALES
# ============================================

urlpatterns = [
    # ============================================
    # ADMINISTRATION
    # ============================================
    path('admin/', admin.site.urls),
    
    # ============================================
    # CKEDITOR 5 - ÉDITEUR DE TEXTE RICHE
    # ============================================
    path('ckeditor5/', include('django_ckeditor_5.urls')),
    
    # ============================================
    # JWT TOKENS (Authentification API)
    # ============================================
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # ============================================
    # DOCUMENTATION API (Optionnel mais recommandé)
    # ============================================
    #path('api/docs/', include_docs_urls(title='API Plateforme Municipale Bot-Makak')),
    #path('api/schema/', get_schema_view(title='API Bot-Makak', description='API de la plateforme municipale'), name='api_schema'),
    
    # ============================================
    # MODULES API PRINCIPAUX
    # ============================================
    path('api/actualites/', include('actualites.urls')),
    path('api/activites/', include('activites.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/archives/', include('archives.urls')),
    path('api/etat-civil/', include('etat_civil.urls')),
    path('api/signature-electronique/', include('signature_electronique.urls')),
    path('api/annuaires/', include('annuaires.urls')),
    path('api/paiements/', include('paiements.urls')),
    path('api/dechets/', include('dechets.urls')),
    
    # ============================================
    # TABLEAUX DE BORD
    # ============================================
    # Dashboard Administrateur
    path('api/dashboard/', include('dashboard.urls')),
    
    # Dashboard Agent
    path('api/dashboard-agent/', include('dashboard_agent.urls')),
    
    # Redirections pour compatibilité (alias)
    path('api/agent-dashboard/', RedirectView.as_view(url='/api/dashboard-agent/', permanent=False)),
    path('api/agent-dashboard/<path:path>', RedirectView.as_view(url='/api/dashboard-agent/%(path)s', permanent=False)),
    
    # ============================================
    # PAGE D'ACCUEIL API
    # ============================================
    path('api/', TemplateView.as_view(template_name='api_root.html'), name='api-root'),
    
    # ============================================
    # RACINE DU SITE (Redirection vers API ou frontend)
    # ============================================
    path('', RedirectView.as_view(url='/api/', permanent=False), name='home'),
    
    # ============================================
    # PAGES D'AUTHENTIFICATION (si vues Django utilisées)
    # ============================================
    # Décommentez si vous utilisez des templates Django pour l'auth
    # path('login/', TemplateView.as_view(template_name='login.html'), name='login'),
    # path('register/', TemplateView.as_view(template_name='register.html'), name='register'),
    # path('dashboard/', TemplateView.as_view(template_name='dashboard.html'), name='dashboard'),
]

# ============================================
# SERVIRE LES FICHIERS STATIQUES ET MÉDIA
# ============================================

if settings.DEBUG:
    # Servir les fichiers média en développement
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    
    # Servir les fichiers statiques en développement
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    
    # Debug toolbar (si installée)
    try:
        import debug_toolbar
        urlpatterns += [
            path('__debug__/', include(debug_toolbar.urls)),
        ]
    except ImportError:
        pass

else:
    # ============================================
    # SERVIRE LES FICHIERS EN PRODUCTION (Optionnel)
    # ============================================
    # En production, il est FORTEMENT RECOMMANDÉ d'utiliser nginx ou Apache
    # pour servir les fichiers statiques et média.
    # Décommentez ces lignes SEULEMENT si vous n'avez pas d'autre choix.
    
    # urlpatterns += [
    #     re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    #     re_path(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    # ]
    pass

# ============================================
# URLS POUR LES TESTS (Optionnel)
# ============================================

# Ces URLs ne sont actives que pendant les tests
if settings.DEBUG and 'test' in sys.argv:
    urlpatterns += [
        path('test-auth/', TemplateView.as_view(template_name='test_auth.html'), name='test_auth'),
    ]

# ============================================
# URLS POUR LES PAGES D'ERREUR PERSONNALISÉES
# ============================================

# Décommentez et adaptez pour les pages d'erreur personnalisées
# handler400 = 'your_app.views.handler400'
# handler403 = 'your_app.views.handler403'
# handler404 = 'your_app.views.handler404'
# handler500 = 'your_app.views.handler500'

# ============================================
# URLS DE SECOURS (Catch-all pour SPA)
# ============================================

# Si vous avez un frontend React/Vue qui gère le routing,
# décommentez cette ligne en dernier pour capturer toutes les routes non trouvées.
# re_path(r'^(?!api|admin|media|static|ckeditor5).*$', 
#         TemplateView.as_view(template_name='index.html'), 
#         name='spa_catchall'),