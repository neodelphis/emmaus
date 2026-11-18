from __future__ import annotations

from datetime import date

import pytest

from app.domain.errors import DomainError
from app.domain.periods import (
    admin_period_options,
    current_period_start,
    ensure_visible_period,
    is_day_editable,
    is_period_open,
    period_days,
    period_end,
    validate_period_start,
    visible_period_starts,
)


def test_current_period_start_follows_service_week() -> None:
    assert current_period_start(date(2026, 11, 17)) == date(2026, 11, 17)  # mardi
    assert current_period_start(date(2026, 11, 21)) == date(2026, 11, 17)  # samedi
    assert current_period_start(date(2026, 11, 22)) == date(2026, 11, 17)  # dimanche
    assert current_period_start(date(2026, 11, 23)) == date(2026, 11, 17)  # lundi


def test_period_days_and_end() -> None:
    days = period_days(date(2026, 11, 17))
    assert days == [
        date(2026, 11, 17),
        date(2026, 11, 18),
        date(2026, 11, 19),
        date(2026, 11, 20),
        date(2026, 11, 21),
    ]
    assert period_end(date(2026, 11, 17)) == date(2026, 11, 21)


def test_day_closes_at_end_of_previous_day() -> None:
    today = date(2026, 11, 17)
    assert is_day_editable(date(2026, 11, 18), today) is True
    assert is_day_editable(date(2026, 11, 17), today) is False
    assert is_day_editable(date(2026, 11, 16), today) is False


def test_visible_periods_tuesday_has_five_periods() -> None:
    starts = visible_period_starts(date(2026, 11, 17))
    assert starts == [
        date(2026, 11, 17),
        date(2026, 11, 24),
        date(2026, 12, 1),
        date(2026, 12, 8),
        date(2026, 12, 15),
    ]


def test_visible_periods_saturday_hides_closed_current_period() -> None:
    starts = visible_period_starts(date(2026, 11, 21))
    assert date(2026, 11, 17) not in starts
    assert starts == [
        date(2026, 11, 24),
        date(2026, 12, 1),
        date(2026, 12, 8),
        date(2026, 12, 15),
    ]


def test_visible_periods_monday_starts_with_next_week() -> None:
    starts = visible_period_starts(date(2026, 11, 23))
    assert starts[0] == date(2026, 11, 24)
    assert len(starts) == 4


def test_period_open_until_saturday() -> None:
    assert is_period_open(date(2026, 11, 17), date(2026, 11, 20)) is True
    assert is_period_open(date(2026, 11, 17), date(2026, 11, 21)) is False


def test_admin_options_include_past_current_and_visible_periods() -> None:
    options = admin_period_options(date(2026, 11, 17))
    assert options == [
        date(2026, 10, 20),
        date(2026, 10, 27),
        date(2026, 11, 3),
        date(2026, 11, 10),
        date(2026, 11, 17),
        date(2026, 11, 24),
        date(2026, 12, 1),
        date(2026, 12, 8),
        date(2026, 12, 15),
    ]


def test_period_must_start_on_tuesday() -> None:
    validate_period_start(date(2026, 11, 17))
    with pytest.raises(DomainError):
        validate_period_start(date(2026, 11, 18))


def test_ensure_visible_period_rejects_closed_period() -> None:
    today = date(2026, 11, 21)
    with pytest.raises(DomainError) as exc_info:
        ensure_visible_period(date(2026, 11, 17), today)
    assert exc_info.value.status_code == 409
