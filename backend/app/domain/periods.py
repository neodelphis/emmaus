from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from app.domain.errors import DomainError

PARIS = ZoneInfo("Europe/Paris")
PERIOD_LENGTH_DAYS = 5  # mardi, mercredi, jeudi, vendredi, samedi

WEEKDAY_LABELS = {
    1: "Mardi",
    2: "Mercredi",
    3: "Jeudi",
    4: "Vendredi",
    5: "Samedi",
}


def now_paris() -> datetime:
    return datetime.now(PARIS)


def today_paris() -> date:
    return now_paris().date()


def current_period_start(today: date) -> date:
    """Mardi de la période de service contenant la date (ou la précédant).

    La semaine de service va du mardi au samedi. Le lundi, la période
    « courante » est donc celle qui vient de se terminer ; elle sera filtrée
    si elle n'est plus ouverte.
    """
    return today - timedelta(days=(today.weekday() - 1) % 7)


def period_days(period_start: date) -> list[date]:
    return [period_start + timedelta(days=offset) for offset in range(PERIOD_LENGTH_DAYS)]


def period_end(period_start: date) -> date:
    return period_start + timedelta(days=PERIOD_LENGTH_DAYS - 1)


def is_day_editable(day: date, today: date) -> bool:
    """Un jour reste modifiable jusqu'à 23 h 59 la veille (heure de Paris)."""
    return day > today


def is_period_open(period_start: date, today: date) -> bool:
    return any(is_day_editable(day, today) for day in period_days(period_start))


def visible_period_starts(today: date) -> list[date]:
    """Période en cours si elle est ouverte, puis les quatre suivantes."""
    current = current_period_start(today)
    candidates = [current + timedelta(days=7 * offset) for offset in range(5)]
    return [start for start in candidates if is_period_open(start, today)]


def admin_period_options(today: date) -> list[date]:
    """Périodes proposées à l'administration : quatre passées, courante et suivantes."""
    current = current_period_start(today)
    past = [current - timedelta(days=7 * offset) for offset in range(4, 0, -1)]
    candidates = [*past, current, *visible_period_starts(today)]
    seen: set[date] = set()
    options: list[date] = []
    for start in candidates:
        if start not in seen:
            seen.add(start)
            options.append(start)
    return options


def validate_period_start(period_start: date) -> None:
    if period_start.weekday() != 1:
        raise DomainError("La période doit commencer un mardi.")


def is_past_period(period_start: date, today: date) -> bool:
    """Une période est passée lorsque son samedi est strictement antérieur à aujourd'hui."""
    return period_end(period_start) < today


def ensure_visible_period(period_start: date, today: date) -> None:
    if period_start not in visible_period_starts(today):
        raise DomainError(
            "Cette période n'est pas ouverte à la saisie. Seule la période en cours "
            "et les quatre suivantes sont accessibles.",
            status_code=409,
        )
