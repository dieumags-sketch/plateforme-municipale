# backend/apps/signature_electronique/serializers.py

from rest_framework import serializers
from django.utils import timezone
from .models import (
    CertificatNumerique, SignatureElectronique, DemandeSignature,
    ConfigurationSignature, JournalSignature, VerificationSignature,
    CachetElectronique, PreuveSignature, RelanceSignature
)


class CertificatNumeriqueSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    utilisateur_email = serializers.EmailField(source='utilisateur.email', read_only=True)  # AJOUTÉ
    est_expire = serializers.SerializerMethodField()
    est_utilisable = serializers.SerializerMethodField()  # AJOUTÉ
    niveau_display = serializers.CharField(source='get_niveau_confiance_display', read_only=True)
    date_expiration_formatee = serializers.SerializerMethodField()  # AJOUTÉ
    date_emission_formatee = serializers.SerializerMethodField()  # AJOUTÉ
    
    class Meta:
        model = CertificatNumerique
        fields = [
            'id', 'utilisateur', 'utilisateur_nom', 'utilisateur_email',
            'numero_serie', 'emetteur', 'sujet_nom', 'sujet_email',
            'date_emission', 'date_emission_formatee', 'date_expiration', 'date_expiration_formatee',
            'est_valide', 'est_expire', 'est_utilisable', 'est_revoque',
            'niveau_confiance', 'niveau_display', 'empreinte'
        ]
        read_only_fields = ['id', 'numero_serie', 'date_emission', 'empreinte']
    
    def get_est_expire(self, obj):
        return obj.est_expire()
    
    def get_est_utilisable(self, obj):
        return obj.est_utilisable()
    
    def get_date_expiration_formatee(self, obj):
        return obj.date_expiration.strftime('%d/%m/%Y') if obj.date_expiration else None
    
    def get_date_emission_formatee(self, obj):
        return obj.date_emission.strftime('%d/%m/%Y') if obj.date_emission else None


class CertificatNumeriqueCreateSerializer(serializers.Serializer):
    """Serializer pour la création d'un certificat"""
    mot_de_passe = serializers.CharField(min_length=8, max_length=128, write_only=True)
    niveau_confiance = serializers.IntegerField(min_value=1, max_value=3, default=1)
    confirmation_mot_de_passe = serializers.CharField(min_length=8, max_length=128, write_only=True)  # AJOUTÉ
    
    def validate(self, data):
        if data['mot_de_passe'] != data.get('confirmation_mot_de_passe'):
            raise serializers.ValidationError({
                'confirmation_mot_de_passe': 'Les mots de passe ne correspondent pas'
            })
        return data


class SignatureElectroniqueListSerializer(serializers.ModelSerializer):
    signataire_nom = serializers.CharField(source='signataire.get_full_name', read_only=True)
    signataire_email = serializers.EmailField(source='signataire.email', read_only=True)  # AJOUTÉ
    module_display = serializers.CharField(source='get_module_source_display', read_only=True)
    type_display = serializers.CharField(source='get_type_signature_display', read_only=True)  # AJOUTÉ
    date_signature_formatee = serializers.SerializerMethodField()  # AJOUTÉ
    statut_couleur = serializers.SerializerMethodField()  # AJOUTÉ
    
    class Meta:
        model = SignatureElectronique
        fields = [
            'id', 'document_titre', 'module_source', 'module_display',
            'signataire', 'signataire_nom', 'signataire_email',
            'timestamp_signature', 'date_signature_formatee',
            'type_signature', 'type_display', 'est_valide', 'statut_couleur'
        ]
    
    def get_date_signature_formatee(self, obj):
        return obj.timestamp_signature.strftime('%d/%m/%Y à %H:%M') if obj.timestamp_signature else None
    
    def get_statut_couleur(self, obj):
        return '#10b981' if obj.est_valide else '#ef4444'


class SignatureElectroniqueDetailSerializer(serializers.ModelSerializer):
    signataire_nom = serializers.CharField(source='signataire.get_full_name', read_only=True)
    signataire_email = serializers.EmailField(source='signataire.email', read_only=True)  # AJOUTÉ
    module_display = serializers.CharField(source='get_module_source_display', read_only=True)
    type_display = serializers.CharField(source='get_type_signature_display', read_only=True)  # AJOUTÉ
    certificat_info = serializers.SerializerMethodField()
    date_signature_formatee = serializers.SerializerMethodField()  # AJOUTÉ
    verification_url = serializers.SerializerMethodField()  # AJOUTÉ
    
    class Meta:
        model = SignatureElectronique
        fields = '__all__'
        read_only_fields = ['id', 'timestamp_signature', 'horodatage']
    
    def get_certificat_info(self, obj):
        if obj.certificat_utilise:
            return {
                'numero_serie': obj.certificat_utilise.numero_serie,
                'date_emission': obj.certificat_utilise.date_emission.isoformat() if obj.certificat_utilise.date_emission else None,
                'date_emission_formatee': obj.certificat_utilise.date_emission.strftime('%d/%m/%Y') if obj.certificat_utilise.date_emission else None,
                'date_expiration': obj.certificat_utilise.date_expiration.isoformat() if obj.certificat_utilise.date_expiration else None,
                'date_expiration_formatee': obj.certificat_utilise.date_expiration.strftime('%d/%m/%Y') if obj.certificat_utilise.date_expiration else None,
                'niveau': obj.certificat_utilise.get_niveau_confiance_display(),
                'emetteur': obj.certificat_utilise.emetteur,
                'est_valide': obj.certificat_utilise.est_valide,
                'est_expire': obj.certificat_utilise.est_expire()
            }
        return None
    
    def get_date_signature_formatee(self, obj):
        return obj.timestamp_signature.strftime('%d/%m/%Y à %H:%M') if obj.timestamp_signature else None
    
    def get_verification_url(self, obj):
        return f"/api/signatures/verifier/{obj.id}/"
    
    def to_representation(self, instance):
        """Ajoute des métadonnées supplémentaires"""
        data = super().to_representation(instance)
        
        # Ajouter le hash du document (tronqué)
        if instance.document_hash:
            data['document_hash_truncated'] = instance.document_hash[:16] + '...'
        
        # Ajouter la taille du document
        if instance.document_contenu:
            data['document_taille'] = len(instance.document_contenu)
        
        return data


class DemandeSignatureSerializer(serializers.ModelSerializer):
    destinataire_email = serializers.EmailField(write_only=True, required=True)
    destinataire_nom = serializers.CharField(source='destinataire.get_full_name', read_only=True)
    destinataire_email_read = serializers.EmailField(source='destinataire.email', read_only=True)  # AJOUTÉ
    envoyeur_nom = serializers.CharField(source='envoyeur.get_full_name', read_only=True)  # AJOUTÉ
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    module_display = serializers.CharField(source='get_module_source_display', read_only=True)
    date_creation_formatee = serializers.SerializerMethodField()
    date_expiration_formatee = serializers.SerializerMethodField()
    url_signature = serializers.SerializerMethodField()  # AJOUTÉ
    est_expiree = serializers.SerializerMethodField()  # AJOUTÉ
    
    class Meta:
        model = DemandeSignature
        fields = [
            'id', 'module_source', 'module_display', 'source_id',
            'document_titre', 'document_contenu', 'destinataire_email',
            'destinataire', 'destinataire_nom', 'destinataire_email_read',
            'envoyeur', 'envoyeur_nom', 'message_personnalise',
            'statut', 'statut_display', 'token', 'date_creation',
            'date_creation_formatee', 'date_expiration', 'date_expiration_formatee',
            'date_signature', 'est_expiree', 'url_signature', 'nb_relances'
        ]
        read_only_fields = [
            'id', 'statut', 'token', 'date_creation', 'date_expiration',
            'destinataire', 'envoyeur', 'date_signature', 'signature'
        ]
    
    def get_date_creation_formatee(self, obj):
        return obj.date_creation.strftime('%d/%m/%Y à %H:%M') if obj.date_creation else None
    
    def get_date_expiration_formatee(self, obj):
        return obj.date_expiration.strftime('%d/%m/%Y') if obj.date_expiration else None
    
    def get_url_signature(self, obj):
        return f"/signature/signer?token={obj.token}"
    
    def get_est_expiree(self, obj):
        return obj.est_expiree()
    
    def validate_destinataire_email(self, value):
        """Vérifie que l'email existe dans le système"""
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(email=value).exists():
            raise serializers.ValidationError("Aucun utilisateur trouvé avec cet email")
        return value
    
    def validate_module_source(self, value):
        """Vérifie que le module source est valide"""
        valid_modules = ['etat_civil', 'archives', 'activites', 'dechets', 'deliberation', 'arrete', 'paiements', 'marche_public', 'contrat']
        if value not in valid_modules:
            raise serializers.ValidationError(f"Module source invalide. Choisir parmi: {', '.join(valid_modules)}")
        return value


class SignerDemandeSerializer(serializers.Serializer):
    """Serializer pour signer une demande via token"""
    token = serializers.CharField(max_length=100)
    signature_image = serializers.CharField(required=False, allow_blank=True, help_text="Image de signature en base64")
    niveau_signature = serializers.IntegerField(min_value=1, max_value=3, default=1)
    mot_de_passe = serializers.CharField(required=False, allow_blank=True, write_only=True)
    code_pin = serializers.CharField(required=False, allow_blank=True, max_length=6, write_only=True)
    raison_signature = serializers.CharField(required=False, allow_blank=True, max_length=255)  # AJOUTÉ
    
    def validate_token(self, value):
        """Vérifie que le token est valide"""
        try:
            demande = DemandeSignature.objects.get(token=value)
            if demande.statut != 'en_attente':
                raise serializers.ValidationError(f"Cette demande est déjà {demande.get_statut_display()}")
            if demande.est_expiree():
                raise serializers.ValidationError("Cette demande a expiré")
        except DemandeSignature.DoesNotExist:
            raise serializers.ValidationError("Token invalide")
        return value
    
    def validate(self, data):
        """Validation croisée"""
        niveau = data.get('niveau_signature', 1)
        
        # Pour les signatures avancées ou qualifiées, mot de passe requis
        if niveau >= 2 and not data.get('mot_de_passe') and not data.get('code_pin'):
            raise serializers.ValidationError({
                'mot_de_passe': 'Un mot de passe ou code PIN est requis pour ce niveau de signature'
            })
        
        return data


class VerifierSignatureSerializer(serializers.Serializer):
    """Serializer pour vérifier une signature"""
    signature_id = serializers.UUIDField()
    document = serializers.CharField(required=False, allow_blank=True, help_text="Contenu du document à vérifier")
    
    def validate_signature_id(self, value):
        """Vérifie que la signature existe"""
        if not SignatureElectronique.objects.filter(id=value).exists():
            raise serializers.ValidationError("Signature non trouvée")
        return value


class CreerCertificatSerializer(serializers.Serializer):
    """Serializer pour créer un certificat numérique"""
    mot_de_passe = serializers.CharField(min_length=8, max_length=128, write_only=True)
    confirmation_mot_de_passe = serializers.CharField(min_length=8, max_length=128, write_only=True)  # AJOUTÉ
    niveau_confiance = serializers.IntegerField(min_value=1, max_value=3, default=1)
    termes_acceptes = serializers.BooleanField(required=True)  # AJOUTÉ
    
    def validate_termes_acceptes(self, value):
        if not value:
            raise serializers.ValidationError("Vous devez accepter les conditions d'utilisation")
        return value
    
    def validate(self, data):
        if data['mot_de_passe'] != data.get('confirmation_mot_de_passe'):
            raise serializers.ValidationError({
                'confirmation_mot_de_passe': 'Les mots de passe ne correspondent pas'
            })
        return data


class ConfigurationSignatureSerializer(serializers.ModelSerializer):
    """Serializer pour la configuration du module signature"""
    
    class Meta:
        model = ConfigurationSignature
        fields = '__all__'
        read_only_fields = ['id']
    
    def validate_delai_validite_demande(self, value):
        if value < 1:
            raise serializers.ValidationError("Le délai doit être d'au moins 1 jour")
        if value > 30:
            raise serializers.ValidationError("Le délai ne peut pas dépasser 30 jours")
        return value


# AJOUTÉ: Serializer pour le journal des signatures
class JournalSignatureSerializer(serializers.ModelSerializer):
    """Serializer pour le journal d'audit des signatures"""
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    date_action_formatee = serializers.SerializerMethodField()
    signature_titre = serializers.CharField(source='signature.document_titre', read_only=True, allow_null=True)
    
    class Meta:
        model = JournalSignature
        fields = [
            'id', 'signature', 'signature_titre', 'action', 'action_display',
            'utilisateur', 'utilisateur_nom', 'commentaire',
            'date_action', 'date_action_formatee', 'adresse_ip'
        ]
        read_only_fields = ['id', 'date_action']
    
    def get_date_action_formatee(self, obj):
        return obj.date_action.strftime('%d/%m/%Y à %H:%M') if obj.date_action else None


# AJOUTÉ: Serializer pour les vérifications de signature
class VerificationSignatureSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des vérifications"""
    verificateur_nom = serializers.CharField(source='verificateur.get_full_name', read_only=True, allow_null=True)
    signature_titre = serializers.CharField(source='signature.document_titre', read_only=True)
    date_verification_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = VerificationSignature
        fields = [
            'id', 'signature', 'signature_titre', 'verificateur', 'verificateur_nom',
            'resultat', 'details', 'date_verification', 'date_verification_formatee'
        ]
        read_only_fields = ['id', 'date_verification']
    
    def get_date_verification_formatee(self, obj):
        return obj.date_verification.strftime('%d/%m/%Y à %H:%M') if obj.date_verification else None


# AJOUTÉ: Serializer pour les cachets électroniques
class CachetElectroniqueSerializer(serializers.ModelSerializer):
    """Serializer pour les cachets électroniques"""
    est_valide = serializers.SerializerMethodField()
    date_expiration_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = CachetElectronique
        fields = [
            'id', 'nom', 'description', 'image', 'est_actif', 'est_valide',
            'date_creation', 'date_expiration', 'date_expiration_formatee'
        ]
        read_only_fields = ['id', 'date_creation']
    
    def get_est_valide(self, obj):
        return obj.est_actif and obj.date_expiration > timezone.now() if obj.date_expiration else obj.est_actif
    
    def get_date_expiration_formatee(self, obj):
        return obj.date_expiration.strftime('%d/%m/%Y') if obj.date_expiration else None


# AJOUTÉ: Serializer pour les preuves de signature
class PreuveSignatureSerializer(serializers.ModelSerializer):
    """Serializer pour les preuves de signature"""
    signature_titre = serializers.CharField(source='signature.document_titre', read_only=True)
    horodatage_formate = serializers.SerializerMethodField()
    
    class Meta:
        model = PreuveSignature
        fields = [
            'id', 'signature', 'signature_titre', 'horodatage_externe',
            'horodatage_formate', 'empreinte_longue', 'preuve_conservation', 'date_creation'
        ]
        read_only_fields = ['id', 'date_creation']
    
    def get_horodatage_formate(self, obj):
        return obj.horodatage_externe.strftime('%d/%m/%Y à %H:%M:%S') if obj.horodatage_externe else None


# AJOUTÉ: Serializer pour les statistiques
class StatistiquesSignatureSerializer(serializers.Serializer):
    """Serializer pour les statistiques de signature"""
    total_signatures = serializers.IntegerField()
    signatures_jour = serializers.IntegerField()
    signatures_mois = serializers.IntegerField()
    par_module = serializers.DictField()
    par_type = serializers.DictField()
    taux_validite = serializers.FloatField()
    demandes_en_attente = serializers.IntegerField()
    certificats_actifs = serializers.IntegerField()


# AJOUTÉ: Serializer pour la relance
class RelanceSignatureSerializer(serializers.ModelSerializer):
    """Serializer pour les relances de signature"""
    demande_titre = serializers.CharField(source='demande.document_titre', read_only=True)
    canal_display = serializers.CharField(source='get_canal_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    date_relance_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = RelanceSignature
        fields = [
            'id', 'demande', 'demande_titre', 'date_relance', 'date_relance_formatee',
            'canal', 'canal_display', 'message', 'statut', 'statut_display'
        ]
        read_only_fields = ['id', 'date_relance']
    
    def get_date_relance_formatee(self, obj):
        return obj.date_relance.strftime('%d/%m/%Y à %H:%M') if obj.date_relance else None


# AJOUTÉ: Serializer pour la demande de signature côté destinataire
class SignerDemandePublicSerializer(serializers.Serializer):
    """Serializer public pour signer une demande (sans authentification)"""
    token = serializers.CharField(max_length=100)
    signature_image = serializers.CharField(required=False, allow_blank=True)
    nom_complet = serializers.CharField(max_length=200, required=False)  # AJOUTÉ
    email = serializers.EmailField(required=False)  # AJOUTÉ
    mot_de_passe = serializers.CharField(required=False, allow_blank=True, write_only=True)
    
    def validate_token(self, value):
        try:
            demande = DemandeSignature.objects.get(token=value)
            if demande.statut != 'en_attente':
                raise serializers.ValidationError(f"Cette demande est déjà {demande.get_statut_display()}")
            if demande.est_expiree():
                raise serializers.ValidationError("Cette demande a expiré")
        except DemandeSignature.DoesNotExist:
            raise serializers.ValidationError("Token invalide")
        return value


# AJOUTÉ: Serializer pour la révocation de certificat
class RevocationCertificatSerializer(serializers.Serializer):
    """Serializer pour la révocation d'un certificat"""
    certificat_id = serializers.UUIDField()
    motif = serializers.CharField(max_length=500, required=False, allow_blank=True)
    mot_de_passe = serializers.CharField(write_only=True, required=True)
    
    def validate_certificat_id(self, value):
        try:
            certificat = CertificatNumerique.objects.get(id=value)
            if certificat.est_revoque:
                raise serializers.ValidationError("Ce certificat est déjà révoqué")
        except CertificatNumerique.DoesNotExist:
            raise serializers.ValidationError("Certificat non trouvé")
        return value


# AJOUTÉ: Serializer pour l'export des signatures
class ExportSignatureSerializer(serializers.Serializer):
    """Serializer pour l'export des signatures"""
    date_debut = serializers.DateField(required=False)
    date_fin = serializers.DateField(required=False)
    module_source = serializers.CharField(required=False, allow_blank=True)
    format = serializers.ChoiceField(choices=['pdf', 'csv', 'json'], default='json')
    
    def validate(self, data):
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        
        if date_debut and date_fin and date_debut > date_fin:
            raise serializers.ValidationError({
                'date_fin': 'La date de fin doit être postérieure à la date de début'
            })
        
        return data