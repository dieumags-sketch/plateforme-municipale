# accounts/utils.py
import secrets
import string
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from twilio.rest import Client
import jwt
from .models import PasswordResetToken, EmailVerificationToken, PhoneVerificationCode

def generate_random_code(length=6):
    """Génère un code aléatoire"""
    return ''.join(secrets.choice(string.digits) for _ in range(length))

def generate_random_password(length=12):
    """Génère un mot de passe aléatoire sécurisé"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def create_reset_token(user):
    """Crée un token de réinitialisation de mot de passe"""
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=24)
    
    PasswordResetToken.objects.create(
        utilisateur=user,
        token=token,
        expires_at=expires_at
    )
    return token

def create_email_verification_token(user):
    """Crée un token de vérification d'email"""
    token = secrets.token_urlsafe(32)
    expires_at = timezone.now() + timedelta(hours=48)
    
    EmailVerificationToken.objects.create(
        utilisateur=user,
        token=token,
        expires_at=expires_at
    )
    return token

def send_verification_email(user, token):
    """Envoie un email de vérification"""
    verification_url = f"{settings.FRONTEND_URL}/accounts/verify-email.html?token={token}"
    
    subject = "Vérifiez votre adresse email"
    message = f"""
    Bonjour {user.get_full_name()},
    
    Merci de vous être inscrit sur la Plateforme Municipale.
    
    Pour confirmer votre adresse email, veuillez cliquer sur le lien suivant :
    {verification_url}
    
    Ce lien expirera dans 48 heures.
    
    Si vous n'avez pas créé de compte, ignorez cet email.
    
    Cordialement,
    L'équipe de la Plateforme Municipale
    """
    
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def send_reset_password_email(user, token):
    """Envoie un email de réinitialisation"""
    reset_url = f"{settings.FRONTEND_URL}/accounts/reset-password.html?token={token}"
    
    subject = "Réinitialisation de votre mot de passe"
    message = f"""
    Bonjour {user.get_full_name()},
    
    Vous avez demandé la réinitialisation de votre mot de passe.
    
    Cliquez sur le lien suivant pour créer un nouveau mot de passe :
    {reset_url}
    
    Ce lien expirera dans 24 heures.
    
    Si vous n'avez pas fait cette demande, ignorez cet email.
    
    Cordialement,
    L'équipe de la Plateforme Municipale
    """
    
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email])

def send_sms_verification(phone_number, code):
    """Envoie un SMS de vérification (via Twilio ou service équivalent)"""
    # Configuration Twilio
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    
    message = f"Votre code de vérification Plateforme Municipale est : {code}. Valable 10 minutes."
    
    try:
        client.messages.create(
            body=message,
            from_=settings.TWILIO_PHONE_NUMBER,
            to=str(phone_number)
        )
        return True
    except Exception as e:
        print(f"Erreur SMS: {e}")
        return False

def create_phone_verification_code(user):
    """Crée et envoie un code de vérification par SMS"""
    code = generate_random_code(6)
    expires_at = timezone.now() + timedelta(minutes=10)
    
    PhoneVerificationCode.objects.filter(utilisateur=user).delete()
    verification = PhoneVerificationCode.objects.create(
        utilisateur=user,
        code=code,
        expires_at=expires_at
    )
    
    if user.telephone:
        send_sms_verification(user.telephone, code)
    
    return verification

def generate_jwt_token(user):
    """Génère un token JWT pour l'API"""
    payload = {
        'user_id': user.id,
        'email': user.email,
        'role': user.role,
        'exp': timezone.now() + timedelta(days=7),
        'iat': timezone.now(),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm='HS256')

def verify_jwt_token(token):
    """Vérifie un token JWT"""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None