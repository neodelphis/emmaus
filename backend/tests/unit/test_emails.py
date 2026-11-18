from __future__ import annotations

import secrets
import smtplib

from app.config import Settings
from app.services.emails import EmailService


def test_from_header_is_well_formed(monkeypatch) -> None:
    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@localhost:5433/unused",
        secret_key=secrets.token_hex(32),
        smtp_from="Emmaus <ne-pas-repondre@emmaus.local>",
    )
    captured: dict[str, object] = {}

    class FakeSMTP:
        def __init__(self, host: str, port: int, timeout: int) -> None:
            captured["host"] = host
            captured["port"] = port

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def send_message(self, message) -> None:
            captured["from"] = message["From"]
            captured["to"] = message["To"]
            captured["body"] = message.get_content()

    monkeypatch.setattr(smtplib, "SMTP", FakeSMTP)
    EmailService(settings).send_volunteer_link(
        to="benevole@example.com",
        name="Marie",
        link="http://localhost:8080/b#jeton",
    )

    assert captured["from"] == "Emmaus <ne-pas-repondre@emmaus.local>"
    assert captured["to"] == "benevole@example.com"
    assert "http://localhost:8080/b#jeton" in str(captured["body"])


def test_smtp_ssl_and_authentication(monkeypatch) -> None:
    settings = Settings(
        database_url="postgresql+psycopg://unused:unused@localhost:5433/unused",
        secret_key=secrets.token_hex(32),
        smtp_host="ssl0.ovh.net",
        smtp_port=465,
        smtp_username="ne-pas-repondre@neodelphis.ovh",
        smtp_password="mot-de-passe-smtp",
        smtp_use_ssl=True,
        smtp_from="Emmaus <ne-pas-repondre@neodelphis.ovh>",
    )
    captured: dict[str, object] = {}

    class FakeSMTPSSL:
        def __init__(self, host: str, port: int, timeout: int, context) -> None:
            captured["host"] = host
            captured["port"] = port
            captured["timeout"] = timeout
            captured["context"] = context

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            return None

        def login(self, username: str, password: str) -> None:
            captured["username"] = username
            captured["password"] = password

        def send_message(self, message) -> None:
            captured["subject"] = message["Subject"]

    monkeypatch.setattr(smtplib, "SMTP_SSL", FakeSMTPSSL)
    EmailService(settings).send_password_reset(
        to="admin@example.com",
        link="https://emmaus-staging.neodelphis.ovh/admin/reinitialiser#jeton",
    )

    assert captured["host"] == "ssl0.ovh.net"
    assert captured["port"] == 465
    assert captured["username"] == "ne-pas-repondre@neodelphis.ovh"
    assert captured["password"] == "mot-de-passe-smtp"
    assert captured["subject"] == "Réinitialisation de votre mot de passe Emmaüs"
    assert captured["context"] is not None
