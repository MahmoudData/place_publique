"""
Configuration du projet Place Publique - MVP
"""

import os

# Chemins
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
IMAGES_DIR = os.path.join(BASE_DIR, 'images')
MODELS_DIR = os.path.join(BASE_DIR, 'models')
LAST_IMAGE_PATH = os.path.join(BASE_DIR, 'static', 'images', 'last_detection.jpg')

# Base de données
DATABASE_PATH = os.path.join(DATA_DIR, 'place_publique.db')

# Modèle YOLO
YOLO_MODEL = 'best_genre.pt'  # XLarge pour meilleure précision 'yolo11x.pt'
YOLO_CONFIDENCE = 0.25     # Seuil de confiance minimum

# Webcam Place de la Comédie (hard-codée pour MVP)
WEBCAM_CONFIG = {
    'name': 'Place de la Comédie',
    'location': 'Montpellier, France',
    'url_base': 'https://filmspv.viewsurf.com/montpellier03/comedie/media_',
    'url_suffix': '.jpg',
}

# Classes à détecter (COCO dataset)
CLASSES_TO_DETECT = [
    'person',      # 0
    'bicycle',     # 1
    'car',         # 2
    'motorcycle',  # 3
    'truck',       # 7
]

# Service d'inférence
DETECTION_INTERVAL_MINUTES = 5  # Toutes les 5 minutes
MAX_RETRIES = 3                 # Nombre de tentatives si échec
RETRY_DELAY_SECONDS = 60        # Délai entre tentatives

# Flask
FLASK_HOST = '0.0.0.0'
FLASK_PORT = 5000
FLASK_DEBUG = True  # False en production

# Stockage images
KEEP_IMAGES = False  # True = garder toutes les images, False = juste les counts
KEEP_LAST_IMAGE = True  # Garder dernière image annotée pour preview
