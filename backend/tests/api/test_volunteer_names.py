from __future__ import annotations


def test_volunteer_first_and_last_names_can_be_created_and_updated(client, admin) -> None:
    response = client.post(
        "/api/admin/volunteers",
        json={
            "name": "Camille Martin",
            "first_name": "Camille",
            "last_name": "Martin",
        },
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["first_name"] == "Camille"
    assert created["last_name"] == "Martin"

    response = client.patch(
        f"/api/admin/volunteers/{created['id']}",
        json={"first_name": "Jean", "last_name": "Dupont"},
    )
    assert response.status_code == 200, response.text
    assert response.json()["first_name"] == "Jean"
    assert response.json()["last_name"] == "Dupont"
    assert response.json()["name"] == "Jean Dupont"


def test_volunteer_names_are_split_when_only_full_name_is_sent(client, admin) -> None:
    response = client.post(
        "/api/admin/volunteers", json={"name": "Sans Prénom"}
    )
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["first_name"] == "Sans"
    assert created["last_name"] == "Prénom"


def test_volunteer_update_requires_both_names(client, admin) -> None:
    created = client.post(
        "/api/admin/volunteers", json={"name": "Solo"}
    ).json()
    response = client.patch(
        f"/api/admin/volunteers/{created['id']}",
        json={"first_name": "Seul"},
    )
    assert response.status_code == 422
