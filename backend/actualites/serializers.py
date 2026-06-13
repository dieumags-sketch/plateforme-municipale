# actualites/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import (
    CategorieActualite, Publication, Reaction, 
    Commentaire, HistoriqueConsultation, PropositionCitoyenne, Partage
)

Utilisateur = get_user_model()

class CategorieActualiteSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategorieActualite
        fields = ['id', 'nom', 'slug', 'description', 'icon', 'couleur', 'ordre']

class ReactionSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    
    class Meta:
        model = Reaction
        fields = ['id', 'type_reaction', 'utilisateur_nom', 'date_creation']
        read_only_fields = ['id', 'date_creation']

class CommentaireSerializer(serializers.ModelSerializer):
    utilisateur_nom = serializers.CharField(source='utilisateur.username', read_only=True)
    utilisateur_avatar = serializers.SerializerMethodField()
    reponses = serializers.SerializerMethodField()
    
    class Meta:
        model = Commentaire
        fields = ['id', 'publication', 'utilisateur', 'utilisateur_nom', 'utilisateur_avatar',
                  'parent', 'reponses', 'contenu', 'est_approuve', 'like_count', 
                  'date_creation', 'date_modification']
        read_only_fields = ['id', 'utilisateur', 'like_count', 'date_creation', 'date_modification']
    
    def get_utilisateur_avatar(self, obj):
        if hasattr(obj.utilisateur, 'photo') and obj.utilisateur.photo:
            return obj.utilisateur.photo.url
        return None
    
    def get_reponses(self, obj):
        if not obj.parent:
            reponses = obj.reponses.filter(est_approuve=True)
            return CommentaireSerializer(reponses, many=True).data
        return []

class PublicationListSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la liste (plus léger)"""
    categorie_nom = serializers.CharField(source='categorie.nom', read_only=True)
    categorie_couleur = serializers.CharField(source='categorie.couleur', read_only=True)
    auteur_nom = serializers.CharField(source='auteur.username', read_only=True)
    reactions_count = serializers.SerializerMethodField()
    commentaires_count = serializers.SerializerMethodField()
    temps_lecture_min = serializers.SerializerMethodField()
    
    class Meta:
        model = Publication
        fields = ['id', 'titre', 'slug', 'accroche', 'type_media', 'media', 'thumbnail',
                  'categorie_nom', 'categorie_couleur', 'auteur_nom', 'date_publication',
                  'est_epingle', 'est_a_la_une', 'vue_count', 'reactions_count', 
                  'commentaires_count', 'temps_lecture_min']
    
    def get_reactions_count(self, obj):
        return obj.reactions.count()
    
    def get_commentaires_count(self, obj):
        return obj.commentaires.filter(est_approuve=True).count()
    
    def get_temps_lecture_min(self, obj):
        return obj.temps_lecture

class PublicationDetailSerializer(serializers.ModelSerializer):
    """Sérialiseur pour le détail (complet)"""
    categorie = CategorieActualiteSerializer(read_only=True)
    auteur_nom = serializers.CharField(source='auteur.username', read_only=True)
    auteur_avatar = serializers.SerializerMethodField()
    reactions = serializers.SerializerMethodField()
    commentaires = serializers.SerializerMethodField()
    reaction_utilisateur = serializers.SerializerMethodField()
    est_dans_favoris = serializers.SerializerMethodField()
    
    class Meta:
        model = Publication
        fields = '__all__'
        read_only_fields = ['id', 'slug', 'vue_count', 'partage_count', 'date_creation', 
                           'date_modification', 'auteur']
    
    def get_auteur_avatar(self, obj):
        if hasattr(obj.auteur, 'photo') and obj.auteur.photo:
            return obj.auteur.photo.url
        return None
    
    def get_reactions(self, obj):
        # Grouper les réactions par type
        reactions_group = {}
        for reaction in obj.reactions.all():
            reactions_group[reaction.type_reaction] = reactions_group.get(reaction.type_reaction, 0) + 1
        return reactions_group
    
    def get_commentaires(self, obj):
        commentaires = obj.commentaires.filter(parent=None, est_approuve=True)
        return CommentaireSerializer(commentaires, many=True).data
    
    def get_reaction_utilisateur(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            reaction = obj.reactions.filter(utilisateur=request.user).first()
            return reaction.type_reaction if reaction else None
        return None
    
    def get_est_dans_favoris(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return HistoriqueConsultation.objects.filter(
                utilisateur=request.user, publication=obj
            ).exists()
        return False

class PublicationCreateUpdateSerializer(serializers.ModelSerializer):
    """Sérialiseur pour la création/modification par l'admin"""
    class Meta:
        model = Publication
        fields = ['titre', 'accroche', 'contenu', 'type_media', 'media', 'media_url',
                  'thumbnail', 'categorie', 'tags', 'date_publication', 'est_epingle', 
                  'est_a_la_une', 'meta_description', 'mots_cles_seo']

class PropositionCitoyenneSerializer(serializers.ModelSerializer):
    auteur_nom = serializers.CharField(source='auteur.username', read_only=True)
    
    class Meta:
        model = PropositionCitoyenne
        fields = ['id', 'titre', 'contenu', 'auteur', 'auteur_nom', 'statut', 
                  'commentaire_moderation', 'date_soumission']
        read_only_fields = ['id', 'auteur', 'statut', 'commentaire_moderation', 'date_soumission']

class PartageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Partage
        fields = ['id', 'publication', 'plateforme', 'date_partage']
        read_only_fields = ['id', 'date_partage']

class HistoriqueConsultationSerializer(serializers.ModelSerializer):
    publication = PublicationListSerializer(read_only=True)
    
    class Meta:
        model = HistoriqueConsultation
        fields = ['id', 'publication', 'date_consultation']