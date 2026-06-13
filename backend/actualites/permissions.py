# actualites/permissions.py
from rest_framework import permissions

class EstAuteurOuModerateur(permissions.BasePermission):
    """Permission : l'utilisateur est l'auteur ou un modérateur/admin"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role == 'admin':
            return True
        return obj.auteur == request.user

class EstModerateur(permissions.BasePermission):
    """Permission : l'utilisateur est modérateur ou admin"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or request.user.role in ['admin', 'moderateur']
        )

class PeutModererCommentaires(permissions.BasePermission):
    """Permission pour modérer les commentaires"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and (
            request.user.is_staff or request.user.role in ['admin', 'moderateur']
        )

class EstProprietaireOuAdmin(permissions.BasePermission):
    """Pour les propositions citoyennes : l'utilisateur est le propriétaire"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role == 'admin':
            return True
        return obj.auteur == request.user