from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_today, require_admin
from app.domain.errors import DomainError
from app.domain.periods import current_period_start, validate_period_start
from app.schemas import WeekViewOut
from app.services.availability import build_week_view

router = APIRouter(
    prefix="/api/admin",
    tags=["administration — semaine"],
    dependencies=[Depends(require_admin)],
)


@router.get("/week", response_model=WeekViewOut)
def week_view(
    period_start: date | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    session: Session = Depends(get_db),
    today: date = Depends(get_today),
) -> WeekViewOut:
    selected = period_start or current_period_start(today)
    try:
        validate_period_start(selected)
    except DomainError as exc:
        raise DomainError(exc.message, status_code=422) from exc
    return build_week_view(
        session, selected, today, include_inactive=include_inactive
    )
