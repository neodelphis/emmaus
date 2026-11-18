from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time

from app.domain.availability import SLOT_STEP_MINUTES, minutes_since_midnight


@dataclass(frozen=True)
class HistoryDay:
    kind: str
    start: time | None
    end: time | None
    period_start: date
    submitted_at: datetime

    @property
    def recency(self) -> tuple[date, datetime]:
        return (self.period_start, self.submitted_at)


@dataclass(frozen=True)
class Suggestion:
    kind: str
    start: time | None = None
    end: time | None = None


def slots_are_close(left: HistoryDay, right: HistoryDay) -> bool:
    """Deux créneaux sont proches si début et fin diffèrent d'au plus 30 minutes."""
    if left.start is None or left.end is None or right.start is None or right.end is None:
        return False
    return (
        abs(minutes_since_midnight(left.start) - minutes_since_midnight(right.start))
        <= SLOT_STEP_MINUTES
        and abs(minutes_since_midnight(left.end) - minutes_since_midnight(right.end))
        <= SLOT_STEP_MINUTES
    )


def suggest_day(history: list[HistoryDay]) -> Suggestion | None:
    """Choisit la réponse la plus fréquente, départagée par la plus récente.

    « Toute la journée » forme une catégorie distincte. Les créneaux proches sont
    regroupés autour de la réponse la plus récente encore libre : la relation de
    proximité n'étant pas transitive, ce regroupement par représentant garantit
    un résultat déterministe.
    """
    candidates = [
        item
        for item in history
        if item.kind == "all_day"
        or (item.kind == "slot" and item.start is not None and item.end is not None)
    ]
    if not candidates:
        return None

    candidates.sort(key=lambda item: item.recency, reverse=True)

    slot_groups: list[list[HistoryDay]] = []
    for item in candidates:
        if item.kind != "slot":
            continue
        for group in slot_groups:
            if slots_are_close(group[0], item):
                group.append(item)
                break
        else:
            slot_groups.append([item])

    all_day_group = [item for item in candidates if item.kind == "all_day"]
    groups: list[list[HistoryDay]] = []
    if all_day_group:
        groups.append(all_day_group)
    groups.extend(slot_groups)

    def group_rank(group: list[HistoryDay]) -> tuple[int, date, datetime]:
        latest = max(group, key=lambda item: item.recency)
        return (len(group), latest.period_start, latest.submitted_at)

    best_group = max(groups, key=group_rank)
    best = max(best_group, key=lambda item: item.recency)
    return Suggestion(kind=best.kind, start=best.start, end=best.end)
