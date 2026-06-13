# backend/archives/serializers.py

from rest_framework import serializers
from .models import *

class CategorieArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieArchive
        fields = ['id', 'nom', 'slug', 'couleur', 'icone']

class ArchiveListSerializer(serializers.ModelSerializer):
    """Serializer léger pour la liste"""
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_couleur = serializers.CharField(source='categorie.couleur', read_only=True)
    categorie_icone = serializers.CharField(source='categorie.icone', read_only=True)
    
    class Meta:
        model = Archive
        fields = ['id', 'titre', 'reference', 'categorie_nom', 'categorie_couleur',
                  'categorie_icone', 'date_document', 'niveau_acces', 'statut', 
                  'vues', 'tarif_consultation', 'vignette']

class ArchiveDetailSerializer(serializers.ModelSerializer):
    """Serializer complet pour le détail"""
    categorie = CategorieArchiveSerializer(read_only=True)
    est_accesible = serializers.SerializerMethodField()
    tarifs = serializers.SerializerMethodField()
    
    class Meta:
        model = Archive
        fields = '__all__'
    
    def get_est_accesible(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            if obj.niveau_acces == 'public':
                return True
            return request.user.is_staff
        return obj.niveau_acces == 'public'
    
    def get_tarifs(self, obj):
        return {
            'consultation': float(obj.tarif_consultation),
            'copie': float(obj.tarif_copie),
            'impression': float(obj.tarif_impression),
            'envoi': float(obj.tarif_envoi)
        }

class DemandeAccesArchiveSerializer(serializers.ModelSerializer):
    archive_titre = serializers.CharField(source='archive.titre', read_only=True)
    archive_reference = serializers.CharField(source='archive.reference', read_only=True)
    demandeur_nom = serializers.CharField(source='demandeur.get_full_name', read_only=True)
    montant_calcule = serializers.SerializerMethodField()
    
    class Meta:
        model = DemandeAccesArchive
        fields = ['id', 'archive', 'archive_titre', 'archive_reference', 'type_demande',
                  'motif', 'statut', 'montant_total', 'montant_calcule', 'date_demande',
                  'demandeur', 'demandeur_nom', 'commentaire_moderation', 'adresse_livraison']
        read_only_fields = ['statut', 'montant_total', 'date_demande']
    
    def get_montant_calcule(self, obj):
        return float(obj.calculer_montant())

class InitierDemandeArchiveSerializer(serializers.Serializer):
    archive_id = serializers.UUIDField()
    type_demande = serializers.ChoiceField(choices=DemandeAccesArchive.TYPES)
    motif = serializers.CharField()
    adresse_livraison = serializers.CharField(required=False)
    justificatif = serializers.CharField(required=False)

class RechercheArchiveSerializer(serializers.Serializer):
    q = serializers.CharField(required=False, allow_blank=True)
    categorie = serializers.CharField(required=False)
    annee_debut = serializers.IntegerField(required=False, min_value=1900, max_value=2030)
    annee_fin = serializers.IntegerField(required=False, min_value=1900, max_value=2030)
    niveau_acces = serializers.CharField(required=False)