from __future__ import annotations

from datetime import time

import pytest

from app.domain.availability import TimeWindow, validate_day_answer, validate_time_window
from app.domain.errors import DomainError

WINDOW = TimeWindow(open_time=time(8, 0), close_time=time(18, 0))


def test_unavailable_day_has_no_times() -> None:
    validate_day_answer(kind="unavailable", start=None, end=None, window=WINDOW)
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="unavailable", start=time(9, 0), end=time(12, 0), window=WINDOW
        )


def test_all_day_has_no_times() -> None:
    validate_day_answer(kind="all_day", start=None, end=None, window=WINDOW)
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="all_day", start=time(9, 0), end=None, window=WINDOW
        )


def test_slot_must_follow_thirty_minute_step() -> None:
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="slot", start=time(9, 15), end=time(12, 0), window=WINDOW
        )


def test_slot_must_be_ordered() -> None:
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="slot", start=time(12, 0), end=time(12, 0), window=WINDOW
        )


def test_slot_must_fit_opening_hours() -> None:
    validate_day_answer(kind="slot", start=time(8, 0), end=time(18, 0), window=WINDOW)
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="slot", start=time(7, 30), end=time(12, 0), window=WINDOW
        )
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="slot", start=time(9, 0), end=time(18, 30), window=WINDOW
        )


def test_slot_requires_configured_hours() -> None:
    with pytest.raises(DomainError):
        validate_day_answer(
            kind="slot", start=time(9, 0), end=time(12, 0), window=None
        )


def test_opening_hours_validation() -> None:
    validate_time_window(WINDOW)
    with pytest.raises(DomainError):
        validate_time_window(TimeWindow(open_time=time(9, 15), close_time=time(18, 0)))
    with pytest.raises(DomainError):
        validate_time_window(TimeWindow(open_time=time(18, 0), close_time=time(9, 0)))
