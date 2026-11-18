from __future__ import annotations

from tests.conftest import volunteer_headers


def _create_volunteer(client, *, default_site: str = "vaire") -> dict:
    response = client.post(
        "/api/admin/volunteers",
        json={
            "name": "Camille Site",
            "email": "camille.site@example.com",
            "gender": "femme",
            "default_site": default_site,
        },
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["token"] = data["link"].split("#", 1)[1]
    return data


def test_admin_can_list_sites_and_hours(client, admin) -> None:
    response = client.get("/api/admin/sites")
    assert response.status_code == 200
    assert response.json() == [
        {"code": "vaire", "name": "Vairé"},
        {"code": "les-essarts", "name": "Les Essarts"},
    ]

    for site in ("vaire", "les-essarts"):
        response = client.get(f"/api/admin/sites/{site}/opening-hours")
        assert response.status_code == 200
        assert len(response.json()) == 5
        assert response.json()[0]["open"] == "08:00"
        assert response.json()[0]["close"] == "18:00"


def test_volunteer_default_site_and_other_site_choice(client, admin) -> None:
    volunteer = _create_volunteer(client, default_site="les-essarts")
    assert volunteer["default_site"] == "les-essarts"

    headers = volunteer_headers(volunteer["token"])
    access = client.get("/api/volunteer", headers=headers).json()
    assert access["default_site"] == "les-essarts"
    assert [site["code"] for site in access["sites"]] == ["vaire", "les-essarts"]

    response = client.put(
        "/api/volunteer/periods/2026-11-17",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-18", "kind": "all_day", "site": "vaire"},
                {"date": "2026-11-19", "kind": "slot", "start": "09:00", "end": "12:00", "site": "les-essarts"},
            ]
        },
    )
    assert response.status_code == 200, response.text
    days = {day["date"]: day for day in response.json()["days"]}
    assert days["2026-11-18"]["answer"]["site"] == "vaire"
    assert days["2026-11-19"]["answer"]["site"] == "les-essarts"

    week_vaire = client.get(
        "/api/admin/week?period_start=2026-11-17&site=vaire"
    ).json()
    row = next(v for v in week_vaire["volunteers"] if v["id"] == volunteer["id"])
    statuses = {day["date"]: day["status"] for day in row["days"]}
    assert statuses["2026-11-18"] == "all_day"
    assert statuses["2026-11-19"] == "unavailable"

    week_essarts = client.get(
        "/api/admin/week?period_start=2026-11-17&site=les-essarts"
    ).json()
    row = next(v for v in week_essarts["volunteers"] if v["id"] == volunteer["id"])
    statuses = {day["date"]: day["status"] for day in row["days"]}
    assert statuses["2026-11-18"] == "unavailable"
    assert statuses["2026-11-19"] == "slot"


def test_admin_last_site_is_saved_and_used_by_default(client, admin) -> None:
    response = client.put(
        "/api/admin/auth/last-site", json={"site": "les-essarts"}
    )
    assert response.status_code == 200
    assert response.json()["last_site"] == "les-essarts"
    assert client.get("/api/admin/auth/me").json()["last_site"] == "les-essarts"

    week = client.get("/api/admin/week?period_start=2026-11-17").json()
    assert week["site"] == "les-essarts"

    week = client.get(
        "/api/admin/week?period_start=2026-11-17&site=vaire"
    ).json()
    assert week["site"] == "vaire"


def test_opening_hours_are_independent_per_site(client, admin) -> None:
    hours = client.get("/api/admin/sites/les-essarts/opening-hours").json()
    for row in hours:
        if row["weekday"] == 3:  # jeudi
            row["open"] = "09:00"
            row["close"] = "16:00"
    response = client.put(
        "/api/admin/sites/les-essarts/opening-hours", json={"hours": hours}
    )
    assert response.status_code == 200

    vaire = client.get("/api/admin/sites/vaire/opening-hours").json()
    vaire_thursday = next(row for row in vaire if row["weekday"] == 3)
    assert vaire_thursday["open"] == "08:00"
    assert vaire_thursday["close"] == "18:00"

    volunteer = _create_volunteer(client, default_site="les-essarts")
    headers = volunteer_headers(volunteer["token"])
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
                {
                    "date": "2026-11-19",
                    "kind": "slot",
                    "start": "08:00",
                    "end": "10:00",
                    "site": "vaire",
                }
            ]
        },
    )
    assert response.status_code == 200, response.text
