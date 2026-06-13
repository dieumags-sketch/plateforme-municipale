from django.db import models

# accounts/models.py
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.db import models
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator
from phonenumber_field.modelfields import PhoneNumberField
import pyotp
import qrcode
from io import BytesIO
import base64

class CustomUserManager(BaseUserManager):
    """Gestionnaire personnalisé pour l'utilisateur"""
    
    def create_user(self, email, username, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        if not username:
            raise ValueError('Le nom d\'utilisateur est obligatoire')
        
        email = self.normalize_email(email)
        user = self.model(email=email, username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('role', 'admin')
        extra_fields.setdefault('is_verified', True)
        
        return self.create_user(email, username, password, **extra_fields)

class Utilisateur(AbstractBaseUser, PermissionsMixin):
    """Modèle utilisateur étendu"""
    
    ROLE_CHOICES = (
        ('citoyen', 'Citoyen'),
        ('agent', 'Agent Municipal'),
        ('moderateur', 'Modérateur'),
        ('admin', 'Administrateur'),
    )
    
    # Informations de base
    email = models.EmailField(unique=True, db_index=True)
    username = models.CharField(max_length=150, unique=True, db_index=True)
    nom = models.CharField(max_length=100, blank=True)
    prenom = models.CharField(max_length=100, blank=True)
    
    # Téléphone avec détection automatique d'indicateur
    telephone = PhoneNumberField(unique=True, null=True, blank=True, db_index=True)
    telephone_verified = models.BooleanField(default=False)
    
    # Statut
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='citoyen')
    
    # Dates
    date_joined = models.DateTimeField(default=timezone.now)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    last_seen = models.DateTimeField(null=True, blank=True)
    
    # Profil
    avatar = models.ImageField(upload_to='avatars/%Y/%m/', null=True, blank=True)
    bio = models.TextField(max_length=500, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    adresse = models.TextField(blank=True)
    code_postal = models.CharField(max_length=10, blank=True)
    ville = models.CharField(max_length=100, blank=True)
    pays = models.CharField(max_length=100, default='Cameroun')
    
    # Préférences
    prefer_notifications_email = models.BooleanField(default=True)
    prefer_notifications_sms = models.BooleanField(default=False)
    langue = models.CharField(max_length=10, default='fr')
    theme = models.CharField(max_length=20, default='light')
    
    # Sécurité
    totp_secret = models.CharField(max_length=32, blank=True, null=True)
    totp_enabled = models.BooleanField(default=False)
    face_encoding = models.TextField(blank=True, null=True)  # Stockage encodage facial
    face_enabled = models.BooleanField(default=False)
    
    # Clés de sécurité (WebAuthn)
    webauthn_credentials = models.JSONField(default=list, blank=True)
    
    # Social auth
    social_auth_provider = models.CharField(max_length=50, blank=True)
    social_auth_id = models.CharField(max_length=255, blank=True, db_index=True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    objects = CustomUserManager()
    
    def __str__(self):
        return f"{self.get_full_name()} ({self.email})"
    
    def get_full_name(self):
        if self.nom and self.prenom:
            return f"{self.prenom} {self.nom}"
        return self.username
    
    def get_short_name(self):
        return self.prenom or self.username
    
    def get_avatar_url(self):
        if self.avatar:
            return self.avatar.url
        # Gravatar par défaut
        import hashlib
        hash_email = hashlib.md5(self.email.lower().encode()).hexdigest()
        return f"https://www.gravatar.com/avatar/{hash_email}?d=identicon&s=200"
    
    def enable_2fa(self):
        """Activer 2FA et générer le secret"""
        self.totp_secret = pyotp.random_base32()
        self.totp_enabled = False  # Sera activé après vérification
        self.save()
        return self.totp_secret
    
    def verify_2fa(self, code):
        """Vérifier le code 2FA"""
        if not self.totp_secret:
            return False
        totp = pyotp.TOTP(self.totp_secret)
        return totp.verify(code)
    
    def get_2fa_qr_code(self):
        """Générer le QR code pour 2FA"""
        if not self.totp_secret:
            return None
        totp = pyotp.TOTP(self.totp_secret)
        uri = totp.provisioning_uri(name=self.email, issuer_name="Plateforme Municipale")
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    
    def update_last_seen(self):
        self.last_seen = timezone.now()
        self.save(update_fields=['last_seen'])
    
    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['username']),
            models.Index(fields=['telephone']),
            models.Index(fields=['role']),
        ]

class FailedLoginAttempt(models.Model):
    """Tentatives de connexion échouées"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, null=True)
    email = models.EmailField()
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-timestamp']

class PasswordResetToken(models.Model):
    """Token de réinitialisation de mot de passe"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()

class EmailVerificationToken(models.Model):
    """Token de vérification d'email"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    token = models.CharField(max_length=255, unique=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    
    def is_valid(self):
        return self.expires_at > timezone.now()

class PhoneVerificationCode(models.Model):
    """Code de vérification téléphone"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def is_valid(self):
        return self.expires_at > timezone.now()

class UserSession(models.Model):
    """Gestion des sessions utilisateur"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE, related_name='sessions')
    session_key = models.CharField(max_length=255, unique=True)
    device_name = models.CharField(max_length=255, blank=True)
    device_type = models.CharField(max_length=50, blank=True)
    ip_address = models.GenericIPAddressField()
    user_agent = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.utilisateur.email} - {self.device_name}"
    

# accounts/models.py - Ajoutez le champ 'used' à PhoneVerificationCode

class PhoneVerificationCode(models.Model):
    """Code de vérification téléphone"""
    utilisateur = models.ForeignKey(Utilisateur, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)  # 👈 AJOUTEZ CETTE LIGNE
    
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()
