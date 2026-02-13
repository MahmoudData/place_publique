# PROMPT CLAUDE CODE - Place Publique

## Contexte du projet

Je développe "Place Publique", un système de comptage automatique de personnes et véhicules via webcam pour des espaces publics (places, ports, stations de ski).

**Stack technique** :
- Python 3.8+
- Flask (frontend web)
- SQLite (base de données)
- YOLOv8 (détection d'objets)
- APScheduler (tâches périodiques)

**Architecture MVP** :
```
Frontend Flask ← API REST → Base de données SQLite
                              ↑
                    Service d'inférence (YOLO)
                              ↓
                    Webcam (scraping toutes les 5 min)
```

**Webcam ciblée** :
- Place de la Comédie, Montpellier
- URL pattern : `https://filmspv.viewsurf.com/montpellier03/comedie/media_{timestamp}.jpg`
- Timestamp = Unix timestamp arrondi à 5 minutes

**Classes à détecter** :
- person, bicycle, car, motorcycle, bus, truck

---

## Structure existante

J'ai déjà créé la structure de base dans `place_publique/` :

```
place_publique/
├── config.py           # Configuration (WEBCAM_CONFIG, CLASSES_TO_DETECT, etc.)
├── requirements.txt    # Dépendances
├── README.md
├── .gitignore
├── data/              # Pour la BDD SQLite
├── models/            # Pour stocker yolov8n.pt
├── images/            # Images temporaires
├── templates/         # Templates HTML
└── static/            # CSS, JS
    ├── css/
    └── js/
```

Le fichier `config.py` contient déjà :
- `WEBCAM_CONFIG` : Configuration de la webcam
- `CLASSES_TO_DETECT` : Liste des classes
- `DATABASE_PATH` : Chemin vers SQLite
- `DETECTION_INTERVAL_MINUTES` : 5 minutes

---

## MISSION : Développer l'application étape par étape

### ÉTAPE 1 : Base de données (database.py)

Créer `database.py` avec SQLAlchemy qui :

1. **Définit les modèles** :
   - `Webcam` (id, name, location, url_pattern, is_active, created_at)
   - `Detection` (id, webcam_id, timestamp, class_name, count, confidence_avg)
   - `Image` optionnel (id, webcam_id, timestamp, image_path, annotated_path)

2. **Fonctions utilitaires** :
   - `init_db()` : Créer les tables
   - `get_db_session()` : Obtenir une session
   - `add_webcam(name, location, url_pattern)` : Ajouter une webcam
   - `save_detection(webcam_id, timestamp, class_name, count, confidence)` : Sauvegarder une détection
   - `get_detections(webcam_id, hours=24)` : Récupérer les détections des X dernières heures

3. **Script de test** à la fin :
   ```python
   if __name__ == "__main__":
       init_db()
       # Ajouter la webcam Place Comédie
       # Ajouter quelques détections de test
       # Afficher les résultats
   ```

**Contraintes** :
- Utiliser SQLAlchemy ORM
- Base SQLite (`config.DATABASE_PATH`)
- Gestion propre des sessions
- Logging pour debug

---

### ÉTAPE 2 : Service d'inférence (inference_service.py)

Créer `inference_service.py` qui :

1. **Classe `WebcamScraper`** :
   ```python
   def get_current_timestamp():
       # Arrondir à 5 minutes
   
   def download_image(timestamp):
       # Construire URL et télécharger
       # Essayer timestamp actuel, puis -5min, -10min
   ```

2. **Classe `YOLODetector`** :
   ```python
   def __init__(self):
       self.model = YOLO('yolov8n.pt')
   
   def detect(self, image_path):
       # Appliquer YOLO
       # Retourner dict {class_name: count}
   ```

3. **Classe `InferenceService`** :
   ```python
   def __init__(self):
       self.scraper = WebcamScraper()
       self.detector = YOLODetector()
       self.db = get_db_session()
   
   def run_once():
       # 1. Télécharger image
       # 2. Détecter objets
       # 3. Sauvegarder en BDD
       # 4. Logger les résultats
   
   def start_scheduler():
       # APScheduler pour exécuter toutes les 5 min
   ```

4. **Point d'entrée** :
   ```python
   if __name__ == "__main__":
       service = InferenceService()
       service.start_scheduler()
       # Garder le programme actif
   ```

**Contraintes** :
- Gérer les erreurs (image non disponible, YOLO échoue)
- Logger chaque action
- Ne pas crasher si une itération échoue
- Filtrer seulement les classes de `config.CLASSES_TO_DETECT`

---

### ÉTAPE 3 : Frontend Flask (app.py)

Créer `app.py` avec Flask :

1. **Routes** :
   ```python
   @app.route('/')
   def index():
       # Page d'accueil avec liste des webcams
   
   @app.route('/webcam/<int:webcam_id>')
   def webcam_detail(webcam_id):
       # Page de détail d'une webcam avec graphiques
   
   @app.route('/api/detections/<int:webcam_id>')
   def api_detections(webcam_id):
       # API JSON pour Chart.js
       # Format : {labels: [...], datasets: [{label: 'person', data: [...]}]}
   ```

2. **Templates** :
   - `templates/base.html` : Template de base (Bootstrap)
   - `templates/index.html` : Page d'accueil
   - `templates/webcam_detail.html` : Détail webcam avec graphiques

3. **Configuration** :
   ```python
   app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DATABASE_PATH}'
   app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
   ```

**Contraintes** :
- Interface simple et claire
- Responsive (Bootstrap)
- Gérer le cas "aucune donnée"
- Format API compatible Chart.js

---

### ÉTAPE 4 : Dashboard et graphiques

Créer `static/js/charts.js` et améliorer `templates/webcam_detail.html` :

1. **JavaScript pour Chart.js** :
   ```javascript
   // Fetch data depuis /api/detections/<id>
   // Créer graphique ligne avec Chart.js
   // Afficher toutes les classes dans le même graphique
   // Refresh toutes les 5 minutes
   ```

2. **Template amélioré** :
   - Affichage du nom de la webcam
   - Graphique Chart.js (canvas)
   - Tableau récapitulatif
   - Dernière image annotée (si disponible)
   - Sélecteur de période (24h, 7j, 30j)

3. **CSS** (`static/css/style.css`) :
   - Style propre et moderne
   - Couleurs cohérentes
   - Layout responsive

**Contraintes** :
- Graphiques clairs et lisibles
- Légende pour chaque classe
- Gestion du temps (timezone locale)
- Performance (ne pas charger trop de données)

---

### ÉTAPE 5 : Script de démarrage

Créer `start.sh` (Linux/Mac) et `start.bat` (Windows) :

**start.sh** :
```bash
#!/bin/bash

echo "🚀 Démarrage de Place Publique"

# Terminal 1 : Inference service
python inference_service.py &
PID1=$!

# Attendre 2 secondes
sleep 2

# Terminal 2 : Flask app
python app.py &
PID2=$!

echo "✅ Services démarrés"
echo "   - Inference service (PID: $PID1)"
echo "   - Flask app (PID: $PID2)"
echo ""
echo "📊 Dashboard : http://localhost:5000"
echo ""
echo "Pour arrêter : Ctrl+C puis : kill $PID1 $PID2"

# Attendre
wait
```

---

## Instructions d'implémentation

**Pour chaque étape** :

1. **Lire le fichier `config.py`** pour comprendre les constantes
2. **Implémenter le fichier demandé** avec :
   - Imports nécessaires
   - Classes/fonctions décrites
   - Gestion d'erreurs robuste
   - Logging approprié
   - Docstrings claires
   - Type hints si possible

3. **Tester le fichier** avec un `if __name__ == "__main__":` qui :
   - Initialise les composants
   - Fait un test simple
   - Affiche les résultats

4. **Me demander validation** avant de passer à l'étape suivante

---

## Exemple de code attendu (database.py)

```python
"""
Gestion de la base de données Place Publique
"""

from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timedelta
import config

Base = declarative_base()

class Webcam(Base):
    """Modèle Webcam"""
    __tablename__ = 'webcams'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    location = Column(String)
    url_pattern = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relation
    detections = relationship('Detection', back_populates='webcam')

class Detection(Base):
    """Modèle Detection"""
    __tablename__ = 'detections'
    
    id = Column(Integer, primary_key=True)
    webcam_id = Column(Integer, ForeignKey('webcams.id'))
    timestamp = Column(DateTime, nullable=False)
    class_name = Column(String, nullable=False)
    count = Column(Integer, nullable=False)
    confidence_avg = Column(Float)
    
    # Relation
    webcam = relationship('Webcam', back_populates='detections')

# Engine et session
engine = create_engine(f'sqlite:///{config.DATABASE_PATH}')
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Créer toutes les tables"""
    Base.metadata.create_all(engine)
    print("✓ Base de données initialisée")

# ... suite du code
```

---

## Critères de qualité

- ✅ **Code propre** : PEP 8, docstrings, commentaires
- ✅ **Robuste** : Gestion d'erreurs, logging
- ✅ **Testé** : Script de test dans chaque fichier
- ✅ **Simple** : MVP = fonctionnel, pas parfait
- ✅ **Documenté** : README à jour avec instructions

---

## Questions à me poser avant de commencer

1. Dois-je utiliser Flask-SQLAlchemy ou SQLAlchemy pure ?
2. Pour Chart.js, quelle version (CDN ou npm) ?
3. Format de date préféré (ISO, epoch, autre) ?
4. Faut-il gérer l'authentification (login) ?
5. Images annotées : sauvegarder ou juste afficher ?

---

## Commençons !

**Étape 1 : database.py**

Crée le fichier `database.py` selon les spécifications ci-dessus.
Une fois terminé, montre-moi le code et nous passerons à l'étape 2.