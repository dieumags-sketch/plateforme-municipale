# accounts/face_recognition.py
import face_recognition
import numpy as np
import base64
import json
from io import BytesIO
from PIL import Image
from django.core.files.uploadedfile import InMemoryUploadedFile

def encode_face_from_image(image_file):
    """
    Encode un visage à partir d'une image
    Retourne l'encodage facial au format JSON
    """
    try:
        # Charger l'image
        if isinstance(image_file, InMemoryUploadedFile):
            image = face_recognition.load_image_file(image_file)
        else:
            image = face_recognition.load_image_file(image_file)
        
        # Détecter les visages
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            return None, "Aucun visage détecté dans l'image"
        
        if len(face_locations) > 1:
            return None, "Plusieurs visages détectés. Veuillez utiliser une photo avec un seul visage."
        
        # Extraire l'encodage
        face_encoding = face_recognition.face_encodings(image, face_locations)[0]
        
        # Convertir en base64 pour stockage
        encoding_json = json.dumps(face_encoding.tolist())
        
        return encoding_json, None
        
    except Exception as e:
        return None, str(e)

def verify_face(face_encoding_stored, face_image):
    """
    Vérifie si le visage correspond à l'encodage stocké
    """
    try:
        # Charger l'encodage stocké
        stored_encoding = np.array(json.loads(face_encoding_stored))
        
        # Charger l'image de vérification
        if isinstance(face_image, InMemoryUploadedFile):
            image = face_recognition.load_image_file(face_image)
        else:
            image = face_recognition.load_image_file(face_image)
        
        # Détecter les visages
        face_locations = face_recognition.face_locations(image)
        
        if len(face_locations) == 0:
            return False, "Aucun visage détecté"
        
        # Extraire l'encodage de vérification
        test_encoding = face_recognition.face_encodings(image, face_locations)[0]
        
        # Comparer les encodages
        results = face_recognition.compare_faces([stored_encoding], test_encoding, tolerance=0.6)
        
        if results[0]:
            return True, "Visage reconnu"
        else:
            return False, "Visage non reconnu"
            
    except Exception as e:
        return False, str(e)

def get_face_landmarks(image_file):
    """Retourne les points de repère du visage (pour l'UI)"""
    try:
        image = face_recognition.load_image_file(image_file)
        face_landmarks_list = face_recognition.face_landmarks(image)
        
        if face_landmarks_list:
            return face_landmarks_list[0]
        return None
    except:
        return None