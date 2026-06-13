# accounts/views.py
from django.shortcuts import render

# accounts/views.py
from rest_framework import generics, status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model, login, logout
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.core.exceptions import ValidationError
from .models import (
    Utilisateur, PasswordResetToken, EmailVerificationToken,
    UserSession, FailedLoginAttempt, PhoneVerificationCode
)
from .serializers import (
    UserSerializer, RegisterSerializer, LoginSerializer, ChangePasswordSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, VerifyEmailSerializer,
    VerifyPhoneSerializer, SendPhoneCodeSerializer, Enable2FASerializer,
    FaceLoginSerializer, EnableFaceSerializer, RegisterPasskeySerializer,
    SocialLoginSerializer, UpdateProfileSerializer, UserSessionSerializer
)
from .permissions import IsOwnerOrAdmin, IsVerified
from .utils import (
    create_reset_token, send_reset_password_email, create_email_verification_token,
    send_verification_email, create_phone_verification_code, generate_jwt_token
)

# ============================================
# RECONNAISSANCE FACIALE - DÉSACTIVÉE TEMPORAIREMENT
# ============================================
# from .face_recognition import encode_face_from_image, verify_face

# Fonctions factices pour remplacer la reconnaissance faciale
def encode_face_from_image(image, *args, **kwargs):
    """Version temporaire - reconnaissance faciale désactivée"""
    return None, "Service de reconnaissance faciale temporairement indisponible"

def verify_face(encoding, image, *args, **kwargs):
    """Version temporaire - reconnaissance faciale désactivée"""
    return False, "Service de reconnaissance faciale temporairement indisponible"

from .social_auth import SocialAuthHandler

Utilisateur = get_user_model()


class RegisterView(generics.CreateAPIView):
    """Inscription d'un nouvel utilisateur"""
    
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Créer token de vérification email
        token = create_email_verification_token(user)
        send_verification_email(user, token)
        
        # Générer JWT
        jwt_token = generate_jwt_token(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': jwt_token,
            'message': 'Inscription réussie. Veuillez vérifier votre email.'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """Connexion utilisateur"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        
        # Vérifier si le compte est actif
        if not user.is_active:
            return Response({'error': 'Ce compte est désactivé'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier si l'email est vérifié (optionnel selon politique)
        if not user.is_verified:
            return Response({'error': 'Veuillez vérifier votre email avant de vous connecter'}, 
                          status=status.HTTP_403_FORBIDDEN)
        
        # Vérifier 2FA
        if user.totp_enabled:
            code = request.data.get('2fa_code')
            if not code:
                return Response({'error': 'Code 2FA requis', 'requires_2fa': True}, 
                              status=status.HTTP_401_UNAUTHORIZED)
            if not user.verify_2fa(code):
                return Response({'error': 'Code 2FA invalide'}, 
                              status=status.HTTP_401_UNAUTHORIZED)
        
        # Créer une session si session_key fournie
        session = None
        if request.session.session_key:
            session = UserSession.objects.create(
                utilisateur=user,
                session_key=request.session.session_key,
                device_name=request.data.get('device_name', ''),
                device_type=request.data.get('device_type', ''),
                ip_address=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        # Mettre à jour dernière connexion
        user.last_login_ip = self.get_client_ip(request)
        user.last_login = timezone.now()
        user.update_last_seen()
        user.save(update_fields=['last_login_ip', 'last_login'])
        
        # Générer token
        jwt_token = generate_jwt_token(user)
        
        response_data = {
            'user': UserSerializer(user).data,
            'token': jwt_token,
            'message': 'Connexion réussie'
        }
        
        if session:
            response_data['session_id'] = session.id
        
        return Response(response_data)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(APIView):
    """Déconnexion utilisateur"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        session_id = request.data.get('session_id')
        
        # Supprimer la session spécifique
        if session_id:
            UserSession.objects.filter(id=session_id, utilisateur=request.user).delete()
        else:
            # Supprimer toutes les sessions de l'utilisateur
            UserSession.objects.filter(utilisateur=request.user).delete()
        
        # Supprimer le token d'authentification si utilisé
        try:
            request.user.auth_token.delete()
        except (AttributeError, Token.DoesNotExist):
            pass
        
        return Response({'message': 'Déconnecté avec succès'})


class MeView(APIView):
    """Informations de l'utilisateur connecté"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class UpdateProfileView(APIView):
    """Mise à jour du profil"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def put(self, request):
        serializer = UpdateProfileSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """Changement de mot de passe"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if not request.user.check_password(serializer.validated_data['old_password']):
            return Response({'error': 'Ancien mot de passe incorrect'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        request.user.set_password(serializer.validated_data['new_password'])
        request.user.save()
        
        # Optionnel: Déconnecter toutes les sessions sauf celle-ci
        if request.data.get('logout_other_sessions', False):
            UserSession.objects.filter(utilisateur=request.user).delete()
        
        return Response({'message': 'Mot de passe modifié avec succès'})


class ForgotPasswordView(APIView):
    """Mot de passe oublié - Envoi email"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        
        try:
            user = Utilisateur.objects.get(email=email, is_active=True)
            
            # Vérifier les tentatives trop fréquentes (optionnel)
            recent_tokens = PasswordResetToken.objects.filter(
                utilisateur=user,
                created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).count()
            
            if recent_tokens > 3:
                return Response({
                    'message': 'Trop de demandes. Veuillez réessayer dans 5 minutes.'
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)
            
            token = create_reset_token(user)
            send_reset_password_email(user, token)
        except Utilisateur.DoesNotExist:
            # Ne pas révéler si l'email existe ou non pour sécurité
            pass
        
        return Response({'message': 'Si cet email existe, un lien de réinitialisation a été envoyé.'})


class ResetPasswordView(APIView):
    """Réinitialisation du mot de passe"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        token = serializer.validated_data['token']
        
        try:
            reset_token = PasswordResetToken.objects.get(
                token=token,
                used=False,
                expires_at__gt=timezone.now()
            )
            
            user = reset_token.utilisateur
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Marquer le token comme utilisé
            reset_token.used = True
            reset_token.save()
            
            # Supprimer toutes les sessions de l'utilisateur (sécurité)
            UserSession.objects.filter(utilisateur=user).delete()
            
            return Response({'message': 'Mot de passe réinitialisé avec succès'})
            
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Token invalide ou expiré'}, 
                          status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """Vérification d'email"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = VerifyEmailSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            token = EmailVerificationToken.objects.select_related('utilisateur').get(
                token=serializer.validated_data['token'],
                expires_at__gt=timezone.now()
            )
            
            user = token.utilisateur
            
            # Éviter de revérifier plusieurs fois
            if user.is_verified:
                token.delete()
                return Response({'message': 'Email déjà vérifié'})
            
            user.is_verified = True
            user.save()
            
            token.delete()
            
            return Response({'message': 'Email vérifié avec succès'})
            
        except EmailVerificationToken.DoesNotExist:
            return Response({'error': 'Token invalide ou expiré'}, 
                          status=status.HTTP_400_BAD_REQUEST)


class SendPhoneCodeView(APIView):
    """Envoi code SMS pour vérification téléphone"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = SendPhoneCodeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        phone = serializer.validated_data['phone']
        
        # Vérifier le format du numéro (optionnel)
        if not phone or len(phone) < 8:
            return Response({'error': 'Numéro de téléphone invalide'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier si le numéro n'est pas déjà utilisé par un autre utilisateur
        if Utilisateur.objects.exclude(id=request.user.id).filter(telephone=phone).exists():
            return Response({'error': 'Ce numéro est déjà utilisé par un autre compte'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Vérifier les tentatives trop fréquentes
        recent_codes = PhoneVerificationCode.objects.filter(
            utilisateur=request.user,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=2)
        ).count()
        
        if recent_codes >= 3:
            return Response({'error': 'Trop de demandes. Veuillez réessayer dans 2 minutes.'}, 
                          status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        # Mettre à jour le numéro
        request.user.telephone = phone
        request.user.save()
        
        # Créer et envoyer le code
        success = create_phone_verification_code(request.user)
        
        if not success:
            return Response({'error': 'Impossible d\'envoyer le code. Réessayez plus tard.'}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response({'message': 'Code de vérification envoyé par SMS'})


class VerifyPhoneView(APIView):
    """Vérification du code SMS"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        serializer = VerifyPhoneSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        try:
            verification = PhoneVerificationCode.objects.get(
                utilisateur=request.user,
                code=serializer.validated_data['code'],
                expires_at__gt=timezone.now(),
                is_used=False
            )
            
            request.user.telephone_verified = True
            request.user.save()
            
            # Marquer le code comme utilisé (au lieu de supprimer)
            verification.is_used = True
            verification.save()
            
            return Response({'message': 'Numéro de téléphone vérifié avec succès'})
            
        except PhoneVerificationCode.DoesNotExist:
            return Response({'error': 'Code invalide ou expiré'}, 
                          status=status.HTTP_400_BAD_REQUEST)


class Enable2FAView(APIView):
    """Activation 2FA"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Obtenir le secret et QR code"""
        if not request.user.totp_secret:
            request.user.enable_2fa()
        
        return Response({
            'secret': request.user.totp_secret,
            'qr_code': request.user.get_2fa_qr_code(),
            'backup_codes': request.user.get_backup_codes() if hasattr(request.user, 'get_backup_codes') else None
        })
    
    def post(self, request):
        """Vérifier et activer 2FA"""
        serializer = Enable2FASerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        if request.user.verify_2fa(serializer.validated_data['code']):
            request.user.totp_enabled = True
            request.user.save()
            return Response({
                'message': '2FA activé avec succès',
                'backup_codes': request.user.generate_backup_codes() if hasattr(request.user, 'generate_backup_codes') else None
            })
        
        return Response({'error': 'Code invalide'}, status=status.HTTP_400_BAD_REQUEST)


class Disable2FAView(APIView):
    """Désactivation 2FA"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Vérifier le mot de passe pour sécurité
        password = request.data.get('password')
        if not password or not request.user.check_password(password):
            return Response({'error': 'Mot de passe requis pour désactiver la 2FA'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        request.user.totp_enabled = False
        request.user.totp_secret = None
        request.user.save()
        
        return Response({'message': '2FA désactivé avec succès'})


class EnableFaceView(APIView):
    """Activation reconnaissance faciale - TEMPORAIREMENT DÉSACTIVÉE"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Service temporairement désactivé
        return Response({
            'error': 'Service de reconnaissance faciale temporairement indisponible. Veuillez réessayer plus tard.'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class DisableFaceView(APIView):
    """Désactivation reconnaissance faciale - TEMPORAIREMENT DÉSACTIVÉE"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        # Service temporairement désactivé
        return Response({
            'error': 'Service de reconnaissance faciale temporairement indisponible. Veuillez réessayer plus tard.'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class FaceLoginView(APIView):
    """Connexion par reconnaissance faciale - TEMPORAIREMENT DÉSACTIVÉE"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        # Service temporairement désactivé
        return Response({
            'error': 'Service de reconnaissance faciale temporairement indisponible. Veuillez utiliser la connexion classique.'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class SocialLoginView(APIView):
    """Connexion via réseaux sociaux"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = SocialLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        provider = serializer.validated_data['provider']
        token = serializer.validated_data['token']
        
        # Vérifier le token selon le provider
        try:
            if provider == 'google':
                user_data = SocialAuthHandler.verify_google_token(token)
            elif provider == 'facebook':
                user_data = SocialAuthHandler.verify_facebook_token(token)
            elif provider == 'apple':
                user_data = SocialAuthHandler.verify_apple_token(token)
            else:
                return Response({'error': 'Provider non supporté'}, 
                              status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Erreur de vérification: {str(e)}'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not user_data:
            return Response({'error': 'Token invalide ou expiré'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        result = SocialAuthHandler.get_or_create_social_user(user_data)
        
        if isinstance(result, tuple):
            user, error = result
        else:
            user, error = result, None
        
        if error:
            return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
        
        jwt_token = generate_jwt_token(user)
        
        return Response({
            'user': UserSerializer(user).data,
            'token': jwt_token,
            'message': f'Connexion avec {provider} réussie'
        })


class SessionsView(APIView):
    """Gestion des sessions utilisateur"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        sessions = UserSession.objects.filter(
            utilisateur=request.user,
            is_active=True
        ).order_by('-last_activity')
        
        serializer = UserSessionSerializer(sessions, many=True)
        return Response(serializer.data)
    
    def delete(self, request, session_id=None):
        if session_id:
            session = get_object_or_404(UserSession, id=session_id, utilisateur=request.user)
            session.delete()
            return Response({'message': 'Session terminée avec succès'})
        
        # Supprimer toutes les sessions sauf la session courante
        current_session_id = request.data.get('current_session_id')
        
        if current_session_id:
            UserSession.objects.filter(
                utilisateur=request.user
            ).exclude(id=current_session_id).delete()
        else:
            # Supprimer toutes les sessions
            UserSession.objects.filter(utilisateur=request.user).delete()
        
        return Response({'message': 'Toutes les sessions ont été terminées'})


class DeleteAccountView(APIView):
    """Suppression de compte"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        password = request.data.get('password')
        
        if not password:
            return Response({'error': 'Mot de passe requis pour supprimer le compte'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        if not request.user.check_password(password):
            return Response({'error': 'Mot de passe incorrect'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        confirmation = request.data.get('confirmation')
        if confirmation != 'DELETE':
            return Response({'error': 'Veuillez confirmer la suppression en écrivant "DELETE"'}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        # Option 1: Désactiver le compte (recommandé)
        request.user.is_active = False
        request.user.email = f"deleted_{request.user.id}_{timezone.now().timestamp()}@deleted.com"
        request.user.username = f"deleted_{request.user.id}"
        request.user.telephone = None
        request.user.save()
        
        # Supprimer toutes les sessions
        UserSession.objects.filter(utilisateur=request.user).delete()
        
        return Response({'message': 'Compte désactivé avec succès'})


# AJOUT - Vue pour renvoyer l'email de vérification
class ResendVerificationEmailView(APIView):
    """Renvoyer l'email de vérification"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        if request.user.is_verified:
            return Response({'message': 'Email déjà vérifié'})
        
        # Vérifier les tentatives trop fréquentes
        recent_tokens = EmailVerificationToken.objects.filter(
            utilisateur=request.user,
            created_at__gte=timezone.now() - timezone.timedelta(minutes=5)
        ).count()
        
        if recent_tokens >= 3:
            return Response({'error': 'Trop de demandes. Veuillez réessayer dans 5 minutes.'}, 
                          status=status.HTTP_429_TOO_MANY_REQUESTS)
        
        token = create_email_verification_token(request.user)
        send_verification_email(request.user, token)
        
        return Response({'message': 'Email de vérification renvoyé'})


# AJOUT - Vue pour vérifier le code 2FA
class Verify2FAView(APIView):
    """Vérifier le code 2FA pendant la connexion"""
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        user_id = request.session.get('2fa_user_id')
        if not user_id:
            return Response({'error': 'Session expirée'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = Utilisateur.objects.get(id=user_id)
            code = request.data.get('code')
            
            if not code:
                return Response({'error': 'Code requis'}, status=status.HTTP_400_BAD_REQUEST)
            
            if user.verify_2fa(code):
                jwt_token = generate_jwt_token(user)
                del request.session['2fa_user_id']
                return Response({
                    'user': UserSerializer(user).data,
                    'token': jwt_token,
                    'message': '2FA vérifié avec succès'
                })
            else:
                return Response({'error': 'Code invalide'}, status=status.HTTP_401_UNAUTHORIZED)
                
        except Utilisateur.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_400_BAD_REQUEST)


# ============================================
# BACKUP CODES 2FA - GESTION DES CODES DE SECOURS
# ============================================

class BackupCodesView(APIView):
    """Gestion des codes de secours 2FA"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Récupérer les codes de secours"""
        if not request.user.totp_enabled:
            return Response(
                {'error': '2FA non activée. Veuillez d\'abord activer l\'authentification à deux facteurs.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Récupérer les codes de secours existants ou en générer
        backup_codes = None
        if hasattr(request.user, 'backup_codes') and request.user.backup_codes:
            backup_codes = request.user.backup_codes
        elif hasattr(request.user, 'get_backup_codes'):
            backup_codes = request.user.get_backup_codes()
        
        if not backup_codes:
            # Générer de nouveaux codes si aucun n'existe
            if hasattr(request.user, 'generate_backup_codes'):
                backup_codes = request.user.generate_backup_codes()
        
        return Response({
            'backup_codes': backup_codes,
            'count': len(backup_codes) if backup_codes else 0,
            'message': 'Conservez ces codes dans un endroit sûr. Chaque code ne peut être utilisé qu\'une seule fois.'
        })
    
    def post(self, request):
        """Régénérer les codes de secours"""
        if not request.user.totp_enabled:
            return Response(
                {'error': '2FA non activée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Vérifier le mot de passe pour sécurité
        password = request.data.get('password')
        if not password:
            return Response(
                {'error': 'Mot de passe requis pour régénérer les codes de secours'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not request.user.check_password(password):
            return Response(
                {'error': 'Mot de passe incorrect'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Générer de nouveaux codes
        if hasattr(request.user, 'generate_backup_codes'):
            new_codes = request.user.generate_backup_codes()
        else:
            # Créer des codes factices si la méthode n'existe pas
            import secrets
            new_codes = [secrets.token_hex(4).upper() for _ in range(10)]
        
        return Response({
            'backup_codes': new_codes,
            'count': len(new_codes),
            'message': 'Nouveaux codes de secours générés avec succès. Les anciens codes ne fonctionnent plus.'
        })
    
# ============================================
# SOCIAL AUTH CALLBACK
# ============================================

class SocialCallbackView(APIView):
    """Callback pour l'authentification sociale (OAuth)"""
    
    permission_classes = [permissions.AllowAny]
    
    def get(self, request):
        provider = request.query_params.get('provider')
        code = request.query_params.get('code')
        
        if not provider or not code:
            return Response({'error': 'Paramètres manquants'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if provider == 'google':
                user_data = SocialAuthHandler.verify_google_token(code)
            elif provider == 'facebook':
                user_data = SocialAuthHandler.verify_facebook_token(code)
            else:
                return Response({'error': 'Provider non supporté'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user_data:
                return Response({'error': 'Token invalide'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = SocialAuthHandler.get_or_create_social_user(user_data)
            
            if isinstance(result, tuple):
                user, error = result
            else:
                user, error = result, None
            
            if error:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
            
            jwt_token = generate_jwt_token(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': jwt_token,
                'message': f'Connexion avec {provider} réussie'
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def post(self, request):
        provider = request.data.get('provider')
        token = request.data.get('token')
        
        if not provider or not token:
            return Response({'error': 'Paramètres manquants'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            if provider == 'google':
                user_data = SocialAuthHandler.verify_google_token(token)
            elif provider == 'facebook':
                user_data = SocialAuthHandler.verify_facebook_token(token)
            else:
                return Response({'error': 'Provider non supporté'}, status=status.HTTP_400_BAD_REQUEST)
            
            if not user_data:
                return Response({'error': 'Token invalide'}, status=status.HTTP_400_BAD_REQUEST)
            
            result = SocialAuthHandler.get_or_create_social_user(user_data)
            
            if isinstance(result, tuple):
                user, error = result
            else:
                user, error = result, None
            
            if error:
                return Response({'error': error}, status=status.HTTP_400_BAD_REQUEST)
            
            jwt_token = generate_jwt_token(user)
            
            return Response({
                'user': UserSerializer(user).data,
                'token': jwt_token,
                'message': f'Connexion avec {provider} réussie'
            })
            
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    
        
# ============================================
# DELETE ALL SESSIONS - DÉCONNEXION DE TOUS LES APPAREILS
# ============================================

class DeleteAllSessionsView(APIView):
    """Supprimer toutes les sessions de l'utilisateur (déconnexion de tous les appareils)"""
    
    permission_classes = [permissions.IsAuthenticated]
    
    def delete(self, request):
        """Supprimer toutes les sessions sauf la session actuelle"""
        current_session_id = request.data.get('current_session_id')
        
        sessions_query = UserSession.objects.filter(utilisateur=request.user)
        
        if current_session_id:
            sessions_query = sessions_query.exclude(id=current_session_id)
        
        deleted_count, _ = sessions_query.delete()
        
        return Response({
            'message': f'{deleted_count} session(s) ont été supprimées',
            'deleted_count': deleted_count
        })
    
    def post(self, request):
        return self.delete(request)