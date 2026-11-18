from __future__ import annotations

import base64
import hashlib
import secrets
from datetime import UTC, datetime, timedelta
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken

from app.config import Settings

# Paramètres Argon2 conformes aux recommandations OWASP (19 Mio, 2 passes).
_password_hasher = PasswordHasher(time_cost=2, memory_cost=19456, parallelism=1)

# Utilisé pour vérifier un mot de passe même lorsque le compte n'existe pas,
# afin de ne pas révéler l'existence d'une adresse par le temps de réponse.
DUMMY_PASSWORD_HASH = _password_hasher.hash(secrets.token_urlsafe(24))

SESSION_COOKIE_NAME = "emmaus_admin_session"


class InvalidSessionError(Exception):
    pass


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def generate_token() -> str:
    """Jeton opaque de 256 bits, adapté aux URL."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session_token(
    admin_id: UUID,
    settings: Settings,
    now: datetime | None = None,
    session_version: int = 1,
) -> str:
    issued_at = now or datetime.now(UTC)
    payload = {
        "sub": str(admin_id),
        "ver": session_version,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + timedelta(hours=settings.session_hours)).timestamp()),
    }
    return jwt.encode(payload, settings.secret, algorithm="HS256")


def decode_session_token(token: str, settings: Settings) -> dict:
    try:
        return jwt.decode(
            token,
            settings.secret,
            algorithms=["HS256"],
            options={"require": ["sub", "ver", "iat", "exp"]},
        )
    except jwt.InvalidTokenError as exc:  # type: ignore[attr-defined]
        raise InvalidSessionError from exc


def _fernet(settings: Settings) -> Fernet:
    digest = hashlib.sha256(settings.secret.encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str, settings: Settings) -> str:
    return _fernet(settings).encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_secret(value: str, settings: Settings) -> str:
    try:
        return _fernet(settings).decrypt(value.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise InvalidSessionError("Le secret chiffré est illisible.") from exc
