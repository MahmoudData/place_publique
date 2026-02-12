"""
Service d'inférence Place Publique
- Scrape la webcam toutes les 5 minutes
- Détecte les objets avec YOLOv8
- Sauvegarde les résultats en BDD
- Conserve la dernière image annotée
"""

import logging
import os
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

import config
from database import add_webcam, init_db, save_detection

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s - %(message)s',
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# WebcamScraper
# ---------------------------------------------------------------------------

class WebcamScraper:
    """Télécharge les images de la webcam viewsurf."""

    BASE_URL = config.WEBCAM_CONFIG['url_base']   # e.g. https://filmspv.viewsurf.com/…/media_
    SUFFIX   = config.WEBCAM_CONFIG['url_suffix']  # .jpg

    # Dossier temporaire pour les images brutes
    TMP_DIR = Path(config.IMAGES_DIR)

    def __init__(self):
        self.TMP_DIR.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Helpers timestamp
    # ------------------------------------------------------------------

    @staticmethod
    def get_rounded_timestamp(offset_minutes: int = 0) -> int:
        """Retourne le timestamp Unix arrondi à 5 minutes + offset."""
        t = int(time.time()) + offset_minutes * 60
        return (t // 300) * 300

    # ------------------------------------------------------------------
    # Téléchargement
    # ------------------------------------------------------------------

    def _fetch(self, url: str, dest: Path) -> bool:
        """Tente de télécharger url vers dest. Retourne True si succès."""
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200 and 'image' in resp.headers.get('Content-Type', ''):
                dest.write_bytes(resp.content)
                logger.debug("Téléchargé %s (%.1f KB)", url, len(resp.content) / 1024)
                return True
        except requests.RequestException as exc:
            logger.debug("Echec fetch %s : %s", url, exc)
        return False

    def download_latest(self) -> Path | None:
        """
        Essaie de télécharger l'image la plus récente disponible.
        Tente le timestamp actuel, puis -5 min, -10 min.

        Returns:
            Path vers l'image téléchargée, ou None si impossible.
        """
        for offset in [0, -5, -10]:
            ts = self.get_rounded_timestamp(offset)
            dest = self.TMP_DIR / f"tmp_{ts}.jpg"

            # Haute qualité d'abord, puis miniature
            for url in [f"{self.BASE_URL}{ts}{self.SUFFIX}",
                        f"{self.BASE_URL}{ts}_tn{self.SUFFIX}"]:
                if self._fetch(url, dest):
                    return dest

        logger.warning("Aucune image disponible après 3 tentatives.")
        return None

    def cleanup(self, path: Path) -> None:
        """Supprime le fichier temporaire."""
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("Cleanup impossible : %s", exc)


# ---------------------------------------------------------------------------
# YOLODetector
# ---------------------------------------------------------------------------

class YOLODetector:
    """Détecte les objets via YOLOv8."""

    CLASSES = set(config.CLASSES_TO_DETECT)
    CONF    = config.YOLO_CONFIDENCE

    def __init__(self):
        from ultralytics import YOLO

        model_path = Path(config.MODELS_DIR) / config.YOLO_MODEL
        if not model_path.exists():
            raise FileNotFoundError(f"Modèle introuvable : {model_path}")

        self.model = YOLO(str(model_path))
        logger.info("Modèle YOLO chargé : %s", model_path)

    def detect(self, image_path: Path) -> tuple[dict[str, int], dict[str, float], Path | None]:
        """
        Applique YOLO sur une image.

        Returns:
            counts       : {class_name: count}
            confidences  : {class_name: avg_confidence}
            annotated    : Path vers l'image annotée (dans static/images/), ou None
        """
        results = self.model(str(image_path), conf=self.CONF, verbose=False)

        counts: dict[str, int]   = {}
        conf_sums: dict[str, float] = {}

        for result in results:
            for box in result.boxes:
                label = self.model.names[int(box.cls)]
                if label not in self.CLASSES:
                    continue
                counts[label]    = counts.get(label, 0) + 1
                conf_sums[label] = conf_sums.get(label, 0.0) + float(box.conf)

        confidences = {k: conf_sums[k] / counts[k] for k in counts}

        # Sauvegarder l'image annotée
        annotated_path: Path | None = None
        try:
            dest = Path(config.LAST_IMAGE_PATH)
            dest.parent.mkdir(parents=True, exist_ok=True)
            annotated_img = results[0].plot()   # numpy array BGR

            import cv2
            cv2.imwrite(str(dest), annotated_img)
            annotated_path = dest
            logger.debug("Image annotée sauvegardée : %s", dest)
        except Exception as exc:
            logger.warning("Impossible de sauvegarder l'image annotée : %s", exc)

        return counts, confidences, annotated_path


# ---------------------------------------------------------------------------
# InferenceService
# ---------------------------------------------------------------------------

class InferenceService:
    """Orchestre scraping + détection + persistance."""

    def __init__(self):
        init_db()

        # S'assurer que la webcam existe en BDD
        self.webcam = add_webcam(
            name=config.WEBCAM_CONFIG['name'],
            location=config.WEBCAM_CONFIG['location'],
            url_pattern=config.WEBCAM_CONFIG['url_base'],
        )
        logger.info("Webcam : %s (id=%d)", self.webcam['name'], self.webcam['id'])

        self.scraper  = WebcamScraper()
        self.detector = YOLODetector()

    # ------------------------------------------------------------------

    def run_once(self) -> bool:
        """
        Exécute un cycle complet : scrape → détecte → sauvegarde.

        Returns:
            True si tout s'est bien passé.
        """
        logger.info("--- Début du cycle d'inférence ---")
        image_path = None

        try:
            # 1. Télécharger l'image
            image_path = self.scraper.download_latest()
            if image_path is None:
                logger.error("Cycle ignoré : image non disponible.")
                return False

            # 2. Détecter
            counts, confidences, _ = self.detector.detect(image_path)

            if not counts:
                logger.info("Aucun objet détecté (classes cibles).")
            else:
                logger.info("Détections : %s", counts)

            # 3. Persister
            ts = datetime.now(timezone.utc)
            for class_name, count in counts.items():
                save_detection(
                    webcam_id=self.webcam['id'],
                    timestamp=ts,
                    class_name=class_name,
                    count=count,
                    confidence=confidences.get(class_name),
                )

            logger.info("Cycle terminé. %d classe(s) sauvegardée(s).", len(counts))
            return True

        except Exception as exc:
            logger.exception("Erreur inattendue pendant le cycle : %s", exc)
            return False

        finally:
            # Nettoyage image temporaire
            if image_path is not None:
                self.scraper.cleanup(image_path)

    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        """Lance APScheduler (bloquant) : exécute run_once toutes les 5 min."""
        interval = config.DETECTION_INTERVAL_MINUTES

        # Premier cycle immédiat
        logger.info("Premier cycle immédiat avant démarrage du scheduler…")
        self.run_once()

        scheduler = BlockingScheduler(timezone='UTC')
        scheduler.add_job(
            self.run_once,
            trigger='interval',
            minutes=interval,
            id='inference',
            name='Inference cycle',
            misfire_grace_time=60,
        )

        logger.info("Scheduler démarré — cycle toutes les %d minutes.", interval)
        logger.info("Appuyez sur Ctrl+C pour arrêter.")

        try:
            scheduler.start()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Arrêt du scheduler.")


# ---------------------------------------------------------------------------
# Entrée principale
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    service = InferenceService()
    service.start_scheduler()
