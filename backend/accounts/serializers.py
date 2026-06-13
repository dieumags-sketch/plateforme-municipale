# accounts/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model, authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.validators import EmailValidator, RegexValidator
from phonenumber_field.serializerfields import PhoneNumberField
from .models import Utilisateur, UserSession

Utilisateur = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    """Sérialiseur principal utilisateur"""
    
    full_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Utilisateur
        fields = [
            'id', 'email', 'username', 'nom', 'prenom', 'full_name',
            'telephone', 'telephone_verified', 'avatar', 'avatar_url',
            'bio', 'date_naissance', 'adresse', 'code_postal', 'ville', 'pays',
            'role', 'is_verified', 'date_joined', 'last_seen',
            'prefer_notifications_email', 'prefer_notifications_sms',
            'langue', 'theme', 'totp_enabled', 'face_enabled'
        ]
        read_only_fields = ['id', 'is_verified', 'date_joined', 'last_seen', 'role']
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    
    def get_avatar_url(self, obj):
        return obj.get_avatar_url()

class RegisterSerializer(serializers.ModelSerializer):
    """Sérialiseur d'inscription"""
    
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password2 = serializers.CharField(write_only=True, required=True)
    telephone = PhoneNumberField(required=False)
    
    class Meta:
        model = Utilisateur
        fields = ['email', 'username', 'password', 'password2', 'nom', 'prenom', 'telephone']
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password2']:
            raise serializers.ValidationError({"password": "Les mots de passe ne correspondent pas."})
        
        # Vérifier si l'email existe déjà
        if Utilisateur.objects.filter(email=attrs['email']).exists():
            raise serializers.ValidationError({"email": "Cet email est déjà utilisé."})
        
        # Vérifier si le username existe déjà
        if Utilisateur.objects.filter(username=attrs['username']).exists():
            raise serializers.ValidationError({"username": "Ce nom d'utilisateur est déjà pris."})
        
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password2')
        user = Utilisateur.objects.create_user(**validated_data)
        return user

class LoginSerializer(serializers.Serializer):
    """Sérialiseur de connexion"""
    
    username = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    password = serializers.CharField(write_only=True)
    totp_code = serializers.CharField(required=False, write_only=True, max_length=6)
    
    def validate(self, attrs):
        username = attrs.get('username')
        email = attrs.get('email')
        password = attrs.get('password')
        totp_code = attrs.get('totp_code')
        
        if not username and not email:
            raise serializers.ValidationError("Email ou nom d'utilisateur requis")
        
        login_identifier = email or username
        
        # Authentification classique
        user = authenticate(username=login_identifier, password=password)
        
        if not user:
            raise serializers.ValidationError("Identifiants invalides")
        
        if not user.is_active:
            raise serializers.ValidationError("Ce compte est désactivé")
        
        # Vérification 2FA si activée
        if user.totp_enabled:
            if not totp_code:
                raise serializers.ValidationError({
                    "totp_code": "Code 2FA requis"
                })
            if not user.verify_2fa(totp_code):
                raise serializers.ValidationError({
                    "totp_code": "Code 2FA invalide"
                })
        
        attrs['user'] = user
        return attrs

class ChangePasswordSerializer(serializers.Serializer):
    """Sérialiseur de changement de mot de passe"""
    
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    confirm_password = serializers.CharField(write_only=True, required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Les mots de passe ne correspondent pas"})
        return attrs

class ForgotPasswordSerializer(serializers.Serializer):
    """Sérialiseur mot de passe oublié"""
    
    email = serializers.EmailField(required=True)

class ResetPasswordSerializer(serializers.Serializer):
    """Sérialiseur réinitialisation mot de passe"""
    
    token = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    confirm_password = serializers.CharField(required=True)
    
    def validate(self, attrs):
        if attrs['new_password'] != attrs['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Les mots de passe ne correspondent pas"})
        return attrs

class VerifyEmailSerializer(serializers.Serializer):
    """Sérialiseur vérification email"""
    
    token = serializers.CharField(required=True)

class VerifyPhoneSerializer(serializers.Serializer):
    """Sérialiseur vérification téléphone"""
    
    code = serializers.CharField(required=True, max_length=6)

class SendPhoneCodeSerializer(serializers.Serializer):
    """Sérialiseur envoi code SMS"""
    
    phone = PhoneNumberField(required=True)

class Enable2FASerializer(serializers.Serializer):
    """Sérialiseur activation 2FA"""
    
    code = serializers.CharField(required=True, max_length=6)

class FaceLoginSerializer(serializers.Serializer):
    """Sérialiseur connexion faciale"""
    
    email = serializers.EmailField(required=True)
    face_image = serializers.ImageField(required=True)

class EnableFaceSerializer(serializers.Serializer):
    """Sérialiseur activation reconnaissance faciale"""
    
    face_image = serializers.ImageField(required=True)

class RegisterPasskeySerializer(serializers.Serializer):
    """Sérialiseur enregistrement passkey"""
    
    credential_id = serializers.CharField(required=True)
    public_key = serializers.JSONField(required=True)
    device_name = serializers.CharField(required=True)

class SocialLoginSerializer(serializers.Serializer):
    """Sérialiseur connexion sociale"""
    
    provider = serializers.ChoiceField(choices=['google', 'facebook', 'apple'])
    token = serializers.CharField(required=True)

class UpdateProfileSerializer(serializers.ModelSerializer):
    """Sérialiseur mise à jour profil"""
    
    class Meta:
        model = Utilisateur
        fields = ['nom', 'prenom', 'bio', 'date_naissance', 'adresse', 
                  'code_postal', 'ville', 'pays', 'avatar', 'langue', 'theme',
                  'prefer_notifications_email', 'prefer_notifications_sms']

class UserSessionSerializer(serializers.ModelSerializer):
    """Sérialiseur session utilisateur"""
    
    class Meta:
        model = UserSession
        fields = ['id', 'device_name', 'device_type', 'ip_address', 
                  'last_activity', 'created_at', 'is_active']