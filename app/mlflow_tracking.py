"""
MLflow tracking & drift detection — Place Publique

Suit les performances des modeles YOLO en production et detecte
les derives via un z-score sur fenetre glissante.

Usage dans inference_service.py :
    tracker, drift = create_tracker(webcam_dict)
    tracker.log_cycle(counts, confidences, inference_time, ...)
    alerts = drift.check_cycle(counts, confidences, gender_rate)
"""

import collections
import logging
import unicodedata
from datetime import datetime, timezone

import config

logger = logging.getLogger(__name__)

# Guard import — MLflow est optionnel
try:
    import mlflow
    MLFLOW_AVAILABLE = True
except ImportError:
    MLFLOW_AVAILABLE = False
    logger.warning("mlflow non installe — tracking desactive.")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_experiment_name(webcam_name: str) -> str:
    """Genere un nom d'experience MLflow propre a partir du nom de webcam."""
    normalized = unicodedata.normalize('NFD', webcam_name)
    ascii_name = ''.join(
        c for c in normalized if unicodedata.category(c) != 'Mn'
    )
    ascii_name = ascii_name.replace(' ', '_').replace("'", '_').lower()
    ascii_name = ''.join(c for c in ascii_name if c.isalnum() or c == '_')
    return f"{config.MLFLOW_EXPERIMENT_PREFIX}_{ascii_name}"


# ---------------------------------------------------------------------------
# ProductionTracker
# ---------------------------------------------------------------------------

class ProductionTracker:
    """Log les metriques de chaque cycle d'inference dans MLflow."""

    def __init__(self, webcam_name: str, webcam_id: int):
        self.webcam_name = webcam_name
        self.webcam_id = webcam_id
        self.enabled = MLFLOW_AVAILABLE and config.MLFLOW_ENABLED
        self._current_run = None
        self._current_day: str | None = None
        self._step = 0

        if not self.enabled:
            return

        mlflow.set_tracking_uri(config.MLFLOW_TRACKING_URI)
        experiment_name = _safe_experiment_name(webcam_name)
        mlflow.set_experiment(experiment_name)
        logger.info("MLflow experiment : %s", experiment_name)

    # ------------------------------------------------------------------

    def _ensure_run(self):
        """Demarre un nouveau run si le jour a change (un run par jour)."""
        if not self.enabled:
            return

        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        if self._current_day == today and self._current_run is not None:
            return

        # Fermer le run precedent
        if self._current_run is not None:
            mlflow.end_run()
            self._step = 0

        self._current_run = mlflow.start_run(run_name=today)
        self._current_day = today

        mlflow.set_tags({
            'webcam_id': str(self.webcam_id),
            'webcam_name': self.webcam_name,
            'model_detection': config.YOLO_MODEL,
            'model_gender': config.YOLO_GENDER_MODEL,
            'confidence_threshold': str(config.YOLO_CONFIDENCE),
        })

        logger.info("MLflow run demarre : %s (webcam=%s)", today, self.webcam_name)

    # ------------------------------------------------------------------

    def log_cycle(self, counts: dict, confidences: dict,
                  inference_time_s: float, image_downloaded: bool,
                  gender_stats: dict) -> None:
        """Log toutes les metriques d'un cycle d'inference."""
        if not self.enabled:
            return

        self._ensure_run()

        metrics = {
            'total_detections': sum(counts.values()),
            'inference_time_s': round(inference_time_s, 3),
            'image_download_success': 1 if image_downloaded else 0,
            'gender_classification_rate': round(gender_stats.get('rate', 0), 3),
            'count_men': gender_stats.get('men', 0),
            'count_women': gender_stats.get('women', 0),
        }

        for cls, count in counts.items():
            safe_cls = cls.lower().replace(' ', '_')
            metrics[f'count_{safe_cls}'] = count
        for cls, conf in confidences.items():
            safe_cls = cls.lower().replace(' ', '_')
            metrics[f'confidence_{safe_cls}'] = round(conf, 4)

        mlflow.log_metrics(metrics, step=self._step)
        self._step += 1

        logger.debug("MLflow: %d metriques loguees (step=%d)",
                      len(metrics), self._step - 1)

    # ------------------------------------------------------------------

    def log_failure(self, reason: str) -> None:
        """Log un echec de cycle (image non disponible, etc.)."""
        if not self.enabled:
            return

        self._ensure_run()
        mlflow.log_metrics({
            'cycle_failure': 1,
            'image_download_success': 0,
            'total_detections': 0,
        }, step=self._step)
        mlflow.set_tag(f'failure_{self._step}', reason)
        self._step += 1

    # ------------------------------------------------------------------

    def close(self):
        """Termine le run MLflow proprement."""
        if self.enabled and self._current_run is not None:
            mlflow.end_run()
            self._current_run = None
            logger.info("MLflow run termine pour %s.", self.webcam_name)


# ---------------------------------------------------------------------------
# DriftDetector
# ---------------------------------------------------------------------------

class DriftDetector:
    """
    Detection de derive par comparaison a une moyenne glissante.

    Utilise un z-score simple : si la valeur courante est a plus de
    z_threshold ecarts-types en dessous de la moyenne, alerte.
    """

    def __init__(self, window_size: int = 50, z_threshold: float = 2.5):
        self.window_size = window_size
        self.z_threshold = z_threshold
        self._windows: dict[str, collections.deque] = {}
        self._min_samples = 10

    # ------------------------------------------------------------------

    def _update_and_check(self, metric: str, value: float) -> str | None:
        """Ajoute la valeur et retourne un message d'alerte si derive."""
        if metric not in self._windows:
            self._windows[metric] = collections.deque(maxlen=self.window_size)

        window = self._windows[metric]

        if len(window) < self._min_samples:
            window.append(value)
            return None

        # Stats AVANT d'ajouter la valeur courante
        values = list(window)
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = variance ** 0.5

        window.append(value)

        if std < 1e-6:
            return None

        z_score = (value - mean) / std

        if z_score < -self.z_threshold:
            return (f"{metric}: valeur={value:.2f}, "
                    f"moyenne={mean:.2f}, z-score={z_score:.2f}")

        return None

    # ------------------------------------------------------------------

    def check_cycle(self, counts: dict, confidences: dict,
                    gender_rate: float) -> list[str]:
        """
        Verifie la derive pour les metriques cles.
        Retourne une liste de messages d'alerte (vide si OK).
        """
        alerts = []

        total = sum(counts.values())
        alert = self._update_and_check('total_detections', total)
        if alert:
            alerts.append(alert)

        if confidences:
            avg_conf = sum(confidences.values()) / len(confidences)
            alert = self._update_and_check('avg_confidence', avg_conf)
            if alert:
                alerts.append(alert)

        alert = self._update_and_check('gender_classification_rate', gender_rate)
        if alert:
            alerts.append(alert)

        if alerts and config.MLFLOW_ALERT_WEBHOOK:
            self._send_webhook(alerts)

        return alerts

    # ------------------------------------------------------------------

    def _send_webhook(self, alerts: list[str]) -> None:
        """Envoie les alertes via webhook HTTP (Slack/Discord/Teams)."""
        try:
            import requests
            payload = {
                'text': '[Place Publique - DRIFT]\n' + '\n'.join(alerts)
            }
            requests.post(config.MLFLOW_ALERT_WEBHOOK, json=payload, timeout=5)
        except Exception as exc:
            logger.debug("Webhook echoue : %s", exc)


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def create_tracker(webcam: dict) -> tuple[ProductionTracker, DriftDetector]:
    """Cree un tracker + drift detector pour une webcam."""
    tracker = ProductionTracker(
        webcam_name=webcam['name'],
        webcam_id=webcam['id'],
    )
    drift = DriftDetector(
        window_size=config.MLFLOW_DRIFT_WINDOW_SIZE,
        z_threshold=config.MLFLOW_DRIFT_Z_THRESHOLD,
    )
    return tracker, drift
