# accounts/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenRefreshView,
    TokenVerifyView,
)
from . import views

# Uniquement si tu as des ViewSets
router = DefaultRouter()
# router.register(r'users', views.UserViewSet, basename='user')

urlpatterns = [
    # ============================================
    # AUTHENTIFICATION DE BASE
    # ============================================
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('me/', views.MeView.as_view(), name='me'),
    
    # JWT Tokens
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('token/verify/', TokenVerifyView.as_view(), name='token_verify'),
    
    # ============================================
    # GESTION DU PROFIL
    # ============================================
    path('profile/', views.UpdateProfileView.as_view(), name='profile'),
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('delete-account/', views.DeleteAccountView.as_view(), name='delete-account'),
    
    # ============================================
    # RÉINITIALISATION MOT DE PASSE
    # ============================================
    path('forgot-password/', views.ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', views.ResetPasswordView.as_view(), name='reset-password'),
    
    # ============================================
    # VÉRIFICATION EMAIL
    # ============================================
    path('verify-email/', views.VerifyEmailView.as_view(), name='verify-email'),
    path('resend-verification/', views.ResendVerificationEmailView.as_view(), name='resend-verification'),
    
    # ============================================
    # VÉRIFICATION TÉLÉPHONE
    # ============================================
    path('send-phone-code/', views.SendPhoneCodeView.as_view(), name='send-phone-code'),
    path('verify-phone/', views.VerifyPhoneView.as_view(), name='verify-phone'),
    
    # ============================================
    # AUTHENTIFICATION À DEUX FACTEURS (2FA)
    # ============================================
    path('2fa/enable/', views.Enable2FAView.as_view(), name='enable-2fa'),
    path('2fa/disable/', views.Disable2FAView.as_view(), name='disable-2fa'),
    path('2fa/verify/', views.Verify2FAView.as_view(), name='verify-2fa'),
    path('2fa/backup-codes/', views.BackupCodesView.as_view(), name='backup-codes'),
    
    # ============================================
    # RECONNAISSANCE FACIALE (DÉSACTIVÉE)
    # ============================================
    # path('face/enable/', views.EnableFaceView.as_view(), name='enable-face'),
    # path('face/login/', views.FaceLoginView.as_view(), name='face-login'),
    # path('face/disable/', views.DisableFaceView.as_view(), name='disable-face'),
    
    # ============================================
    # CONNEXION SOCIALE (OAuth)
    # ============================================
    path('social/', views.SocialLoginView.as_view(), name='social-login'),
    # path('social/callback/', views.SocialCallbackView.as_view(), name='social-callback'),
    
    # ============================================
    # GESTION DES SESSIONS
    # ============================================
    path('sessions/', views.SessionsView.as_view(), name='sessions'),
    path('sessions/<int:session_id>/', views.SessionsView.as_view(), name='session-delete'),
    # path('sessions/all/', views.DeleteAllSessionsView.as_view(), name='delete-all-sessions'),
]

# Inclure les URLs du router si nécessaire
urlpatterns += router.urls