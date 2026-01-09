# place_publique

Place Publique - FlowView
Solution d'analyse vidéo intelligente pour le comptage de flux dans les espaces publics.

Contexte du projet
FlowView est une startup spécialisée dans l'analyse vidéo intelligente. Le projet Place Publique vise à fournir aux acteurs territoriaux (villes, stations de ski, ports, offices de tourisme) un outil performant pour quantifier les flux de visiteurs et de véhicules à partir de caméras déjà installées.

Ce projet a été réalisé dans le cadre du Master 2 Data/IA (Mise en situation professionnelle).

Objectifs
Comptage automatisé : Détection de piétons, véhicules, skieurs ou bateaux selon le contexte client.

Respect de la vie privée : Solution Privacy by Design conforme au RGPD (pas de reconnaissance faciale, uniquement du dénombrement).

Aide à la décision : Fournir des statistiques pour dimensionner les services publics et gérer les infrastructures.

Fonctionnalités
L'application se décompose en plusieurs modules :

Backend d'Inférence (IA) :

Utilisation de modèles YOLO (You Only Look Once) pour la détection d'objets.

Traitement périodique des flux vidéo ou images statiques.

Stockage des résultats (comptages par classe) en base de données temporelle.

Frontend (Application Web) :

Interface développée avec Flask.

Tableau de bord de visualisation des statistiques (graphiques Chart.js).

Gestion des caméras (ajout/suppression de flux).

Monitoring MLOps :

Suivi des expériences et modèles via MLflow.

Structure du dépôt
Ce dépôt contient l'ensemble des livrables techniques et documentaires attendus.

place_publique/ ├── app/ # Code source de l'application Flask │ ├── static/ # Fichiers CSS, JS, Images │ ├── templates/ # Templates HTML (Jinja2) │ ├── app.py # Point d'entrée de l'application web │ └── ... ├── data/ # Données (DB SQLite, CSVs exemples) ├── docs/ # Documentation obligatoire │ ├── architecture.md # Architecture technique et production │ ├── veille.md # Rapport de veille technique (SOTA) │ └── conformite.md # Analyse RGPD et AI Act ├── models/ # Partie Data Science & IA │ ├── notebooks/ # Notebooks d'entraînement et d'évaluation │ ├── weights/ # Poids des modèles entraînés (.pt) │ └── inference.py # Script de détection d'objets ├── tests/ # Tests unitaires ├── requirements.txt # Dépendances Python └── README.md # Ce fichier

Installation et Démarrage
Prérequis
Python 3.9 ou supérieur

Git

1. Cloner le projet
git clone https://github.com/MahmoudData/place_publique.git cd place_publique

2. Créer un environnement virtuel
python -m venv venv

Sur Windows :
venv\Scripts\activate

Sur Mac/Linux :
source venv/bin/activate

3. Installer les dépendances
pip install -r requirements.txt

4. Lancer l'application Web
cd app flask run

L'application sera accessible à l'adresse : http://127.0.0.1:5000

5. Lancer le script d'inférence (Simulation)
Dans un second terminal :

python models/inference.py

Documentation détaillée
Veuillez consulter les documents suivants pour les détails techniques et juridiques :

Rapport de Veille (docs/veille.md) : Comparatif des modèles (YOLO vs R-CNN), stratégies d'annotation et choix techniques.

Architecture de Production (docs/architecture.md) : Proposition de déploiement scalable (Docker, Kubernetes) et gestion de la dérive (Drift).

Conformité & Éthique (docs/conformite.md) : Analyse d'impact (DPIA), conformité AI Act et mesures de protection des données.

Auteurs
Équipe FlowView :

Mahmoud Merheb - Rôle (Lead Tech / MLOps)

Arthur Baron - Rôle ( Data Scientist)

Saadoune Skander - Rôle (Backend Dev)

Projet académique réalisé conformément au sujet Place Publique MSC-2-IA.