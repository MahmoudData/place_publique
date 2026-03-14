"""
Service d'inférence Place Publique
- Scrape les webcams toutes les 5 minutes
- Détecte les objets avec YOLOv8
- Sauvegarde les résultats en BDD
- Conserve la dernière image annotée par webcam

Scrapers disponibles :
  - ViewsurfScraper : webcam Viewsurf (URL horodatée)
  - TwitchScraper   : stream Twitch live via Streamlink + OpenCV
"""

import logging
import os
import time
import unicodedata
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
# Utilitaires
# ---------------------------------------------------------------------------

def _safe_name(name: str) -> str:
    """
    Transforme un nom de webcam en identifiant sûr pour un nom de fichier :
    - Supprime les accents (é→e, è→e, â→a, etc.)
    - Remplace espaces et apostrophes par des underscores
    - Ne conserve que les caractères alphanumériques et _
    """
    # Normalisation Unicode NFD : décompose les lettres accentuées
    normalized = unicodedata.normalize('NFD', name)
    # Supprimer les caractères de combinaison (accents)
    ascii_name = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    # Remplacer espaces et apostrophes par _
    ascii_name = ascii_name.replace(' ', '_').replace("'", '_')
    # Garder seulement alphanum + _
    ascii_name = ''.join(c for c in ascii_name if c.isalnum() or c == '_')
    return ascii_name


# ---------------------------------------------------------------------------
# ViewsurfScraper (anciennement WebcamScraper)
# ---------------------------------------------------------------------------

class ViewsurfScraper:
    """Télécharge les images de la webcam Viewsurf (URL horodatée)."""

    def __init__(self, url_base: str, url_suffix: str, tmp_dir: Path):
        self.url_base  = url_base
        self.url_suffix = url_suffix
        self.tmp_dir   = tmp_dir
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

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
            dest = self.tmp_dir / f"tmp_{ts}.jpg"

            # Haute qualité d'abord, puis miniature
            for url in [f"{self.url_base}{ts}{self.url_suffix}",
                        f"{self.url_base}{ts}_tn{self.url_suffix}"]:
                if self._fetch(url, dest):
                    return dest

        logger.warning("Viewsurf : aucune image disponible après 3 tentatives.")
        return None

    def cleanup(self, path: Path) -> None:
        """Supprime le fichier temporaire."""
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("Cleanup impossible : %s", exc)


# ---------------------------------------------------------------------------
# TwitchScraper
# ---------------------------------------------------------------------------

class TwitchScraper:
    """
    Capture une frame depuis un stream Twitch live.

    Utilise l'API Python Streamlink pour récupérer l'URL HLS, puis
    OpenCV pour lire la vidéo et extraire une image.
    """

    def __init__(self, channel: str, tmp_dir: Path):
        """
        Args:
            channel: Nom de la chaîne Twitch (ex. 'villebethunegplace')
            tmp_dir: Dossier temporaire où stocker la frame
        """
        self.channel = channel
        self.tmp_dir = tmp_dir
        self.tmp_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------

    def _get_stream_url(self) -> str | None:
        """
        Récupère l'URL HLS du stream via l'API Python de Streamlink.

        Returns:
            URL HLS (str) ou None si le stream est hors ligne / erreur.
        """
        try:
            from streamlink import Streamlink

            session = Streamlink()
            streams = session.streams(f"https://www.twitch.tv/{self.channel}")

            if not streams:
                logger.warning("Twitch %s : aucun stream disponible.", self.channel)
                return None

            url = streams["best"].url
            logger.debug("Twitch %s : stream trouvé (%s).",
                         self.channel, list(streams.keys()))
            return url

        except Exception as exc:
            logger.error("Twitch %s : erreur Streamlink : %s", self.channel, exc)
            return None

    # ------------------------------------------------------------------

    def download_latest(self) -> Path | None:
        """
        Capture une frame depuis le stream Twitch.

        Returns:
            Path vers l'image capturée, ou None en cas d'échec.
        """
        import cv2

        stream_url = self._get_stream_url()
        if not stream_url:
            return None

        dest = self.tmp_dir / f"tmp_twitch_{self.channel}_{int(time.time())}.jpg"

        try:
            logger.debug("Twitch %s : connexion au stream OpenCV…", self.channel)
            cap = cv2.VideoCapture(stream_url)

            if not cap.isOpened():
                logger.error("Twitch %s : OpenCV ne peut pas ouvrir le stream.", self.channel)
                return None

            # Lire quelques frames pour stabiliser le buffer HLS
            for _ in range(3):
                cap.read()

            # Frame finale
            ret, frame = cap.read()
            cap.release()

            if not ret or frame is None:
                logger.error("Twitch %s : frame non récupérée.", self.channel)
                return None

            cv2.imwrite(str(dest), frame)
            size_kb = dest.stat().st_size / 1024
            logger.debug("Twitch %s : frame sauvegardée (%.1f KB).", self.channel, size_kb)
            return dest

        except Exception as exc:
            logger.error("Twitch %s : erreur OpenCV : %s", self.channel, exc)
            # Nettoyage partiel
            if dest.exists():
                dest.unlink(missing_ok=True)
            return None

    def cleanup(self, path: Path) -> None:
        """Supprime le fichier temporaire."""
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            logger.debug("Cleanup impossible : %s", exc)


# ---------------------------------------------------------------------------
# Factory : choisit le bon scraper selon webcam.type
# ---------------------------------------------------------------------------

def make_scraper(webcam: dict, tmp_dir: Path):
    """
    Retourne l'instance de scraper appropriée selon webcam['type'].

    Args:
        webcam:  Dict retourné par add_webcam / get_webcam
        tmp_dir: Dossier pour les images temporaires

    Returns:
        ViewsurfScraper | TwitchScraper
    """
    webcam_type = webcam.get('type', 'viewsurf')

    if webcam_type == 'twitch':
        channel = webcam.get('channel')
        if not channel:
            raise ValueError(
                f"Webcam '{webcam['name']}' de type 'twitch' sans champ 'channel'."
            )
        return TwitchScraper(channel=channel, tmp_dir=tmp_dir)

    # Défaut : viewsurf
    return ViewsurfScraper(
        url_base=webcam['url_pattern'],
        url_suffix=config.WEBCAM_CONFIG.get('url_suffix', '.jpg'),
        tmp_dir=tmp_dir,
    )


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

    def detect(self, image_path: Path,
               annotated_dest: Path | None = None
               ) -> tuple[dict[str, int], dict[str, float], Path | None]:
        """
        Applique YOLO sur une image.

        Args:
            image_path:     Image source
            annotated_dest: Où sauvegarder l'image annotée (None = config par défaut)

        Returns:
            counts       : {class_name: count}
            confidences  : {class_name: avg_confidence}
            annotated    : Path vers l'image annotée, ou None
        """
        results = self.model(str(image_path), conf=self.CONF, verbose=False)

        counts: dict[str, int]      = {}
        conf_sums: dict[str, float] = {}

        for result in results:
            for box in result.boxes:
                label = self.model.names[int(box.cls)]
                if label not in self.CLASSES:
                    continue
                counts[label]    = counts.get(label, 0) + 1
                conf_sums[label] = conf_sums.get(label, 0.0) + float(box.conf)

        confidences = {k: conf_sums[k] / counts[k] for k in counts}

        # Sauvegarder l'image annotée (uniquement les classes cibles)
        if annotated_dest is None:
            annotated_dest = Path(config.LAST_IMAGE_PATH)

        annotated_path: Path | None = None
        try:
            annotated_dest.parent.mkdir(parents=True, exist_ok=True)

            # Filtrer les boxes pour ne garder que nos classes
            result = results[0]
            keep = [
                i for i, box in enumerate(result.boxes)
                if self.model.names[int(box.cls)] in self.CLASSES
            ]
            filtered = result[keep] if keep else result[[]]
            annotated_img = filtered.plot()   # numpy array BGR

            import cv2
            cv2.imwrite(str(annotated_dest), annotated_img)
            annotated_path = annotated_dest
            logger.debug("Image annotée sauvegardée : %s", annotated_dest)
        except Exception as exc:
            logger.warning("Impossible de sauvegarder l'image annotée : %s", exc)

        return counts, confidences, annotated_path


# ---------------------------------------------------------------------------
# WebcamJob : un cycle complet pour UNE webcam
# ---------------------------------------------------------------------------

class WebcamJob:
    """
    Exécute le cycle scrape → détecte → sauvegarde pour une webcam donnée.
    """

    def __init__(self, webcam: dict, detector: YOLODetector):
        self.webcam   = webcam
        self.detector = detector
        self.scraper  = make_scraper(webcam, Path(config.IMAGES_DIR))

        # Image annotée spécifique à cette webcam
        static_images = Path(config.LAST_IMAGE_PATH).parent
        self.annotated_dest = static_images / f"last_detection_{webcam['id']}_{_safe_name(webcam['name'])}.jpg"

    # ------------------------------------------------------------------

    def run_once(self) -> bool:
        """
        Exécute un cycle complet : scrape → détecte → sauvegarde.

        Returns:
            True si tout s'est bien passé.
        """
        name = self.webcam['name']
        logger.info("--- Début du cycle : %s ---", name)
        image_path = None

        try:
            # 1. Télécharger l'image
            image_path = self.scraper.download_latest()
            if image_path is None:
                logger.error("[%s] Cycle ignoré : image non disponible.", name)
                return False

            # 2. Détecter
            counts, confidences, _ = self.detector.detect(
                image_path, annotated_dest=self.annotated_dest
            )

            if not counts:
                logger.info("[%s] Aucun objet détecté (classes cibles).", name)
            else:
                logger.info("[%s] Détections : %s", name, counts)

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

            logger.info("[%s] Cycle terminé. %d classe(s) sauvegardée(s).",
                        name, len(counts))
            return True

        except Exception as exc:
            logger.exception("[%s] Erreur inattendue pendant le cycle : %s", name, exc)
            return False

        finally:
            if image_path is not None:
                self.scraper.cleanup(image_path)


# ---------------------------------------------------------------------------
# InferenceService
# ---------------------------------------------------------------------------

class InferenceService:
    """Orchestre scraping + détection + persistance pour toutes les webcams."""

    def __init__(self):
        init_db()

        self.detector = YOLODetector()

        # --- Webcam 1 : Place de la Comédie (Viewsurf) ---
        comedie = add_webcam(
            name=config.WEBCAM_CONFIG['name'],
            location=config.WEBCAM_CONFIG['location'],
            url_pattern=config.WEBCAM_CONFIG['url_base'],
            type='viewsurf',
        )
        logger.info("Webcam : %s (id=%d, type=viewsurf)", comedie['name'], comedie['id'])

        # --- Webcam 2 : Grand'Place Béthune (Twitch) ---
        bethune = add_webcam(
            name="Grand'Place Béthune",
            location="Béthune, France",
            url_pattern="https://www.twitch.tv/villebethunegplace",
            type='twitch',
            channel='villebethunegplace',
        )
        logger.info("Webcam : %s (id=%d, type=twitch)", bethune['name'], bethune['id'])

        # Créer un job par webcam
        self.jobs = [
            WebcamJob(webcam=comedie,  detector=self.detector),
            WebcamJob(webcam=bethune,  detector=self.detector),
        ]

    # ------------------------------------------------------------------

    def run_all_once(self) -> None:
        """Exécute un cycle pour chaque webcam enregistrée."""
        for job in self.jobs:
            job.run_once()

    # ------------------------------------------------------------------

    def start_scheduler(self) -> None:
        """Lance APScheduler (bloquant) : exécute run_all_once toutes les 5 min."""
        interval = config.DETECTION_INTERVAL_MINUTES

        # Premier cycle immédiat
        logger.info("Premier cycle immédiat avant démarrage du scheduler…")
        self.run_all_once()

        scheduler = BlockingScheduler(timezone='UTC')
        scheduler.add_job(
            self.run_all_once,
            trigger='interval',
            minutes=interval,
            id='inference_all',
            name='Inference cycle (all webcams)',
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
