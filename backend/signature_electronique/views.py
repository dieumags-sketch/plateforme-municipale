# backend/apps/signature_electronique/views.py
# ============================================
# VERSION CORRIGÉE : ACCÈS UNIQUEMENT AUX UTILISATEURS CONNECTÉS
# EXCEPTION : signer_token (endpoint public pour les liens email)
# ============================================

from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny  # ✅ Garder AllowAny pour signer_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.core.mail import send_mail
from django.db.models import Q, Count
from django.contrib.auth import get_user_model
from .models import (
    CertificatNumerique, SignatureElectronique, DemandeSignature,
    ConfigurationSignature, JournalSignature, VerificationSignature
)
from .serializers import (
    CertificatNumeriqueSerializer, CreerCertificatSerializer,
    SignatureElectroniqueListSerializer, SignatureElectroniqueDetailSerializer,
    DemandeSignatureSerializer, ConfigurationSignatureSerializer,
    VerifierSignatureSerializer, SignerDemandeSerializer
)
from .utils import (
    generer_paire_cles, chiffrer_cle_privee, dechiffrer_cle_privee,
    generer_certificat, signer_document, verifier_signature,
    calculer_hash_contenu, generer_token
)
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
import secrets

User = get_user_model()


# ============================================
# CERTIFICATS - PROTÉGÉ
# ============================================

class CertificatViewSet(viewsets.ModelViewSet):
    """Gestion des certificats numériques - Accessible uniquement aux utilisateurs connectés"""
    serializer_class = CertificatNumeriqueSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['numero_serie', 'utilisateur__email', 'utilisateur__username']
    ordering_fields = ['date_creation', 'date_expiration']
    
    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, 'role', '') in ['admin']:
            return CertificatNumerique.objects.all()
        return CertificatNumerique.objects.filter(utilisateur=self.request.user)
    
    @action(detail=False, methods=['get'])
    def mon_certificat(self, request):
        """Récupérer mon certificat"""
        try:
            certificat = CertificatNumerique.objects.get(utilisateur=request.user)
            serializer = self.get_serializer(certificat)
            return Response(serializer.data)
        except CertificatNumerique.DoesNotExist:
            return Response({'exists': False}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'])
    def creer(self, request):
        """Créer un certificat numérique"""
        if CertificatNumerique.objects.filter(utilisateur=request.user, est_valide=True).exists():
            return Response(
                {'error': 'Vous avez déjà un certificat valide. Veuillez le renouveler s\'il est expiré.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CreerCertificatSerializer(data=request.data)
        if serializer.is_valid():
            mot_de_passe = serializer.validated_data['mot_de_passe']
            niveau = serializer.validated_data.get('niveau_confiance', 'standard')
            
            try:
                cle_privee, cle_publique = generer_paire_cles()
                cle_privee_chiffree = chiffrer_cle_privee(cle_privee, mot_de_passe)
                
                sujet_info = {
                    'cn': request.user.get_full_name() or request.user.username,
                    'org': 'Commune de Bot-Makak',
                    'email': request.user.email,
                    'c': 'CM',
                    'st': 'Centre',
                    'l': 'Bot-Makak'
                }
                certificat = generer_certificat(cle_privee, cle_publique, sujet_info)
                
                numero_serie = secrets.token_hex(16).upper()
                date_expiration = timezone.now() + timezone.timedelta(days=365)
                
                certificat_obj = CertificatNumerique.objects.create(
                    utilisateur=request.user,
                    certificat=certificat.decode() if isinstance(certificat, bytes) else certificat,
                    cle_publique=cle_publique.public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode(),
                    cle_privee_chiffree=cle_privee_chiffree,
                    numero_serie=numero_serie,
                    date_expiration=date_expiration,
                    niveau_confiance=niveau
                )
                
                try:
                    send_mail(
                        subject="Certificat numérique créé - Bot-Makak",
                        message=f"""Bonjour {request.user.get_full_name() or request.user.username},

Votre certificat numérique a été créé avec succès.

📋 Détails du certificat:
• Numéro de série: {numero_serie}
• Date d'expiration: {date_expiration.strftime('%d/%m/%Y')}
• Niveau: {niveau}

⚠️ Important: Conservez votre mot de passe en sécurité. Il est nécessaire pour signer des documents.

---
Commune de Bot-Makak
Service de Signature Électronique
""",
                        from_email='signature@botmatmakak.net',
                        recipient_list=[request.user.email],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Erreur envoi email: {e}")
                
                return Response(
                    CertificatNumeriqueSerializer(certificat_obj).data,
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response(
                    {'error': f'Erreur lors de la création du certificat: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def revoquer(self, request, pk=None):
        """Révoquer un certificat"""
        certificat = self.get_object()
        
        if certificat.utilisateur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if certificat.est_revoque:
            return Response({'error': 'Certificat déjà révoqué'}, status=status.HTTP_400_BAD_REQUEST)
        
        motif = request.data.get('motif', 'Aucun motif fourni')
        
        certificat.est_revoque = True
        certificat.date_revocation = timezone.now()
        certificat.save(update_fields=['est_revoque', 'date_revocation'])
        
        JournalSignature.objects.create(
            signature=None,
            action='revocation_certificat',
            utilisateur=request.user,
            commentaire=motif,
            adresse_ip=self.get_client_ip(request)
        )
        
        return Response({'message': 'Certificat révoqué avec succès'})
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


# ============================================
# SIGNATURES - PROTÉGÉ
# ============================================

class SignatureViewSet(viewsets.ModelViewSet):
    """Gestion des signatures - Accessible uniquement aux utilisateurs connectés"""
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['document_titre', 'signataire__email', 'module_source']
    ordering_fields = ['timestamp_signature', 'horodatage']
    ordering = ['-timestamp_signature']
    
    def get_serializer_class(self):
        if self.action == 'retrieve':
            return SignatureElectroniqueDetailSerializer
        return SignatureElectroniqueListSerializer
    
    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, 'role', '') in ['admin']:
            return SignatureElectronique.objects.all()
        return SignatureElectronique.objects.filter(signataire=self.request.user)
    
    @action(detail=False, methods=['post'])
    def signer_document(self, request):
        """Signer un document directement"""
        module_source = request.data.get('module_source')
        source_id = request.data.get('source_id')
        document_titre = request.data.get('document_titre')
        document_contenu = request.data.get('document_contenu')
        signature_image = request.data.get('signature_image')
        mot_de_passe = request.data.get('mot_de_passe')
        
        if not all([module_source, document_titre, document_contenu]):
            return Response(
                {'error': 'Champs requis: module_source, document_titre, document_contenu'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            certificat = CertificatNumerique.objects.get(
                utilisateur=request.user,
                est_valide=True,
                est_revoque=False
            )
            if certificat.est_expire():
                return Response(
                    {'error': 'Votre certificat a expiré. Veuillez en créer un nouveau.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        except CertificatNumerique.DoesNotExist:
            return Response(
                {'error': 'Aucun certificat valide trouvé. Veuillez créer un certificat.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not mot_de_passe:
            return Response(
                {'error': 'Mot de passe requis pour déchiffrer votre clé privée'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            cle_privee = dechiffrer_cle_privee(certificat.cle_privee_chiffree, mot_de_passe)
        except Exception:
            return Response(
                {'error': 'Mot de passe incorrect ou clé corrompue'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        try:
            signature = signer_document(document_contenu, cle_privee)
            document_hash = calculer_hash_contenu(document_contenu)
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la signature: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        signature_obj = SignatureElectronique.objects.create(
            module_source=module_source,
            source_id=source_id or '',
            document_titre=document_titre,
            document_hash=document_hash,
            signataire=request.user,
            certificat_utilise=certificat,
            signature_valeur=signature if isinstance(signature, str) else signature.decode(),
            horodatage=timezone.now(),
            adresse_ip=self.get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:500],
            signature_image=signature_image
        )
        
        JournalSignature.objects.create(
            signature=signature_obj,
            action='creation',
            utilisateur=request.user,
            commentaire=f'Signature du document: {document_titre}',
            adresse_ip=self.get_client_ip(request)
        )
        
        mettre_a_jour_module_source(signature_obj)
        
        return Response({
            'signature_id': str(signature_obj.id),
            'document_hash': document_hash,
            'timestamp': signature_obj.horodatage.isoformat(),
            'message': 'Document signé avec succès'
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'])
    def verifier(self, request):
        """Vérifier une signature"""
        serializer = VerifierSignatureSerializer(data=request.data)
        if serializer.is_valid():
            signature_id = serializer.validated_data['signature_id']
            document = serializer.validated_data.get('document')
            
            try:
                signature = SignatureElectronique.objects.select_related(
                    'signataire', 'certificat_utilise'
                ).get(id=signature_id)
            except SignatureElectronique.DoesNotExist:
                return Response(
                    {'valide': False, 'message': 'Signature non trouvée'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            certificat = signature.certificat_utilise
            
            if not certificat.est_valide:
                return Response({'valide': False, 'message': 'Certificat invalide'})
            
            if certificat.est_revoque:
                return Response({'valide': False, 'message': 'Certificat révoqué'})
            
            if certificat.est_expire():
                return Response({'valide': False, 'message': 'Certificat expiré'})
            
            try:
                cle_publique = serialization.load_pem_public_key(
                    certificat.cle_publique.encode(),
                    backend=default_backend()
                )
                
                est_valide = verifier_signature(document, signature.signature_valeur, cle_publique) if document else True
                
                hash_match = True
                if document:
                    hash_calcule = calculer_hash_contenu(document)
                    hash_match = hash_calcule == signature.document_hash
                
                resultat = est_valide and hash_match
                
                VerificationSignature.objects.create(
                    signature=signature,
                    verificateur=request.user,
                    resultat=resultat,
                    details={
                        'signature_valide': est_valide,
                        'hash_match': hash_match,
                        'adresse_ip': self.get_client_ip(request)
                    }
                )
                
                return Response({
                    'valide': resultat,
                    'message': 'Signature authentique' if resultat else 'Signature invalide',
                    'details': {
                        'signataire': signature.signataire.get_full_name() or signature.signataire.username,
                        'signataire_email': signature.signataire.email,
                        'document': signature.document_titre,
                        'date_signature': signature.timestamp_signature.isoformat() if signature.timestamp_signature else None,
                        'certificat_numero': certificat.numero_serie,
                        'certificat_emetteur': 'Commune de Bot-Makak'
                    }
                })
                
            except Exception as e:
                return Response(
                    {'valide': False, 'message': f'Erreur de vérification: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def qrcode(self, request, pk=None):
        """Générer un QR code pour la signature"""
        signature = self.get_object()
        
        if signature.signataire != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        verification_url = f"https://botmatmakak.cm/verifier-signature?id={signature.id}"
        qr_url = f"https://api.qrserver.com/v1/create-qr-code/?size=300x300&data={verification_url}"
        
        return Response({
            'qr_url': qr_url,
            'verification_url': verification_url,
            'signature_id': str(signature.id)
        })
    
    @action(detail=True, methods=['get'])
    def certificat(self, request, pk=None):
        """Télécharger le certificat associé à la signature"""
        signature = self.get_object()
        certificat = signature.certificat_utilise
        
        if certificat and certificat.certificat:
            from django.http import HttpResponse
            response = HttpResponse(certificat.certificat, content_type='application/x-pem-file')
            response['Content-Disposition'] = f'attachment; filename="certificat_{certificat.numero_serie}.pem"'
            return response
        
        return Response({'error': 'Certificat non disponible'}, status=status.HTTP_404_NOT_FOUND)
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


# ============================================
# DEMANDES DE SIGNATURE - PROTÉGÉ
# ============================================

class DemandeSignatureViewSet(viewsets.ModelViewSet):
    """Gestion des demandes de signature - Accessible uniquement aux utilisateurs connectés"""
    serializer_class = DemandeSignatureSerializer
    permission_classes = [IsAuthenticated]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['document_titre', 'destinataire__email']
    ordering_fields = ['date_creation', 'date_expiration']
    ordering = ['-date_creation']
    
    def get_queryset(self):
        if self.request.user.is_staff or getattr(self.request.user, 'role', '') in ['admin']:
            return DemandeSignature.objects.all()
        return DemandeSignature.objects.filter(
            Q(destinataire=self.request.user) | Q(envoyeur=self.request.user)
        )
    
    @action(detail=False, methods=['post'])
    def envoyer(self, request):
        """Envoyer une demande de signature"""
        serializer = DemandeSignatureSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('destinataire_email')
            if not email:
                return Response(
                    {'error': 'Email du destinataire requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                destinataire = User.objects.get(email=email)
            except User.DoesNotExist:
                return Response(
                    {'error': f'Utilisateur avec l\'email {email} non trouvé'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            try:
                config = ConfigurationSignature.objects.first()
                delai_jours = config.delai_validite_demande if config else 7
            except:
                delai_jours = 7
            
            token = generer_token()
            date_expiration = timezone.now() + timezone.timedelta(days=delai_jours)
            
            demande = DemandeSignature.objects.create(
                module_source=serializer.validated_data['module_source'],
                source_id=serializer.validated_data.get('source_id', ''),
                document_titre=serializer.validated_data['document_titre'],
                document_contenu=serializer.validated_data['document_contenu'],
                destinataire=destinataire,
                envoyeur=request.user,
                token=token,
                date_expiration=date_expiration,
                message_personnalise=serializer.validated_data.get('message_personnalise', '')
            )
            
            signature_url = f"https://botmatmakak.cm/signature/signer?token={token}"
            try:
                send_mail(
                    subject=f"Demande de signature - {demande.document_titre}",
                    message=f"""
Bonjour {destinataire.get_full_name() or destinataire.username},

{request.user.get_full_name() or request.user.username} vous demande de signer le document suivant:

📄 Document: {demande.document_titre}
📅 Date limite: {date_expiration.strftime('%d/%m/%Y')}

{serializer.validated_data.get('message_personnalise', '')}

🔗 Lien pour signer: {signature_url}

⚠️ Ce lien est valable jusqu'au {date_expiration.strftime('%d/%m/%Y')}.

---
Commune de Bot-Makak
Service de Signature Électronique
""",
                    from_email='signature@botmatmakak.net',
                    recipient_list=[email],
                    fail_silently=True
                )
            except Exception as e:
                print(f"Erreur envoi email: {e}")
            
            return Response(
                DemandeSignatureSerializer(demande).data,
                status=status.HTTP_201_CREATED
            )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def signer_token(self, request):
        """
        Signer via token (sans authentification)
        ⚠️ CET ENDPOINT RESTE PUBLIC - utilisé pour les liens envoyés par email
        """
        serializer = SignerDemandeSerializer(data=request.data)
        if serializer.is_valid():
            token = serializer.validated_data['token']
            signature_image = serializer.validated_data.get('signature_image')
            
            try:
                demande = DemandeSignature.objects.get(token=token, statut='en_attente')
            except DemandeSignature.DoesNotExist:
                return Response(
                    {'error': 'Demande non trouvée ou déjà traitée'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            if demande.date_expiration and demande.date_expiration < timezone.now():
                demande.statut = 'expire'
                demande.save(update_fields=['statut'])
                return Response(
                    {'error': 'Cette demande a expiré'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                certificat = CertificatNumerique.objects.get(
                    utilisateur=demande.destinataire,
                    est_valide=True,
                    est_revoque=False
                )
                if certificat.est_expire():
                    return Response(
                        {'error': 'Votre certificat a expiré. Veuillez en créer un nouveau.'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except CertificatNumerique.DoesNotExist:
                return Response(
                    {'error': 'Aucun certificat valide trouvé. Veuillez créer un certificat.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            mot_de_passe = serializer.validated_data.get('mot_de_passe')
            if not mot_de_passe:
                return Response(
                    {'error': 'Mot de passe requis'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                cle_privee = dechiffrer_cle_privee(certificat.cle_privee_chiffree, mot_de_passe)
            except Exception:
                return Response(
                    {'error': 'Mot de passe incorrect'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
            
            try:
                signature = signer_document(demande.document_contenu, cle_privee)
                document_hash = calculer_hash_contenu(demande.document_contenu)
            except Exception as e:
                return Response(
                    {'error': f'Erreur lors de la signature: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            signature_obj = SignatureElectronique.objects.create(
                module_source=demande.module_source,
                source_id=demande.source_id,
                document_titre=demande.document_titre,
                document_hash=document_hash,
                signataire=demande.destinataire,
                certificat_utilise=certificat,
                signature_valeur=signature if isinstance(signature, str) else signature.decode(),
                horodatage=timezone.now(),
                signature_image=signature_image,
                adresse_ip=self.get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')[:500]
            )
            
            demande.signature = signature_obj
            demande.statut = 'signe'
            demande.date_signature = timezone.now()
            demande.save(update_fields=['signature', 'statut', 'date_signature'])
            
            JournalSignature.objects.create(
                signature=signature_obj,
                action='creation',
                utilisateur=demande.destinataire,
                commentaire=f'Signature via demande: {demande.document_titre}',
                adresse_ip=self.get_client_ip(request)
            )
            
            mettre_a_jour_module_source(signature_obj)
            
            if demande.envoyeur and demande.envoyeur.email:
                try:
                    send_mail(
                        subject=f"Document signé - {demande.document_titre}",
                        message=f"""
Bonjour {demande.envoyeur.get_full_name() or demande.envoyeur.username},

Le document "{demande.document_titre}" a été signé par {demande.destinataire.get_full_name() or demande.destinataire.username}.

Date de signature: {timezone.now().strftime('%d/%m/%Y à %H:%M')}

---
Commune de Bot-Makak
Service de Signature Électronique
""",
                        from_email='signature@botmatmakak.net',
                        recipient_list=[demande.envoyeur.email],
                        fail_silently=True
                    )
                except Exception as e:
                    print(f"Erreur envoi email: {e}")
            
            return Response({
                'message': 'Document signé avec succès',
                'signature_id': str(signature_obj.id)
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def annuler(self, request, pk=None):
        """Annuler une demande de signature"""
        demande = self.get_object()
        
        if demande.envoyeur != request.user and not (request.user.is_staff or getattr(request.user, 'role', '') in ['admin']):
            return Response({'error': 'Non autorisé'}, status=status.HTTP_403_FORBIDDEN)
        
        if demande.statut != 'en_attente':
            return Response(
                {'error': f'Seules les demandes en attente peuvent être annulées (statut: {demande.statut})'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        demande.statut = 'annule'
        demande.save(update_fields=['statut'])
        
        return Response({'message': 'Demande annulée avec succès'})
    
    def get_client_ip(self, request):
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')


# ============================================
# CONFIGURATION - ADMIN UNIQUEMENT
# ============================================

class ConfigurationSignatureViewSet(viewsets.ModelViewSet):
    """Configuration du module de signature - Admin uniquement"""
    queryset = ConfigurationSignature.objects.all()
    serializer_class = ConfigurationSignatureSerializer
    permission_classes = [IsAuthenticated]  # ✅ MODIFIÉ (était IsAdminUser)
    
    def dispatch(self, request, *args, **kwargs):
        """Vérification admin avant toute action"""
        if not (request.user.is_staff or getattr(request.user, 'role', '') == 'admin'):
            return Response(
                {'error': 'Accès réservé aux administrateurs'},
                status=status.HTTP_403_FORBIDDEN
            )
        return super().dispatch(request, *args, **kwargs)
    
    def get_queryset(self):
        return ConfigurationSignature.objects.all()[:1]
    
    def perform_create(self, serializer):
        if ConfigurationSignature.objects.exists():
            from rest_framework import serializers
            raise serializers.ValidationError("Une configuration existe déjà. Utilisez la mise à jour.")
        serializer.save()
    
    @action(detail=False, methods=['post'])
    def regenerer_cles(self, request):
        """Régénérer les clés de signature système"""
        from .utils import generer_paire_cles_systeme
        
        try:
            cle_privee, cle_publique = generer_paire_cles_systeme()
            
            config = ConfigurationSignature.objects.first()
            if config:
                config.cle_privee_systeme = cle_privee
                config.cle_publique_systeme = cle_publique
                config.save()
            else:
                ConfigurationSignature.objects.create(
                    cle_privee_systeme=cle_privee,
                    cle_publique_systeme=cle_publique
                )
            
            return Response({'message': 'Clés système régénérées avec succès'})
        except Exception as e:
            return Response(
                {'error': f'Erreur lors de la régénération: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================
# FONCTION UTILITAIRE (inchangée)
# ============================================

def mettre_a_jour_module_source(signature):
    """Met à jour le module source après signature"""
    if not signature.module_source or not signature.source_id:
        return
    
    try:
        if signature.module_source == 'etat_civil':
            from apps.etat_civil.models import DemandeActe
            demande = DemandeActe.objects.filter(id=signature.source_id).first()
            if demande and demande.statut not in ['signe', 'delivre']:
                demande.statut = 'signe'
                demande.date_signature = signature.timestamp_signature or signature.horodatage
                demande.save(update_fields=['statut', 'date_signature'])
        
        elif signature.module_source == 'archives':
            from apps.archives.models import DemandeAccesArchive
            demande = DemandeAccesArchive.objects.filter(id=signature.source_id).first()
            if demande and demande.statut != 'paye':
                demande.statut = 'paye'
                demande.date_traitement = signature.horodatage
                demande.save(update_fields=['statut', 'date_traitement'])
        
        elif signature.module_source == 'activites':
            from apps.activites.models import InscriptionActivite
            inscription = InscriptionActivite.objects.filter(id=signature.source_id).first()
            if inscription and inscription.statut != 'confirme':
                inscription.statut = 'confirme'
                inscription.date_confirmation = signature.horodatage
                inscription.save(update_fields=['statut', 'date_confirmation'])
        
        elif signature.module_source == 'dechets':
            from apps.dechets.models import DemandeEncombrant
            demande = DemandeEncombrant.objects.filter(id=signature.source_id).first()
            if demande:
                demande.statut = 'effectuee'
                demande.date_realisation = signature.horodatage
                demande.save(update_fields=['statut', 'date_realisation'])
        
        elif signature.module_source == 'paiements':
            from apps.paiements.models import TransactionPaiement
            transaction = TransactionPaiement.objects.filter(id=signature.source_id).first()
            if transaction:
                transaction.statut = 'confirme'
                transaction.date_confirmation = signature.horodatage
                transaction.save(update_fields=['statut', 'date_confirmation'])
                
    except Exception as e:
        print(f"Erreur mise à jour module source {signature.module_source}: {e}")