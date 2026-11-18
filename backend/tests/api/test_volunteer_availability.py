from __future__ import annotations

from datetime import UTC, date, datetime, time, timedelta

from app.models import AvailabilityResponse, DayAvailability
from tests.conftest import set_today, volunteer_headers


def _add_history(
    session,
    volunteer_id,
    period_start: date,
    *,
    day_offset: int,
    kind: str,
    start=None,
    end=None,
    submitted_at: datetime | None = None,
) -> None:
    response = AvailabilityResponse(
        volunteer_id=volunteer_id,
        period_start=period_start,
        submitted_at=submitted_at or datetime(2026, 11, 10, 12, tzinfo=UTC),
    )
    session.add(response)
    session.flush()
    if kind != "unavailable":
        session.add(
            DayAvailability(
                response_id=response.id,
                day_date=period_start + timedelta(days=day_offset),
                kind=kind,
                start_time=start,
                end_time=end,
            )
        )
    session.commit()


def test_current_period_days_and_closing(client, volunteer) -> None:
    response = client.get("/api/volunteer", headers=volunteer_headers(volunteer["token"]))
    assert response.status_code == 200
    payload = response.json()
    assert payload["today"] == "2026-11-17"
    assert [period["start"] for period in payload["periods"]] == [
        "2026-11-17",
        "2026-11-24",
        "2026-12-01",
        "2026-12-08",
        "2026-12-15",
    ]
    current = payload["periods"][0]
    assert current["submitted"] is False
    editable = {day["date"]: day["editable"] for day in current["days"]}
    assert editable["2026-11-17"] is False  # la veille à 23 h 59 est passée
    assert editable["2026-11-18"] is True
    assert all(day["suggestion"] is None for day in current["days"])


def test_save_partial_period_and_admin_distinction(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-18", "kind": "all_day"},
                {"date": "2026-11-19", "kind": "slot", "start": "09:00", "end": "12:00"},
                {"date": "2026-11-20", "kind": "unavailable"},
                {"date": "2026-11-21", "kind": "slot", "start": "08:00", "end": "09:00"},
            ]
        },
    )
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["submitted"] is True
    assert payload["submitted_at"] is not None
    days = {day["date"]: day for day in payload["days"]}
    assert days["2026-11-18"]["answer"] == {
        "kind": "all_day",
        "start": None,
        "end": None,
    }
    assert days["2026-11-19"]["answer"]["start"] == "09:00"
    assert days["2026-11-20"]["answer"] is None
    assert days["2026-11-17"]["answer"] is None  # non renseigné, donc indisponible

    response = client.get("/api/admin/week?period_start=2026-11-17")
    assert response.status_code == 200
    row = next(r for r in response.json()["volunteers"] if r["id"] == volunteer["id"])
    assert row["submitted"] is True
    statuses = {day["date"]: day["status"] for day in row["days"]}
    assert statuses["2026-11-17"] == "unavailable"
    assert statuses["2026-11-18"] == "all_day"
    assert statuses["2026-11-19"] == "slot"
    assert statuses["2026-11-20"] == "unavailable"


def test_closed_day_rejects_the_whole_save(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-17", "kind": "all_day"},
                {"date": "2026-11-18", "kind": "all_day"},
            ]
        },
    )
    assert response.status_code == 409
    assert "23 h 59" in response.json()["detail"]

    access = client.get("/api/volunteer", headers=headers).json()
    assert access["periods"][0]["submitted"] is False


def test_slot_must_fit_opening_hours_and_step(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    base = {"date": "2026-11-18", "kind": "slot"}

    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={"days": [{**base, "start": "07:30", "end": "09:00"}]},
    )
    assert response.status_code == 400

    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={"days": [{**base, "start": "09:15", "end": "10:00"}]},
    )
    assert response.status_code == 400

    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={"days": [{**base, "start": "12:00", "end": "09:00"}]},
    )
    assert response.status_code == 400


def test_period_outside_the_visible_range_is_refused(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-10",
        headers=headers,
        json={"days": []},
    )
    assert response.status_code == 409


def test_period_must_start_on_tuesday(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-18",
        headers=headers,
        json={"days": []},
    )
    assert response.status_code == 400


def test_submitted_empty_period_differs_from_unanswered(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-24",
        headers=headers,
        json={"days": []},
    )
    assert response.status_code == 200
    assert response.json()["submitted"] is True

    second = client.post(
        "/api/admin/volunteers", json={"name": "Sans réponse"}
    ).json()

    week = client.get("/api/admin/week?period_start=2026-11-24").json()
    rows = {row["id"]: row for row in week["volunteers"]}
    assert rows[volunteer["id"]]["submitted"] is True
    assert all(day["status"] == "unavailable" for day in rows[volunteer["id"]]["days"])

    assert rows[second["id"]]["submitted"] is False
    assert all(day["status"] == "unanswered" for day in rows[second["id"]]["days"])


def test_suggestions_use_four_most_recent_completed_periods(client, volunteer, db_session) -> None:
    _add_history(
        db_session,
        volunteer["id"],
        date(2026, 11, 10),
        day_offset=1,
        kind="all_day",
        submitted_at=datetime(2026, 11, 15, 12, tzinfo=UTC),
    )
    _add_history(
        db_session,
        volunteer["id"],
        date(2026, 11, 3),
        day_offset=1,
        kind="all_day",
        submitted_at=datetime(2026, 11, 8, 12, tzinfo=UTC),
    )
    _add_history(
        db_session,
        volunteer["id"],
        date(2026, 10, 27),
        day_offset=1,
        kind="slot",
        start=time(9, 0),
        end=time(12, 0),
        submitted_at=datetime(2026, 11, 1, 12, tzinfo=UTC),
    )
    _add_history(
        db_session,
        volunteer["id"],
        date(2026, 10, 20),
        day_offset=1,
        kind="slot",
        start=time(9, 0),
        end=time(12, 0),
        submitted_at=datetime(2026, 10, 25, 12, tzinfo=UTC),
    )
    # Cinquième période : elle ne doit pas entrer dans le calcul.
    _add_history(
        db_session,
        volunteer["id"],
        date(2026, 10, 13),
        day_offset=1,
        kind="slot",
        start=time(9, 0),
        end=time(12, 0),
        submitted_at=datetime(2026, 10, 18, 12, tzinfo=UTC),
    )
    # Période future : jamais utilisée.
    _add_history(
        db_session,
        volunteer["id"],
        date(2026, 12, 1),
        day_offset=1,
        kind="all_day",
        submitted_at=datetime(2026, 11, 16, 12, tzinfo=UTC),
    )

    response = client.get("/api/volunteer", headers=volunteer_headers(volunteer["token"]))
    assert response.status_code == 200
    period = next(p for p in response.json()["periods"] if p["start"] == "2026-11-17")
    wednesday = next(day for day in period["days"] if day["date"] == "2026-11-18")
    assert wednesday["suggestion"] == {
        "kind": "all_day",
        "start": None,
        "end": None,
    }


def test_changing_opening_hours_does_not_rewrite_existing_answers(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-19", "kind": "slot", "start": "08:00", "end": "17:00"}
            ]
        },
    )
    assert response.status_code == 200

    hours = client.get("/api/admin/opening-hours").json()
    for row in hours:
        if row["weekday"] == 3:  # jeudi
            row["open"] = "09:00"
            row["close"] = "16:00"
    response = client.put("/api/admin/opening-hours", json={"hours": hours})
    assert response.status_code == 200

    access = client.get("/api/volunteer", headers=headers).json()
    thursday = next(
        day
        for day in access["periods"][0]["days"]
        if day["date"] == "2026-11-19"
    )
    assert thursday["answer"]["start"] == "08:00"

    # Une nouvelle saisie doit respecter les nouvelles bornes.
    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-19", "kind": "slot", "start": "08:00", "end": "10:00"}
            ]
        },
    )
    assert response.status_code == 400

    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-19", "kind": "slot", "start": "09:00", "end": "16:00"}
            ]
        },
    )
    assert response.status_code == 200


def test_volunteer_cannot_access_another_volunteer_data(client, volunteer) -> None:
    second = client.post(
        "/api/admin/volunteers", json={"name": "Autre Personne"}
    ).json()
    payload = client.get(
        "/api/volunteer", headers=volunteer_headers(second["link"].split("#", 1)[1])
    ).json()
    assert payload["volunteer_name"] == "Autre Personne"
    assert "Marie Dupont" not in str(payload)


def test_saturday_hides_current_period(client, volunteer) -> None:
    set_today(client, date(2026, 11, 21))
    payload = client.get(
        "/api/volunteer", headers=volunteer_headers(volunteer["token"])
    ).json()
    assert [period["start"] for period in payload["periods"]] == [
        "2026-11-24",
        "2026-12-01",
        "2026-12-08",
        "2026-12-15",
    ]
