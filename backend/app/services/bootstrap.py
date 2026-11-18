from __future__ import annotations

import logging
from datetime import time

from sqlalchemy import func, select, text, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.sites import DEFAULT_SITE, SITES
from app.models import AdminUser, DayAvailability, SiteOpeningHours, Volunteer
from app.security import hash_password

logger = logging.getLogger(__name__)

DEFAULT_OPEN_TIME = time(8, 0)
DEFAULT_CLOSE_TIME = time(18, 0)
OPENING_WEEKDAYS = (1, 2, 3, 4, 5)


def ensure_site_opening_hours(session: Session) -> None:
    """Initialise les horaires par site, en reprenant l'ancienne table globale."""
    existing = {
        (row.site, row.weekday)
        for row in session.scalars(select(SiteOpeningHours)).all()
    }

    if not any(site == DEFAULT_SITE for site, _ in existing):
        legacy_table = session.scalar(text("SELECT to_regclass('public.opening_hours')"))
        if legacy_table is not None:
            legacy_rows = session.execute(
                text("SELECT weekday, open_time, close_time FROM opening_hours")
            ).all()
            for row in legacy_rows:
                session.add(
                    SiteOpeningHours(
                        site=DEFAULT_SITE,
                        weekday=row.weekday,
                        open_time=row.open_time,
                        close_time=row.close_time,
                    )
                )
                existing.add((DEFAULT_SITE, row.weekday))
            if legacy_rows:
                session.flush()

    for site in SITES:
        for weekday in OPENING_WEEKDAYS:
            if (site.code, weekday) not in existing:
                session.add(
                    SiteOpeningHours(
                        site=site.code,
                        weekday=weekday,
                        open_time=DEFAULT_OPEN_TIME,
                        close_time=DEFAULT_CLOSE_TIME,
                    )
                )
    session.commit()


def backfill_sites(session: Session) -> None:
    """Affecte le site historique par défaut aux données antérieures aux sites."""
    session.execute(
        update(Volunteer)
        .where(Volunteer.default_site.is_(None))
        .values(default_site=DEFAULT_SITE)
    )
    session.execute(
        update(DayAvailability)
        .where(DayAvailability.site.is_(None))
        .values(site=DEFAULT_SITE)
    )
    session.execute(
        update(AdminUser)
        .where(AdminUser.last_site.is_(None))
        .values(last_site=DEFAULT_SITE)
    )
    session.commit()


def backfill_volunteer_names(session: Session) -> None:
    """Sépare le nom complet historique en prénom et nom pour les fiches existantes."""
    volunteers = session.scalars(
        select(Volunteer).where(Volunteer.first_name.is_(None))
    ).all()
    for volunteer in volunteers:
        first, _, last = volunteer.name.strip().partition(" ")
        volunteer.first_name = first.strip() or volunteer.name.strip()
        volunteer.last_name = last.strip() or None
    session.commit()


def backfill_admin_roles(session: Session, settings: Settings) -> None:
    """Garantit que le compte administrateur initial est administrateur principal."""
    if settings.admin_email is None:
        return
    admin = session.scalar(
        select(AdminUser).where(AdminUser.email == str(settings.admin_email).lower())
    )
    if admin is not None and admin.role != "super_admin":
        admin.role = "super_admin"
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
            role="super_admin",
            gender=settings.admin_gender,
            last_site=DEFAULT_SITE,
        )
    )
    session.commit()
    logger.info("Compte administrateur initial créé.")
