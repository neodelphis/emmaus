from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.deps import get_db, get_today, require_admin
from app.domain.errors import DomainError
from app.domain.periods import current_period_start, validate_period_start
from app.domain.sites import DEFAULT_SITE
from app.models import AdminUser
from app.schemas import SiteCode, WeekViewOut
from app.services.availability import build_week_view

router = APIRouter(tags=["administration — semaine"])


@router.get("/api/admin/week", response_model=WeekViewOut)
def week_view(
    period_start: date | None = Query(default=None),
    site: SiteCode | None = Query(default=None),
    include_inactive: bool = Query(default=False),
    admin: AdminUser = Depends(require_admin),
    session: Session = Depends(get_db),
    today: date = Depends(get_today),
) -> WeekViewOut:
    selected = period_start or current_period_start(today)
    try:
        validate_period_start(selected)
    except DomainError as exc:
        raise DomainError(exc.message, status_code=422) from exc
    selected_site = site or admin.last_site or DEFAULT_SITE
    return build_week_view(
        session,
        selected,
        today,
        site=selected_site,
        include_inactive=include_inactive,
    )
