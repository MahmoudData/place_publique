# Place Publique

Comptage automatique de personnes et vehicules sur des places publiques via webcam, avec detection YOLOv8 et dashboard temps reel.

## Architecture

```
Flask (dashboard)  <--  API REST  -->  SQLite
                                         ^
                               Inference Service
                              (APScheduler / 5 min)
                                    |
                          YOLOv8 detection + genre
                                    |
                              Webcam scraping
```

## Stack technique

- **Detection** : YOLOv8 (detection objets + classification genre)
- **Backend** : Flask + Gunicorn
- **Base de donnees** : SQLite + SQLAlchemy
- **Frontend** : Bootstrap 5 + Chart.js
- **Scheduling** : APScheduler (cycle toutes les 5 min)
- **Tracking** : MLflow (metriques + drift detection)

## Installation locale

```bash
cd app
pip install -r requirements.txt
```

Placer les modeles YOLO dans `app/models/` :
- `best.pt` — detection (person, car, bicycle, motorcycle, truck)
- `best_genre.pt` — classification genre (Man, Woman)

## Lancement local

```bash
# Terminal 1 : service d'inference
cd app
python inference_service.py

# Terminal 2 : serveur Flask
cd app
python app.py
```

Dashboard accessible sur `http://localhost:5000`

## Deploiement Docker

```bash
# Build + lancement
docker compose up --build -d

# Voir les logs
docker compose logs -f

# Arreter
docker compose down
```

## Structure du projet

```
place_publique/
├── app/
│   ├── app.py                 # Frontend Flask + API
│   ├── inference_service.py   # Pipeline YOLO + scraping
│   ├── database.py            # Modeles SQLAlchemy
│   ├── config.py              # Configuration
│   ├── mlflow_tracking.py     # Tracking MLflow + drift
│   ├── requirements.txt
│   ├── models/                # Modeles YOLO (.pt)
│   ├── data/                  # SQLite + MLflow
│   ├── templates/
│   └── static/
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Webcams configurees

| Webcam | Localisation | Source |
|--------|-------------|--------|
| Place de la Comedie | Montpellier | Viewsurf |
| Grand Place Bethune | Bethune | Twitch |

## API

- `GET /api/detections/<webcam_id>?hours=24` — donnees Chart.js (line chart)
- `GET /api/stats/<webcam_id>?period=hourly&class=person` — stats agregees (bar chart)

## MLflow

```bash
mlflow ui --backend-store-uri sqlite:///app/data/mlflow.db
```

Interface MLflow sur `http://localhost:5000` (port par defaut MLflow).
