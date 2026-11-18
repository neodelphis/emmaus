from __future__ import annotations

import os
import secrets
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL")
if not TEST_DATABASE_URL:
    pytest.skip(
        "TEST_DATABASE_URL doit pointer vers une base PostgreSQL de test "
        "(voir README, section Tests).",
        allow_module_level=True,
    )

# L'import de app.main construit une application au chargement du module :
# la configuration doit être disponible avant cet import.
os.environ.setdefault("DATABASE_URL", TEST_DATABASE_URL)
os.environ.setdefault("SECRET_KEY", secrets.token_hex(32))
os.environ.setdefault("ADMIN_EMAIL", "bootstrap@example.com")
os.environ.setdefault("ADMIN_PASSWORD", secrets.token_urlsafe(18))

from app.config import Settings  # noqa: E402
from app.database import Base  # noqa: E402
from app.deps import get_today  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import AdminUser  # noqa: E402
from app.security import hash_password  # noqa: E402
from app.services.bootstrap import ensure_opening_hours  # noqa: E402
from app.services.emails import EmailService  # noqa: E402

TABLES = (
    "password_reset_tokens",
    "day_availabilities",
    "availability_responses",
    "volunteers",
    "admin_users",
    "opening_hours",
)


@pytest.fixture(scope="session")
def settings() -> Settings:
    return Settings(
        database_url=TEST_DATABASE_URL,
        secret_key=secrets.token_hex(32),
        frontend_url="http://localhost:8080",
        seed_admin=False,
        smtp_host="localhost",
        smtp_port=1025,
        cookie_secure=False,
    )


@pytest.fixture(scope="session")
def engine(settings: Settings):
    db_engine = create_engine(settings.database_url)
    Base.metadata.drop_all(db_engine)
    Base.metadata.create_all(db_engine)
    yield db_engine
    db_engine.dispose()


@pytest.fixture
def today() -> date:
    return date(2026, 11, 17)  # un mardi


@pytest.fixture
def app(settings: Settings, engine, today: date):
    application = create_app(settings)
    application.dependency_overrides[get_today] = lambda: today
    return application


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def clean_database(client, engine):
    with Session(engine) as session:
        session.execute(text(f"TRUNCATE TABLE {', '.join(TABLES)} RESTART IDENTITY CASCADE"))
        session.commit()
    with Session(engine) as session:
        ensure_opening_hours(session)
    yield


@pytest.fixture
def db_session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def admin_credentials() -> tuple[str, str]:
    return ("admin@emmaus.fr", "MotDePasseTest-123!")


@pytest.fixture
def admin(client, engine, admin_credentials):
    email, password = admin_credentials
    with Session(engine) as session:
        session.add(AdminUser(email=email, password_hash=hash_password(password)))
        session.commit()
    response = client.post(
        "/api/admin/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return {"email": email, "password": password, **response.json()}


@pytest.fixture
def volunteer(client, admin):
    response = client.post(
        "/api/admin/volunteers",
        json={"name": "Marie Dupont", "email": "marie@example.com"},
    )
    assert response.status_code == 201, response.text
    data = response.json()
    data["token"] = data["link"].split("#", 1)[1]
    return data


@pytest.fixture
def sent_emails(monkeypatch):
    messages: list[dict[str, str]] = []

    def fake_send(self, *, to: str, subject: str, text: str) -> None:
        messages.append({"to": to, "subject": subject, "text": text})

    monkeypatch.setattr(EmailService, "_send", fake_send)
    return messages


def login(client, email: str, password: str):
    return client.post("/api/admin/auth/login", json={"email": email, "password": password})


def set_today(client, value: date) -> None:
    client.app.dependency_overrides[get_today] = lambda: value


def volunteer_headers(token: str) -> dict[str, str]:
    return {"X-Volunteer-Token": token}
