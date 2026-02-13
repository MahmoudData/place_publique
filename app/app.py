"""
Frontend Flask - Place Publique
"""

import unicodedata
from datetime import timedelta
from pathlib import Path

from flask import Flask, jsonify, render_template, abort, request
from sqlalchemy import func

import config
from database import get_all_webcams, get_detections, get_webcam, init_db
from database import SessionLocal, Detection, utcnow

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Init BDD au démarrage
# ---------------------------------------------------------------------------

with app.app_context():
    init_db()


# ---------------------------------------------------------------------------
# Routes HTML
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Page d'accueil — liste des webcams actives."""
    webcams = get_all_webcams()
    return render_template('index.html', webcams=webcams)


# ---------------------------------------------------------------------------
# API JSON
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """Même logique que dans inference_service.py — doit rester synchronisée."""
    normalized = unicodedata.normalize('NFD', name)
    ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    ascii_name = ascii_name.replace(' ', '_').replace("'", '_')
    return ''.join(c for c in ascii_name if c.isalnum() or c == '_')


def _last_image_url(webcam: dict) -> str | None:
    """
    Retourne l'URL Flask de la dernière image annotée pour cette webcam,
    ou None si le fichier n'existe pas encore.

    Logique miroir de WebcamJob.annotated_dest dans inference_service.py :
        static/images/last_detection_{id}_{safe_name}.jpg
    """
    static_images = Path(config.LAST_IMAGE_PATH).parent
    filename = f"last_detection_{webcam['id']}_{_safe_name(webcam['name'])}.jpg"
    filepath = static_images / filename

    if filepath.exists():
        return f"/static/images/{filename}"

    return None


@app.route('/api/detections/<int:webcam_id>')
def api_detections(webcam_id: int):
    """
    Retourne les détections au format Chart.js.

    Query params:
        hours (int, default 24) : fenêtre temporelle

    Response:
        {
          "last_image_url": "/static/images/last_detection_1_Place_de_la_Comedie.jpg" | null,
          "labels": ["2026-02-11T10:00:00Z", ...],
          "datasets": [
            {"label": "person", "data": [12, 8, 15, ...]},
            ...
          ]
        }
    """
    webcam = get_webcam(webcam_id)
    if webcam is None:
        abort(404)

    try:
        hours = int(request.args.get('hours', 24))
        hours = max(1, min(hours, 720))   # borner entre 1h et 30j
    except ValueError:
        hours = 24

    rows = get_detections(webcam_id, hours=hours)
    image_url = _last_image_url(webcam)

    if not rows:
        return jsonify({'last_image_url': image_url, 'labels': [], 'datasets': []})

    # Collecter les timestamps uniques (triés) et les classes présentes
    timestamps = sorted({r['timestamp'] for r in rows})
    classes    = sorted({r['class_name'] for r in rows})

    # Construire un index {(timestamp, class_name): count}
    index: dict = {}
    for r in rows:
        index[(r['timestamp'], r['class_name'])] = r['count']

    # Labels ISO 8601
    labels = [ts.strftime('%Y-%m-%dT%H:%M:%SZ') for ts in timestamps]

    # Couleurs par classe (cohérentes avec le CSS)
    COLORS = {
        'person':     'rgba(54,  162, 235, 0.8)',  # bleu
        'bicycle':    'rgba(75,  192, 192, 0.8)',  # vert-cyan
        'car':        'rgba(255, 99,  132, 0.8)',  # rouge
        'motorcycle': 'rgba(255, 159,  64, 0.8)',  # orange
        'truck':      'rgba(153, 102, 255, 0.8)',  # violet
    }

    datasets = []
    for cls in classes:
        datasets.append({
            'label':           cls,
            'data':            [index.get((ts, cls), 0) for ts in timestamps],
            'borderColor':     COLORS.get(cls, 'rgba(100,100,100,0.8)'),
            'backgroundColor': COLORS.get(cls, 'rgba(100,100,100,0.2)').replace('0.8', '0.2'),
            'tension':         0.3,
            'fill':            False,
        })

    return jsonify({'last_image_url': image_url, 'labels': labels, 'datasets': datasets})


@app.route('/api/stats/<int:webcam_id>')
def api_stats(webcam_id: int):
    """
    Retourne les statistiques agrégées de fréquentation.

    Query params:
        period : 'hourly' | 'daily' | 'weekly' | 'monthly'  (défaut: hourly)
        class  : nom de classe YOLO (défaut: 'person'), doit être dans CLASSES_TO_DETECT

    Response:
        {
          "labels":     ["00h", "01h", ...],
          "data":       [5.2, 3.1, ...],
          "period":     "hourly",
          "class_name": "person"
        }
    """
    if get_webcam(webcam_id) is None:
        abort(404)

    period = request.args.get('period', 'hourly')
    if period not in ('hourly', 'daily', 'weekly', 'monthly'):
        period = 'hourly'

    class_name = request.args.get('class', 'person')
    if class_name not in config.CLASSES_TO_DETECT:
        class_name = 'person'

    session = SessionLocal()
    try:
        base_q = (
            session.query(Detection)
            .filter(
                Detection.webcam_id == webcam_id,
                Detection.class_name == class_name,
            )
        )

        if period == 'hourly':
            # Moyenne par heure de la journée (0-23) sur les 30 derniers jours
            since = utcnow() - timedelta(days=30)
            rows = (
                base_q.filter(Detection.timestamp >= since)
                .with_entities(
                    func.strftime('%H', Detection.timestamp).label('bucket'),
                    func.avg(Detection.count).label('value'),
                )
                .group_by('bucket')
                .order_by('bucket')
                .all()
            )
            # Remplir les 24 heures (certaines peuvent être absentes)
            index = {r.bucket: round(r.value, 1) for r in rows}
            labels = [f"{h:02d}h" for h in range(24)]
            data   = [index.get(f"{h:02d}", 0) for h in range(24)]

        elif period == 'daily':
            # Total par jour sur les 30 derniers jours
            since = utcnow() - timedelta(days=30)
            rows = (
                base_q.filter(Detection.timestamp >= since)
                .with_entities(
                    func.strftime('%Y-%m-%d', Detection.timestamp).label('bucket'),
                    func.sum(Detection.count).label('value'),
                )
                .group_by('bucket')
                .order_by('bucket')
                .all()
            )
            labels = [r.bucket for r in rows]
            data   = [int(r.value) for r in rows]

        elif period == 'weekly':
            # Total par semaine sur les 52 dernières semaines
            since = utcnow() - timedelta(weeks=52)
            rows = (
                base_q.filter(Detection.timestamp >= since)
                .with_entities(
                    func.strftime('%Y-W%W', Detection.timestamp).label('bucket'),
                    func.sum(Detection.count).label('value'),
                )
                .group_by('bucket')
                .order_by('bucket')
                .all()
            )
            labels = [r.bucket for r in rows]
            data   = [int(r.value) for r in rows]

        else:  # monthly
            # Total par mois sur les 24 derniers mois
            since = utcnow() - timedelta(days=730)
            rows = (
                base_q.filter(Detection.timestamp >= since)
                .with_entities(
                    func.strftime('%Y-%m', Detection.timestamp).label('bucket'),
                    func.sum(Detection.count).label('value'),
                )
                .group_by('bucket')
                .order_by('bucket')
                .all()
            )
            labels = [r.bucket for r in rows]
            data   = [int(r.value) for r in rows]

    finally:
        session.close()

    return jsonify({'labels': labels, 'data': data, 'period': period, 'class_name': class_name})


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
