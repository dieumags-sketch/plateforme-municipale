# backend/apps/etat_civil/serializers.py

from rest_framework import serializers
from .models import (
    Region, Departement, Arrondissement, DistrictSante,
    DemandeActe, ConfigurationTarif, HistoriqueStatut, NotificationActe,
    CertificatVie, CopieActe  # AJOUTÉS
)


# ============================================
# GÉOGRAPHIE
# ============================================

class RegionSerializer(serializers.ModelSerializer):
    """Serializer pour les régions du Cameroun"""
    class Meta:
        model = Region
        fields = ['id', 'nom', 'code', 'chef_lieu', 'population']  # AJOUTÉ chef_lieu, population
        read_only_fields = ['id']


class DepartementSerializer(serializers.ModelSerializer):
    """Serializer pour les départements"""
    region_nom = serializers.CharField(source='region.nom', read_only=True)
    
    class Meta:
        model = Departement
        fields = ['id', 'nom', 'code', 'region', 'region_nom', 'chef_lieu']  # AJOUTÉ chef_lieu
        read_only_fields = ['id']


class ArrondissementSerializer(serializers.ModelSerializer):
    """Serializer pour les arrondissements"""
    departement_nom = serializers.CharField(source='departement.nom', read_only=True)
    
    class Meta:
        model = Arrondissement
        fields = ['id', 'nom', 'code', 'departement', 'departement_nom', 'chef_lieu']  # AJOUTÉ chef_lieu
        read_only_fields = ['id']


class DistrictSanteSerializer(serializers.ModelSerializer):
    """Serializer pour les districts de santé"""
    arrondissement_nom = serializers.CharField(source='arrondissement.nom', read_only=True)
    
    class Meta:
        model = DistrictSante
        fields = ['id', 'nom', 'code', 'arrondissement', 'arrondissement_nom']
        read_only_fields = ['id']


# ============================================
# CONFIGURATION TARIFAIRE
# ============================================

class ConfigurationTarifSerializer(serializers.ModelSerializer):
    """Serializer pour les configurations tarifaires"""
    type_acte_display = serializers.CharField(source='get_type_acte_display', read_only=True)
    
    class Meta:
        model = ConfigurationTarif
        fields = '__all__'
        read_only_fields = ['date_modification']
    
    def validate(self, data):
        """Validation des tarifs"""
        if data.get('tarif_normal', 0) < 0:
            raise serializers.ValidationError({'tarif_normal': 'Le tarif normal ne peut pas être négatif'})
        if data.get('tarif_retard', 0) < 0:
            raise serializers.ValidationError({'tarif_retard': 'Le tarif de retard ne peut pas être négatif'})
        if data.get('delai_normal_jours', 0) <= 0:
            raise serializers.ValidationError({'delai_normal_jours': 'Le délai doit être supérieur à 0'})
        return data


# ============================================
# NOTIFICATIONS ET HISTORIQUE
# ============================================

class NotificationActeSerializer(serializers.ModelSerializer):
    """Serializer pour les notifications"""
    date_envoi_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationActe
        fields = ['id', 'titre', 'message', 'est_lue', 'date_envoi', 'date_envoi_formatee', 'date_lecture']
        read_only_fields = ['date_envoi']
    
    def get_date_envoi_formatee(self, obj):
        return obj.date_envoi.strftime('%d/%m/%Y à %H:%M') if obj.date_envoi else None


class HistoriqueStatutSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique des statuts"""
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    date_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = HistoriqueStatut
        fields = ['id', 'ancien_statut', 'nouveau_statut', 'commentaire', 
                  'utilisateur', 'utilisateur_nom', 'date', 'date_formatee']
        read_only_fields = ['date']
    
    def get_date_formatee(self, obj):
        return obj.date.strftime('%d/%m/%Y à %H:%M') if obj.date else None


# ============================================
# DEMANDE D'ACTE (LISTE ET DÉTAIL)
# ============================================

class DemandeActeListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste des demandes"""
    type_acte_display = serializers.CharField(source='get_type_acte_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    statut_couleur = serializers.SerializerMethodField()
    demandeur_nom = serializers.CharField(source='demandeur.get_full_name', read_only=True)
    tarif_calcule = serializers.SerializerMethodField()
    date_creation_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = DemandeActe
        fields = [
            'id', 'reference', 'type_acte', 'type_acte_display', 'statut', 
            'statut_display', 'statut_couleur', 'demandeur', 'demandeur_nom', 
            'tarif_calcule', 'date_creation', 'date_creation_formatee'
        ]
    
    def get_statut_couleur(self, obj):
        """Retourne la couleur associée au statut"""
        couleurs = {
            'brouillon': '#6c757d',
            'en_attente': '#f59e0b',
            'en_cours': '#3b82f6',
            'valide_agent': '#10b981',
            'valide_citoyen': '#8b5cf6',
            'signe': '#06b6d4',
            'rejete': '#ef4444',
            'delivre': '#10b981',
            'expire': '#dc2626'  # AJOUTÉ
        }
        return couleurs.get(obj.statut, '#6c757d')
    
    def get_tarif_calcule(self, obj):
        return float(obj.calculer_tarif())
    
    def get_date_creation_formatee(self, obj):
        return obj.date_creation.strftime('%d/%m/%Y') if obj.date_creation else None


class DemandeActeDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail d'une demande"""
    type_acte_display = serializers.CharField(source='get_type_acte_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    demandeur_nom = serializers.CharField(source='demandeur.get_full_name', read_only=True)
    demandeur_email = serializers.CharField(source='demandeur.email', read_only=True)
    demandeur_telephone = serializers.CharField(source='demandeur.telephone', read_only=True)  # AJOUTÉ
    agent_traitant_nom = serializers.SerializerMethodField()
    autorite_signataire_nom = serializers.SerializerMethodField()
    tarif_calcule = serializers.SerializerMethodField()
    tarif_calcule_formate = serializers.SerializerMethodField()  # AJOUTÉ
    pdf_url = serializers.SerializerMethodField()
    qr_code_url = serializers.SerializerMethodField()
    historique = serializers.SerializerMethodField()
    notifications = serializers.SerializerMethodField()
    
    # Dates formatées
    date_creation_formatee = serializers.SerializerMethodField()
    date_validation_agent_formatee = serializers.SerializerMethodField()
    date_validation_citoyen_formatee = serializers.SerializerMethodField()
    date_signature_formatee = serializers.SerializerMethodField()
    date_delivrance_formatee = serializers.SerializerMethodField()
    date_expiration_copie_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = DemandeActe
        fields = '__all__'
        read_only_fields = ['id', 'reference', 'date_creation', 'date_modification']
    
    def get_agent_traitant_nom(self, obj):
        if obj.agent_traitant:
            return obj.agent_traitant.get_full_name() or obj.agent_traitant.username
        return None
    
    def get_autorite_signataire_nom(self, obj):
        if obj.autorite_signataire:
            return obj.autorite_signataire.get_full_name() or obj.autorite_signataire.username
        return None
    
    def get_tarif_calcule(self, obj):
        return float(obj.calculer_tarif())
    
    def get_tarif_calcule_formate(self, obj):
        return f"{obj.calculer_tarif():,.0f} FCFA"
    
    def get_pdf_url(self, obj):
        if obj.fichier_pdf and hasattr(obj.fichier_pdf, 'url'):
            try:
                return obj.fichier_pdf.url
            except:
                return None
        return None
    
    def get_qr_code_url(self, obj):
        if obj.qr_code and hasattr(obj.qr_code, 'url'):
            try:
                return obj.qr_code.url
            except:
                return None
        return None
    
    def get_historique(self, obj):
        historique = obj.historique.all()
        return HistoriqueStatutSerializer(historique, many=True).data
    
    def get_notifications(self, obj):
        notifications = obj.notifications.all()[:10]
        return NotificationActeSerializer(notifications, many=True).data
    
    # Méthodes pour les dates formatées
    def get_date_creation_formatee(self, obj):
        return obj.date_creation.strftime('%d/%m/%Y à %H:%M') if obj.date_creation else None
    
    def get_date_validation_agent_formatee(self, obj):
        return obj.date_validation_agent.strftime('%d/%m/%Y à %H:%M') if obj.date_validation_agent else None
    
    def get_date_validation_citoyen_formatee(self, obj):
        return obj.date_validation_citoyen.strftime('%d/%m/%Y à %H:%M') if obj.date_validation_citoyen else None
    
    def get_date_signature_formatee(self, obj):
        return obj.date_signature.strftime('%d/%m/%Y à %H:%M') if obj.date_signature else None
    
    def get_date_delivrance_formatee(self, obj):
        return obj.date_delivrance.strftime('%d/%m/%Y à %H:%M') if obj.date_delivrance else None
    
    def get_date_expiration_copie_formatee(self, obj):
        return obj.date_expiration_copie.strftime('%d/%m/%Y') if obj.date_expiration_copie else None


class DemandeActeSerializer(serializers.ModelSerializer):
    """Serializer principal (adapte selon le contexte)"""
    
    def to_representation(self, instance):
        """Utilise un serializer différent selon le contexte"""
        request = self.context.get('request')
        if request and request.method == 'GET' and self.context.get('detail', False):
            return DemandeActeDetailSerializer(instance, context=self.context).data
        return super().to_representation(instance)
    
    class Meta:
        model = DemandeActe
        fields = [
            'id', 'reference', 'type_acte', 'statut', 'data_acte',
            'demandeur', 'agent_traitant', 'autorite_signataire',
            'tarif_applique', 'paiement_effectue', 'reference_paiement',
            'commentaire_rejet', 'date_creation', 'date_modification',
            'date_validation_agent', 'date_validation_citoyen',
            'date_signature', 'date_delivrance', 'date_expiration_copie'
        ]
        read_only_fields = ['id', 'reference', 'date_creation', 'date_modification']


# ============================================
# SÉRIALIZERS POUR LES FORMULAIRES DE DÉCLARATION
# ============================================

class BaseDeclarationSerializer(serializers.Serializer):
    """Serializer de base pour toutes les déclarations"""
    
    def validate(self, data):
        """Validation de base"""
        # Vérifier les champs requis
        required_fields = getattr(self, 'required_fields', [])
        for field in required_fields:
            if not data.get(field):
                raise serializers.ValidationError({field: 'Ce champ est requis'})
        return data


class DemandeNaissanceSerializer(BaseDeclarationSerializer):
    """Serializer pour la déclaration de naissance"""
    
    required_fields = ['region', 'departement', 'arrondissement', 'lieu_naissance',
                       'enfant_nom', 'enfant_prenom', 'enfant_date_naissance',
                       'enfant_sexe', 'mere_nom', 'mere_prenom', 'pere_nom', 'pere_prenom']
    
    # Section 1 - Géographique
    region = serializers.CharField(max_length=100)
    departement = serializers.CharField(max_length=100)
    arrondissement = serializers.CharField(max_length=100)
    district_sante = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    aire_sante = serializers.CharField(required=False, allow_blank=True)
    formation_sanitaire = serializers.CharField(required=False, allow_blank=True)
    lieu_naissance = serializers.CharField(max_length=200)
    
    # Section 2 - Enfant
    enfant_nom = serializers.CharField(max_length=100)
    enfant_prenom = serializers.CharField(max_length=100)
    enfant_date_naissance = serializers.DateField()
    enfant_sexe = serializers.ChoiceField(choices=['M', 'F'])
    enfant_type_naissance = serializers.CharField(required=False, allow_blank=True)
    enfant_rang = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    enfant_poids = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    enfant_taille = serializers.IntegerField(required=False, allow_null=True, min_value=20, max_value=100)
    enfant_assistant = serializers.ChoiceField(
        choices=['medecin', 'sage_femme', 'infirmiere', 'accouchement', 'aucune'],
        required=False, allow_null=True
    )
    
    # Section 3 - Mère
    mere_nom = serializers.CharField(max_length=100)
    mere_prenom = serializers.CharField(max_length=100)
    mere_date_naissance = serializers.DateField(required=False, allow_null=True)
    mere_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    mere_domicile = serializers.CharField(required=False, allow_blank=True)
    mere_duree_residence = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    mere_profession = serializers.CharField(required=False, allow_blank=True)
    mere_telephone1 = serializers.CharField(required=False, allow_blank=True)
    mere_telephone2 = serializers.CharField(required=False, allow_blank=True)
    mere_situation_matrimoniale = serializers.ChoiceField(
        choices=['celibataire', 'mariee', 'divorcee', 'veuve'],
        required=False, allow_null=True
    )
    mere_niveau_scolarite = serializers.ChoiceField(
        choices=['primaire', 'secondaire', 'superieur', 'sans'],
        required=False, allow_null=True
    )
    mere_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    mere_cni = serializers.CharField(required=False, allow_blank=True)
    mere_enfants_vivants = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    mere_deces_foetal = serializers.IntegerField(required=False, allow_null=True, min_value=0)
    mere_dernier_deces_vivant = serializers.DateField(required=False, allow_null=True)
    
    # Section 4 - Père
    pere_nom = serializers.CharField(max_length=100)
    pere_prenom = serializers.CharField(max_length=100)
    pere_date_naissance = serializers.DateField(required=False, allow_null=True)
    pere_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    pere_domicile = serializers.CharField(required=False, allow_blank=True)
    pere_profession = serializers.CharField(required=False, allow_blank=True)
    pere_telephone1 = serializers.CharField(required=False, allow_blank=True)
    pere_telephone2 = serializers.CharField(required=False, allow_blank=True)
    pere_niveau_scolarite = serializers.ChoiceField(
        choices=['primaire', 'secondaire', 'superieur', 'sans'],
        required=False, allow_null=True
    )
    pere_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    pere_cni = serializers.CharField(required=False, allow_blank=True)
    
    # Section 5 - Déclarant
    declarant_nom = serializers.CharField(max_length=100)
    declarant_prenom = serializers.CharField(max_length=100)
    declarant_qualite = serializers.CharField(max_length=100)
    declarant_telephone = serializers.CharField(required=False, allow_blank=True)
    declarant_attestation = serializers.BooleanField(default=False)
    declarant_signature = serializers.BooleanField(default=False)
    date_signature = serializers.DateField(required=False, allow_null=True)
    
    def validate_enfant_date_naissance(self, value):
        """Vérifie que la date de naissance n'est pas dans le futur"""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError('La date de naissance ne peut pas être dans le futur')
        return value


class DemandeMariageSerializer(BaseDeclarationSerializer):
    """Serializer pour la déclaration de mariage"""
    
    required_fields = ['epoux_nom', 'epoux_prenom', 'epoux_date_naissance',
                       'epouse_nom', 'epouse_prenom', 'epouse_date_naissance',
                       'date_mariage', 'lieu_mariage']
    
    # Époux
    epoux_nom = serializers.CharField(max_length=100)
    epoux_prenom = serializers.CharField(max_length=100)
    epoux_date_naissance = serializers.DateField()
    epoux_lieu_naissance = serializers.CharField(max_length=200)
    epoux_domicile = serializers.CharField(required=False, allow_blank=True)
    epoux_profession = serializers.CharField(required=False, allow_blank=True)
    epoux_telephone = serializers.CharField(required=False, allow_blank=True)
    epoux_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    epoux_cni = serializers.CharField(required=False, allow_blank=True)
    
    # Parents époux
    epoux_pere_nom = serializers.CharField(required=False, allow_blank=True)
    epoux_pere_prenom = serializers.CharField(required=False, allow_blank=True)
    epoux_mere_nom = serializers.CharField(required=False, allow_blank=True)
    epoux_mere_prenom = serializers.CharField(required=False, allow_blank=True)
    
    # Épouse
    epouse_nom = serializers.CharField(max_length=100)
    epouse_prenom = serializers.CharField(max_length=100)
    epouse_date_naissance = serializers.DateField()
    epouse_lieu_naissance = serializers.CharField(max_length=200)
    epouse_domicile = serializers.CharField(required=False, allow_blank=True)
    epouse_profession = serializers.CharField(required=False, allow_blank=True)
    epouse_telephone = serializers.CharField(required=False, allow_blank=True)
    epouse_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    epouse_cni = serializers.CharField(required=False, allow_blank=True)
    
    # Parents épouse
    epouse_pere_nom = serializers.CharField(required=False, allow_blank=True)
    epouse_pere_prenom = serializers.CharField(required=False, allow_blank=True)
    epouse_mere_nom = serializers.CharField(required=False, allow_blank=True)
    epouse_mere_prenom = serializers.CharField(required=False, allow_blank=True)
    
    # Mariage
    date_mariage = serializers.DateField()
    lieu_mariage = serializers.CharField(max_length=200)
    regime_matrimonial = serializers.CharField(required=False, allow_blank=True)
    
    # Témoins
    temoins = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    
    # Consentements
    consentement_epoux = serializers.BooleanField(default=True)
    consentement_epouse = serializers.BooleanField(default=True)
    consentement_parents_epoux = serializers.BooleanField(default=False)
    consentement_parents_epouse = serializers.BooleanField(default=False)
    
    def validate_date_mariage(self, value):
        """Vérifie que la date de mariage n'est pas dans le futur"""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError('La date de mariage ne peut pas être dans le futur')
        return value


class DemandeDecesSerializer(BaseDeclarationSerializer):
    """Serializer pour la déclaration de décès"""
    
    required_fields = ['defunt_nom', 'defunt_prenom', 'date_deces', 'lieu_deces',
                       'declarant_nom', 'declarant_prenom']
    
    # Défunt
    defunt_nom = serializers.CharField(max_length=100)
    defunt_prenom = serializers.CharField(max_length=100)
    defunt_date_naissance = serializers.DateField(required=False, allow_null=True)
    defunt_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    defunt_domicile = serializers.CharField(required=False, allow_blank=True)
    defunt_profession = serializers.CharField(required=False, allow_blank=True)
    defunt_sexe = serializers.ChoiceField(choices=['M', 'F'], required=False, allow_null=True)
    defunt_pere_nom = serializers.CharField(required=False, allow_blank=True)
    defunt_mere_nom = serializers.CharField(required=False, allow_blank=True)
    defunt_conjoint_nom = serializers.CharField(required=False, allow_blank=True)
    
    # Décès
    date_deces = serializers.DateField()
    heure_deces = serializers.TimeField(required=False, allow_null=True)
    lieu_deces = serializers.CharField(max_length=200)
    cause_deces = serializers.CharField(required=False, allow_blank=True)
    cause_precise = serializers.CharField(required=False, allow_blank=True)
    
    # Certificat médical
    certificat_medical = serializers.BooleanField(default=False)
    medecin_nom = serializers.CharField(required=False, allow_blank=True)
    medecin_titre = serializers.CharField(required=False, allow_blank=True)
    
    # Déclarant
    declarant_nom = serializers.CharField(max_length=100)
    declarant_prenom = serializers.CharField(max_length=100)
    declarant_qualite = serializers.CharField(max_length=100, required=False, allow_blank=True)
    declarant_domicile = serializers.CharField(required=False, allow_blank=True)
    declarant_telephone = serializers.CharField(required=False, allow_blank=True)
    
    def validate_date_deces(self, value):
        """Vérifie que la date de décès n'est pas dans le futur"""
        from django.utils import timezone
        if value > timezone.now().date():
            raise serializers.ValidationError('La date de décès ne peut pas être dans le futur')
        return value


class DemandeReconnaissanceSerializer(BaseDeclarationSerializer):
    """Serializer pour la reconnaissance d'enfant"""
    
    required_fields = ['enfant_nom', 'enfant_prenom', 'enfant_date_naissance',
                       'parent_nom', 'parent_prenom']
    
    # Enfant
    enfant_nom = serializers.CharField(max_length=100)
    enfant_prenom = serializers.CharField(max_length=100)
    enfant_date_naissance = serializers.DateField()
    enfant_lieu_naissance = serializers.CharField(max_length=200)
    enfant_sexe = serializers.ChoiceField(choices=['M', 'F'], required=False, allow_null=True)
    enfant_mere_nom = serializers.CharField(required=False, allow_blank=True)
    enfant_mere_prenom = serializers.CharField(required=False, allow_blank=True)
    
    # Parent reconnaissant
    parent_nom = serializers.CharField(max_length=100)
    parent_prenom = serializers.CharField(max_length=100)
    parent_date_naissance = serializers.DateField(required=False, allow_null=True)
    parent_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    parent_domicile = serializers.CharField(required=False, allow_blank=True)
    parent_profession = serializers.CharField(required=False, allow_blank=True)
    parent_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    parent_cni = serializers.CharField(required=False, allow_blank=True)
    parent_telephone = serializers.CharField(required=False, allow_blank=True)
    
    # Reconnaissance
    date_reconnaissance = serializers.DateField(required=False, allow_null=True)
    lieu_reconnaissance = serializers.CharField(required=False, allow_blank=True)
    type_reconnaissance = serializers.ChoiceField(
        choices=['paternite', 'maternite', 'simple'],
        required=False, allow_null=True
    )
    
    # Témoins
    temoins = serializers.ListField(child=serializers.CharField(), required=False, default=list)


class DemandeAdoptionSerializer(BaseDeclarationSerializer):
    """Serializer pour la demande d'adoption"""
    
    required_fields = ['enfant_nom_original', 'enfant_prenom_original',
                       'adoptant1_nom', 'adoptant1_prenom',
                       'jugement_date', 'jugement_tribunal', 'jugement_numero']
    
    # Enfant
    enfant_nom_original = serializers.CharField(max_length=100)
    enfant_prenom_original = serializers.CharField(max_length=100)
    enfant_nouveau_nom = serializers.CharField(required=False, allow_blank=True)
    enfant_nouveau_prenom = serializers.CharField(required=False, allow_blank=True)
    enfant_date_naissance = serializers.DateField(required=False, allow_null=True)
    enfant_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    enfant_sexe = serializers.ChoiceField(choices=['M', 'F'], required=False, allow_null=True)
    enfant_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    
    # Parents biologiques
    parent_biologique_pere_nom = serializers.CharField(required=False, allow_blank=True)
    parent_biologique_mere_nom = serializers.CharField(required=False, allow_blank=True)
    
    # Adoptant(s)
    type_adoption = serializers.ChoiceField(
        choices=['pleniere', 'simple', 'conjointe', 'individuelle'],
        required=False, allow_null=True
    )
    adoptant1_nom = serializers.CharField(max_length=100)
    adoptant1_prenom = serializers.CharField(max_length=100)
    adoptant1_date_naissance = serializers.DateField(required=False, allow_null=True)
    adoptant1_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    adoptant1_profession = serializers.CharField(required=False, allow_blank=True)
    adoptant1_domicile = serializers.CharField(required=False, allow_blank=True)
    adoptant1_nationalite = serializers.CharField(default='Camerounaise', max_length=50)
    adoptant1_cni = serializers.CharField(required=False, allow_blank=True)
    
    adoptant2_nom = serializers.CharField(required=False, allow_blank=True)
    adoptant2_prenom = serializers.CharField(required=False, allow_blank=True)
    adoptant2_date_naissance = serializers.DateField(required=False, allow_null=True)
    adoptant2_lieu_naissance = serializers.CharField(required=False, allow_blank=True)
    
    # Jugement
    jugement_date = serializers.DateField()
    jugement_tribunal = serializers.CharField(max_length=200)
    jugement_numero = serializers.CharField(max_length=100)
    
    # Consentements
    consentement_enfant = serializers.BooleanField(default=False)
    consentement_parents_biologiques = serializers.BooleanField(default=False)


# ============================================
# SÉRIALIZERS POUR LES ACTIONS API
# ============================================

class ValidationCitoyenSerializer(serializers.Serializer):
    """Serializer pour la validation par le citoyen"""
    valide = serializers.BooleanField()
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=500)


class TraitementAgentSerializer(serializers.Serializer):
    """Serializer pour le traitement par l'agent"""
    action = serializers.ChoiceField(choices=['valider', 'rejeter', 'en_cours'])
    commentaire = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate(self, data):
        """Validation selon l'action"""
        if data.get('action') == 'rejeter' and not data.get('commentaire'):
            raise serializers.ValidationError({
                'commentaire': 'Un commentaire est requis pour rejeter une demande'
            })
        return data


class SignatureSerializer(serializers.Serializer):
    """Serializer pour la signature électronique"""
    signature = serializers.CharField(required=True)  # Base64 de la signature
    date_signature = serializers.DateTimeField(required=True)
    position_x = serializers.IntegerField(default=0)
    position_y = serializers.IntegerField(default=0)
    largeur = serializers.IntegerField(default=200)  # AJOUTÉ
    hauteur = serializers.IntegerField(default=80)  # AJOUTÉ


class RelanceSerializer(serializers.Serializer):
    """Serializer pour la relance d'une demande"""
    message = serializers.CharField(required=False, allow_blank=True, max_length=500)
    type_relance = serializers.ChoiceField(
        choices=['email', 'sms', 'both'],
        default='email'
    )


class RechercheSerializer(serializers.Serializer):
    """Serializer pour la recherche avancée"""
    q = serializers.CharField(required=False, allow_blank=True, max_length=200)
    type_acte = serializers.ChoiceField(choices=DemandeActe.TYPE_ACTES, required=False, allow_blank=True)
    statut = serializers.ChoiceField(choices=DemandeActe.STATUTS, required=False, allow_blank=True)
    date_debut = serializers.DateField(required=False, allow_null=True)
    date_fin = serializers.DateField(required=False, allow_null=True)
    page = serializers.IntegerField(default=1, min_value=1)
    page_size = serializers.IntegerField(default=10, min_value=1, max_value=100)
    
    def validate(self, data):
        """Validation des dates"""
        date_debut = data.get('date_debut')
        date_fin = data.get('date_fin')
        
        if date_debut and date_fin and date_debut > date_fin:
            raise serializers.ValidationError({
                'date_debut': 'La date de début doit être antérieure à la date de fin'
            })
        
        return data


# ============================================
# SÉRIALIZERS AJOUTÉS
# ============================================

class CertificatVieSerializer(serializers.ModelSerializer):
    """Serializer pour les certificats de vie"""
    beneficiaire_nom = serializers.CharField(source='beneficiaire', read_only=True)
    date_validite_formatee = serializers.SerializerMethodField()
    est_valide = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = CertificatVie
        fields = '__all__'
        read_only_fields = ['id', 'date_creation']
    
    def get_date_validite_formatee(self, obj):
        return obj.date_validite.strftime('%d/%m/%Y') if obj.date_validite else None


class CopieActeSerializer(serializers.ModelSerializer):
    """Serializer pour les copies d'actes"""
    motif_court = serializers.CharField(source='motif', read_only=True)
    
    class Meta:
        model = CopieActe
        fields = '__all__'
        read_only_fields = ['id', 'date_demande']


# ============================================
# SERIALIZER POUR LES STATISTIQUES
# ============================================

class StatistiquesEtatCivilSerializer(serializers.Serializer):
    """Serializer pour les statistiques de l'état civil"""
    total_demandes = serializers.IntegerField()
    par_type = serializers.DictField()
    par_statut = serializers.DictField()
    par_mois = serializers.ListField()
    tarif_moyen = serializers.DecimalField(max_digits=10, decimal_places=2)
    delai_moyen_traitement = serializers.FloatField()
    taux_satisfaction = serializers.FloatField(required=False, allow_null=True)