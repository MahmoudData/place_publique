# Configuration du Projet : Place Publique (FastAPI Version)

## 1. Contexte et Objectif

Développer une solution de comptage automatisé pour la **Place de la Comédie à Montpellier**.
**Cibles :** Flux de personnes et véhicules pour l'aide à la décision des commerçants et de la ville.
**Source :** Webcams publiques de Montpellier.



## 2. Stack Technique Actualisée


**Framework Web :** **FastAPI** (remplace Flask pour de meilleures performances asynchrones).
**Serveur ASGI :** **Uvicorn** (pour le développement) et **Gunicorn + Uvicorn workers** (pour la production).
**IA :** YOLOv11 (Ultralytics) - Modèles pré-entraînés fine-tunés si besoin.
**Base de données :** SQLite avec **SQLAlchemy** (Asynchrone) pour le stockage temporel.
**Frontend :** Templates **Jinja2** (via FastAPI) + **Chart.js** pour les dashboards.



## 3. Structure de fichiers (Refactorisée)

```text
place_publique/
├── app/
│   ├── main.py          # Point d'entrée FastAPI
│   ├── api/             # Endpoints (Webcams, Stats, Inférence)
│   ├── core/            # Logique métier (yolo_engine.py, config.py)
│   ├── db/              # Modèles SQLAlchemy et base de données
│   ├── static/          # Assets (CSS, JS Chart.js)
│   └── templates/       # Vues HTML (Jinja2)
├── scripts/
│   └── worker.py        # Script périodique de capture (Background Tasks)
├── models/              # YOLOv11 weights (.pt)
├── requirements.txt
[cite_start]└── architecture.md      # Documentation de la scalabilité [cite: 146]

```

## 4. Directives pour Claude Code

### A. Gestion du flux asynchrone

* Utiliser `httpx` (asynchrone) au lieu de `requests` pour récupérer les images des webcams de Montpellier afin de ne pas bloquer l'event loop.

* Implémenter le service d'inférence YOLO dans un thread séparé ou via une `Background Task` de FastAPI pour maintenir la réactivité de l'API.



### B. Inférence et "Place de la Comédie"

* Configurer le `yolo_engine.py` pour filtrer uniquement les classes pertinentes à Montpellier : `person`, `bicycle`, `car`, `motorcycle`, `bus`.

* Prévoir un seuil de confiance (`conf=0.25`) ajustable pour limiter les faux positifs en cas de pluie ou de nuit.



### C. Dashboarding

* Créer un endpoint `/stats/{camera_id}` qui renvoie les données JSON formatées pour Chart.js.

* Utiliser les templates Jinja2 pour afficher une page de monitoring "Live" montrant la dernière image annotée (image encodée en base64 pour éviter le stockage disque inutile).



5. Conformité et Robustesse 

* **RGPD :** Ne stocker que le résultat numérique (ex: `count: 45`) et le timestamp. Supprimer l'image de la mémoire immédiatement après l'inférence.
**Robustesse :** Gérer les timeouts si le site de la ville de Montpellier met du temps à répondre.
