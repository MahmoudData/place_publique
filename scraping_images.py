"""
Collecteur d'images automatique - Place de la Comédie (Montpellier)
Récupère 1 image toutes les 5 minutes en haute qualité
"""

import requests
import time
from datetime import datetime, timedelta
import os
import sys

# Configuration
OUTPUT_DIR = "images_comedie"
INTERVAL_MINUTES = 5
MAX_IMAGES = 3  # 0 = infini

def get_rounded_timestamp(offset_minutes=0):
    """
    Calcule le timestamp arrondi à 5 minutes
    offset_minutes : décalage en minutes (négatif pour le passé)
    """
    current_time = int(time.time())
    
    # Ajouter l'offset
    if offset_minutes != 0:
        current_time += (offset_minutes * 60)
    
    # Arrondir au multiple de 300 inférieur (5 minutes)
    rounded = (current_time // 300) * 300
    
    return rounded


def download_image_by_timestamp(timestamp, output_path):
    """
    Télécharge l'image pour un timestamp donné
    """
    base_url = "https://filmspv.viewsurf.com/montpellier03/comedie/media_"
    
    # Essayer d'abord sans _tn (haute qualité)
    urls_to_try = [
        f"{base_url}{timestamp}.jpg",
        f"{base_url}{timestamp}_tn.jpg",
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')
                if 'image' in content_type:
                    with open(output_path, 'wb') as f:
                        f.write(response.content)
                    
                    size = len(response.content) / 1024
                    return True, size, url
        except Exception as e:
            continue
    
    return False, 0, None


def collect_current_image():
    """
    Récupère l'image actuelle avec stratégie de fallback
    """
    # Essayer le timestamp actuel et les 2 précédents
    for offset in [0, -5, -10]:
        timestamp = get_rounded_timestamp(offset)
        
        now = datetime.now()
        filename = f"{now.strftime('%Y%m%d_%H%M%S')}_comedie.jpg"
        filepath = os.path.join(OUTPUT_DIR, filename)
        
        success, size, url = download_image_by_timestamp(timestamp, filepath)
        
        if success:
            return True, filepath, size, timestamp
        
        # Si échec, supprimer le fichier vide
        if os.path.exists(filepath):
            os.remove(filepath)
    
    return False, None, 0, None


def run_collection(max_images=50, interval_minutes=5):
    """
    Lance la collecte d'images
    """    
    image_count = 0
    failed_attempts = 0
    last_timestamp = None
    
    print("\n" + "=" * 70)
    print("🚀 DÉMARRAGE DE LA COLLECTE - Place de la Comédie")
    print("=" * 70)
    
    try:
        while True:
            now = datetime.now()
            # Récupérer l'image
            success, filepath, size, timestamp = collect_current_image()
            if success:
                if timestamp == last_timestamp:
                    # Supprimer le doublon
                    if os.path.exists(filepath):
                        os.remove(filepath)
                else:
                    print(f"Image téléchargée : {os.path.basename(filepath)} ({size:.1f} KB)")
                    image_count += 1
                    last_timestamp = timestamp
                    failed_attempts = 0
                    if max_images > 0 and image_count >= max_images:
                        print(f"Objectif atteint : {image_count} images collectées !")
                        break
            else:
                failed_attempts += 1
                print(f"Échec de téléchargement (tentative {failed_attempts})")
                if failed_attempts >= 5:
                    print("Trop d'échecs consécutifs. Arrêt de la collecte.")
                    break
            if max_images == 0 or image_count < max_images:
                wait_seconds = interval_minutes * 60
                time.sleep(wait_seconds)
    
    except KeyboardInterrupt:
        print("Arrêt demandé (Ctrl+C)")
    
    finally:
        print_summary()


def print_summary():
    """Affiche le résumé de la collecte"""
    print("\nRésumé de la collecte :")
    try:
        files = sorted([f for f in os.listdir(OUTPUT_DIR) if f.endswith('.jpg')])
    except FileNotFoundError:
        files = []
    if files:
        print(f"Nombre d'images collectées : {len(files)}")
        print(f"Dossier : {os.path.abspath(OUTPUT_DIR)}/")
        total_size = sum(os.path.getsize(os.path.join(OUTPUT_DIR, f)) for f in files) / (1024 * 1024)
        print(f"Taille totale : {total_size:.2f} MB")
        print(f"Première image : {files[0]}")
        print(f"Dernière image  : {files[-1]}")
        if len(files) >= 2:
            first_time = datetime.strptime(files[0][:15], '%Y%m%d_%H%M%S')
            last_time = datetime.strptime(files[-1][:15], '%Y%m%d_%H%M%S')
            duration = last_time - first_time
            print(f"Durée couverte : {duration}")
    else:
        print("Aucune image collectée")


if __name__ == "__main__":
    run_collection(max_images=MAX_IMAGES, interval_minutes=INTERVAL_MINUTES)