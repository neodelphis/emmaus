from __future__ import annotations

from uuid import uuid4

from tests.conftest import volunteer_headers


def _week_day(client, volunteer_id: str, day_date: str) -> dict:
    week = client.get("/api/admin/week?period_start=2026-11-24").json()
    row = next(row for row in week["volunteers"] if row["id"] == volunteer_id)
    return next(day for day in row["days"] if day["date"] == day_date)


def test_meal_is_included_by_default_and_can_be_toggled(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-24",
        headers=headers,
        json={"days": [{"date": "2026-11-24", "kind": "all_day"}]},
    )
    assert response.status_code == 200

    day = _week_day(client, volunteer["id"], "2026-11-24")
    assert day["status"] == "all_day"
    assert day["meal_excluded"] is False

    response = client.put(
        f"/api/admin/volunteers/{volunteer['id']}/meal-exclusions/2026-11-24"
    )
    assert response.status_code == 204

    day = _week_day(client, volunteer["id"], "2026-11-24")
    assert day["status"] == "all_day"
    assert day["meal_excluded"] is True

    # L'exclusion est idempotente.
    response = client.put(
        f"/api/admin/volunteers/{volunteer['id']}/meal-exclusions/2026-11-24"
    )
    assert response.status_code == 204
    assert _week_day(client, volunteer["id"], "2026-11-24")["meal_excluded"] is True

    response = client.delete(
        f"/api/admin/volunteers/{volunteer['id']}/meal-exclusions/2026-11-24"
    )
    assert response.status_code == 204
    assert _week_day(client, volunteer["id"], "2026-11-24")["meal_excluded"] is False


def test_meal_exclusion_requires_an_all_day_availability(client, volunteer) -> None:
    headers = volunteer_headers(volunteer["token"])
    response = client.put(
        "/api/volunteer/periods/2026-11-24",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-25", "kind": "slot", "start": "09:00", "end": "12:00"}
            ]
        },
    )
    assert response.status_code == 200

    response = client.put(
        f"/api/admin/volunteers/{volunteer['id']}/meal-exclusions/2026-11-25"
    )
    assert response.status_code == 409
    assert "toute la journée" in response.json()["detail"].lower()

    # Aucune disponibilité du tout.
    response = client.put(
        f"/api/admin/volunteers/{volunteer['id']}/meal-exclusions/2026-11-26"
    )
    assert response.status_code == 409


def test_meal_endpoints_require_authentication(client) -> None:
    response = client.put(
        f"/api/admin/volunteers/{uuid4()}/meal-exclusions/2026-11-24"
    )
    assert response.status_code == 401
    response = client.delete(
        f"/api/admin/volunteers/{uuid4()}/meal-exclusions/2026-11-24"
    )
    assert response.status_code == 401
