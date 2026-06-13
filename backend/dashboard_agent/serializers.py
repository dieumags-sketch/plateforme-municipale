# dashboard_agent/serializers.py
from rest_framework import serializers
from .models import TacheAgent, NotificationAgent

class TacheAgentSerializer(serializers.ModelSerializer):
    type_display = serializers.CharField(source='get_type_tache_display', read_only=True)
    priorite_display = serializers.CharField(source='get_priorite_display', read_only=True)
    statut_display = serializers.CharField(source='get_statut_display', read_only=True)
    assigne_nom = serializers.CharField(source='assigne_a.get_full_name', read_only=True)
    date_echeance_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = TacheAgent
        fields = '__all__'
        read_only_fields = ['id', 'date_creation']
    
    def get_date_echeance_formatee(self, obj):
        return obj.date_echeance.strftime('%d/%m/%Y %H:%M') if obj.date_echeance else None


class NotificationAgentSerializer(serializers.ModelSerializer):
    date_formatee = serializers.SerializerMethodField()
    
    class Meta:
        model = NotificationAgent
        fields = '__all__'
        read_only_fields = ['id', 'date_creation']
    
    def get_date_formatee(self, obj):
        return obj.date_creation.strftime('%d/%m/%Y %H:%M') if obj.date_creation else None