# backend/apps/etat_civil/utils.py
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile

def generer_pdf_acte(demande):
    """Génère le PDF de l'acte selon son type"""
    # À implémenter selon le type d'acte
    pass

def generer_qr_code(demande):
    """Génère un QR code pour l'acte"""
    qr_data = f"{demande.reference}|{demande.type_acte}|{demande.date_signature}"
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue(), f"qr_{demande.reference}.png")

def envoyer_notification(demande, titre, message):
    """Envoie une notification au citoyen"""
    NotificationActe.objects.create(
        demande=demande,
        titre=titre,
        message=message
    )
    
    if demande.demandeur.email:
        send_mail(
            subject=titre,
            message=message,
            from_email='etat-civil@botmatmakak.net',
            recipient_list=[demande.demandeur.email],
            fail_silently=True
        )