# activites/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    CategorieActivite, Activite, Inscription, 
    PaiementActivite, NotificationActivite, AvisActivite
)

Utilisateur = get_user_model()

class CategorieActiviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieActivite
        fields = ['id', 'nom', 'slug', 'description', 'icon', 'couleur', 'ordre']

class ActiviteListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la liste (léger)"""
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_couleur = serializers.CharField(source='categorie.couleur', read_only=True)
    organisateur_nom = serializers.CharField(source='organisateur.get_full_name', read_only=True)
    places_restantes = serializers.SerializerMethodField()
    nb_inscrits = serializers.IntegerField(source='nb_inscrits', read_only=True)
    
    class Meta:
        model = Activite
        fields = [
            'id', 'titre', 'slug', 'type_activite', 'description_courte',
            'image_principale', 'date_debut', 'date_fin', 'lieu', 'ville',
            'prix', 'est_gratuit', 'capacite_max', 'places_restantes', 'nb_inscrits',
            'statut', 'est_a_la_une', 'est_recommandee', 'categorie_nom', 'categorie_couleur',
            'organisateur_nom', 'vue_count'
        ]
    
    def get_places_restantes(self, obj):
        return obj.places_restantes

class ActiviteDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le détail (complet)"""
    categorie = CategorieActiviteSerializer(read_only=True)
    organisateur_nom = serializers.CharField(source='organisateur.get_full_name', read_only=True)
    organisateur_email = serializers.CharField(source='organisateur.email', read_only=True)
    places_restantes = serializers.SerializerMethodField()
    est_inscrit = serializers.SerializerMethodField()
    
    class Meta:
        model = Activite
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'vue_count', 'partage_count', 'date_creation', 'date_modification']
    
    def get_places_restantes(self, obj):
        return obj.places_restantes
    
    def get_est_inscrit(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.inscriptions.filter(
                utilisateur=request.user,
                statut__in=['en_attente_paiement', 'confirmee']
            ).exists()
        return False

class ActiviteCreateUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la création/modification"""
    
    class Meta:
        model = Activite
        fields = [
            'titre', 'type_activite', 'categorie', 'description_courte', 'description_longue',
            'image_principale', 'images_galerie', 'video_url', 'date_debut', 'date_fin',
            'date_limite_inscription', 'capacite_max', 'prix', 'lieu', 'adresse', 'ville',
            'coordonnees_gps', 'partenaires', 'est_a_la_une', 'est_recommandee'
        ]

class InscriptionSerializer(serializers.ModelSerializer):
    activite_titre = serializers.CharField(source='activite.titre', read_only=True)
    activite_date = serializers.DateTimeField(source='activite.date_debut', read_only=True)
    activite_image = serializers.ImageField(source='activite.image_principale', read_only=True)
    utilisateur_nom = serializers.CharField(source='utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = Inscription
        fields = [
            'id', 'reference', 'activite', 'activite_titre', 'activite_date', 'activite_image',
            'utilisateur', 'utilisateur_nom', 'nom_complet', 'email', 'telephone',
            'date_naissance', 'adresse', 'commentaire', 'nombre_places', 'noms_accompagnants',
            'montant_total', 'moyen_paiement', 'statut', 'qr_code', 'date_inscription'
        ]
        read_only_fields = ['id', 'reference', 'montant_total', 'qr_code', 'date_inscription']

class InscriptionCreateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour création d'inscription"""
    
    class Meta:
        model = Inscription
        fields = [
            'activite', 'nom_complet', 'email', 'telephone', 'date_naissance',
            'adresse', 'commentaire', 'nombre_places', 'noms_accompagnants'
        ]
    
    def validate(self, data):
        activite = data['activite']
        
        # Vérifier que l'activité est publiée
        if activite.statut != 'publie':
            raise serializers.ValidationError("Cette activité n'est pas disponible")
        
        # Vérifier la date limite d'inscription
        if activite.date_limite_inscription < timezone.now():
            raise serializers.ValidationError("La date limite d'inscription est dépassée")
        
        # Vérifier les places restantes
        if activite.capacite_max > 0:
            places_restantes = activite.places_restantes
            if places_restantes < data.get('nombre_places', 1):
                raise serializers.ValidationError(f"Plus que {places_restantes} place(s) disponible(s)")
        
        return data

class PaiementActiviteSerializer(serializers.ModelSerializer):
    class Meta:
        model = PaiementActivite
        fields = [
            'id', 'inscription', 'montant', 'moyen_paiement', 'statut',
            'transaction_id', 'numero_telephone', 'operator', 'date_demande', 'date_validation'
        ]
        read_only_fields = ['id', 'statut', 'transaction_id', 'date_demande', 'date_validation']

class PaiementInitSerializer(serializers.Serializer):
    """Sérialiseur pour initier un paiement"""
    inscription_id = serializers.IntegerField()
    moyen_paiement = serializers.ChoiceField(choices=['mtn', 'orange'])
    numero_telephone = serializers.CharField(max_length=20)

class AvisActiviteSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='inscription.utilisateur.get_full_name', read_only=True)
    
    class Meta:
        model = AvisActivite
        fields = ['id', 'inscription', 'note', 'commentaire', 'est_approuve', 'utilisateur_nom', 'date_creation']
        read_only_fields = ['id', 'est_approuve', 'date_creation']