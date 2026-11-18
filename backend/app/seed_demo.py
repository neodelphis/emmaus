"""Jeu de données de démonstration pour la V1 locale.

À exécuter dans le conteneur API :

    docker compose exec api python -m app.seed_demo

Le script remplace les bénévoles dont l'adresse se termine par
``@demo.emmaus.fr``, crée ou réinitialise un compte administrateur normal de
démonstration, puis affiche les liens personnels à ouvrir. Il refuse de
s'exécuter lorsque ``APP_ENV=production``.
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import Base, utcnow
from app.domain.periods import (
    PARIS,
    current_period_start,
    period_days,
    period_end,
    today_paris,
    visible_period_starts,
)
from app.domain.sites import DEFAULT_SITE
from app.models import AdminUser, AvailabilityResponse, DayAvailability, Volunteer
from app.security import hash_password
from app.services.links import LinkService

DEMO_DOMAIN = "@demo.emmaus.fr"
DEMO_ADMIN_EMAIL = f"admin.test{DEMO_DOMAIN}"
DEMO_ADMIN_PASSWORD = "test-admin-123"
DayKind = Literal["all_day", "slot"]


def _submitted_at_for(period_start: date) -> datetime:
    """Horodatage plausible pour une réponse historique (fin de période)."""
    end = period_end(period_start)
    return datetime.combine(end, time(12, 0), tzinfo=PARIS).astimezone(UTC)


def _add_response(
    session: Session,
    volunteer: Volunteer,
    period_start: date,
    days: dict[int, tuple[DayKind, time | None, time | None]],
    *,
    submitted_at: datetime,
    site: str = DEFAULT_SITE,
    site_overrides: dict[int, str] | None = None,
) -> None:
    response = AvailabilityResponse(
        volunteer_id=volunteer.id,
        period_start=period_start,
        submitted_at=submitted_at,
    )
    session.add(response)
    session.flush()
    dates = period_days(period_start)
    for offset, (kind, start, end) in days.items():
        session.add(
            DayAvailability(
                response_id=response.id,
                day_date=dates[offset],
                kind=kind,
                start_time=start,
                end_time=end,
                site=(site_overrides or {}).get(offset, site),
            )
        )


def _last_completed_start(today):
    current = current_period_start(today)
    return current if period_end(current) < today else current - timedelta(days=7)


def seed_demo() -> list[tuple[str, str, bool]]:
    settings = get_settings()
    if settings.app_env.lower() in {"production", "prod"}:
        raise SystemExit("Le jeu de démonstration est interdit en production.")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    link_service = LinkService(settings)
    today = today_paris()

    with Session(engine) as session:
        existing = session.scalars(
            select(Volunteer).where(Volunteer.email.like(f"%{DEMO_DOMAIN}"))
        ).all()
        for volunteer in existing:
            session.delete(volunteer)
        session.commit()

        volunteers = {
            "marie": Volunteer(
                name="Marie Dupont",
                email=f"marie.dupont{DEMO_DOMAIN}",
                gender="femme",
                default_site="vaire",
            ),
            "jean": Volunteer(
                name="Jean Martin",
                email=f"jean.martin{DEMO_DOMAIN}",
                gender="homme",
                default_site="vaire",
            ),
            "fatima": Volunteer(
                name="Fatima Benali",
                email=f"fatima.benali{DEMO_DOMAIN}",
                gender="femme",
                default_site="les-essarts",
            ),
            "paul": Volunteer(
                name="Paul Durand",
                email=f"paul.durand{DEMO_DOMAIN}",
                gender="homme",
                default_site="vaire",
            ),
            "karim": Volunteer(
                name="Karim Haddad",
                email=f"karim.haddad{DEMO_DOMAIN}",
                gender="homme",
                default_site="les-essarts",
            ),
            "ancien": Volunteer(
                name="Ancien Bénévole",
                email=f"ancien.benevole{DEMO_DOMAIN}",
                gender="homme",
                default_site="vaire",
                is_active=False,
            ),
        }
        links: dict[str, str] = {}
        for key, volunteer in volunteers.items():
            links[key] = link_service.issue_link(volunteer)
            session.add(volunteer)
        session.flush()

        periods = visible_period_starts(today)
        primary = periods[0]
        secondary = periods[1]
        history = [
            _last_completed_start(today) - timedelta(days=7 * offset)
            for offset in range(4)
        ]

        # Marie : un historique régulier et aucune réponse récente, pour montrer
        # les propositions préremplies (sauf le vendredi, sans historique).
        for start in history:
            _add_response(
                session,
                volunteers["marie"],
                start,
                {
                    0: ("all_day", None, None),
                    1: ("all_day", None, None),
                    2: ("slot", time(9, 0), time(12, 0)),
                    4: ("slot", time(14, 0), time(17, 0)),
                },
                submitted_at=_submitted_at_for(start),
            )

        # Jean : réponses enregistrées sur la période courante et la suivante.
        current_days = {
            3: ("all_day", None, None),
            4: ("slot", time(14, 0), time(17, 0)),
        }
        _add_response(
            session,
            volunteers["jean"],
            primary,
            current_days,
            submitted_at=utcnow(),
        )
        _add_response(
            session,
            volunteers["jean"],
            secondary,
            {
                0: ("slot", time(8, 0), time(12, 0)),
                1: ("slot", time(8, 0), time(12, 0)),
                2: ("slot", time(8, 0), time(12, 0)),
                3: ("slot", time(8, 0), time(12, 0)),
                4: ("all_day", None, None),
            },
            submitted_at=utcnow(),
            site_overrides={3: "les-essarts"},
        )

        # Fatima : aucune réponse ni historique, pour le cas « sans réponse ».

        # Paul : historique différent et semaine suivante renseignée tout public.
        for start in history:
            _add_response(
                session,
                volunteers["paul"],
                start,
                {
                    1: ("slot", time(10, 0), time(16, 0)),
                    2: ("slot", time(10, 0), time(16, 0)),
                    3: ("slot", time(10, 0), time(16, 0)),
                    4: ("slot", time(10, 0), time(14, 0)),
                },
                submitted_at=_submitted_at_for(start),
            )
        _add_response(
            session,
            volunteers["paul"],
            secondary,
            {
                0: ("all_day", None, None),
                1: ("all_day", None, None),
                2: ("all_day", None, None),
                3: ("all_day", None, None),
                4: ("all_day", None, None),
            },
            submitted_at=utcnow(),
        )

        # Karim : une période suivante avec des statuts variés.
        _add_response(
            session,
            volunteers["karim"],
            secondary,
            {
                1: ("all_day", None, None),
                2: ("slot", time(9, 0), time(13, 0)),
                4: ("slot", time(15, 0), time(18, 0)),
            },
            submitted_at=utcnow(),
        )

        # Ancien bénévole : désactivé, avec un historique conservé.
        for start in history[:2]:
            _add_response(
                session,
                volunteers["ancien"],
                start,
                {
                    1: ("all_day", None, None),
                    2: ("slot", time(9, 0), time(12, 0)),
                },
                submitted_at=_submitted_at_for(start),
            )

        demo_admin = session.scalar(
            select(AdminUser).where(AdminUser.email == DEMO_ADMIN_EMAIL)
        )
        if demo_admin is None:
            demo_admin = AdminUser(
                email=DEMO_ADMIN_EMAIL,
                password_hash=hash_password(DEMO_ADMIN_PASSWORD),
                first_name="Admin",
                last_name="Test",
                role="admin",
                gender="homme",
                last_site=DEFAULT_SITE,
            )
            session.add(demo_admin)
        else:
            demo_admin.password_hash = hash_password(DEMO_ADMIN_PASSWORD)
            demo_admin.first_name = "Admin"
            demo_admin.last_name = "Test"
            demo_admin.role = "admin"
            demo_admin.gender = "homme"
            demo_admin.last_site = DEFAULT_SITE

        session.commit()

        return [
            (volunteer.name, links[key], volunteer.is_active)
            for key, volunteer in volunteers.items()
        ]


def main() -> int:
    rows = seed_demo()
    settings = get_settings()
    print(f"Données de démonstration créées dans {settings.database_url.split('@')[-1]}.")
    print(f"Période courante : {visible_period_starts(today_paris())[0]}")
    print("\nLiens personnels à ouvrir :\n")
    for name, link, active in rows:
        suffix = "" if active else "  (bénévole désactivé : le lien est refusé)"
        print(f"- {name} : {link}{suffix}")
    print("\nCompte administrateur de démonstration :")
    print(f"- {DEMO_ADMIN_EMAIL} / {DEMO_ADMIN_PASSWORD} (rôle Administrateur)")
    print(
        "\nRelancer cette commande remplace les bénévoles de démonstration "
        f"(adresses en {DEMO_DOMAIN}) et réinitialise le compte administrateur "
        "de démonstration."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
