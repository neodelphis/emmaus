from __future__ import annotations

from dataclasses import dataclass
from datetime import time

from app.domain.errors import DomainError

SLOT_STEP_MINUTES = 30


@dataclass(frozen=True)
class TimeWindow:
    open_time: time
    close_time: time


def minutes_since_midnight(value: time) -> int:
    return value.hour * 60 + value.minute


def is_on_step(value: time, step_minutes: int = SLOT_STEP_MINUTES) -> bool:
    return (
        value.second == 0
        and value.microsecond == 0
        and minutes_since_midnight(value) % step_minutes == 0
    )


def validate_time_window(window: TimeWindow) -> None:
    if not is_on_step(window.open_time) or not is_on_step(window.close_time):
        raise DomainError("Les heures d'ouverture doivent suivre un pas de 30 minutes.")
    if window.open_time >= window.close_time:
        raise DomainError("L'heure de fermeture doit être postérieure à l'heure d'ouverture.")


def validate_day_answer(
    *,
    kind: str,
    start: time | None,
    end: time | None,
    window: TimeWindow | None,
) -> None:
    if kind == "unavailable":
        if start is not None or end is not None:
            raise DomainError("Un jour indisponible ne peut pas avoir d'horaires.")
        return

    if kind == "all_day":
        if start is not None or end is not None:
            raise DomainError("Une disponibilité toute la journée ne peut pas avoir d'horaires.")
        return

    if kind != "slot":
        raise DomainError("Type de disponibilité inconnu.")

    if start is None or end is None:
        raise DomainError("Un créneau doit avoir une heure de début et une heure de fin.")
    if window is None:
        raise DomainError("Les horaires d'ouverture ne sont pas configurés pour ce jour.")
    if not is_on_step(start) or not is_on_step(end):
        raise DomainError("Les horaires doivent suivre un pas de 30 minutes.")
    if start >= end:
        raise DomainError("L'heure de fin doit être postérieure à l'heure de début.")
    if start < window.open_time or end > window.close_time:
        raise DomainError(
            "Le créneau doit être compris dans les heures d'ouverture "
            f"({window.open_time.strftime('%H:%M')}–{window.close_time.strftime('%H:%M')})."
        )
