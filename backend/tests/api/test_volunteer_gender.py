from __future__ import annotations


def test_volunteer_gender_can_be_set_and_updated(client, admin) -> None:
    response = client.post(
        "/api/admin/volunteers",
        json={"name": "Camille Martin", "email": "camille@example.com", "gender": "femme"},
    )
    assert response.status_code == 201
    created = response.json()
    assert created["gender"] == "femme"

    response = client.patch(
        f"/api/admin/volunteers/{created['id']}", json={"gender": "homme"}
    )
    assert response.status_code == 200
    assert response.json()["gender"] == "homme"

    response = client.get("/api/admin/volunteers")
    row = next(item for item in response.json() if item["id"] == created["id"])
    assert row["gender"] == "homme"


def test_volunteer_gender_is_optional_for_existing_records(client, admin) -> None:
    response = client.post(
        "/api/admin/volunteers", json={"name": "Sans Genre"}
    )
    assert response.status_code == 201
    assert response.json()["gender"] is None


def test_volunteer_gender_must_be_known(client, admin) -> None:
    response = client.post(
        "/api/admin/volunteers",
        json={"name": "Genre Invalide", "gender": "autre"},
    )
    assert response.status_code == 422
