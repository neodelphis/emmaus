from __future__ import annotations

import logging
from datetime import time

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import AdminUser, OpeningHours
from app.security import hash_password

logger = logging.getLogger(__name__)

DEFAULT_OPEN_TIME = time(8, 0)
DEFAULT_CLOSE_TIME = time(18, 0)
OPENING_WEEKDAYS = (1, 2, 3, 4, 5)


def ensure_opening_hours(session: Session) -> None:
    existing = set(session.scalars(select(OpeningHours.weekday)).all())
    for weekday in OPENING_WEEKDAYS:
        if weekday not in existing:
            session.add(
                OpeningHours(
                    weekday=weekday,
                    open_time=DEFAULT_OPEN_TIME,
                    close_time=DEFAULT_CLOSE_TIME,
                )
            )
    session.commit()


def ensure_first_admin(session: Session, settings: Settings) -> None:
    """Crée le premier administrateur uniquement si aucun compte n'existe."""
    admin_count = session.scalar(select(func.count()).select_from(AdminUser)) or 0
    if admin_count > 0:
        # Rattrapage pour les comptes créés avant l'ajout du genre : le compte
        # initial renseigné dans .env reçoit son genre au démarrage, sans
        # écraser une valeur déjà choisie dans l'interface.
        if settings.admin_email is not None and settings.admin_gender is not None:
            existing = session.scalar(
                select(AdminUser).where(
                    AdminUser.email == str(settings.admin_email).lower()
                )
            )
            if existing is not None and existing.gender is None:
                existing.gender = settings.admin_gender
                session.commit()
        return
    if not settings.seed_admin:
        return
    if settings.admin_email is None or settings.admin_password is None:
        logger.warning(
            "Aucun administrateur n'existe. Renseignez ADMIN_EMAIL et ADMIN_PASSWORD "
            "pour créer le premier compte."
        )
        return

    settings.validate_bootstrap_credentials()
    session.add(
        AdminUser(
            email=str(settings.admin_email).lower(),
            password_hash=hash_password(settings.admin_password.get_secret_value()),
            gender=settings.admin_gender,
        )
    )
    session.commit()
    logger.info("Compte administrateur initial créé.")
