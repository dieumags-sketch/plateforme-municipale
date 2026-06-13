# dechets/permissions.py
from rest_framework import permissions

class EstAgentOuAdmin(permissions.BasePermission):
    """
    Permission pour les agents de collecte et administrateurs
    Les agents peuvent voir et modifier leurs tournées
    """
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        # Admin a tous les droits
        if request.user.is_staff or request.user.role == 'admin':
            return True
        
        # Agent peut accéder
        if request.user.role == 'agent':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Admin peut tout faire
        if request.user.is_staff or request.user.role == 'admin':
            return True
        
        # Agent peut modifier ses propres tournées
        if request.user.role == 'agent':
            if hasattr(obj, 'agent') and obj.agent == request.user:
                return True
            if hasattr(obj, 'tournee') and obj.tournee.agent == request.user:
                return True
        
        return False

class EstAdmin(permissions.BasePermission):
    """Permission réservée aux administrateurs"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or request.user.role == 'admin'
        )
    
    def has_object_permission(self, request, view, obj):
        return request.user.is_authenticated and (
            request.user.is_staff or request.user.role == 'admin'
        )

class EstProprietaireSignalement(permissions.BasePermission):
    """Vérifie si l'utilisateur est le propriétaire du signalement"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role in ['admin', 'agent']:
            return True
        
        if request.user.is_authenticated:
            return obj.citoyen == request.user
        
        return False

class LectureSeuleOuAuthentifie(permissions.BasePermission):
    """Permission mixte : lecture seule pour tous, écriture pour authentifiés"""
    
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_authenticated