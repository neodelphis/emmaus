from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.deps import get_db, get_today, get_volunteer
from app.models import Volunteer
from app.schemas import PeriodSaveIn, PeriodViewOut, VolunteerAccessOut
from app.services.availability import (
    build_single_period_view,
    build_volunteer_access,
    save_period,
)

router = APIRouter(prefix="/api/volunteer", tags=["bénévole"])


@router.get("", response_model=VolunteerAccessOut)
def access(
    volunteer: Volunteer = Depends(get_volunteer),
    session: Session = Depends(get_db),
    today: date = Depends(get_today),
) -> VolunteerAccessOut:
    return build_volunteer_access(session, volunteer, today)


@router.put("/periods/{period_start}", response_model=PeriodViewOut)
def save_availability(
    period_start: date,
    payload: PeriodSaveIn,
    volunteer: Volunteer = Depends(get_volunteer),
    session: Session = Depends(get_db),
    today: date = Depends(get_today),
) -> PeriodViewOut:
    response = save_period(session, volunteer, period_start, payload, today)
    return build_single_period_view(session, volunteer, response, today)
