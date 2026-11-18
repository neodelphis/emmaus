from __future__ import annotations


def test_regular_admin_can_access_planning_and_volunteers(client, regular_admin) -> None:
    assert client.get("/api/admin/week").status_code == 200
    assert client.get("/api/admin/volunteers").status_code == 200
    assert client.get("/api/admin/sites").status_code == 200
    assert regular_admin["role"] == "admin"


def test_regular_admin_cannot_manage_administrators_or_hours(
    client, regular_admin
) -> None:
    assert client.get("/api/admin/auth/administrators").status_code == 403
    response = client.post(
        "/api/admin/auth/administrators",
        json={
            "email": "nouveau@example.com",
            "password": "MotDePasseTest-123!",
            "gender": "homme",
        },
    )
    assert response.status_code == 403

    hours = client.get("/api/admin/sites/vaire/opening-hours")
    assert hours.status_code == 200
    response = client.put(
        "/api/admin/sites/vaire/opening-hours", json={"hours": hours.json()}
    )
    assert response.status_code == 403


def test_super_admin_can_manage_administrators(client, admin) -> None:
    assert admin["role"] == "super_admin"
    assert client.get("/api/admin/auth/administrators").status_code == 200
    response = client.post(
        "/api/admin/auth/administrators",
        json={
            "email": "collaborateur@example.com",
            "password": "MotDePasseTest-123!",
            "gender": "femme",
            "role": "admin",
            "first_name": "Camille",
            "last_name": "Martin",
        },
    )
    assert response.status_code == 201
    assert response.json()["role"] == "admin"
    assert response.json()["first_name"] == "Camille"
