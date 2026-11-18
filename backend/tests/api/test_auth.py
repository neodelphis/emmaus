from __future__ import annotations

import re

from tests.conftest import login


def test_admin_endpoints_require_authentication(client) -> None:
    for path in ("/api/admin/volunteers", "/api/admin/week", "/api/admin/sites"):
        response = client.get(path)
        assert response.status_code == 401


def test_login_logout_flow(client, admin) -> None:
    response = client.get("/api/admin/auth/me")
    assert response.status_code == 200
    assert response.json()["email"] == admin["email"]

    response = client.post("/api/admin/auth/logout")
    assert response.status_code == 204

    response = client.get("/api/admin/auth/me")
    assert response.status_code == 401


def test_login_rejects_bad_password(client, admin_credentials) -> None:
    email, _ = admin_credentials
    response = login(client, email, "MauvaisMotDePasse-123!")
    assert response.status_code == 401
    assert "incorrect" in response.json()["detail"].lower()


def test_forgot_password_is_generic_for_unknown_account(client, sent_emails) -> None:
    response = client.post(
        "/api/admin/auth/forgot-password", json={"email": "inconnu@example.com"}
    )
    assert response.status_code == 202
    assert sent_emails == []


def test_password_reset_flow_invalidates_old_sessions(
    client, admin, sent_emails
) -> None:
    response = client.post(
        "/api/admin/auth/forgot-password", json={"email": admin["email"]}
    )
    assert response.status_code == 202
    assert len(sent_emails) == 1

    match = re.search(r"/admin/reinitialiser#([A-Za-z0-9_-]+)", sent_emails[0]["text"])
    assert match is not None
    token = match.group(1)

    new_password = "NouveauMotDePasse-123!"
    response = client.post(
        "/api/admin/auth/reset-password",
        json={"token": token, "password": new_password},
    )
    assert response.status_code == 204

    # La session ouverte avant la réinitialisation n'est plus acceptée.
    assert client.get("/api/admin/auth/me").status_code == 401
    assert login(client, admin["email"], admin["password"]).status_code == 401
    assert login(client, admin["email"], new_password).status_code == 200

    # Un jeton de réinitialisation est à usage unique.
    response = client.post(
        "/api/admin/auth/reset-password",
        json={"token": token, "password": "EncoreUnAutre-123!"},
    )
    assert response.status_code == 400


def test_password_reset_rejects_unknown_token(client) -> None:
    response = client.post(
        "/api/admin/auth/reset-password",
        json={"token": "jeton-invalide-mais-suffisamment-long", "password": "MotDePasseTest-123!"},
    )
    assert response.status_code == 400


def test_create_administrator_and_duplicate(client, admin) -> None:
    response = client.post(
        "/api/admin/auth/administrators",
        json={
            "email": "seconde@emmaus.fr",
            "password": "SecondCompte-123!",
            "gender": "femme",
        },
    )
    assert response.status_code == 201
    assert response.json()["email"] == "seconde@emmaus.fr"
    assert response.json()["gender"] == "femme"

    response = client.post(
        "/api/admin/auth/administrators",
        json={
            "email": "SECONDE@emmaus.fr",
            "password": "SecondCompte-123!",
            "gender": "homme",
        },
    )
    assert response.status_code == 409

    response = client.get("/api/admin/auth/administrators")
    assert response.status_code == 200
    assert len(response.json()) == 2

    assert login(client, "seconde@emmaus.fr", "SecondCompte-123!").status_code == 200
    assert client.get("/api/admin/auth/me").json()["gender"] == "femme"


def test_create_administrator_requires_strong_password(client, admin) -> None:
    response = client.post(
        "/api/admin/auth/administrators",
        json={"email": "faible@emmaus.fr", "password": "court", "gender": "homme"},
    )
    assert response.status_code == 422


def test_create_administrator_requires_gender(client, admin) -> None:
    response = client.post(
        "/api/admin/auth/administrators",
        json={"email": "sans-genre@emmaus.fr", "password": "MotDePasseTest-123!"},
    )
    assert response.status_code == 422


def test_administrator_gender_can_be_updated(client, admin) -> None:
    response = client.patch("/api/admin/auth/me", json={"gender": "femme"})
    assert response.status_code == 200
    assert response.json()["gender"] == "femme"
    assert client.get("/api/admin/auth/me").json()["gender"] == "femme"

    response = client.patch("/api/admin/auth/me", json={"gender": "autre"})
    assert response.status_code == 422
