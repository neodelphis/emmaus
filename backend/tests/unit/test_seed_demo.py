from __future__ import annotations

from collections import defaultdict
from datetime import date, time, timedelta

import pytest

from app.domain.periods import period_end, visible_period_starts
from app.domain.sites import SITE_CODES
from scripts.seed_demo import (
    DEMO_DOMAIN,
    DEMO_VOLUNTEERS,
    build_demo_plan,
    daily_counts,
)

WEEK_START = date(2026, 11, 16)  # un lundi
DAYS_OF_WEEK = tuple(WEEK_START + timedelta(days=offset) for offset in range(7))


@pytest.mark.parametrize("today", DAYS_OF_WEEK)
def test_plan_contains_about_twenty_active_volunteers(today: date) -> None:
    plan = build_demo_plan(today)
    active = [spec for spec in plan.volunteers if spec.is_active]
    assert len(active) == 20
    assert len(plan.volunteers) == 21
    assert sum(1 for spec in plan.volunteers if not spec.is_active) == 1
    assert {spec.default_site for spec in active} == set(SITE_CODES)


@pytest.mark.parametrize("today", DAYS_OF_WEEK)
def test_busiest_site_day_reaches_fifteen_volunteers(today: date) -> None:
    plan = build_demo_plan(today)
    per_site_day = [
        daily_counts(plan, period_start, site)
        for period_start in plan.visible_starts
        for site in SITE_CODES
    ]
    # Au moins une journée réunit 15 bénévoles sur un même site, sans jamais
    # dépasser cette densité (limite demandée pour les données de test).
    assert max(max(counts) for counts in per_site_day) == 15
    assert all(max(counts) <= 15 for counts in per_site_day)


def test_plan_is_anchored_on_the_given_today() -> None:
    for today in (date(2026, 11, 16), date(2027, 1, 1), date(2030, 6, 15)):
        plan = build_demo_plan(today)
        assert plan.today == today
        assert plan.visible_starts == tuple(visible_period_starts(today))
        for response in plan.responses:
            assert response.period_start.weekday() == 1  # mardi
            assert (
                response.period_start in plan.visible_starts
                or period_end(response.period_start) < today
            )
        for start in plan.history_starts:
            assert period_end(start) < today
            assert start not in plan.visible_starts


def test_plan_follows_today_from_one_week_to_the_next() -> None:
    first = build_demo_plan(date(2026, 11, 17))
    second = build_demo_plan(date(2026, 11, 24))
    assert second.visible_starts[0] == first.visible_starts[1]
    assert second.history_starts[0] == first.history_starts[0] + timedelta(days=7)


@pytest.mark.parametrize("today", DAYS_OF_WEEK)
def test_demo_days_respect_half_hour_steps_and_opening_hours(today: date) -> None:
    plan = build_demo_plan(today)
    for response in plan.responses:
        assert set(response.days).issubset(range(5))
        for day in response.days.values():
            if day.kind == "all_day":
                assert day.start is None
                assert day.end is None
                continue
            assert day.kind == "slot"
            assert day.start is not None and day.end is not None
            assert day.start < day.end
            for bound in (day.start, day.end):
                assert bound.minute in (0, 30)
                assert time(8, 0) <= bound <= time(18, 0)
            if day.site is not None:
                assert day.site in SITE_CODES


def test_plan_keeps_the_documented_profiles() -> None:
    plan = build_demo_plan(date(2026, 11, 17))
    current = plan.visible_starts[0]
    periods_by_volunteer: dict[str, set[date]] = defaultdict(set)
    for response in plan.responses:
        periods_by_volunteer[response.volunteer_key].add(response.period_start)

    # Marie n'a que de l'historique : ses disponibilités servent aux propositions.
    assert periods_by_volunteer["marie"]
    assert current not in periods_by_volunteer["marie"]
    # Fatima n'a aucune réponse : elle illustre « sans réponse ».
    assert periods_by_volunteer["fatima"] == set()
    # L'ancien bénévole est désactivé mais conserve son historique.
    assert plan.volunteer("ancien").is_active is False
    assert periods_by_volunteer["ancien"]


def test_plan_has_one_response_per_volunteer_and_period() -> None:
    plan = build_demo_plan(date(2026, 11, 17))
    keys = [(response.volunteer_key, response.period_start) for response in plan.responses]
    assert len(keys) == len(set(keys))


def test_demo_emails_are_unique_and_use_the_demo_domain() -> None:
    emails = [spec.email for spec in DEMO_VOLUNTEERS]
    assert len(emails) == len(set(emails))
    assert all(email.endswith(DEMO_DOMAIN) for email in emails)
    assert all(email.isascii() for email in emails)
    assert all(spec.first_name and spec.last_name for spec in DEMO_VOLUNTEERS)
