from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.config import Settings
from app.security import (
    InvalidSessionError,
    create_session_token,
    decode_session_token,
    decrypt_secret,
    encrypt_secret,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)


@pytest.fixture
def local_settings() -> Settings:
    return Settings(
        database_url="postgresql+psycopg://unused:unused@localhost:5433/unused",
        secret_key=secrets.token_hex(32),
    )


def test_password_hash_roundtrip() -> None:
    password_hash = hash_password("MotDePasseTest-123!")
    assert password_hash != "MotDePasseTest-123!"
    assert verify_password("MotDePasseTest-123!", password_hash) is True
    assert verify_password("AutreMotDePasse-123!", password_hash) is False


def test_generated_tokens_are_unique_and_hashed() -> None:
    first, second = generate_token(), generate_token()
    assert first != second
    assert len(first) >= 32
    assert hash_token(first) != first
    assert hash_token(first) == hash_token(first)


def test_secret_encryption_roundtrip(local_settings: Settings) -> None:
    encrypted = encrypt_secret("jeton-secret", local_settings)
    assert "jeton-secret" not in encrypted
    assert decrypt_secret(encrypted, local_settings) == "jeton-secret"


def test_session_token_roundtrip(local_settings: Settings) -> None:
    admin_id = uuid4()
    token = create_session_token(admin_id, local_settings)
    payload = decode_session_token(token, local_settings)
    assert payload["sub"] == str(admin_id)

    with pytest.raises(InvalidSessionError):
        decode_session_token(token + "x", local_settings)


def test_expired_session_token_is_rejected(local_settings: Settings) -> None:
    admin_id = uuid4()
    token = create_session_token(admin_id, local_settings, now=datetime.now(UTC) - timedelta(days=2))
    with pytest.raises(InvalidSessionError):
        decode_session_token(token, local_settings)
