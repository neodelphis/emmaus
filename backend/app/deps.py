from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.config import Settings
from app.domain.periods import today_paris
from app.models import AdminUser, Volunteer
from app.security import (
    SESSION_COOKIE_NAME,
    InvalidSessionError,
    decode_session_token,
)
from app.services.emails import EmailService
from app.services.links import LinkService

VOLUNTEER_TOKEN_HEADER = "X-Volunteer-Token"


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_link_service(settings: Settings = Depends(get_settings)) -> LinkService:
    return LinkService(settings)


def get_email_service(settings: Settings = Depends(get_settings)) -> EmailService:
    return EmailService(settings)


def get_db(request: Request) -> Iterator[Session]:
    session_factory = request.app.state.session_factory
    with session_factory() as session:
        yield session


def get_today() -> date:
    return today_paris()


def require_admin(
    request: Request,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminUser:
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vous devez vous connecter.",
        )
    try:
        payload = decode_session_token(token, settings)
        admin_id = UUID(payload["sub"])
        session_version = int(payload["ver"])
    except (InvalidSessionError, ValueError, KeyError, TypeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Votre session a expiré. Reconnectez-vous.",
        ) from exc

    admin = session.get(AdminUser, admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Votre session a expiré. Reconnectez-vous.",
        )
    # Une réinitialisation de mot de passe invalide les sessions ouvertes auparavant.
    if session_version != admin.session_version:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Votre session a expiré. Reconnectez-vous.",
        )
    return admin


def require_super_admin(admin: AdminUser = Depends(require_admin)) -> AdminUser:
    if admin.role != "super_admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette action est réservée à un administrateur principal.",
        )
    return admin


def get_volunteer(
    request: Request,
    session: Session = Depends(get_db),
    link_service: LinkService = Depends(get_link_service),
) -> Volunteer:
    token = request.headers.get(VOLUNTEER_TOKEN_HEADER, "").strip()
    volunteer = link_service.find_volunteer(session, token) if token else None
    if volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ce lien personnel n'est plus valable.",
        )
    return volunteer
