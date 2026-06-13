# dechets/serializers.py
from rest_framework import serializers
from .models import (
    Quartier, PointCollecte, CalendrierCollecte, Signalement,
    DemandeEncombrant, Tournee, TourneePoint, StatsCollecte
)

class QuartierSerializer(serializers.ModelSerializer):
    class Meta:
        model = Quartier
        fields = ['id', 'nom', 'slug', 'description', 'latitude', 'longitude', 'ordre']

class PointCollecteSerializer(serializers.ModelSerializer):
    quartier_nom = serializers.CharField(source='quartier.nom', read_only=True)
    
    class Meta:
        model = PointCollecte
        fields = '__all__'
        read_only_fields = ['code', 'signalements_count', 'collectes_count']

class CalendrierCollecteSerializer(serializers.ModelSerializer):
    jour_nom = serializers.SerializerMethodField()
    quartier_nom = serializers.CharField(source='quartier.nom', read_only=True)
    
    class Meta:
        model = CalendrierCollecte
        fields = '__all__'
    
    def get_jour_nom(self, obj):
        return obj.get_jour_semaine_display()

class SignalementListSerializer(serializers.ModelSerializer):
    type_icon = serializers.SerializerMethodField()
    quartier_nom = serializers.SerializerMethodField()
    
    class Meta:
        model = Signalement
        fields = ['id', 'type_signalement', 'type_icon', 'adresse_description', 
                  'quartier_nom', 'statut', 'photo', 'date_signalement']
    
    def get_type_icon(self, obj):
        icons = {
            'bac_plein': '🗑️', 'bac_debordant': '⚠️', 'bac_casse': '🔨',
            'depot_sauvage': '🚯', 'odeur': '👃', 'autre': '📌'
        }
        return icons.get(obj.type_signalement, '📌')
    
    def get_quartier_nom(self, obj):
        if obj.point_collecte:
            return obj.point_collecte.quartier.nom
        return "-"

class SignalementCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Signalement
        fields = ['type_signalement', 'point_collecte', 'description', 'photo',
                  'adresse_description', 'latitude', 'longitude', 'nom_citoyen', 'telephone']

class DemandeEncombrantSerializer(serializers.ModelSerializer):
    citoyen_nom = serializers.CharField(source='citoyen.get_full_name', read_only=True)
    
    class Meta:
        model = DemandeEncombrant
        fields = '__all__'
        read_only_fields = ['id', 'citoyen', 'statut', 'date_demande']

class DemandeEncombrantCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = DemandeEncombrant
        fields = ['type_encombrant', 'description', 'photo', 'adresse', 
                  'latitude', 'longitude', 'point_repere', 'date_souhaitee', 'creneau_horaire']

class TourneePointSerializer(serializers.ModelSerializer):
    point_nom = serializers.CharField(source='point.adresse_reference', read_only=True)
    point_code = serializers.CharField(source='point.code', read_only=True)
    
    class Meta:
        model = TourneePoint
        fields = ['id', 'ordre', 'point', 'point_nom', 'point_code', 
                  'est_vide', 'photo_preuve', 'heure_passage', 'commentaire']

class TourneeSerializer(serializers.ModelSerializer):
    quartier_nom = serializers.CharField(source='quartier.nom', read_only=True)
    agent_nom = serializers.CharField(source='agent.get_full_name', read_only=True)
    points = TourneePointSerializer(source='tourneepoint_set', many=True, read_only=True)
    
    class Meta:
        model = Tournee
        fields = '__all__'

class TourneeUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tournee
        fields = ['statut', 'debut_reel', 'fin_reelle']

class StatsCollecteSerializer(serializers.ModelSerializer):
    class Meta:
        model = StatsCollecte
        fields = '__all__'