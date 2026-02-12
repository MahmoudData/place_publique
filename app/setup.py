#!/usr/bin/env python3
"""
Script d'installation du projet Place Publique
Lance automatiquement toutes les étapes nécessaires
"""

import os
import sys
import subprocess

def print_step(step_num, description):
    """Affiche une étape avec formatage"""
    print("\n" + "=" * 70)
    print(f"ÉTAPE {step_num} : {description}")
    print("=" * 70)

def run_command(command, description):
    """Exécute une commande shell"""
    print(f"  → {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"  ✓ {description} - OK")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Erreur : {e}")
        print(f"  Sortie : {e.stdout}")
        print(f"  Erreur : {e.stderr}")
        return False

def main():
    print("\n" + "=" * 70)
    print("🚀 INSTALLATION - Place Publique MVP")
    print("=" * 70)
    
    # Étape 1 : Vérifier Python
    print_step(1, "Vérification de Python")
    python_version = sys.version_info
    print(f"  Version Python : {python_version.major}.{python_version.minor}.{python_version.micro}")
    
    if python_version.major < 3 or (python_version.major == 3 and python_version.minor < 8):
        print("  ✗ Python 3.8+ requis !")
        sys.exit(1)
    print("  ✓ Version Python OK")
    
    # Étape 2 : Créer environnement virtuel
    print_step(2, "Création de l'environnement virtuel")
    
    if not os.path.exists('venv'):
        if not run_command(f"{sys.executable} -m venv venv", "Création du venv"):
            print("  ⚠️  Échec de création du venv, on continue sans...")
    else:
        print("  ✓ venv déjà existant")
    
    # Étape 3 : Installation des dépendances
    print_step(3, "Installation des dépendances Python")
    
    # Déterminer le chemin de pip
    if os.name == 'nt':  # Windows
        pip_cmd = 'venv\\Scripts\\pip'
    else:  # Linux/Mac
        pip_cmd = 'venv/bin/pip'
    
    # Si venv n'existe pas, utiliser pip système
    if not os.path.exists(pip_cmd):
        pip_cmd = 'pip'
    
    if not run_command(f"{pip_cmd} install -r requirements.txt", "Installation des packages"):
        print("  ⚠️  Certaines dépendances n'ont pas pu être installées")
        print("  💡 Essayez manuellement : pip install -r requirements.txt")
    
    # Étape 4 : Téléchargement du modèle YOLO
    print_step(4, "Téléchargement du modèle YOLO")
    
    if os.name == 'nt':
        python_cmd = 'venv\\Scripts\\python'
    else:
        python_cmd = 'venv/bin/python'
    
    if not os.path.exists(python_cmd):
        python_cmd = sys.executable
    
    download_cmd = f'{python_cmd} -c "from ultralytics import YOLO; model = YOLO(\'yolov8n.pt\'); print(\'Modèle téléchargé\')"'
    
    if not run_command(download_cmd, "Téléchargement YOLOv8n"):
        print("  ⚠️  Le modèle sera téléchargé au premier lancement")
    
    # Étape 5 : Vérification de la structure
    print_step(5, "Vérification de la structure")
    
    required_dirs = ['data', 'models', 'images', 'templates', 'static']
    all_ok = True
    
    for dir_name in required_dirs:
        if os.path.exists(dir_name):
            print(f"  ✓ Dossier {dir_name}/ existe")
        else:
            print(f"  ✗ Dossier {dir_name}/ manquant")
            all_ok = False
    
    # Résumé
    print("\n" + "=" * 70)
    print("📊 RÉSUMÉ DE L'INSTALLATION")
    print("=" * 70)
    
    if all_ok:
        print("\n✅ Installation terminée avec succès !")
        print("\n📝 Prochaines étapes :")
        print("  1. Activer l'environnement virtuel :")
        if os.name == 'nt':
            print("     venv\\Scripts\\activate")
        else:
            print("     source venv/bin/activate")
        print("\n  2. Passer à l'ÉTAPE 2 : Base de données")
    else:
        print("\n⚠️  Installation complétée avec des avertissements")
        print("Vérifiez les erreurs ci-dessus")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    main()
