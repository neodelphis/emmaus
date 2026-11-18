from __future__ import annotations

from datetime import UTC, date, datetime, time

from app.domain.suggestions import HistoryDay, slots_are_close, suggest_day


def day(
    *,
    period_start: date,
    kind: str,
    start: time | None = None,
    end: time | None = None,
    submitted_at: datetime | None = None,
) -> HistoryDay:
    return HistoryDay(
        kind=kind,
        start=start,
        end=end,
        period_start=period_start,
        submitted_at=submitted_at or datetime(2026, 11, 10, 12, tzinfo=UTC),
    )


def test_no_history_means_no_suggestion() -> None:
    assert suggest_day([]) is None


def test_all_day_wins_when_most_frequent() -> None:
    history = [
        day(period_start=date(2026, 11, 10), kind="all_day"),
        day(period_start=date(2026, 11, 3), kind="all_day"),
        day(
            period_start=date(2026, 10, 27),
            kind="slot",
            start=time(9, 0),
            end=time(12, 0),
        ),
    ]
    suggestion = suggest_day(history)
    assert suggestion is not None
    assert suggestion.kind == "all_day"
    assert suggestion.start is None


def test_close_slots_are_grouped_and_latest_is_used() -> None:
    history = [
        day(
            period_start=date(2026, 11, 10),
            kind="slot",
            start=time(9, 0),
            end=time(12, 30),
        ),
        day(
            period_start=date(2026, 11, 3),
            kind="slot",
            start=time(9, 30),
            end=time(12, 0),
        ),
        day(
            period_start=date(2026, 10, 27),
            kind="slot",
            start=time(9, 0),
            end=time(12, 0),
        ),
        day(period_start=date(2026, 10, 20), kind="all_day"),
    ]
    suggestion = suggest_day(history)
    assert suggestion is not None
    assert suggestion.kind == "slot"
    # Le créneau réel le plus récent du groupe majoritaire est repris.
    assert (suggestion.start, suggestion.end) == (time(9, 0), time(12, 30))


def test_distant_slots_are_not_grouped() -> None:
    history = [
        day(
            period_start=date(2026, 11, 10),
            kind="slot",
            start=time(9, 0),
            end=time(12, 0),
        ),
        day(
            period_start=date(2026, 11, 3),
            kind="slot",
            start=time(14, 0),
            end=time(17, 0),
        ),
    ]
    suggestion = suggest_day(history)
    assert suggestion is not None
    # Égalité de fréquence : la réponse la plus récente départage.
    assert (suggestion.start, suggestion.end) == (time(9, 0), time(12, 0))


def test_frequency_beats_recency() -> None:
    history = [
        day(
            period_start=date(2026, 11, 10),
            kind="slot",
            start=time(14, 0),
            end=time(17, 0),
        ),
        day(
            period_start=date(2026, 11, 3),
            kind="slot",
            start=time(9, 0),
            end=time(12, 0),
        ),
        day(
            period_start=date(2026, 10, 27),
            kind="slot",
            start=time(9, 30),
            end=time(12, 30),
        ),
    ]
    suggestion = suggest_day(history)
    assert suggestion is not None
    assert (suggestion.start, suggestion.end) == (time(9, 0), time(12, 0))


def test_slot_closeness_requires_both_bounds_within_thirty_minutes() -> None:
    left = day(
        period_start=date(2026, 11, 10),
        kind="slot",
        start=time(9, 0),
        end=time(12, 0),
    )
    close = day(
        period_start=date(2026, 11, 3),
        kind="slot",
        start=time(9, 30),
        end=time(12, 30),
    )
    far = day(
        period_start=date(2026, 10, 27),
        kind="slot",
        start=time(9, 0),
        end=time(13, 0),
    )
    assert slots_are_close(left, close) is True
    assert slots_are_close(left, far) is False
