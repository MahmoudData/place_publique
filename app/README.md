# Place Publique - MVP

Système de comptage automatique d'objets (personnes, véhicules) via webcam.

## Architecture MVP

```
place_publique/
├── app.py                      # Application Flask (à venir étape 4)
├── inference_service.py        # Service de détection YOLO (étape 3)
├── database.py                 # Gestion BDD SQLite (étape 2)
├── config.py                   # Configuration
├── requirements.txt            # Dépendances Python
├── README.md                   # Ce fichier
│
├── models/                     # Modèles YOLO
│   └── .gitkeep
│
├── data/                       # Base de données
│   └── place_publique.db       # SQLite (créé automatiquement)
│
├── images/                     # Images collectées (temporaire)
│   └── .gitkeep
│
├── templates/                  # Templates HTML Flask (étape 4)
│   └── .gitkeep
│
└── static/                     # CSS, JS, images statiques (étape 5)
    ├── css/
    ├── js/
    └── .gitkeep
```

## Installation

```bash
# 1. Créer environnement virtuel
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 2. Installer dépendances
pip install -r requirements.txt

# 3. Télécharger le modèle YOLO
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

## Utilisation

```bash
# Terminal 1 : Service d'inférence (background)
python inference_service.py

# Terminal 2 : Application Flask (web)
python app.py
```

Puis ouvrir : http://localhost:5000

## Configuration

Fichier `config.py` :
- `WEBCAM_URL_PATTERN` : Pattern URL de la webcam
- `DETECTION_INTERVAL` : Intervalle de détection (minutes)
- `CLASSES_TO_DETECT` : Classes YOLO à détecter

## Statut du projet

- [x] Veille technique
- [x] Script de scraping webcam
- [x] Tests YOLO
- [x] Architecture système
- [ ] ÉTAPE 1 : Structure projet ← EN COURS
- [ ] ÉTAPE 2 : Base de données
- [ ] ÉTAPE 3 : Service d'inférence
- [ ] ÉTAPE 4 : Frontend Flask
- [ ] ÉTAPE 5 : Dashboard graphiques
