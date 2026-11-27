"""Jeu de données de démonstration pour la V1 locale.

À exécuter dans le conteneur API :

    docker compose exec api python scripts/seed_demo.py

Le script remplace les bénévoles dont l'adresse se termine par
``@demo.emmaus.fr``, crée ou réinitialise un compte administrateur normal de
démonstration, puis affiche les liens personnels à ouvrir. Il refuse de
s'exécuter lorsque ``APP_ENV=production``.

Toutes les périodes sont calculées à partir de la date du jour (fuseau
``Europe/Paris``) : l'historique, la période en cours et les périodes suivantes
restent donc cohérents à chaque nouvelle génération.
"""

from __future__ import annotations

import sys
import unicodedata
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import Settings, get_settings
from app.database import Base, utcnow
from app.domain.periods import (
    PARIS,
    current_period_start,
    period_days,
    period_end,
    today_paris,
    visible_period_starts,
)
from app.domain.sites import DEFAULT_SITE, SITE_CODES, site_name
from app.models import AdminUser, AvailabilityResponse, DayAvailability, Volunteer
from app.security import hash_password
from app.services.links import LinkService

DEMO_DOMAIN = "@demo.emmaus.fr"
DEMO_ADMIN_EMAIL = f"admin.test{DEMO_DOMAIN}"
DEMO_ADMIN_PASSWORD = "test-admin-123"

DayKind = Literal["all_day", "slot"]
PeriodKey = Literal["history", "current", "next"]
SiteCode = Literal["vaire", "les-essarts"]

WEEKDAY_SHORT = ("mar.", "mer.", "jeu.", "ven.", "sam.")


@dataclass(frozen=True)
class DemoDay:
    """Disponibilité d'un jour ; ``site`` vide reprend le site du bénévole."""

    kind: DayKind
    start: time | None = None
    end: time | None = None
    site: SiteCode | None = None


def all_day(site: SiteCode | None = None) -> DemoDay:
    return DemoDay("all_day", site=site)


def slot(start: str, end: str, site: SiteCode | None = None) -> DemoDay:
    start_time = time.fromisoformat(start)
    end_time = time.fromisoformat(end)
    if not start_time < end_time:
        raise ValueError(f"Créneau invalide : {start} – {end}")
    return DemoDay("slot", start_time, end_time, site)


def _slug(value: str) -> str:
    """Forme ASCII minuscule utilisée dans les adresses de démonstration."""
    decomposed = unicodedata.normalize("NFKD", value)
    return decomposed.encode("ascii", "ignore").decode("ascii").lower()


@dataclass(frozen=True)
class ResponsePattern:
    """Réponse type, rattachée à un historique, à la période courante ou suivante."""

    period: PeriodKey
    days: dict[int, DemoDay]
    weeks: int = 1  # nombre de semaines d'historique où répéter le modèle


@dataclass(frozen=True)
class VolunteerSpec:
    key: str
    first_name: str
    last_name: str
    gender: Literal["homme", "femme"]
    default_site: SiteCode
    responses: tuple[ResponsePattern, ...] = ()
    is_active: bool = True

    @property
    def name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    @property
    def email(self) -> str:
        local = f"{_slug(self.first_name)}.{_slug(self.last_name)}"
        return f"{local}{DEMO_DOMAIN}"


@dataclass(frozen=True)
class PlannedResponse:
    volunteer_key: str
    period_start: date
    submitted_at: datetime
    days: dict[int, DemoDay]


@dataclass(frozen=True)
class DemoPlan:
    today: date
    history_starts: tuple[date, ...]
    visible_starts: tuple[date, ...]
    responses: tuple[PlannedResponse, ...]

    @property
    def volunteers(self) -> tuple[VolunteerSpec, ...]:
        return DEMO_VOLUNTEERS

    def volunteer(self, key: str) -> VolunteerSpec:
        return next(spec for spec in DEMO_VOLUNTEERS if spec.key == key)


def _submitted_at_for(period_start: date) -> datetime:
    """Horodatage plausible pour une réponse historique (fin de période)."""
    end = period_end(period_start)
    return datetime.combine(end, time(12, 0), tzinfo=PARIS).astimezone(UTC)


def _last_completed_start(today: date) -> date:
    current = current_period_start(today)
    return current if period_end(current) < today else current - timedelta(days=7)


# Une vingtaine de bénévoles, dont une majorité rattachée à Vairé : le samedi de
# la période en cours réunit ainsi 15 bénévoles sur le site de Vairé, ce qui
# permet de vérifier l'affichage d'une journée chargée.
DEMO_VOLUNTEERS: tuple[VolunteerSpec, ...] = (
    # Marie : un historique régulier et aucune réponse récente, pour montrer
    # les propositions préremplies (sauf le vendredi, sans historique).
    VolunteerSpec(
        key="marie",
        first_name="Marie",
        last_name="Dupont",
        gender="femme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="history",
                weeks=4,
                days={
                    0: all_day(),
                    1: all_day(),
                    2: slot("09:00", "12:00"),
                    4: slot("14:00", "17:00"),
                },
            ),
        ),
    ),
    # Jean : réponses enregistrées sur la période courante et la suivante, avec
    # un vendredi passé aux Essarts.
    VolunteerSpec(
        key="jean",
        first_name="Jean",
        last_name="Martin",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    3: all_day(),
                    4: slot("14:00", "17:00"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: slot("08:00", "12:00"),
                    1: slot("08:00", "12:00"),
                    2: slot("08:00", "12:00"),
                    3: slot("08:00", "12:00", site="les-essarts"),
                    4: all_day(),
                },
            ),
        ),
    ),
    # Fatima : aucune réponse ni historique, pour le cas « sans réponse ».
    VolunteerSpec(
        key="fatima",
        first_name="Fatima",
        last_name="Benali",
        gender="femme",
        default_site="les-essarts",
    ),
    # Paul : historique différent et semaine suivante renseignée tout public.
    VolunteerSpec(
        key="paul",
        first_name="Paul",
        last_name="Durand",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="history",
                weeks=4,
                days={
                    1: slot("10:00", "16:00"),
                    2: slot("10:00", "16:00"),
                    3: slot("10:00", "16:00"),
                    4: slot("10:00", "14:00"),
                },
            ),
            ResponsePattern(
                period="current",
                days={
                    1: slot("10:00", "16:00"),
                    2: slot("10:00", "16:00"),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={offset: all_day() for offset in range(5)},
            ),
        ),
    ),
    # Karim : des statuts variés sur la période suivante.
    VolunteerSpec(
        key="karim",
        first_name="Karim",
        last_name="Haddad",
        gender="homme",
        default_site="les-essarts",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    1: all_day(),
                    3: slot("09:00", "13:00"),
                    4: all_day(site="vaire"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: all_day(),
                    2: slot("09:00", "13:00"),
                    4: slot("15:00", "18:00"),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="elise",
        first_name="Élise",
        last_name="Moreau",
        gender="femme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: slot("08:00", "12:00"),
                    1: slot("08:00", "12:00", site="les-essarts"),
                    2: all_day(),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: all_day(),
                    1: all_day(),
                    2: slot("08:00", "12:00"),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="thomas",
        first_name="Thomas",
        last_name="Lefèvre",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: all_day(),
                    2: slot("14:00", "18:00"),
                    3: all_day(),
                    4: slot("09:00", "12:00"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: slot("08:00", "12:00"),
                    2: all_day(),
                    3: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="aicha",
        first_name="Aïcha",
        last_name="Diallo",
        gender="femme",
        default_site="les-essarts",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: all_day(),
                    1: all_day(),
                    2: all_day(),
                    4: all_day(site="vaire"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: all_day(),
                    3: all_day(),
                    4: slot("09:00", "13:00", site="vaire"),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="michel",
        first_name="Michel",
        last_name="Bernard",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: slot("14:00", "18:00"),
                    1: slot("09:00", "12:00", site="les-essarts"),
                    3: slot("08:00", "12:00"),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: slot("10:00", "16:00"),
                    3: all_day(),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="sophie",
        first_name="Sophie",
        last_name="Garnier",
        gender="femme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: all_day(),
                    1: slot("09:00", "12:00"),
                    3: all_day(),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: all_day(),
                    1: all_day(),
                    3: slot("08:00", "12:00"),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="lucie",
        first_name="Lucie",
        last_name="Petit",
        gender="femme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    1: all_day(),
                    2: slot("08:00", "13:00"),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    2: all_day(),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="herve",
        first_name="Hervé",
        last_name="Roux",
        gender="homme",
        default_site="les-essarts",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    1: all_day(),
                    2: all_day(),
                    3: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: all_day(),
                    2: all_day(),
                    3: slot("14:00", "18:00"),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="nadia",
        first_name="Nadia",
        last_name="Cherif",
        gender="femme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: slot("09:00", "13:00"),
                    2: all_day(),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: all_day(),
                    2: slot("14:00", "18:00"),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="etienne",
        first_name="Étienne",
        last_name="Leroy",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: all_day(),
                    1: slot("14:00", "18:00"),
                    3: all_day(),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: slot("08:00", "12:00"),
                    3: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="camille",
        first_name="Camille",
        last_name="Fontaine",
        gender="femme",
        default_site="les-essarts",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    1: all_day(),
                    2: all_day(),
                    3: slot("10:00", "16:00"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: all_day(),
                    2: all_day(site="les-essarts"),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="bruno",
        first_name="Bruno",
        last_name="Marchand",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: all_day(),
                    1: slot("14:00", "18:00", site="les-essarts"),
                    2: slot("09:00", "12:00"),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: all_day(),
                    2: all_day(),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="sandrine",
        first_name="Sandrine",
        last_name="Lecomte",
        gender="femme",
        default_site="les-essarts",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: slot("14:00", "18:00"),
                    1: all_day(),
                    3: slot("08:00", "12:00"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: slot("09:00", "13:00"),
                    2: all_day(),
                    4: slot("08:00", "12:00", site="les-essarts"),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="youssef",
        first_name="Youssef",
        last_name="Amrani",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: slot("08:00", "12:00"),
                    2: all_day(),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: all_day(),
                    4: slot("08:00", "12:00"),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="chantal",
        first_name="Chantal",
        last_name="Guérin",
        gender="femme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    1: slot("08:00", "12:00"),
                    2: slot("14:00", "18:00"),
                    4: all_day(),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    0: slot("14:00", "18:00"),
                    2: all_day(),
                    4: all_day(),
                },
            ),
        ),
    ),
    VolunteerSpec(
        key="david",
        first_name="David",
        last_name="Perrin",
        gender="homme",
        default_site="vaire",
        responses=(
            ResponsePattern(
                period="current",
                days={
                    0: all_day(),
                    3: all_day(),
                    4: slot("09:00", "13:00"),
                },
            ),
            ResponsePattern(
                period="next",
                days={
                    1: all_day(),
                    3: all_day(),
                    4: all_day(),
                },
            ),
        ),
    ),
    # Ancien bénévole : désactivé, avec un historique conservé.
    VolunteerSpec(
        key="ancien",
        first_name="Ancien",
        last_name="Bénévole",
        gender="homme",
        default_site="vaire",
        is_active=False,
        responses=(
            ResponsePattern(
                period="history",
                weeks=2,
                days={
                    1: all_day(),
                    2: slot("09:00", "12:00"),
                },
            ),
        ),
    ),
)


def build_demo_plan(today: date, *, now: datetime | None = None) -> DemoPlan:
    """Construit le plan de démonstration relatif à ``today``, sans base de données."""
    visible = tuple(visible_period_starts(today))
    primary = visible[0]
    secondary = visible[1] if len(visible) > 1 else None
    history_starts = tuple(
        _last_completed_start(today) - timedelta(days=7 * offset) for offset in range(4)
    )
    submitted_now = now or utcnow()

    responses: list[PlannedResponse] = []
    for spec in DEMO_VOLUNTEERS:
        for pattern in spec.responses:
            if pattern.period == "history":
                if pattern.weeks > len(history_starts):
                    raise ValueError("L'historique de démonstration est limité à 4 semaines.")
                for start in history_starts[: pattern.weeks]:
                    responses.append(
                        PlannedResponse(
                            volunteer_key=spec.key,
                            period_start=start,
                            submitted_at=_submitted_at_for(start),
                            days=pattern.days,
                        )
                    )
                continue
            start = primary if pattern.period == "current" else secondary
            if start is None:
                continue
            responses.append(
                PlannedResponse(
                    volunteer_key=spec.key,
                    period_start=start,
                    submitted_at=submitted_now,
                    days=pattern.days,
                )
            )

    return DemoPlan(
        today=today,
        history_starts=history_starts,
        visible_starts=visible,
        responses=tuple(responses),
    )


def daily_counts(plan: DemoPlan, period_start: date, site: str) -> tuple[int, ...]:
    """Nombre de bénévoles actifs disponibles par jour d'une période, pour un site."""
    counts = [0] * 5
    for response in plan.responses:
        if response.period_start != period_start:
            continue
        spec = plan.volunteer(response.volunteer_key)
        if not spec.is_active:
            continue
        for offset, day in response.days.items():
            if (day.site or spec.default_site) == site:
                counts[offset] += 1
    return tuple(counts)


def _add_response(session: Session, volunteer: Volunteer, planned: PlannedResponse) -> None:
    response = AvailabilityResponse(
        volunteer_id=volunteer.id,
        period_start=planned.period_start,
        submitted_at=planned.submitted_at,
    )
    session.add(response)
    session.flush()
    dates = period_days(planned.period_start)
    for offset, day in planned.days.items():
        start, end = (day.start, day.end) if day.kind == "slot" else (None, None)
        session.add(
            DayAvailability(
                response_id=response.id,
                day_date=dates[offset],
                kind=day.kind,
                start_time=start,
                end_time=end,
                site=day.site or volunteer.default_site,
            )
        )


def seed_demo(
    settings: Settings | None = None, plan: DemoPlan | None = None
) -> list[tuple[str, str, bool]]:
    settings = settings or get_settings()
    if settings.app_env.lower() in {"production", "prod"}:
        raise SystemExit("Le jeu de démonstration est interdit en production.")

    engine = create_engine(settings.database_url, pool_pre_ping=True)
    Base.metadata.create_all(engine)
    link_service = LinkService(settings)
    plan = plan or build_demo_plan(today_paris())

    with Session(engine) as session:
        existing = session.scalars(
            select(Volunteer).where(Volunteer.email.like(f"%{DEMO_DOMAIN}"))
        ).all()
        for volunteer in existing:
            session.delete(volunteer)
        session.commit()

        volunteers: dict[str, Volunteer] = {}
        links: dict[str, str] = {}
        for spec in plan.volunteers:
            volunteer = Volunteer(
                name=spec.name,
                first_name=spec.first_name,
                last_name=spec.last_name,
                email=spec.email,
                gender=spec.gender,
                default_site=spec.default_site,
                is_active=spec.is_active,
            )
            links[spec.key] = link_service.issue_link(volunteer)
            session.add(volunteer)
            volunteers[spec.key] = volunteer
        session.flush()

        for planned in plan.responses:
            _add_response(session, volunteers[planned.volunteer_key], planned)

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
            (spec.name, links[spec.key], spec.is_active) for spec in plan.volunteers
        ]


def main() -> int:
    settings = get_settings()
    plan = build_demo_plan(today_paris())
    rows = seed_demo(settings, plan)
    current = plan.visible_starts[0]
    active = sum(1 for spec in plan.volunteers if spec.is_active)
    inactive = sum(1 for spec in plan.volunteers if not spec.is_active)
    print(f"Données de démonstration créées dans {settings.database_url.split('@')[-1]}.")
    print(
        f"{active} bénévoles actifs et {inactive} "
        f"{'bénévole désactivé' if inactive == 1 else 'bénévoles désactivés'}, "
        f"sur la période ouverte du {current.strftime('%d/%m/%Y')} "
        f"au {period_end(current).strftime('%d/%m/%Y')}."
    )
    print("\nDisponibilités de la première période ouverte :\n")
    for site in SITE_CODES:
        counts = daily_counts(plan, current, site)
        detail = " · ".join(
            f"{label} {count}" for label, count in zip(WEEKDAY_SHORT, counts, strict=True)
        )
        print(f"- {site_name(site)} : {detail}")
    print("\nLiens personnels à ouvrir :\n")
    for name, link, is_active in rows:
        suffix = "" if is_active else "  (bénévole désactivé : le lien est refusé)"
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
