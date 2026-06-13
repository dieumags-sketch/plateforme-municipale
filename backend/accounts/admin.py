# accounts/admin.py - Version corrigée
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.utils import timezone
from .models import (
    Utilisateur, FailedLoginAttempt, UserSession, 
    PasswordResetToken, EmailVerificationToken, PhoneVerificationCode
)


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    list_display = [
        'email', 
        'username', 
        'get_full_name', 
        'role', 
        'is_verified',           # 👈 AJOUTÉ - champ réel (pour list_editable)
        'is_verified_status',    # 👈 GARDÉ - version avec icône
        'is_active_status',
        'last_seen'
    ]
    list_filter = ['role', 'is_verified', 'is_active', 'date_joined']
    list_editable = ['is_verified']  # ✅ Maintenant 'is_verified' est dans list_display
    search_fields = ['email', 'username', 'nom', 'prenom', 'telephone']
    ordering = ['-date_joined']
    
    fieldsets = (
        ('Informations personnelles', {
            'fields': ('email', 'username', 'nom', 'prenom', 'telephone', 'date_naissance', 'avatar')
        }),
        ('Adresse', {
            'fields': ('adresse', 'code_postal', 'ville', 'pays'),
            'classes': ('collapse',)
        }),
        ('Vérification du compte', {
            'fields': ('is_verified', 'telephone_verified'),
            'description': '<span style="color: #e67e22; font-weight: bold;">⚠️ Cochez "is_verified" pour permettre la connexion</span>',
            'classes': ('wide',)
        }),
        ('Statut et permissions', {
            'fields': ('role', 'is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')
        }),
        ('Sécurité', {
            'fields': ('totp_enabled', 'face_enabled', 'webauthn_credentials'),
            'classes': ('collapse',)
        }),
        ('Préférences', {
            'fields': ('prefer_notifications_email', 'prefer_notifications_sms', 'langue', 'theme'),
            'classes': ('collapse',)
        }),
        ('Dates importantes', {
            'fields': ('last_login', 'date_joined', 'last_seen', 'last_login_ip'),
            'classes': ('collapse',)
        }),
    )
    
    readonly_fields = ['last_login', 'date_joined', 'last_seen', 'last_login_ip']
    
    def is_verified_status(self, obj):
        """Affiche une icône pour is_verified (version visuelle)"""
        if obj.is_verified:
            return format_html('<span style="color: #27ae60; font-weight: bold;">✓ Vérifié</span>')
        return format_html('<span style="color: #e74c3c; font-weight: bold;">✗ Non vérifié</span>')
    is_verified_status.short_description = "Statut vérification"
    is_verified_status.admin_order_field = 'is_verified'
    
    def is_active_status(self, obj):
        """Affiche une icône pour is_active"""
        if obj.is_active:
            return format_html('<span style="color: #27ae60; font-weight: bold;">✓ Actif</span>')
        return format_html('<span style="color: #e74c3c; font-weight: bold;">✗ Inactif</span>')
    is_active_status.short_description = "Statut compte"
    is_active_status.admin_order_field = 'is_active'
    
    def get_full_name(self, obj):
        return obj.get_full_name()
    get_full_name.short_description = "Nom complet"
    
    actions = ['verify_emails', 'unverify_emails']
    
    def verify_emails(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} utilisateur(s) ont été vérifiés.')
    verify_emails.short_description = "✓ Marquer les emails comme vérifiés"
    
    def unverify_emails(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} utilisateur(s) ont été marqués comme non vérifiés.')
    unverify_emails.short_description = "✗ Marquer les emails comme non vérifiés"


@admin.register(FailedLoginAttempt)
class FailedLoginAttemptAdmin(admin.ModelAdmin):
    list_display = ['email', 'ip_address', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['email', 'ip_address']
    readonly_fields = ['email', 'ip_address', 'user_agent', 'timestamp']


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'device_name', 'ip_address', 'last_activity', 'is_active']
    list_filter = ['is_active', 'device_type', 'created_at']
    search_fields = ['utilisateur__email', 'session_key', 'device_name']
    readonly_fields = ['session_key', 'created_at', 'last_activity']


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'token_short', 'created_at', 'expires_at', 'used', 'is_valid_status']
    list_filter = ['used', 'created_at']
    search_fields = ['utilisateur__email', 'token']
    readonly_fields = ['token', 'created_at', 'expires_at']
    
    def token_short(self, obj):
        return f"{obj.token[:20]}..." if len(obj.token) > 20 else obj.token
    token_short.short_description = "Token"
    
    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valide</span>')
        return format_html('<span style="color: red;">✗ Invalide/Expiré</span>')
    is_valid_status.short_description = "Statut"


@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ['utilisateur', 'token_short', 'created_at', 'expires_at', 'is_valid_status']
    list_filter = ['created_at']
    search_fields = ['utilisateur__email', 'token']
    readonly_fields = ['token', 'created_at', 'expires_at']
    
    def token_short(self, obj):
        return f"{obj.token[:20]}..." if len(obj.token) > 20 else obj.token
    token_short.short_description = "Token"
    
    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valide</span>')
        return format_html('<span style="color: red;">✗ Expiré</span>')
    is_valid_status.short_description = "Statut"


@admin.register(PhoneVerificationCode)
class PhoneVerificationCodeAdmin(admin.ModelAdmin):
    """Administration des codes de vérification téléphone"""
    list_display = ['utilisateur', 'code', 'created_at', 'expires_at', 'used', 'is_valid_status']
    list_filter = ['used', 'created_at']
    search_fields = ['utilisateur__email', 'code']
    readonly_fields = ['code', 'created_at', 'expires_at']
    list_editable = ['used']  # Permet de marquer comme utilisé directement
    
    def is_valid_status(self, obj):
        if obj.is_valid():
            return format_html('<span style="color: green;">✓ Valide</span>')
        return format_html('<span style="color: red;">✗ Invalide/Expiré</span>')
    is_valid_status.short_description = "Statut"