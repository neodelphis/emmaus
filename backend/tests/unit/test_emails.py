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
