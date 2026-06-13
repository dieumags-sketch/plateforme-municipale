# backend/apps/etat_civil/permissions.py
from rest_framework import permissions

class EstAgentOuAdmin(permissions.BasePermission):
    """Permission pour les agents municipaux et admins"""
    
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        return request.user.is_staff or getattr(request.user, 'role', '') in ['admin', 'agent']
    
    def has_object_permission(self, request, view, obj):
        if not request.user.is_authenticated:
            return False
        if request.user.is_staff or getattr(request.user, 'role', '') in ['admin']:
            return True
        if getattr(request.user, 'role', '') == 'agent':
            return True
        return False