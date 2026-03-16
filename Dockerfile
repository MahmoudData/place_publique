# =============================================================================
# Place Publique - Dockerfile
# =============================================================================
# Image unique avec les deux services :
#   - inference_service.py (APScheduler, YOLO, scraping)
#   - app.py (Flask / Gunicorn)
# =============================================================================

FROM python:3.11-slim

# ---- Dépendances système ----
# libgl1 + libglib2.0 : OpenCV
# ffmpeg : Streamlink (capture Twitch)
# curl : healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends \
        libgl1 \
        libglib2.0-0 \
        ffmpeg \
        curl \
    && rm -rf /var/lib/apt/lists/*

# ---- Répertoire de travail ----
WORKDIR /app

# ---- Dépendances Python (cache layer) ----
COPY app/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ---- Code applicatif ----
COPY app/ .

# ---- Créer les répertoires nécessaires ----
RUN mkdir -p data images static/images

# ---- Variables d'environnement ----
ENV PYTHONUNBUFFERED=1
ENV FLASK_DEBUG=0

# ---- Port Flask ----
EXPOSE 5000

# ---- Healthcheck ----
HEALTHCHECK --interval=60s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:5000/ || exit 1

# ---- Démarrage : inference en background + Gunicorn au premier plan ----
CMD ["bash", "-c", "python inference_service.py & sleep 3 && gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app"]
