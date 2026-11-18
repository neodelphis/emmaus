from __future__ import annotations

import logging
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, get_email_service, get_link_service, require_admin
from app.domain.sites import DEFAULT_SITE
from app.models import (
    AvailabilityResponse,
    DayAvailability,
    MealExclusion,
    Volunteer,
)
from app.schemas import (
    LinkOut,
    VolunteerCreatedOut,
    VolunteerCreateIn,
    VolunteerOut,
    VolunteerUpdateIn,
)
from app.services.emails import EmailDeliveryError, EmailService
from app.services.links import LinkService

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/admin/volunteers",
    tags=["administration — bénévoles"],
    dependencies=[Depends(require_admin)],
)


def _ensure_all_day(session: Session, volunteer_id: UUID, day_date: date) -> None:
    day = session.scalar(
        select(DayAvailability.id)
        .join(
            AvailabilityResponse,
            AvailabilityResponse.id == DayAvailability.response_id,
        )
        .where(
            AvailabilityResponse.volunteer_id == volunteer_id,
            DayAvailability.day_date == day_date,
            DayAvailability.kind == "all_day",
        )
    )
    if day is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce bénévole n’est pas disponible toute la journée à cette date.",
        )


def _split_name(name: str) -> tuple[str, str | None]:
    first, _, last = name.strip().partition(" ")
    return first.strip(), last.strip() or None


def _out(volunteer: Volunteer) -> VolunteerOut:
    return VolunteerOut(
        id=volunteer.id,
        name=volunteer.name,
        first_name=volunteer.first_name,
        last_name=volunteer.last_name,
        email=volunteer.email,
        gender=volunteer.gender,
        default_site=volunteer.default_site,  # type: ignore[arg-type]
        is_active=volunteer.is_active,
        has_link=bool(volunteer.link_token_hash),
        created_at=volunteer.created_at,
    )


def _get_or_404(session: Session, volunteer_id: UUID) -> Volunteer:
    volunteer = session.get(Volunteer, volunteer_id)
    if volunteer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bénévole introuvable.",
        )
    return volunteer


@router.get("", response_model=list[VolunteerOut])
def list_volunteers(session: Session = Depends(get_db)) -> list[VolunteerOut]:
    volunteers = session.scalars(
        select(Volunteer).order_by(Volunteer.is_active.desc(), Volunteer.name.asc())
    ).all()
    return [_out(volunteer) for volunteer in volunteers]


@router.post("", response_model=VolunteerCreatedOut, status_code=status.HTTP_201_CREATED)
def create_volunteer(
    payload: VolunteerCreateIn,
    session: Session = Depends(get_db),
    link_service: LinkService = Depends(get_link_service),
) -> VolunteerCreatedOut:
    first_name = payload.first_name.strip() if payload.first_name else None
    last_name = payload.last_name.strip() if payload.last_name else None
    if first_name and last_name:
        name = f"{first_name} {last_name}"
    else:
        name = payload.name.strip()
        first_name, last_name = _split_name(name)

    volunteer = Volunteer(
        name=name,
        first_name=first_name,
        last_name=last_name,
        email=str(payload.email).lower() if payload.email else None,
        gender=payload.gender,
        default_site=payload.default_site or DEFAULT_SITE,
    )
    link = link_service.issue_link(volunteer)
    session.add(volunteer)
    session.commit()
    session.refresh(volunteer)
    return VolunteerCreatedOut(**_out(volunteer).model_dump(), link=link)


@router.patch("/{volunteer_id}", response_model=VolunteerOut)
def update_volunteer(
    volunteer_id: UUID,
    payload: VolunteerUpdateIn,
    session: Session = Depends(get_db),
) -> VolunteerOut:
    volunteer = _get_or_404(session, volunteer_id)
    fields = payload.model_fields_set
    if "first_name" in fields or "last_name" in fields:
        first_name = (
            payload.first_name
            if "first_name" in fields
            else volunteer.first_name
        )
        last_name = (
            payload.last_name
            if "last_name" in fields
            else volunteer.last_name
        )
        first_name = first_name.strip() if first_name else ""
        last_name = last_name.strip() if last_name else ""
        if not first_name or not last_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le prénom et le nom sont obligatoires.",
            )
        volunteer.first_name = first_name
        volunteer.last_name = last_name
        volunteer.name = f"{first_name} {last_name}"
    elif "name" in fields and payload.name is not None:
        volunteer.name = payload.name.strip()
        volunteer.first_name, volunteer.last_name = _split_name(volunteer.name)
    if "email" in fields:
        volunteer.email = str(payload.email).lower() if payload.email else None
    if "gender" in fields and payload.gender is not None:
        volunteer.gender = payload.gender
    if "default_site" in fields and payload.default_site is not None:
        volunteer.default_site = payload.default_site
    if "is_active" in fields and payload.is_active is not None:
        volunteer.is_active = payload.is_active
    session.commit()
    session.refresh(volunteer)
    return _out(volunteer)


@router.delete("/{volunteer_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_volunteer(
    volunteer_id: UUID,
    session: Session = Depends(get_db),
) -> Response:
    volunteer = _get_or_404(session, volunteer_id)
    session.delete(volunteer)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{volunteer_id}/link", response_model=LinkOut)
def get_link(
    volunteer_id: UUID,
    session: Session = Depends(get_db),
    link_service: LinkService = Depends(get_link_service),
) -> LinkOut:
    volunteer = _get_or_404(session, volunteer_id)
    link = link_service.volunteer_link(volunteer)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aucun lien actif. Générez un nouveau lien pour ce bénévole.",
        )
    return LinkOut(link=link)


@router.post("/{volunteer_id}/link/revoke", status_code=status.HTTP_204_NO_CONTENT)
def revoke_link(
    volunteer_id: UUID,
    session: Session = Depends(get_db),
    link_service: LinkService = Depends(get_link_service),
) -> Response:
    volunteer = _get_or_404(session, volunteer_id)
    link_service.revoke(volunteer)
    session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{volunteer_id}/link/regenerate", response_model=LinkOut)
def regenerate_link(
    volunteer_id: UUID,
    session: Session = Depends(get_db),
    link_service: LinkService = Depends(get_link_service),
) -> LinkOut:
    volunteer = _get_or_404(session, volunteer_id)
    link = link_service.issue_link(volunteer)
    session.commit()
    return LinkOut(link=link)


@router.post("/{volunteer_id}/link/send", status_code=status.HTTP_204_NO_CONTENT)
def send_link(
    volunteer_id: UUID,
    session: Session = Depends(get_db),
    link_service: LinkService = Depends(get_link_service),
    email_service: EmailService = Depends(get_email_service),
) -> Response:
    volunteer = _get_or_404(session, volunteer_id)
    if not volunteer.is_active:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce bénévole est désactivé. Réactivez-le avant d'envoyer un lien.",
        )
    if not volunteer.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ce bénévole n'a pas d'adresse courriel. Communiquez le lien autrement.",
        )
    link = link_service.volunteer_link(volunteer)
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Aucun lien actif. Générez un nouveau lien pour ce bénévole.",
        )
    try:
        email_service.send_volunteer_link(
            to=volunteer.email, name=volunteer.name, link=link
        )
    except EmailDeliveryError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Le courriel n'a pas pu être envoyé. Vérifiez le service de messagerie.",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.put(
    "/{volunteer_id}/meal-exclusions/{day_date}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def exclude_from_meal(
    volunteer_id: UUID,
    day_date: date,
    session: Session = Depends(get_db),
) -> Response:
    volunteer = _get_or_404(session, volunteer_id)
    _ensure_all_day(session, volunteer.id, day_date)

    existing = session.scalar(
        select(MealExclusion).where(
            MealExclusion.volunteer_id == volunteer.id,
            MealExclusion.day_date == day_date,
        )
    )
    if existing is None:
        session.add(MealExclusion(volunteer_id=volunteer.id, day_date=day_date))
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete(
    "/{volunteer_id}/meal-exclusions/{day_date}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def include_in_meal(
    volunteer_id: UUID,
    day_date: date,
    session: Session = Depends(get_db),
) -> Response:
    volunteer = _get_or_404(session, volunteer_id)
    existing = session.scalar(
        select(MealExclusion).where(
            MealExclusion.volunteer_id == volunteer.id,
            MealExclusion.day_date == day_date,
        )
    )
    if existing is not None:
        session.delete(existing)
        session.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
