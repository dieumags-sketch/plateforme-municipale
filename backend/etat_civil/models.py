# backend/apps/etat_civil/models.py

from django.db import models
from django.contrib.auth import get_user_model
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
import uuid
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from datetime import datetime, date, timedelta  # AJOUTÉ
import json  # AJOUTÉ

User = get_user_model()


class ConfigurationTarif(models.Model):
    """Configuration des tarifs par type d'acte"""
    
    TYPE_ACTE_CHOICES = [
        ('naissance', 'Acte de naissance'),
        ('mariage', 'Acte de mariage'),
        ('deces', 'Acte de décès'),
        ('reconnaissance', 'Acte de reconnaissance'),
        ('adoption', 'Acte d\'adoption'),
        ('certificat_vie', 'Certificat de vie'),  # AJOUTÉ
        ('extrait', 'Extrait d\'acte'),  # AJOUTÉ
    ]
    
    type_acte = models.CharField(max_length=20, choices=TYPE_ACTE_CHOICES, unique=True)
    delai_normal_jours = models.IntegerField(default=45, help_text="Délai normal en jours pour déclaration")
    tarif_normal = models.DecimalField(max_digits=10, decimal_places=2, default=1000, help_text="Tarif pour déclaration dans les délais")
    tarif_retard = models.DecimalField(max_digits=10, decimal_places=2, default=10000, help_text="Tarif pour déclaration hors délais")
    
    # AJOUTÉ: Tarifs supplémentaires
    tarif_copie = models.DecimalField(max_digits=10, decimal_places=2, default=500, help_text="Tarif pour copie supplémentaire")
    tarif_extrait = models.DecimalField(max_digits=10, decimal_places=2, default=1000, help_text="Tarif pour extrait d'acte")
    
    est_actif = models.BooleanField(default=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Configuration tarifaire"
        verbose_name_plural = "Configurations tarifaires"
        ordering = ['type_acte']  # AJOUTÉ
    
    def __str__(self):
        return f"{self.get_type_acte_display()} - {self.tarif_normal} FCFA"


class Region(models.Model):
    """Région du Cameroun"""
    nom = models.CharField(max_length=100)
    code = models.CharField(max_length=5, unique=True)
    
    # AJOUTÉ
    chef_lieu = models.CharField(max_length=100, blank=True)
    population = models.PositiveIntegerField(default=0, help_text="Population estimée")
    
    class Meta:
        ordering = ['nom']
        verbose_name = "Région"
        verbose_name_plural = "Régions"
    
    def __str__(self):
        return self.nom


class Departement(models.Model):
    """Département"""
    nom = models.CharField(max_length=100)
    region = models.ForeignKey(Region, on_delete=models.CASCADE, related_name='departements')
    code = models.CharField(max_length=10, unique=True)
    
    # AJOUTÉ
    chef_lieu = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['nom']
        verbose_name = "Département"
        verbose_name_plural = "Départements"
    
    def __str__(self):
        return f"{self.nom} ({self.region.nom})"


class Arrondissement(models.Model):
    """Arrondissement"""
    nom = models.CharField(max_length=100)
    departement = models.ForeignKey(Departement, on_delete=models.CASCADE, related_name='arrondissements')
    code = models.CharField(max_length=10, unique=True)
    
    # AJOUTÉ
    chef_lieu = models.CharField(max_length=100, blank=True)
    
    class Meta:
        ordering = ['nom']
        verbose_name = "Arrondissement"
        verbose_name_plural = "Arrondissements"
    
    def __str__(self):
        return f"{self.nom} ({self.departement.nom})"


class DistrictSante(models.Model):
    """District de santé"""
    nom = models.CharField(max_length=200)
    arrondissement = models.ForeignKey(Arrondissement, on_delete=models.CASCADE, related_name='districts_sante')
    code = models.CharField(max_length=20, unique=True)
    
    class Meta:
        verbose_name = "District de santé"
        verbose_name_plural = "Districts de santé"
    
    def __str__(self):
        return self.nom


class DemandeActe(models.Model):
    """Demande d'acte d'état civil"""
    
    TYPE_ACTES = [
        ('naissance', 'Acte de naissance'),
        ('mariage', 'Acte de mariage'),
        ('deces', 'Acte de décès'),
        ('reconnaissance', 'Acte de reconnaissance'),
        ('adoption', 'Acte d\'adoption'),
        ('certificat_vie', 'Certificat de vie'),  # AJOUTÉ
        ('extrait', 'Extrait d\'acte'),  # AJOUTÉ
    ]
    
    STATUTS = [
        ('brouillon', 'Brouillon'),
        ('en_attente', 'En attente de validation'),
        ('en_cours', 'En cours de traitement'),
        ('valide_agent', 'Validé par agent'),
        ('valide_citoyen', 'Validé par citoyen'),
        ('signe', 'Signé'),
        ('rejete', 'Rejeté'),
        ('delivre', 'Délivré'),
        ('expire', 'Expiré'),  # AJOUTÉ
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    reference = models.CharField(max_length=50, unique=True, blank=True)
    type_acte = models.CharField(max_length=20, choices=TYPE_ACTES)
    
    # Relations
    demandeur = models.ForeignKey(User, on_delete=models.CASCADE, related_name='demandes_actes')
    agent_traitant = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='actes_traites')
    autorite_signataire = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name='actes_signes')
    
    # Données du formulaire
    data_acte = models.JSONField(default=dict)  # CORRIGÉ: data → data_acte
    
    # Statut et workflow
    statut = models.CharField(max_length=20, choices=STATUTS, default='brouillon')
    commentaire_rejet = models.TextField(blank=True)
    
    # Dates
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    date_validation_agent = models.DateTimeField(null=True, blank=True)
    date_validation_citoyen = models.DateTimeField(null=True, blank=True)
    date_signature = models.DateTimeField(null=True, blank=True)
    date_delivrance = models.DateTimeField(null=True, blank=True)
    date_expiration_copie = models.DateTimeField(null=True, blank=True)
    
    # Paiement
    tarif_applique = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    paiement_effectue = models.BooleanField(default=False)
    reference_paiement = models.CharField(max_length=100, blank=True)
    date_paiement = models.DateTimeField(null=True, blank=True)
    
    # Documents générés
    fichier_pdf = models.FileField(upload_to='actes_pdf/%Y/%m/', null=True, blank=True)  # CORRIGÉ: upload_to avec dossiers
    qr_code = models.ImageField(upload_to='qrcodes/%Y/%m/', null=True, blank=True)  # CORRIGÉ: upload_to avec dossiers
    
    # AJOUTÉ: Documents justificatifs
    piece_identite = models.FileField(upload_to='etat_civil/identite/%Y/%m/', null=True, blank=True)
    justificatif_domicile = models.FileField(upload_to='etat_civil/domicile/%Y/%m/', null=True, blank=True)
    
    # Métadonnées
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-date_creation']
        indexes = [
            models.Index(fields=['reference']),
            models.Index(fields=['statut', 'type_acte']),
            models.Index(fields=['demandeur', 'statut']),
            models.Index(fields=['date_creation']),  # AJOUTÉ
        ]
    
    def save(self, *args, **kwargs):
        if not self.reference:
            annee = timezone.now().year
            type_code = {
                'naissance': 'N', 
                'mariage': 'M', 
                'deces': 'D', 
                'reconnaissance': 'R', 
                'adoption': 'A',
                'certificat_vie': 'V',  # AJOUTÉ
                'extrait': 'E'  # AJOUTÉ
            }.get(self.type_acte, 'X')
            
            # Compter les demandes du jour pour le séquencement
            today = timezone.now().date()
            count_today = DemandeActe.objects.filter(
                date_creation__date=today,
                type_acte=self.type_acte
            ).count()
            
            sequence = str(count_today + 1).zfill(4)
            self.reference = f"{type_code}/{annee}/{sequence}"
        
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.reference} - {self.get_type_acte_display()}"
    
    def calculer_tarif(self):
        """Calcule le tarif en fonction de la date de naissance/décès"""
        try:
            config = ConfigurationTarif.objects.get(type_acte=self.type_acte, est_actif=True)
            
            if self.type_acte == 'naissance':
                date_naissance_str = self.data_acte.get('enfant_date_naissance') or self.data_acte.get('date_naissance')
                if date_naissance_str:
                    try:
                        if isinstance(date_naissance_str, str):
                            date_naissance = datetime.strptime(date_naissance_str, '%Y-%m-%d').date()
                        else:
                            date_naissance = date_naissance_str
                        
                        jours_apres = (timezone.now().date() - date_naissance).days
                        
                        if jours_apres <= config.delai_normal_jours:
                            return config.tarif_normal
                        else:
                            return config.tarif_retard
                    except (ValueError, TypeError):
                        pass
            
            elif self.type_acte == 'deces':
                date_deces_str = self.data_acte.get('date_deces')
                if date_deces_str:
                    try:
                        if isinstance(date_deces_str, str):
                            date_deces = datetime.strptime(date_deces_str, '%Y-%m-%d').date()
                        else:
                            date_deces = date_deces_str
                        
                        jours_apres = (timezone.now().date() - date_deces).days
                        
                        if jours_apres <= config.delai_normal_jours:
                            return config.tarif_normal
                        else:
                            return config.tarif_retard
                    except (ValueError, TypeError):
                        pass
            
            elif self.type_acte == 'extrait':
                return config.tarif_extrait or config.tarif_normal
            
            return config.tarif_normal
            
        except ConfigurationTarif.DoesNotExist:
            return 1000  # Tarif par défaut
    
    def generer_qr_code(self):
        """Génère un QR code pour l'acte"""
        try:
            qr_data = {
                'reference': self.reference,
                'type': self.type_acte,
                'date_signature': self.date_signature.isoformat() if self.date_signature else '',
                'url': f"/verifier/{self.reference}"
            }
            qr_string = json.dumps(qr_data)
            
            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=4,
                error_correction=qrcode.constants.ERROR_CORRECT_M
            )
            qr.add_data(qr_string)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            buffer = BytesIO()
            img.save(buffer, format='PNG')
            buffer.seek(0)
            
            filename = f"qr_{self.reference}.png"
            self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
            return True
        except Exception as e:
            print(f"Erreur génération QR code: {e}")
            return False
    
    def generer_pdf(self):
        """Génère le PDF de l'acte"""
        from reportlab.lib.pagesizes import A4
        from reportlab.lib import colors
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from io import BytesIO
        
        try:
            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4, 
                                   rightMargin=2*cm, leftMargin=2*cm,
                                   topMargin=2*cm, bottomMargin=2*cm)
            
            styles = getSampleStyleSheet()
            style_titre = ParagraphStyle(
                'Titre', 
                parent=styles['Heading1'], 
                fontSize=16, 
                alignment=1, 
                textColor=colors.HexColor('#1a237e'),
                spaceAfter=10
            )
            style_soustitre = ParagraphStyle(
                'Soustitre',
                parent=styles['Heading2'],
                fontSize=12,
                alignment=1,
                spaceAfter=15
            )
            style_normal = ParagraphStyle(
                'Normal', 
                parent=styles['Normal'], 
                fontSize=10, 
                spaceAfter=5
            )
            style_bold = ParagraphStyle(
                'Bold',
                parent=styles['Normal'],
                fontSize=10,
                spaceAfter=5,
                fontName='Helvetica-Bold'
            )
            
            story = []
            
            # En-tête
            story.append(Paragraph("RÉPUBLIQUE DU CAMEROUN", style_titre))
            story.append(Paragraph("Paix - Travail - Patrie", style_soustitre))
            story.append(Spacer(1, 10))
            story.append(Paragraph("MAIRIE DE BOT-MAKAK", style_titre))
            story.append(Paragraph("Service de l'État Civil", style_soustitre))
            story.append(Spacer(1, 20))
            
            # Titre
            titres = {
                'naissance': "ACTE DE NAISSANCE",
                'mariage': "ACTE DE MARIAGE",
                'deces': "ACTE DE DÉCÈS",
                'reconnaissance': "ACTE DE RECONNAISSANCE",
                'adoption': "ACTE D'ADOPTION",
                'certificat_vie': "CERTIFICAT DE VIE",
                'extrait': "EXTRAIT D'ACTE"
            }
            story.append(Paragraph(titres.get(self.type_acte, "ACTE D'ÉTAT CIVIL"), style_titre))
            story.append(Spacer(1, 20))
            
            # Contenu selon le type
            data = self.data_acte
            
            if self.type_acte == 'naissance':
                story.append(Paragraph("I. INFORMATIONS SUR L'ENFANT", style_bold))
                story.append(Paragraph(f"Nom complet: {data.get('enfant_nom', '')} {data.get('enfant_prenom', '')}", style_normal))
                story.append(Paragraph(f"Date de naissance: {data.get('enfant_date_naissance', '')}", style_normal))
                story.append(Paragraph(f"Lieu de naissance: {data.get('enfant_lieu_naissance', '')}", style_normal))
                story.append(Paragraph(f"Sexe: {data.get('enfant_sexe', '')}", style_normal))
                story.append(Spacer(1, 10))
                
                story.append(Paragraph("II. INFORMATIONS SUR LA MÈRE", style_bold))
                story.append(Paragraph(f"Nom: {data.get('mere_nom', '')} {data.get('mere_prenom', '')}", style_normal))
                story.append(Paragraph(f"Date de naissance: {data.get('mere_date_naissance', '')}", style_normal))
                story.append(Paragraph(f"Profession: {data.get('mere_profession', '')}", style_normal))
                story.append(Spacer(1, 10))
                
                story.append(Paragraph("III. INFORMATIONS SUR LE PÈRE", style_bold))
                story.append(Paragraph(f"Nom: {data.get('pere_nom', '')} {data.get('pere_prenom', '')}", style_normal))
                story.append(Paragraph(f"Date de naissance: {data.get('pere_date_naissance', '')}", style_normal))
                story.append(Paragraph(f"Profession: {data.get('pere_profession', '')}", style_normal))
                
            elif self.type_acte == 'mariage':
                story.append(Paragraph("I. INFORMATIONS SUR LES ÉPOUX", style_bold))
                story.append(Paragraph(f"Époux: {data.get('epoux_nom', '')} {data.get('epoux_prenom', '')}", style_normal))
                story.append(Paragraph(f"Épouse: {data.get('epouse_nom', '')} {data.get('epouse_prenom', '')}", style_normal))
                story.append(Spacer(1, 10))
                story.append(Paragraph(f"Date de mariage: {data.get('date_mariage', '')}", style_normal))
                story.append(Paragraph(f"Lieu de mariage: {data.get('lieu_mariage', '')}", style_normal))
                story.append(Paragraph(f"Régime matrimonial: {data.get('regime_matrimonial', '')}", style_normal))
                
            elif self.type_acte == 'deces':
                story.append(Paragraph("I. INFORMATIONS SUR LE DÉFUNT", style_bold))
                story.append(Paragraph(f"Nom: {data.get('defunt_nom', '')} {data.get('defunt_prenom', '')}", style_normal))
                story.append(Paragraph(f"Date de naissance: {data.get('defunt_date_naissance', '')}", style_normal))
                story.append(Paragraph(f"Date de décès: {data.get('date_deces', '')}", style_normal))
                story.append(Paragraph(f"Lieu de décès: {data.get('lieu_deces', '')}", style_normal))
                
            # Numéro d'acte
            story.append(Spacer(1, 20))
            story.append(Paragraph(f"<b>Numéro d'acte:</b> {self.reference}", style_normal))
            story.append(Paragraph(f"<b>Date de délivrance:</b> {timezone.now().strftime('%d/%m/%Y à %H:%M')}", style_normal))
            
            # Signatures
            story.append(Spacer(1, 30))
            signatures_data = [
                ["Le déclarant", "L'officier d'état civil", "Le Maire"],
                ["_________________", "_________________", "_________________"],
            ]
            sig_table = Table(signatures_data, colWidths=[5*cm, 5*cm, 5*cm])
            sig_table.setStyle(TableStyle([
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('FONTSIZE', (0,0), (-1,-1), 9),
            ]))
            story.append(sig_table)
            
            # Mention de validité
            if self.date_expiration_copie:
                story.append(Spacer(1, 20))
                story.append(Paragraph(
                    f"<i>Copie certifiée conforme à l'original. Valable jusqu'au {self.date_expiration_copie.strftime('%d/%m/%Y')}</i>",
                    ParagraphStyle('Italic', parent=styles['Normal'], textColor=colors.grey, fontSize=8)
                ))
            
            doc.build(story)
            buffer.seek(0)
            return buffer.getvalue()
            
        except Exception as e:
            print(f"Erreur génération PDF: {e}")
            return None


class HistoriqueStatut(models.Model):
    """Historique des changements de statut"""
    demande = models.ForeignKey(DemandeActe, on_delete=models.CASCADE, related_name='historique')
    ancien_statut = models.CharField(max_length=20)
    nouveau_statut = models.CharField(max_length=20)
    commentaire = models.TextField(blank=True)
    utilisateur = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        verbose_name = "Historique de statut"
        verbose_name_plural = "Historiques de statut"
        indexes = [
            models.Index(fields=['demande', 'date']),
        ]
    
    def __str__(self):
        return f"{self.demande.reference} - {self.ancien_statut} → {self.nouveau_statut} ({self.date.strftime('%d/%m/%Y %H:%M')})"


class NotificationActe(models.Model):
    """Notifications pour le citoyen"""
    demande = models.ForeignKey(DemandeActe, on_delete=models.CASCADE, related_name='notifications')
    titre = models.CharField(max_length=200)
    message = models.TextField()
    est_lue = models.BooleanField(default=False)
    date_envoi = models.DateTimeField(auto_now_add=True)
    date_lecture = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-date_envoi']
        verbose_name = "Notification d'acte"
        verbose_name_plural = "Notifications d'actes"
        indexes = [
            models.Index(fields=['demande', 'est_lue']),
        ]
    
    def __str__(self):
        return f"{self.titre} - {self.date_envoi.strftime('%d/%m/%Y %H:%M')}"
    
    def marquer_comme_lue(self):
        """Marque la notification comme lue"""
        if not self.est_lue:
            self.est_lue = True
            self.date_lecture = timezone.now()
            self.save(update_fields=['est_lue', 'date_lecture'])


# AJOUTÉ: Modèle pour les certificats de vie
class CertificatVie(models.Model):
    """Certificat de vie pour pensionnés"""
    demande = models.OneToOneField(DemandeActe, on_delete=models.CASCADE, related_name='certificat_vie')
    beneficiaire = models.CharField(max_length=200)
    date_naissance = models.DateField()
    lieu_naissance = models.CharField(max_length=200)
    numero_pension = models.CharField(max_length=50)
    date_validite = models.DateField()
    
    class Meta:
        verbose_name = "Certificat de vie"
        verbose_name_plural = "Certificats de vie"
    
    def __str__(self):
        return f"Certificat de {self.beneficiaire} - valable jusqu'au {self.date_validite}"
    
    def est_valide(self):
        """Vérifie si le certificat est encore valide"""
        return self.date_validite >= timezone.now().date()


# AJOUTÉ: Modèle pour les copies d'actes
class CopieActe(models.Model):
    """Demande de copie d'acte existant"""
    demande = models.OneToOneField(DemandeActe, on_delete=models.CASCADE, related_name='copie')
    acte_original = models.CharField(max_length=50, help_text="Référence de l'acte original")
    nombre_copies = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(10)])
    motif = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "Copie d'acte"
        verbose_name_plural = "Copies d'actes"
    
    def __str__(self):
        return f"{self.nombre_copies} copie(s) de {self.acte_original}"