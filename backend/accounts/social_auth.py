# accounts/social_auth.py
from django.conf import settings
import requests
from .models import Utilisateur
from .utils import generate_random_password

class SocialAuthHandler:
    """Gestionnaire d'authentification sociale"""
    
    @staticmethod
    def verify_google_token(token):
        """Vérifie un token Google"""
        try:
            response = requests.get(
                f"https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}"
            )
            if response.status_code == 200:
                data = response.json()
                return {
                    'email': data.get('email'),
                    'first_name': data.get('given_name', ''),
                    'last_name': data.get('family_name', ''),
                    'picture': data.get('picture', ''),
                    'provider_id': data.get('sub'),
                    'provider': 'google'
                }
        except:
            pass
        return None
    
    @staticmethod
    def verify_facebook_token(token):
        """Vérifie un token Facebook"""
        try:
            response = requests.get(
                f"https://graph.facebook.com/me?fields=id,name,email,picture&access_token={token}"
            )
            if response.status_code == 200:
                data = response.json()
                name_parts = data.get('name', '').split(' ', 1)
                return {
                    'email': data.get('email'),
                    'first_name': name_parts[0] if name_parts else '',
                    'last_name': name_parts[1] if len(name_parts) > 1 else '',
                    'picture': data.get('picture', {}).get('data', {}).get('url', ''),
                    'provider_id': data.get('id'),
                    'provider': 'facebook'
                }
        except:
            pass
        return None
    
    @staticmethod
    def verify_apple_token(token):
        """Vérifie un token Apple (nécessite vérification côté serveur)"""
        # Apple nécessite une validation plus complexe avec JWT
        # Cette partie est simplifiée, à compléter selon les besoins
        try:
            import jwt
            from jwt.algorithms import RSAAlgorithm
            
            # Récupérer les clés publiques Apple
            response = requests.get("https://appleid.apple.com/auth/keys")
            keys = response.json()
            
            # Décoder le token (simplifié)
            headers = jwt.get_unverified_header(token)
            # Validation complète à implémenter
            return None
        except:
            pass
        return None
    
    @staticmethod
    def get_or_create_social_user(user_data):
        """Récupère ou crée un utilisateur à partir des données sociales"""
        provider = user_data.get('provider')
        provider_id = user_data.get('provider_id')
        email = user_data.get('email')
        
        if not email:
            return None, "Email non fourni par le fournisseur"
        
        # Chercher l'utilisateur existant
        user = Utilisateur.objects.filter(email=email).first()
        
        if user:
            # Mettre à jour les informations sociales
            user.social_auth_provider = provider
            user.social_auth_id = provider_id
            user.save()
            return user, None
        
        # Créer un nouvel utilisateur
        username = email.split('@')[0]
        base_username = username
        counter = 1
        
        while Utilisateur.objects.filter(username=username).exists():
            username = f"{base_username}{counter}"
            counter += 1
        
        user = Utilisateur.objects.create_user(
            email=email,
            username=username,
            password=generate_random_password(),
            nom=user_data.get('last_name', ''),
            prenom=user_data.get('first_name', ''),
            is_verified=True,  # Email vérifié par le provider
            social_auth_provider=provider,
            social_auth_id=provider_id
        )
        
        return user, None