"""
Frontend Flask - Place Publique
"""

from flask import Flask, jsonify, render_template, abort, request

import config
from database import get_all_webcams, get_detections, get_webcam, init_db

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

@app.route('/api/detections/<int:webcam_id>')
def api_detections(webcam_id: int):
    """
    Retourne les détections au format Chart.js.

    Query params:
        hours (int, default 24) : fenêtre temporelle

    Response:
        {
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

    if not rows:
        return jsonify({'labels': [], 'datasets': []})

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
        'person': 'rgba(54,  162, 235, 0.8)',
        'car':    'rgba(255, 99,  132, 0.8)',
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

    return jsonify({'labels': labels, 'datasets': datasets})


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    app.run(
        host=config.FLASK_HOST,
        port=config.FLASK_PORT,
        debug=config.FLASK_DEBUG,
    )
