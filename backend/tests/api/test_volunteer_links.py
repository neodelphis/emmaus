from __future__ import annotations

from tests.conftest import volunteer_headers


def _create(client, name: str, email: str | None = None):
    response = client.post(
        "/api/admin/volunteers", json={"name": name, "email": email}
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["token"] = data["link"].split("#", 1)[1]
    return data


def test_link_is_created_with_volunteer(client, admin) -> None:
    data = _create(client, "Jean Martin", "jean@example.com")
    assert data["link"].startswith("http://localhost:8080/b#")
    assert data["has_link"] is True
    assert data["email"] == "jean@example.com"

    response = client.get("/api/volunteer", headers=volunteer_headers(data["token"]))
    assert response.status_code == 200
    payload = response.json()
    assert payload["volunteer_name"] == "Jean Martin"
    assert "email" not in payload
    assert len(payload["periods"]) == 5
    assert len(payload["opening_hours"]) == 5


def test_invalid_or_revoked_link_is_refused(client, admin) -> None:
    response = client.get(
        "/api/volunteer", headers={"X-Volunteer-Token": "jeton-inconnu"}
    )
    assert response.status_code == 404

    volunteer = _create(client, "Sans Lien")
    response = client.post(f"/api/admin/volunteers/{volunteer['id']}/link/revoke")
    assert response.status_code == 204

    response = client.get(
        "/api/volunteer", headers=volunteer_headers(volunteer["token"])
    )
    assert response.status_code == 404

    response = client.get(f"/api/admin/volunteers/{volunteer['id']}/link")
    assert response.status_code == 409


def test_link_is_stable_on_resend_and_copy(client, admin, sent_emails) -> None:
    volunteer = _create(client, "Paul Durand", "paul@example.com")

    response = client.get(f"/api/admin/volunteers/{volunteer['id']}/link")
    assert response.status_code == 200
    assert response.json()["link"] == volunteer["link"]

    response = client.post(f"/api/admin/volunteers/{volunteer['id']}/link/send")
    assert response.status_code == 204
    assert len(sent_emails) == 1
    assert volunteer["link"] in sent_emails[0]["text"]

    # Le renvoi ne régénère pas le jeton.
    response = client.get(f"/api/admin/volunteers/{volunteer['id']}/link")
    assert response.json()["link"] == volunteer["link"]


def test_send_without_email_returns_clear_error(client, admin) -> None:
    volunteer = _create(client, "Sans Courriel")
    response = client.post(f"/api/admin/volunteers/{volunteer['id']}/link/send")
    assert response.status_code == 400
    assert "courriel" in response.json()["detail"].lower()


def test_regenerate_invalidates_previous_link(client, admin) -> None:
    volunteer = _create(client, "Léa Petit")
    old_token = volunteer["token"]

    response = client.post(f"/api/admin/volunteers/{volunteer['id']}/link/regenerate")
    assert response.status_code == 200
    new_link = response.json()["link"]
    assert new_link != volunteer["link"]
    new_token = new_link.split("#", 1)[1]

    assert (
        client.get("/api/volunteer", headers=volunteer_headers(old_token)).status_code
        == 404
    )
    assert (
        client.get("/api/volunteer", headers=volunteer_headers(new_token)).status_code
        == 200
    )


def test_deactivation_preserves_history_but_blocks_access(client, admin) -> None:
    volunteer = _create(client, "Anne Roux")
    headers = volunteer_headers(volunteer["token"])

    response = client.put(
        "/api/volunteer/periods/2026-11-24",
        headers=headers,
        json={
            "days": [
                {"date": "2026-11-25", "kind": "all_day"},
            ]
        },
    )
    assert response.status_code == 200

    response = client.patch(
        f"/api/admin/volunteers/{volunteer['id']}", json={"is_active": False}
    )
    assert response.status_code == 200
    assert response.json()["is_active"] is False

    assert client.get("/api/volunteer", headers=headers).status_code == 404

    response = client.get("/api/admin/week?period_start=2026-11-24")
    assert response.status_code == 200
    assert all(row["id"] != volunteer["id"] for row in response.json()["volunteers"])

    response = client.get(
        "/api/admin/week?period_start=2026-11-24&include_inactive=true"
    )
    assert response.status_code == 200
    row = next(row for row in response.json()["volunteers"] if row["id"] == volunteer["id"])
    assert row["submitted"] is True

    # Réactivation : l'historique et le lien restent valides.
    client.patch(f"/api/admin/volunteers/{volunteer['id']}", json={"is_active": True})
    assert client.get("/api/volunteer", headers=headers).status_code == 200


def test_delete_volunteer_removes_link_and_answers(client, admin) -> None:
    volunteer = _create(client, "Marc Blanc")
    headers = volunteer_headers(volunteer["token"])
    client.put(
        "/api/volunteer/periods/2026-11-24",
        headers=headers,
        json={"days": [{"date": "2026-11-25", "kind": "all_day"}]},
    )

    response = client.delete(f"/api/admin/volunteers/{volunteer['id']}")
    assert response.status_code == 204

    assert client.get("/api/volunteer", headers=headers).status_code == 404
    assert (
        client.get(f"/api/admin/volunteers/{volunteer['id']}/link").status_code == 404
    )


def test_first_volunteer_created_has_unique_token(client, admin) -> None:
    first = _create(client, "Premier")
    second = _create(client, "Second")
    assert first["token"] != second["token"]
