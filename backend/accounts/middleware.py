# accounts/middleware.py
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed

class APIAuthenticationMiddleware:
    """Middleware pour l'authentification API"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Vérifier le token dans l'en-tête Authorization
        auth_header = request.headers.get('Authorization')
        
        if auth_header and auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
            
            try:
                from .utils import verify_jwt_token
                payload = verify_jwt_token(token)
                
                if payload:
                    from .models import Utilisateur
                    request.user = Utilisateur.objects.get(id=payload['user_id'])
            except Exception:
                pass
        
        return self.get_response(request)