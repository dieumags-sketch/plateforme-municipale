# dechets/offline_sync.py
import json
import uuid
from django.utils import timezone
from django.core.files.base import ContentFile
import base64

class OfflineSyncManager:
    """
    Gestionnaire de synchronisation pour le mode offline
    Stocke les données localement et les synchronise quand la connexion revient
    """
    
    @staticmethod
    def prepare_signalement_offline(data):
        """
        Prépare un signalement pour stockage offline
        Convertit les fichiers en base64 pour stockage local
        """
        offline_data = {
            'id': str(uuid.uuid4()),
            'type': 'signalement',
            'data': {
                'type_signalement': data.get('type_signalement'),
                'adresse_description': data.get('adresse_description'),
                'description': data.get('description', ''),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'nom_citoyen': data.get('nom_citoyen', ''),
                'telephone': data.get('telephone', ''),
                'timestamp': timezone.now().isoformat()
            }
        }
        
        # Convertir la photo en base64 si présente
        if data.get('photo'):
            offline_data['data']['photo_base64'] = data['photo']
        
        return offline_data
    
    @staticmethod
    def prepare_demande_offline(data):
        """Prépare une demande d'encombrant pour stockage offline"""
        offline_data = {
            'id': str(uuid.uuid4()),
            'type': 'demande_encombrant',
            'data': {
                'type_encombrant': data.get('type_encombrant'),
                'adresse': data.get('adresse'),
                'point_repere': data.get('point_repere', ''),
                'date_souhaitee': data.get('date_souhaitee'),
                'creneau_horaire': data.get('creneau_horaire', ''),
                'description': data.get('description', ''),
                'latitude': data.get('latitude'),
                'longitude': data.get('longitude'),
                'timestamp': timezone.now().isoformat()
            }
        }
        
        if data.get('photo'):
            offline_data['data']['photo_base64'] = data['photo']
        
        return offline_data
    
    @staticmethod
    def prepare_tournee_offline(tournee_data):
        """
        Prépare une tournée pour utilisation offline
        Télécharge toutes les données nécessaires avant le départ
        """
        offline_tournee = {
            'id': tournee_data.get('id'),
            'date': tournee_data.get('date'),
            'quartier': tournee_data.get('quartier'),
            'quartier_nom': tournee_data.get('quartier_nom'),
            'points': []
        }
        
        for point in tournee_data.get('points', []):
            offline_tournee['points'].append({
                'id': point.get('point'),
                'ordre': point.get('ordre'),
                'adresse': point.get('point_nom', ''),
                'code': point.get('point_code', ''),
                'latitude': point.get('latitude'),
                'longitude': point.get('longitude'),
                'est_vide': False,
                'photo_preuve': None,
                'heure_passage': None
            })
        
        return offline_tournee
    
    @staticmethod
    def reconstruct_signalement_from_offline(offline_data, user):
        """
        Reconstruit un signalement à partir des données offline
        """
        from .models import Signalement
        
        data = offline_data['data']
        signalement = Signalement(
            type_signalement=data['type_signalement'],
            adresse_description=data['adresse_description'],
            description=data['description'],
            latitude=data.get('latitude'),
            longitude=data.get('longitude'),
            nom_citoyen=data.get('nom_citoyen', user.get_full_name() if user else ''),
            telephone=data.get('telephone', str(user.telephone) if user and user.telephone else ''),
            citoyen=user if user and user.is_authenticated else None,
            statut='en_attente'
        )
        
        # Restaurer la photo si présente
        if data.get('photo_base64'):
            import base64
            from django.core.files.base import ContentFile
            
            format, imgstr = data['photo_base64'].split(';base64,')
            ext = format.split('/')[-1]
            signalement.photo.save(
                f"signalement_offline_{offline_data['id']}.{ext}",
                ContentFile(base64.b64decode(imgstr)),
                save=False
            )
        
        return signalement
    
    @staticmethod
    def synchroniser_signalements_offline(signalements_offline, user):
        """
        Synchronise tous les signalements stockés offline vers le serveur
        """
        results = []
        for offline_sig in signalements_offline:
            try:
                signalement = OfflineSyncManager.reconstruct_signalement_from_offline(offline_sig, user)
                signalement.save()
                results.append({
                    'id': offline_sig['id'],
                    'success': True,
                    'server_id': signalement.id
                })
            except Exception as e:
                results.append({
                    'id': offline_sig['id'],
                    'success': False,
                    'error': str(e)
                })
        
        return results

class OfflineStorage:
    """
    Interface pour le stockage IndexedDB côté frontend
    Ces méthodes sont appelées par le JavaScript
    """
    
    @staticmethod
    def get_sync_data():
        """Retourne les données à synchroniser"""
        from .models import PointCollecte, CalendrierCollecte, Quartier
        
        # Données essentielles pour le mode offline
        quartiers = list(Quartier.objects.values('id', 'nom', 'slug', 'latitude', 'longitude'))
        points = list(PointCollecte.objects.filter(statut='actif').values(
            'id', 'code', 'type', 'adresse_reference', 'latitude', 'longitude', 'quartier_id'
        ))
        calendrier = list(CalendrierCollecte.objects.filter(est_actif=True).values(
            'id', 'quartier_id', 'jour_semaine', 'heure_passage'
        ))
        
        return {
            'quartiers': quartiers,
            'points_collecte': points,
            'calendrier': calendrier,
            'version': timezone.now().timestamp()
        }