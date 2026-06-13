# accounts/backends.py
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
import pyotp

Utilisateur = get_user_model()

class EmailOrUsernameBackend(ModelBackend):
    """Authentification par email OU nom d'utilisateur"""
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        try:
            user = Utilisateur.objects.get(
                Q(email__iexact=username) | Q(username__iexact=username)
            )
        except Utilisateur.DoesNotExist:
            return None
        
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None

class PhoneBackend(ModelBackend):
    """Authentification par numéro de téléphone"""
    
    def authenticate(self, request, phone=None, code=None, **kwargs):
        if phone is None or code is None:
            return None
        
        from .models import PhoneVerificationCode
        
        try:
            user = Utilisateur.objects.get(telephone=phone)
            verification = PhoneVerificationCode.objects.filter(
                utilisateur=user, 
                code=code
            ).first()
            
            if verification and verification.is_valid():
                verification.delete()
                return user
        except Utilisateur.DoesNotExist:
            return None
        return None

class TOTPBackend(ModelBackend):
    """Authentification 2FA avec TOTP"""
    
    def authenticate(self, request, user=None, totp_code=None, **kwargs):
        if user is None or totp_code is None:
            return None
        
        if user.totp_enabled and user.verify_2fa(totp_code):
            return user
        return None