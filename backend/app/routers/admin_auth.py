from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.config import Settings
from app.deps import get_db, get_email_service, get_settings, require_admin
from app.domain.sites import DEFAULT_SITE
from app.models import AdminUser, PasswordResetToken
from app.schemas import (
    AdminOut,
    CreateAdminIn,
    ForgotPasswordIn,
    LoginIn,
    MessageOut,
    ResetPasswordIn,
    UpdateLastSiteIn,
    UpdateMeIn,
)
from app.security import (
    DUMMY_PASSWORD_HASH,
    SESSION_COOKIE_NAME,
    create_session_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from app.services.emails import EmailDeliveryError, EmailService
from app.services.links import LinkService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/admin/auth", tags=["administration — authentification"])


def _set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        max_age=settings.session_hours * 3600,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


@router.post("/login", response_model=AdminOut)
def login(
    payload: LoginIn,
    response: Response,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> AdminOut:
    admin = session.scalar(
        select(AdminUser).where(AdminUser.email == str(payload.email).lower())
    )
    if admin is None:
        # Coût de vérification équivalent à celui d'un compte existant.
        verify_password(payload.password, DUMMY_PASSWORD_HASH)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse courriel ou mot de passe incorrect.",
        )
    if not verify_password(payload.password, admin.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Adresse courriel ou mot de passe incorrect.",
        )
    token = create_session_token(admin.id, settings, session_version=admin.session_version)
    _set_session_cookie(response, token, settings)
    return AdminOut.model_validate(admin)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout() -> Response:
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return response


@router.get("/me", response_model=AdminOut)
def me(admin: AdminUser = Depends(require_admin)) -> AdminOut:
    return AdminOut.model_validate(admin)


@router.put("/last-site", response_model=AdminOut)
def update_last_site(
    payload: UpdateLastSiteIn,
    admin: AdminUser = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AdminOut:
    admin.last_site = payload.site
    session.commit()
    session.refresh(admin)
    return AdminOut.model_validate(admin)


@router.patch("/me", response_model=AdminOut)
def update_me(
    payload: UpdateMeIn,
    admin: AdminUser = Depends(require_admin),
    session: Session = Depends(get_db),
) -> AdminOut:
    fields = payload.model_fields_set
    if "gender" in fields:
        admin.gender = payload.gender
    if "first_name" in fields:
        admin.first_name = payload.first_name.strip() if payload.first_name else None
    if "last_name" in fields:
        admin.last_name = payload.last_name.strip() if payload.last_name else None
    session.commit()
    session.refresh(admin)
    return AdminOut.model_validate(admin)


@router.post("/forgot-password", status_code=status.HTTP_202_ACCEPTED, response_model=MessageOut)
def forgot_password(
    payload: ForgotPasswordIn,
    session: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    email_service: EmailService = Depends(get_email_service),
) -> MessageOut:
    admin = session.scalar(
        select(AdminUser).where(AdminUser.email == str(payload.email).lower())
    )
    generic = MessageOut(
        message=(
            "Si un compte existe pour cette adresse, "
            "un courriel de réinitialisation a été envoyé."
        )
    )
    if admin is None:
        return generic

    token = generate_token()
    now = datetime.now(UTC)
    session.add(
        PasswordResetToken(
            admin_id=admin.id,
            token_hash=hash_token(token),
            expires_at=now + timedelta(minutes=settings.reset_token_minutes),
        )
    )
    session.commit()

    try:
        email_service.send_password_reset(
            to=admin.email, link=LinkService(settings).reset_url(token)
        )
    except EmailDeliveryError:
        # On ne révèle pas l'existence du compte et on ne renvoie pas d'erreur exploitable.
        logger.warning("Le courriel de réinitialisation n'a pas pu être envoyé.")
    return generic


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    payload: ResetPasswordIn,
    session: Session = Depends(get_db),
) -> Response:
    now = datetime.now(UTC)
    reset_token = session.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(payload.token))
        .with_for_update()
    )
    if (
        reset_token is None
        or reset_token.used_at is not None
        or reset_token.expires_at <= now
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien de réinitialisation est invalide ou a expiré.",
        )

    admin = session.get(AdminUser, reset_token.admin_id)
    if admin is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce lien de réinitialisation est invalide ou a expiré.",
        )

    admin.password_hash = hash_password(payload.password)
    admin.password_changed_at = now
    admin.session_version += 1
    reset_token.used_at = now
    session.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.admin_id == admin.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/administrators", response_model=AdminOut, status_code=status.HTTP_201_CREATED)
def create_administrator(
    payload: CreateAdminIn,
    session: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> AdminOut:
    email = str(payload.email).lower()
    existing = session.scalar(select(AdminUser).where(AdminUser.email == email))
    if existing is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Un compte administrateur existe déjà avec cette adresse.",
        )
    admin = AdminUser(
        email=email,
        password_hash=hash_password(payload.password),
        first_name=payload.first_name.strip() if payload.first_name else None,
        last_name=payload.last_name.strip() if payload.last_name else None,
        gender=payload.gender,
        last_site=DEFAULT_SITE,
    )
    session.add(admin)
    session.commit()
    session.refresh(admin)
    return AdminOut.model_validate(admin)


@router.get("/administrators", response_model=list[AdminOut])
def list_administrators(
    session: Session = Depends(get_db),
    _: AdminUser = Depends(require_admin),
) -> list[AdminOut]:
    admins = session.scalars(select(AdminUser).order_by(AdminUser.created_at.asc())).all()
    return [AdminOut.model_validate(admin) for admin in admins]
