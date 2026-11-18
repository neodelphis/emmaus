from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_db, require_admin
from app.domain.availability import TimeWindow, validate_time_window
from app.domain.sites import SITES
from app.models import SiteOpeningHours
from app.schemas import (
    OpeningHoursOut,
    OpeningHoursUpdateIn,
    SiteCode,
    SiteOut,
)
from app.services.availability import load_opening_hours, opening_hours_out

router = APIRouter(
    prefix="/api/admin/sites",
    tags=["administration — sites"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[SiteOut])
def list_sites() -> list[SiteOut]:
    return [SiteOut(code=site.code, name=site.name) for site in SITES]


@router.get("/{site}/opening-hours", response_model=list[OpeningHoursOut])
def get_opening_hours(
    site: SiteCode,
    session: Session = Depends(get_db),
) -> list[OpeningHoursOut]:
    return opening_hours_out(load_opening_hours(session, site))


@router.put("/{site}/opening-hours", response_model=list[OpeningHoursOut])
def update_opening_hours(
    site: SiteCode,
    payload: OpeningHoursUpdateIn,
    session: Session = Depends(get_db),
) -> list[OpeningHoursOut]:
    for item in payload.hours:
        validate_time_window(TimeWindow(open_time=item.open, close_time=item.close))

    existing = {
        hours.weekday: hours
        for hours in session.scalars(
            select(SiteOpeningHours).where(SiteOpeningHours.site == site)
        ).all()
    }
    for item in payload.hours:
        row = existing.get(item.weekday)
        if row is None:
            row = SiteOpeningHours(
                site=site,
                weekday=item.weekday,
                open_time=item.open,
                close_time=item.close,
            )
            session.add(row)
        else:
            row.open_time = item.open
            row.close_time = item.close
    session.commit()
    return opening_hours_out(load_opening_hours(session, site))
