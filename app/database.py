"""
Gestion de la base de données Place Publique
SQLAlchemy pure (pas Flask-SQLAlchemy)
"""

import logging
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy import (Boolean, Column, DateTime, Float, ForeignKey, Integer,
                        String, create_engine)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

import config

# Logging
logger = logging.getLogger(__name__)


def utcnow() -> datetime:
    """Retourne l'heure actuelle UTC (timezone-aware)."""
    return datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Base déclarative
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------

class Webcam(Base):
    """Webcam surveillée"""
    __tablename__ = 'webcams'

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False)
    location    = Column(String)
    url_pattern = Column(String, nullable=False)   # URL de base (sans timestamp)
    type        = Column(String, default='viewsurf')  # 'viewsurf' ou 'twitch'
    channel     = Column(String)                   # Channel Twitch (si type='twitch')
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), default=utcnow)

    detections = relationship('Detection', back_populates='webcam',
                               cascade='all, delete-orphan')

    def __repr__(self) -> str:
        return f"<Webcam id={self.id} name={self.name!r} type={self.type!r}>"


class Detection(Base):
    """Résultat de détection pour une classe à un instant T"""
    __tablename__ = 'detections'

    id             = Column(Integer, primary_key=True)
    webcam_id      = Column(Integer, ForeignKey('webcams.id'), nullable=False)
    timestamp      = Column(DateTime(timezone=True), nullable=False, index=True)
    class_name     = Column(String, nullable=False)
    count          = Column(Integer, nullable=False)
    confidence_avg = Column(Float)

    webcam = relationship('Webcam', back_populates='detections')

    def __repr__(self) -> str:
        return (f"<Detection webcam={self.webcam_id} "
                f"ts={self.timestamp} class={self.class_name} count={self.count}>")


# ---------------------------------------------------------------------------
# Engine & Session factory
# ---------------------------------------------------------------------------

os.makedirs(os.path.dirname(config.DATABASE_PATH), exist_ok=True)

engine = create_engine(
    f'sqlite:///{config.DATABASE_PATH}',
    connect_args={'check_same_thread': False},  # nécessaire avec Flask
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


# ---------------------------------------------------------------------------
# Utilitaires
# ---------------------------------------------------------------------------

def init_db() -> None:
    """Créer toutes les tables (idempotent) et migrer les colonnes manquantes."""
    Base.metadata.create_all(engine)
    _migrate_webcam_columns()
    logger.info("Base de données initialisée : %s", config.DATABASE_PATH)


def _migrate_webcam_columns() -> None:
    """
    Ajoute les colonnes 'type' et 'channel' à la table webcams si elles
    n'existent pas encore (migration légère pour BDD existante).
    """
    with engine.connect() as conn:
        from sqlalchemy import text, inspect as sa_inspect
        inspector = sa_inspect(engine)
        existing_cols = {c['name'] for c in inspector.get_columns('webcams')}

        if 'type' not in existing_cols:
            conn.execute(text("ALTER TABLE webcams ADD COLUMN type VARCHAR DEFAULT 'viewsurf'"))
            conn.commit()
            logger.info("Colonne 'type' ajoutée à la table webcams.")

        if 'channel' not in existing_cols:
            conn.execute(text("ALTER TABLE webcams ADD COLUMN channel VARCHAR"))
            conn.commit()
            logger.info("Colonne 'channel' ajoutée à la table webcams.")


@contextmanager
def get_db_session():
    """
    Context manager qui fournit une session SQLAlchemy.

    Usage :
        with get_db_session() as session:
            session.add(...)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Sérialisation
# ---------------------------------------------------------------------------

def _webcam_to_dict(webcam: Webcam) -> dict:
    return {
        'id':          webcam.id,
        'name':        webcam.name,
        'location':    webcam.location,
        'url_pattern': webcam.url_pattern,
        'type':        webcam.type or 'viewsurf',
        'channel':     webcam.channel,
        'is_active':   webcam.is_active,
        'created_at':  webcam.created_at,
    }


# ---------------------------------------------------------------------------
# API publique
# ---------------------------------------------------------------------------

def add_webcam(name: str, location: str, url_pattern: str,
               type: str = 'viewsurf', channel: str | None = None) -> dict:
    """
    Ajoute une webcam si elle n'existe pas déjà (basé sur le nom).

    Args:
        name:        Nom affiché
        location:    Localisation géographique
        url_pattern: URL de base (viewsurf) ou chaîne Twitch (twitch)
        type:        'viewsurf' ou 'twitch'
        channel:     Nom de la chaîne Twitch (si type='twitch')

    Returns:
        Dict {'id', 'name', 'location', 'url_pattern', 'type', 'channel',
              'is_active', 'created_at'}
    """
    with get_db_session() as session:
        existing = session.query(Webcam).filter_by(name=name).first()
        if existing:
            # Mettre à jour les champs si ils ont changé
            changed = False
            for attr, val in [('location', location), ('url_pattern', url_pattern),
                              ('type', type), ('channel', channel)]:
                if getattr(existing, attr) != val:
                    setattr(existing, attr, val)
                    changed = True
            if changed:
                session.flush()
                logger.info("Webcam mise à jour : %s (id=%d)", name, existing.id)
            else:
                logger.info("Webcam déjà présente : %s (id=%d)", name, existing.id)
            return _webcam_to_dict(existing)

        webcam = Webcam(name=name, location=location, url_pattern=url_pattern,
                        type=type, channel=channel)
        session.add(webcam)
        session.flush()   # obtenir l'id avant commit
        result = _webcam_to_dict(webcam)
        logger.info("Webcam ajoutée : %s (id=%d, type=%s)", name, webcam.id, type)
        return result


def save_detection(webcam_id: int, timestamp: datetime,
                   class_name: str, count: int,
                   confidence: float | None = None) -> None:
    """Enregistre une détection en base."""
    with get_db_session() as session:
        detection = Detection(
            webcam_id=webcam_id,
            timestamp=timestamp,
            class_name=class_name,
            count=count,
            confidence_avg=confidence,
        )
        session.add(detection)
    logger.debug("Détection sauvegardée : webcam=%d ts=%s class=%s count=%d",
                 webcam_id, timestamp, class_name, count)


def get_detections(webcam_id: int, hours: int = 24) -> list[dict]:
    """
    Récupère les détections des X dernières heures.

    Returns:
        Liste de dicts :
        [{'timestamp': datetime, 'class_name': str, 'count': int, 'confidence_avg': float}, ...]
    """
    since = utcnow() - timedelta(hours=hours)
    with get_db_session() as session:
        rows = (
            session.query(Detection)
            .filter(
                Detection.webcam_id == webcam_id,
                Detection.timestamp >= since,
            )
            .order_by(Detection.timestamp.asc())
            .all()
        )
        return [
            {
                'timestamp':      r.timestamp,
                'class_name':     r.class_name,
                'count':          r.count,
                'confidence_avg': r.confidence_avg,
            }
            for r in rows
        ]


def get_webcam(webcam_id: int) -> dict | None:
    """Retourne une webcam par son id sous forme de dict, ou None."""
    with get_db_session() as session:
        webcam = session.get(Webcam, webcam_id)
        return _webcam_to_dict(webcam) if webcam else None


def get_all_webcams() -> list[dict]:
    """Retourne toutes les webcams actives sous forme de liste de dicts."""
    with get_db_session() as session:
        webcams = session.query(Webcam).filter_by(is_active=True).all()
        return [_webcam_to_dict(w) for w in webcams]


# ---------------------------------------------------------------------------
# Test / initialisation standalone
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s [%(levelname)s] %(message)s')

    print("=== Initialisation de la base de données ===")
    init_db()

    print("\n--- Ajout de la webcam Place de la Comédie ---")
    webcam = add_webcam(
        name=config.WEBCAM_CONFIG['name'],
        location=config.WEBCAM_CONFIG['location'],
        url_pattern=config.WEBCAM_CONFIG['url_base'],
    )
    print(f"  -> id={webcam['id']}  name={webcam['name']}  location={webcam['location']}")

    print("\n--- Ajout de détections de test ---")
    now = utcnow()
    test_data = [
        ('person',     12, 0.82),
        ('car',         4, 0.71),
        ('bicycle',     2, 0.65),
        ('motorcycle',  1, 0.58),
    ]
    for class_name, count, conf in test_data:
        save_detection(webcam['id'], now, class_name, count, conf)
        print(f"  -> {class_name}: {count} (conf={conf})")

    print("\n--- Lecture des détections (dernières 24h) ---")
    detections = get_detections(webcam['id'], hours=24)
    for d in detections:
        print(f"  {d['timestamp']}  {d['class_name']:12s}  count={d['count']}  "
              f"conf={d['confidence_avg']:.2f}")

    print(f"\n[OK] {len(detections)} detection(s) en base.")
