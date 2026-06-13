# accounts/permissions.py
from rest_framework import permissions

class IsOwnerOrAdmin(permissions.BasePermission):
    """Vérifie si l'utilisateur est le propriétaire ou un admin"""
    
    def has_object_permission(self, request, view, obj):
        if request.user.is_staff or request.user.role == 'admin':
            return True
        return obj == request.user

class IsVerified(permissions.BasePermission):
    """Vérifie si l'utilisateur a vérifié son email"""
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.is_verified

class IsRole(permissions.BasePermission):
    """Vérifie le rôle de l'utilisateur"""
    
    def __init__(self, allowed_roles):
        self.allowed_roles = allowed_roles
    
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.role in self.allowed_roles