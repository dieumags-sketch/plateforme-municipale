# annuaires/serializers.py
from rest_framework import serializers
from .models import (
    CategorieStructure, Structure, Elu, 
    FavoriStructure, AvisStructure, ContactStructure
)

class CategorieStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieStructure
        fields = ['id', 'nom', 'slug', 'description', 'icon', 'couleur']

class StructureListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la liste (léger)"""
    type_icon = serializers.SerializerMethodField()
    distance = serializers.FloatField(read_only=True)
    
    class Meta:
        model = Structure
        fields = [
            'id', 'nom', 'slug', 'type_structure', 'description',
            'adresse', 'quartier', 'ville', 'latitude', 'longitude',
            'telephone', 'image_principale', 'statut', 'est_populaire',
            'vue_count', 'distance'
        ]
    
    def get_type_icon(self, obj):
        icons = {
            'mairie': '🏛️', 'ecole': '🏫', 'hopital': '🏥', 'marche': '🛒',
            'police': '👮', 'transport': '🚌', 'culture': '🎭', 'sport': '⚽',
            'social': '🤝', 'religion': '⛪', 'autre': '📌'
        }
        return icons.get(obj.type_structure, '📌')

class StructureDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le détail (complet)"""
    categorie = CategorieStructureSerializer(read_only=True)
    horaires = serializers.DictField(source='horaires_par_jour', read_only=True)
    est_ouvert = serializers.BooleanField(read_only=True)
    avis_recents = serializers.SerializerMethodField()
    note_moyenne = serializers.SerializerMethodField()
    est_favori = serializers.SerializerMethodField()
    
    class Meta:
        model = Structure
        fields = '__all__'
    
    def get_avis_recents(self, obj):
        avis = obj.avis.filter(est_approuve=True)[:5]
        return AvisStructureSerializer(avis, many=True).data
    
    def get_note_moyenne(self, obj):
        avis = obj.avis.filter(est_approuve=True)
        if avis.exists():
            return round(sum(a.note for a in avis) / avis.count(), 1)
        return 0
    
    def get_est_favori(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.favoris.filter(utilisateur=request.user).exists()
        return False

class EluSerializer(serializers.ModelSerializer):
    nom_complet = serializers.CharField(source='nom_complet', read_only=True)
    
    class Meta:
        model = Elu
        fields = '__all__'

class AvisStructureSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = AvisStructure
        fields = ['id', 'structure', 'utilisateur', 'utilisateur_nom', 'note', 'commentaire', 'date_creation']
        read_only_fields = ['id', 'utilisateur', 'date_creation']

class FavoriStructureSerializer(serializers.ModelSerializer):
    structure = StructureListSerializer(read_only=True)
    
    class Meta:
        model = FavoriStructure
        fields = ['id', 'structure', 'date_ajout']

class ContactStructureSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactStructure
        fields = ['id', 'structure', 'sujet', 'message', 'nom', 'email', 'telephone']
        read_only_fields = ['id', 'date_creation', 'est_traite']