# activites/notifications.py
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import NotificationActivite

class NotificationService:
    """Service de notifications pour les activités"""
    
    @staticmethod
    def envoyer_confirmation_inscription(inscription):
        """Envoyer une confirmation d'inscription"""
        
        # Envoyer par email
        sujet = f"Confirmation inscription - {inscription.activite.titre}"
        message = f"""
Bonjour {inscription.nom_complet},

Votre inscription à l'activité "{inscription.activite.titre}" a été confirmée.

📅 Date : {inscription.activite.date_debut.strftime('%d/%m/%Y à %H:%M')}
📍 Lieu : {inscription.activite.lieu}
🎟️ Référence : {inscription.reference}
💰 Montant payé : {inscription.montant_total} FCFA

Présentez ce QR code à l'entrée :
(Joindre QR code dans l'email)

Pour toute question, contactez-nous.

Cordialement,
Plateforme Municipale
        """
        
        try:
            send_mail(
                sujet, message, settings.DEFAULT_FROM_EMAIL,
                [inscription.email], fail_silently=False
            )
        except Exception as e:
            print(f"Erreur envoi email: {e}")
        
        # Enregistrer la notification
        NotificationActivite.objects.create(
            utilisateur=inscription.utilisateur,
            activite=inscription.activite,
            type='inscription',
            canal='email',
            sujet=sujet,
            message=message,
            est_envoyee=True,
            date_envoi=timezone.now()
        )
    
    @staticmethod
    def envoyer_rappel(inscription):
        """Envoyer un rappel avant l'activité"""
        sujet = f"Rappel : {inscription.activite.titre} demain"
        message = f"""
Bonjour {inscription.nom_complet},

Ceci est un rappel : L'activité "{inscription.activite.titre}" aura lieu demain à {inscription.activite.date_debut.strftime('%H:%M')}.

📍 Lieu : {inscription.activite.lieu}

N'oubliez pas votre QR code d'entrée !

Cordialement,
Plateforme Municipale
        """
        
        try:
            send_mail(
                sujet, message, settings.DEFAULT_FROM_EMAIL,
                [inscription.email], fail_silently=False
            )
        except Exception as e:
            print(f"Erreur envoi email rappel: {e}")
    
    @staticmethod
    def notifier_annulation(inscription, raison=""):
        """Notifier l'annulation d'une inscription"""
        sujet = f"Annulation inscription - {inscription.activite.titre}"
        message = f"""
Bonjour {inscription.nom_complet},

Votre inscription à l'activité "{inscription.activite.titre}" a été annulée.
{raison}

Pour toute question, contactez-nous.

Cordialement,
Plateforme Municipale
        """
        
        try:
            send_mail(
                sujet, message, settings.DEFAULT_FROM_EMAIL,
                [inscription.email], fail_silently=False
            )
        except Exception as e:
            print(f"Erreur envoi email annulation: {e}")