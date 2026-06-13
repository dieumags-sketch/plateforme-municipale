# backend/apps/paiements/serializers.py

from rest_framework import serializers
from .models import (
    ConfigurationPaiement, TransactionPaiement, PortefeuilleCitoyen,
    RecuPaiement, JournalPaiement, TransactionPortefeuille,
    FactureRecurrente, Remboursement, WebhookPaiement  # AJOUTÉS
)


class ConfigurationPaiementSerializer(serializers.ModelSerializer):
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    
    # AJOUTÉ: Validation du pourcentage
    frais_pourcentage = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
    taxe = serializers.DecimalField(max_digits=5, decimal_places=2, min_value=0, max_value=100)
    
    class Meta:
        model = ConfigurationPaiement
        fields = '__all__'
        read_only_fields = ['id', 'date_modification']  # AJOUTÉ
    
    def validate(self, data):
        """Validation croisée"""
        # Vérifier que montant_min <= montant_max
        if data.get('montant_min', 0) > data.get('montant_max', 0):
            raise serializers.ValidationError({
                'montant_min': 'Le montant minimum ne peut pas être supérieur au montant maximum'
            })
        
        # Pour Mobile Money, vérifier les champs requis
        mode = data.get('mode')
        if mode in ['mtn', 'orange']:
            if not data.get('api_url'):
                raise serializers.ValidationError({
                    'api_url': 'L\'URL API est requise pour les paiements Mobile Money'
                })
            if not data.get('merchant_code'):
                raise serializers.ValidationError({
                    'merchant_code': 'Le code marchand est requis pour les paiements Mobile Money'
                })
        
        # Pour virement, vérifier les coordonnées bancaires
        if mode == 'virement':
            if not data.get('iban') and not data.get('rib'):
                raise serializers.ValidationError({
                    'iban': 'L\'IBAN ou le RIB est requis pour les virements bancaires'
                })
        
        return data


class TransactionPaiementListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste"""
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    utilisateur_nom = serializers.SerializerMethodField()  # CORRIGÉ: utilisateur_nom
    statut_couleur = serializers.SerializerMethodField()
    montant_total_formate = serializers.SerializerMethodField()  # AJOUTÉ
    
    class Meta:
        model = TransactionPaiement
        fields = [
            'id', 'reference', 'montant_total', 'montant_total_formate',
            'mode', 'mode_display', 'statut', 'statut_display', 
            'statut_couleur', 'utilisateur_nom', 'date_creation', 'module_source'
        ]
    
    def get_utilisateur_nom(self, obj):
        """Récupère le nom complet de l'utilisateur"""
        if obj.utilisateur:
            return obj.utilisateur.get_full_name() or obj.utilisateur.username
        return "Utilisateur inconnu"
    
    def get_statut_couleur(self, obj):
        couleurs = {
            'initie': '#f59e0b',      # Orange
            'en_attente': '#3b82f6',   # Bleu
            'confirme': '#10b981',     # Vert
            'echoue': '#ef4444',       # Rouge
            'annule': '#6c757d',       # Gris
            'rembourse': '#8b5cf6',    # Violet
            'expire': '#dc2626'        # Rouge foncé (AJOUTÉ)
        }
        return couleurs.get(obj.statut, '#6c757d')
    
    def get_montant_total_formate(self, obj):
        """Formatage du montant avec séparateur de milliers"""
        return f"{obj.montant_total:,.0f} FCFA"


class TransactionPaiementDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail"""
    mode_display = serializers.CharField(source='get_mode_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    utilisateur_nom = serializers.SerializerMethodField()
    utilisateur_email = serializers.EmailField(source='utilisateur.email', read_only=True)  # AJOUTÉ
    utilisateur_telephone = serializers.CharField(source='utilisateur.telephone', read_only=True)  # AJOUTÉ
    recu_url = serializers.SerializerMethodField()
    logs = serializers.SerializerMethodField()
    peut_etre_annulee = serializers.BooleanField(read_only=True)  # AJOUTÉ
    est_expiree = serializers.BooleanField(read_only=True)  # AJOUTÉ
    
    class Meta:
        model = TransactionPaiement
        fields = '__all__'
        read_only_fields = ['reference', 'date_creation', 'id']
    
    def get_utilisateur_nom(self, obj):
        if obj.utilisateur:
            return obj.utilisateur.get_full_name() or obj.utilisateur.username
        return "Utilisateur inconnu"
    
    def get_recu_url(self, obj):
        if hasattr(obj, 'recu') and obj.recu and obj.recu.fichier_pdf:
            try:
                return obj.recu.fichier_pdf.url
            except:
                return None
        return None
    
    def get_logs(self, obj):
        logs = obj.logs.all()[:20]
        return [
            {
                'action': log.action,
                'message': log.message,
                'ancien_statut': log.ancien_statut,
                'nouveau_statut': log.nouveau_statut,
                'date_action': log.date_action.isoformat() if log.date_action else None,
                'date_action_formatee': log.date_action.strftime('%d/%m/%Y %H:%M') if log.date_action else None
            }
            for log in logs
        ]
    
    def to_representation(self, instance):
        """Ajoute des informations supplémentaires"""
        data = super().to_representation(instance)
        
        # Ajouter des métadonnées calculées
        data['peut_etre_annulee'] = instance.peut_etre_annulee()
        data['est_expiree'] = instance.est_expiree()
        
        # Formater les montants
        data['montant_net_formate'] = f"{instance.montant_net:,.0f} FCFA"
        data['frais_formate'] = f"{instance.frais:,.0f} FCFA"
        data['taxe_formate'] = f"{instance.taxe:,.0f} FCFA"
        data['montant_total_formate'] = f"{instance.montant_total:,.0f} FCFA"
        
        # Formater les dates
        if instance.date_creation:
            data['date_creation_formatee'] = instance.date_creation.strftime('%d/%m/%Y à %H:%M')
        if instance.date_confirmation:
            data['date_confirmation_formatee'] = instance.date_confirmation.strftime('%d/%m/%Y à %H:%M')
        if instance.date_expiration:
            data['date_expiration_formatee'] = instance.date_expiration.strftime('%d/%m/%Y à %H:%M')
        
        return data


class InitierPaiementSerializer(serializers.Serializer):
    """Serializer pour initier un paiement"""
    montant = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=1,
        error_messages={
            'min_value': 'Le montant minimum est de 1 FCFA',
            'invalid': 'Veuillez entrer un montant valide'
        }
    )
    mode = serializers.ChoiceField(choices=TransactionPaiement.MODES)
    telephone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    module_source = serializers.ChoiceField(choices=TransactionPaiement.MODULES_SOURCE)
    source_id = serializers.CharField(required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True, max_length=500)
    
    def validate(self, data):
        """Validation croisée"""
        mode = data.get('mode')
        telephone = data.get('telephone')
        
        # Pour Mobile Money, le téléphone est requis
        if mode in ['mtn', 'orange']:
            if not telephone:
                raise serializers.ValidationError({
                    'telephone': 'Le numéro de téléphone est requis pour le paiement Mobile Money'
                })
            
            # Validation simple du numéro (à adapter selon le Cameroun)
            if len(telephone) < 9:
                raise serializers.ValidationError({
                    'telephone': 'Numéro de téléphone invalide'
                })
        
        # Vérifier le montant par rapport à la configuration
        try:
            config = ConfigurationPaiement.objects.get(mode=mode, est_actif=True)
            if data['montant'] < config.montant_min:
                raise serializers.ValidationError({
                    'montant': f'Le montant minimum pour ce mode de paiement est de {config.montant_min:,.0f} FCFA'
                })
            if data['montant'] > config.montant_max:
                raise serializers.ValidationError({
                    'montant': f'Le montant maximum pour ce mode de paiement est de {config.montant_max:,.0f} FCFA'
                })
        except ConfigurationPaiement.DoesNotExist:
            pass
        
        return data


class ConfirmerPaiementSerializer(serializers.Serializer):
    """Serializer pour confirmer un paiement"""
    reference = serializers.CharField(max_length=100)
    code = serializers.CharField(max_length=10, required=False, allow_blank=True)
    preuve_virement = serializers.FileField(required=False)
    
    def validate(self, data):
        """Validation croisée"""
        reference = data.get('reference')
        code = data.get('code')
        preuve = data.get('preuve_virement')
        
        # Vérifier que la transaction existe
        try:
            transaction = TransactionPaiement.objects.get(reference=reference)
        except TransactionPaiement.DoesNotExist:
            raise serializers.ValidationError({
                'reference': 'Transaction non trouvée'
            })
        
        # Vérifier les champs requis selon le mode
        if transaction.mode in ['mtn', 'orange']:
            if not code:
                raise serializers.ValidationError({
                    'code': 'Le code de validation est requis pour le paiement Mobile Money'
                })
        
        if transaction.mode == 'virement':
            if not preuve and not transaction.preuve_virement:
                raise serializers.ValidationError({
                    'preuve_virement': 'La preuve de virement est requise'
                })
        
        # Vérifier que la transaction n'est pas déjà confirmée
        if transaction.statut == 'confirme':
            raise serializers.ValidationError({
                'reference': 'Cette transaction a déjà été confirmée'
            })
        
        # Vérifier que la transaction n'est pas expirée
        if transaction.est_expiree():
            raise serializers.ValidationError({
                'reference': 'Cette transaction a expiré'
            })
        
        return data


class RemboursementSerializer(serializers.Serializer):
    """Serializer pour le remboursement"""
    reference = serializers.CharField(max_length=100)
    motif = serializers.CharField(max_length=500)
    
    def validate_reference(self, value):
        """Valide que la transaction existe et peut être remboursée"""
        try:
            transaction = TransactionPaiement.objects.get(reference=value)
        except TransactionPaiement.DoesNotExist:
            raise serializers.ValidationError('Transaction non trouvée')
        
        if transaction.statut != 'confirme':
            raise serializers.ValidationError('Seules les transactions confirmées peuvent être remboursées')
        
        if not transaction.peut_etre_rembourse():
            raise serializers.ValidationError('Le délai de remboursement est dépassé (14 jours max)')
        
        return value


class PortefeuilleSerializer(serializers.ModelSerializer):
    """Serializer pour le portefeuille citoyen"""
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    solde_formate = serializers.SerializerMethodField()
    plafond_formate = serializers.SerializerMethodField()
    
    class Meta:
        model = PortefeuilleCitoyen
        fields = [
            'id', 'solde', 'solde_formate', 'points_fidelite',
            'plafond', 'plafond_formate', 'est_active',
            'utilisateur_nom', 'date_derniere_mise_a_jour'
        ]
        read_only_fields = ['id', 'points_fidelite', 'date_derniere_mise_a_jour']
    
    def get_solde_formate(self, obj):
        return f"{obj.solde:,.0f} FCFA"
    
    def get_plafond_formate(self, obj):
        return f"{obj.plafond:,.0f} FCFA"


class RechargerPortefeuilleSerializer(serializers.Serializer):
    """Serializer pour recharger le portefeuille"""
    montant = serializers.DecimalField(
        max_digits=10, 
        decimal_places=2,
        min_value=100,
        max_value=500000,
        error_messages={
            'min_value': 'Le montant minimum de recharge est de 100 FCFA',
            'max_value': 'Le montant maximum de recharge est de 500 000 FCFA'
        }
    )
    mode = serializers.ChoiceField(choices=TransactionPaiement.MODES)
    telephone = serializers.CharField(max_length=20, required=False, allow_blank=True)
    
    def validate(self, data):
        mode = data.get('mode')
        telephone = data.get('telephone')
        
        # Pour Mobile Money, téléphone requis
        if mode in ['mtn', 'orange'] and not telephone:
            raise serializers.ValidationError({
                'telephone': 'Le numéro de téléphone est requis pour ce mode de paiement'
            })
        
        return data


# AJOUTÉ: Serializer pour les transactions du portefeuille
class TransactionPortefeuilleSerializer(serializers.ModelSerializer):
    """Serializer pour l'historique du portefeuille"""
    type_display = serializers.CharField(source='get_type_transaction_display', read_only=True)
    categorie_display = serializers.CharField(source='get_categorie_display', read_only=True)
    montant_formate = serializers.SerializerMethodField()
    date_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = TransactionPortefeuille
        fields = [
            'id', 'montant', 'montant_formate', 'type_transaction', 'type_display',
            'categorie', 'categorie_display', 'description', 'solde_apres',
            'date_creation', 'date_formatee'
        ]
    
    def get_montant_formate(self, obj):
        return f"{obj.montant:,.0f} FCFA"
    
    def get_date_formatee(self, obj):
        return obj.date_creation.strftime('%d/%m/%Y à %H:%M')


# AJOUTÉ: Serializer pour les factures récurrentes
class FactureRecurrenteSerializer(serializers.ModelSerializer):
    """Serializer pour les factures récurrentes"""
    periode_display = serializers.CharField(source='get_periode_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    montant_formate = serializers.SerializerMethodField()
    prochaine_echeance_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = FactureRecurrente
        fields = [
            'id', 'libelle', 'montant', 'montant_formate', 'periode', 'periode_display',
            'jour_echeance', 'prochaine_echeance', 'prochaine_echeance_formatee',
            'statut', 'statut_display', 'dernier_paiement', 'date_creation'
        ]
        read_only_fields = ['id', 'date_creation']
    
    def get_montant_formate(self, obj):
        return f"{obj.montant:,.0f} FCFA"
    
    def get_prochaine_echeance_formatee(self, obj):
        return obj.prochaine_echeance.strftime('%d/%m/%Y') if obj.prochaine_echeance else None


# AJOUTÉ: Serializer pour les remboursements
class RemboursementSerializer(serializers.ModelSerializer):
    """Serializer pour les demandes de remboursement"""
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    montant_formate = serializers.SerializerMethodField()
    date_demande_formatee = serializers.SerializerMethodField()
    transaction_reference = serializers.CharField(source='transaction.reference', read_only=True)
    
    class Meta:
        model = Remboursement
        fields = [
            'id', 'transaction', 'transaction_reference', 'motif', 'montant_rembourse',
            'montant_formate', 'statut', 'statut_display', 'commentaire_moderation',
            'date_demande', 'date_demande_formatee', 'date_traitement', 'traite_par'
        ]
        read_only_fields = ['id', 'date_demande']
    
    def get_montant_formate(self, obj):
        return f"{obj.montant_rembourse:,.0f} FCFA"
    
    def get_date_demande_formatee(self, obj):
        return obj.date_demande.strftime('%d/%m/%Y à %H:%M') if obj.date_demande else None


# AJOUTÉ: Serializer pour les webhooks
class WebhookPaiementSerializer(serializers.ModelSerializer):
    """Serializer pour la configuration des webhooks"""
    evenement_display = serializers.CharField(source='get_evenement_display', read_only=True)
    
    class Meta:
        model = WebhookPaiement
        fields = '__all__'
        read_only_fields = ['id', 'tentative_compteur', 'dernier_envoi', 'date_creation']
    
    def validate_url(self, value):
        """Valide que l'URL est HTTPS en production"""
        import sys
        if not sys.argv[1:2] == ['runserver'] and not value.startswith('https://'):
            raise serializers.ValidationError('L\'URL doit utiliser HTTPS en production')
        return value


# AJOUTÉ: Serializer pour les recus
class RecuPaiementSerializer(serializers.ModelSerializer):
    """Serializer pour les reçus de paiement"""
    transaction_reference = serializers.CharField(source='transaction.reference', read_only=True)
    transaction_montant = serializers.DecimalField(source='transaction.montant_total', read_only=True, max_digits=10, decimal_places=2)
    
    class Meta:
        model = RecuPaiement
        fields = ['id', 'numero_recu', 'fichier_pdf', 'qr_code', 'date_generation',
                  'transaction_reference', 'transaction_montant']


# AJOUTÉ: Serializer pour les statistiques
class StatistiquesPaiementSerializer(serializers.Serializer):
    """Serializer pour les statistiques de paiement"""
    total_transactions = serializers.IntegerField()
    total_montant = serializers.DecimalField(max_digits=15, decimal_places=2)
    total_confirmees = serializers.IntegerField()
    taux_succes = serializers.FloatField()
    par_mode = serializers.DictField()
    par_statut = serializers.DictField()
    par_jour = serializers.ListField()
    
    def to_representation(self, instance):
        """Formate les montants"""
        data = super().to_representation(instance)
        if data.get('total_montant'):
            data['total_montant_formate'] = f"{data['total_montant']:,.0f} FCFA"
        return data
    
class UtiliserPortefeuilleSerializer(serializers.Serializer):
    montant = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=1)
    module_source = serializers.CharField(max_length=50)
    source_id = serializers.CharField(max_length=100, required=False, allow_blank=True)    