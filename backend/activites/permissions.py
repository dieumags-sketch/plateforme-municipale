# activites/permissions.py
from rest_framework import permissions

class EstOrganisateurOuAdmin(permissions.BasePermission):
    """Vérifie si l'utilisateur est l'organisateur ou un admin"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role == 'admin':
            return True
        return obj.organisateur == request.user

class EstProprietaireInscription(permissions.BasePermission):
    """Vérifie si l'utilisateur est le propriétaire de l'inscription"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role == 'admin':
            return True
        return obj.utilisateur == request.user

class PeutGererActivites(permissions.BasePermission):
    """Permission pour gérer les activités (admin, moderateur, agent)"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in ['admin', 'moderateur', 'agent']