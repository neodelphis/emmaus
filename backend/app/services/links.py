from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.models import Volunteer
from app.security import (
    InvalidSessionError,
    decrypt_secret,
    encrypt_secret,
    generate_token,
    hash_token,
)


class LinkService:
    """Génère et résout les liens personnels sans jamais exposer le jeton côté serveur."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def volunteer_url(self, token: str) -> str:
        # Le jeton est placé dans le fragment : il n'est jamais transmis au serveur
        # lors de l'ouverture du lien, ni journalisé par le proxy.
        return f"{self.settings.frontend_url}/b#{token}"

    def reset_url(self, token: str) -> str:
        return f"{self.settings.frontend_url}/admin/reinitialiser#{token}"

    def issue_link(self, volunteer: Volunteer) -> str:
        token = generate_token()
        volunteer.link_token_hash = hash_token(token)
        volunteer.link_token_encrypted = encrypt_secret(token, self.settings)
        return self.volunteer_url(token)

    def raw_token(self, volunteer: Volunteer) -> str | None:
        if not volunteer.link_token_encrypted:
            return None
        try:
            return decrypt_secret(volunteer.link_token_encrypted, self.settings)
        except InvalidSessionError:
            return None

    def volunteer_link(self, volunteer: Volunteer) -> str | None:
        token = self.raw_token(volunteer)
        return self.volunteer_url(token) if token else None

    def revoke(self, volunteer: Volunteer) -> None:
        volunteer.link_token_hash = None
        volunteer.link_token_encrypted = None

    def find_volunteer(self, session: Session, token: str) -> Volunteer | None:
        token_hash = hash_token(token)
        return session.scalar(
            select(Volunteer).where(
                Volunteer.link_token_hash == token_hash,
                Volunteer.is_active.is_(True),
            )
        )
