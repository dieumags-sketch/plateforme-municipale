# signature_electronique/utils.py

import hashlib
import secrets
from datetime import datetime, timedelta
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC  # CORRIGÉ: PBKDF2HMAC au lieu de PBKDF2
from cryptography.x509.oid import NameOID
import base64
import json


def generer_paire_cles():
    """Génère une paire de clés RSA (2048 bits)"""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    public_key = private_key.public_key()
    return private_key, public_key


def chiffrer_cle_privee(private_key, password):
    """Chiffre la clé privée avec un mot de passe"""
    # Convertir la clé privée en PEM
    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.BestAvailableEncryption(password.encode())
    )
    return pem.decode()


def dechiffrer_cle_privee(encrypted_pem, password):
    """Déchiffre la clé privée avec le mot de passe"""
    try:
        private_key = serialization.load_pem_private_key(
            encrypted_pem.encode(),
            password=password.encode(),
            backend=default_backend()
        )
        return private_key
    except Exception as e:
        raise Exception("Mot de passe incorrect ou clé corrompue") from e


def generer_certificat(private_key, public_key, sujet_info):
    """Génère un certificat X.509 auto-signé"""
    subject = x509.Name([
        x509.NameAttribute(NameOID.COUNTRY_NAME, sujet_info.get('c', 'CM')),
        x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, sujet_info.get('st', 'Centre')),
        x509.NameAttribute(NameOID.LOCALITY_NAME, sujet_info.get('l', 'Bot-Makak')),
        x509.NameAttribute(NameOID.ORGANIZATION_NAME, sujet_info.get('org', 'Commune de Bot-Makak')),
        x509.NameAttribute(NameOID.COMMON_NAME, sujet_info.get('cn', 'Bot-Makak Signature')),
        x509.NameAttribute(NameOID.EMAIL_ADDRESS, sujet_info.get('email', 'signature@botmatmakak.net')),
    ])
    
    # Construction du certificat
    cert = x509.CertificateBuilder().subject_name(
        subject
    ).issuer_name(
        subject  # Auto-signé
    ).public_key(
        public_key
    ).serial_number(
        x509.random_serial_number()
    ).not_valid_before(
        datetime.now()
    ).not_valid_after(
        datetime.now() + timedelta(days=365)
    ).add_extension(
        x509.BasicConstraints(ca=True, path_length=None), critical=True,
    ).sign(private_key, hashes.SHA256(), default_backend())
    
    # Convertir en PEM
    return cert.public_bytes(serialization.Encoding.PEM)


def signer_document(document, private_key):
    """Signe un document avec la clé privée"""
    # Convertir le document en bytes si nécessaire
    if isinstance(document, str):
        document = document.encode('utf-8')
    
    # Calculer le hash
    hash_algo = hashes.SHA256()
    hasher = hashes.Hash(hash_algo, default_backend())
    hasher.update(document)
    digest = hasher.finalize()
    
    # Signer
    signature = private_key.sign(
        digest,
        padding.PKCS1v15(),
        hashes.SHA256()
    )
    
    return base64.b64encode(signature).decode()


def verifier_signature(document, signature_base64, public_key_pem):
    """Vérifie la signature d'un document"""
    try:
        # Charger la clé publique
        public_key = serialization.load_pem_public_key(
            public_key_pem.encode() if isinstance(public_key_pem, str) else public_key_pem,
            backend=default_backend()
        )
        
        # Convertir le document en bytes
        if isinstance(document, str):
            document = document.encode('utf-8')
        
        # Décoder la signature
        signature = base64.b64decode(signature_base64)
        
        # Calculer le hash
        hash_algo = hashes.SHA256()
        hasher = hashes.Hash(hash_algo, default_backend())
        hasher.update(document)
        digest = hasher.finalize()
        
        # Vérifier
        public_key.verify(
            signature,
            digest,
            padding.PKCS1v15(),
            hashes.SHA256()
        )
        return True
    except Exception:
        return False


def calculer_hash_contenu(contenu):
    """Calcule le hash SHA-256 d'un contenu"""
    if isinstance(contenu, str):
        contenu = contenu.encode('utf-8')
    return hashlib.sha256(contenu).hexdigest()


def generer_token():
    """Génère un token unique pour les demandes de signature"""
    return secrets.token_urlsafe(32)


def generer_paire_cles_systeme():
    """Génère une paire de clés pour le système"""
    return generer_paire_cles()


# Fonctions pour l'authentification sociale (à compléter)
class SocialAuthHandler:
    """Handler pour l'authentification sociale"""
    
    @staticmethod
    def verify_google_token(token):
        """Vérifie un token Google"""
        # Implémentation à compléter
        import requests
        try:
            response = requests.get(f'https://www.googleapis.com/oauth2/v3/tokeninfo?id_token={token}')
            if response.status_code == 200:
                return response.json()
        except:
            pass
        return None
    
    @staticmethod
    def verify_facebook_token(token):
        """Vérifie un token Facebook"""
        # Implémentation à compléter
        import requests
        try:
            response = requests.get(f'https://graph.facebook.com/me?access_token={token}')
            if response.status_code == 200:
                data = response.json()
                return {
                    'id': data.get('id'),
                    'email': data.get('email'),
                    'name': data.get('name'),
                    'provider': 'facebook'
                }
        except:
            pass
        return None
    
    @staticmethod
    def verify_apple_token(token):
        """Vérifie un token Apple"""
        # Implémentation à compléter
        return None
    
    @staticmethod
    def get_or_create_social_user(user_data):
        """Crée ou récupère un utilisateur à partir des données sociales"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        email = user_data.get('email')
        provider = user_data.get('provider')
        social_id = user_data.get('id')
        
        if not email:
            return None, "Email requis"
        
        user = User.objects.filter(email=email).first()
        if user:
            return user, None
        
        # Créer un nouvel utilisateur
        username = f"{provider}_{social_id}"[:150]
        user = User.objects.create_user(
            username=username,
            email=email,
            password=secrets.token_urlsafe(16)
        )
        
        return user, None
    
    @staticmethod
    def verify_google_auth_code(code):
        """Échange un code d'authentification Google contre un token"""
        # Implémentation complète à ajouter
        return None
    
    @staticmethod
    def verify_facebook_auth_code(code):
        """Échange un code d'authentification Facebook contre un token"""
        # Implémentation complète à ajouter
        return None
    
    @staticmethod
    def exchange_code_for_token(code, provider):
        """Échange un code d'authentification contre un token"""
        if provider == 'google':
            return SocialAuthHandler.verify_google_auth_code(code)
        elif provider == 'facebook':
            return SocialAuthHandler.verify_facebook_auth_code(code)
        return None