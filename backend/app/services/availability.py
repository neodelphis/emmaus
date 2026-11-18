from __future__ import annotations

from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.database import utcnow
from app.domain.availability import TimeWindow, validate_day_answer
from app.domain.errors import DomainError
from app.domain.periods import (
    WEEKDAY_LABELS,
    admin_period_options,
    current_period_start,
    ensure_visible_period,
    is_day_editable,
    period_days,
    period_end,
    validate_period_start,
    visible_period_starts,
)
from app.domain.suggestions import HistoryDay, suggest_day
from app.models import (
    AvailabilityResponse,
    DayAvailability,
    MealExclusion,
    OpeningHours,
    Volunteer,
)
from app.schemas import (
    DayAnswerOut,
    DayViewOut,
    OpeningHoursOut,
    PeriodOptionOut,
    PeriodSaveIn,
    PeriodViewOut,
    VolunteerAccessOut,
    WeekDayOut,
    WeekViewOut,
    WeekVolunteerOut,
)


def load_opening_hours(session: Session) -> dict[int, OpeningHours]:
    return {hours.weekday: hours for hours in session.scalars(select(OpeningHours)).all()}


def opening_hours_out(hours: dict[int, OpeningHours]) -> list[OpeningHoursOut]:
    return [
        OpeningHoursOut(
            weekday=weekday,
            open=hours[weekday].open_time,
            close=hours[weekday].close_time,
        )
        for weekday in sorted(hours)
    ]


def window_for(hours: dict[int, OpeningHours], weekday: int) -> TimeWindow | None:
    value = hours.get(weekday)
    if value is None:
        return None
    return TimeWindow(open_time=value.open_time, close_time=value.close_time)


def load_visible_responses(
    session: Session, volunteer_id: UUID, starts: list[date]
) -> dict[date, AvailabilityResponse]:
    if not starts:
        return {}
    responses = session.scalars(
        select(AvailabilityResponse)
        .where(
            AvailabilityResponse.volunteer_id == volunteer_id,
            AvailabilityResponse.period_start.in_(starts),
        )
        .options(selectinload(AvailabilityResponse.days))
    ).all()
    return {response.period_start: response for response in responses}


def load_history(
    session: Session, volunteer_id: UUID, today: date
) -> dict[int, list[HistoryDay]]:
    """Quatre dernières périodes achevées renseignées, par jour de la semaine."""
    # Le samedi de la période doit être strictement antérieur à aujourd'hui.
    last_start = today - timedelta(days=4)
    responses = session.scalars(
        select(AvailabilityResponse)
        .where(
            AvailabilityResponse.volunteer_id == volunteer_id,
            AvailabilityResponse.period_start < last_start,
        )
        .order_by(AvailabilityResponse.period_start.desc())
        .limit(4)
        .options(selectinload(AvailabilityResponse.days))
    ).all()

    history: dict[int, list[HistoryDay]] = {weekday: [] for weekday in WEEKDAY_LABELS}
    for response in responses:
        for day in response.days:
            if day.weekday not in history:
                continue
            history[day.weekday].append(
                HistoryDay(
                    kind=day.kind,
                    start=day.start_time,
                    end=day.end_time,
                    period_start=response.period_start,
                    submitted_at=response.submitted_at,
                )
            )
    return history


def _answer_out(day: DayAvailability) -> DayAnswerOut:
    return DayAnswerOut(kind=day.kind, start=day.start_time, end=day.end_time)


def build_period_view(
    *,
    period_start: date,
    response: AvailabilityResponse | None,
    today: date,
    history: dict[int, list[HistoryDay]],
    with_suggestions: bool,
) -> PeriodViewOut:
    day_rows = {row.day_date: row for row in response.days} if response else {}
    days: list[DayViewOut] = []
    for day_date in period_days(period_start):
        weekday = day_date.weekday()
        row = day_rows.get(day_date)
        suggestion = None
        if with_suggestions and response is None:
            suggested = suggest_day(history.get(weekday, []))
            if suggested is not None:
                suggestion = DayAnswerOut(
                    kind=suggested.kind, start=suggested.start, end=suggested.end
                )
        days.append(
            DayViewOut(
                date=day_date,
                weekday=weekday,
                editable=is_day_editable(day_date, today),
                answer=_answer_out(row) if row else None,
                suggestion=suggestion,
            )
        )

    return PeriodViewOut(
        start=period_start,
        end=period_end(period_start),
        submitted=response is not None,
        submitted_at=response.submitted_at if response else None,
        days=days,
    )


def build_volunteer_access(
    session: Session, volunteer: Volunteer, today: date
) -> VolunteerAccessOut:
    starts = visible_period_starts(today)
    responses = load_visible_responses(session, volunteer.id, starts)
    history = load_history(session, volunteer.id, today)
    hours = load_opening_hours(session)

    periods = [
        build_period_view(
            period_start=start,
            response=responses.get(start),
            today=today,
            history=history,
            with_suggestions=True,
        )
        for start in starts
    ]
    return VolunteerAccessOut(
        volunteer_name=volunteer.name,
        today=today,
        opening_hours=opening_hours_out(hours),
        periods=periods,
    )


def build_single_period_view(
    session: Session, volunteer: Volunteer, response: AvailabilityResponse, today: date
) -> PeriodViewOut:
    return build_period_view(
        period_start=response.period_start,
        response=response,
        today=today,
        history={},
        with_suggestions=False,
    )


def save_period(
    session: Session,
    volunteer: Volunteer,
    period_start: date,
    payload: PeriodSaveIn,
    today: date,
) -> AvailabilityResponse:
    validate_period_start(period_start)
    ensure_visible_period(period_start, today)

    expected_days = period_days(period_start)
    seen: set[date] = set()
    for item in payload.days:
        if item.date in seen:
            raise DomainError("Un jour ne peut être renseigné qu'une seule fois.")
        seen.add(item.date)
        if item.date not in expected_days:
            raise DomainError("Le jour indiqué n'appartient pas à cette période.")
        if not is_day_editable(item.date, today):
            raise DomainError(
                "Ce jour n'est plus modifiable : les réponses ferment à 23 h 59 la veille.",
                status_code=409,
            )

    hours = load_opening_hours(session)
    for item in payload.days:
        validate_day_answer(
            kind=item.kind,
            start=item.start,
            end=item.end,
            window=window_for(hours, item.date.weekday()),
        )

    response = session.scalar(
        select(AvailabilityResponse).where(
            AvailabilityResponse.volunteer_id == volunteer.id,
            AvailabilityResponse.period_start == period_start,
        )
    )
    if response is None:
        response = AvailabilityResponse(
            volunteer_id=volunteer.id,
            period_start=period_start,
            submitted_at=utcnow(),
        )
        session.add(response)
        session.flush()

    existing = {day.day_date: day for day in response.days}
    for item in payload.days:
        row = existing.get(item.date)
        if item.kind == "unavailable":
            if row is not None:
                session.delete(row)
            continue
        if row is None:
            row = DayAvailability(response_id=response.id, day_date=item.date, kind=item.kind)
            session.add(row)
        row.kind = item.kind
        row.start_time = item.start if item.kind == "slot" else None
        row.end_time = item.end if item.kind == "slot" else None

    response.submitted_at = utcnow()
    session.commit()

    fresh = session.scalar(
        select(AvailabilityResponse)
        .where(AvailabilityResponse.id == response.id)
        .options(selectinload(AvailabilityResponse.days))
        .execution_options(populate_existing=True)
    )
    assert fresh is not None
    return fresh


def build_week_view(
    session: Session,
    period_start: date,
    today: date,
    *,
    include_inactive: bool = False,
) -> WeekViewOut:
    validate_period_start(period_start)
    starts = admin_period_options(today)

    query = select(Volunteer).order_by(Volunteer.name.asc(), Volunteer.created_at.asc())
    if not include_inactive:
        query = query.where(Volunteer.is_active.is_(True))
    volunteers = session.scalars(query).all()
    volunteer_ids = [volunteer.id for volunteer in volunteers]

    responses: dict[UUID, AvailabilityResponse] = {}
    week_dates = period_days(period_start)
    excluded_meals: set[tuple[UUID, date]] = set()
    if volunteer_ids:
        rows = session.scalars(
            select(AvailabilityResponse)
            .where(
                AvailabilityResponse.period_start == period_start,
                AvailabilityResponse.volunteer_id.in_(volunteer_ids),
            )
            .options(selectinload(AvailabilityResponse.days))
        ).all()
        responses = {row.volunteer_id: row for row in rows}

        exclusions = session.scalars(
            select(MealExclusion).where(
                MealExclusion.volunteer_id.in_(volunteer_ids),
                MealExclusion.day_date.in_(week_dates),
            )
        ).all()
        excluded_meals = {
            (exclusion.volunteer_id, exclusion.day_date) for exclusion in exclusions
        }

    week_rows: list[WeekVolunteerOut] = []
    for volunteer in volunteers:
        response = responses.get(volunteer.id)
        day_rows = {row.day_date: row for row in response.days} if response else {}
        days: list[WeekDayOut] = []
        for day_date in week_dates:
            row = day_rows.get(day_date)
            if response is None:
                status = "unanswered"
                start = end = None
            elif row is None:
                status = "unavailable"
                start = end = None
            else:
                status = row.kind
                start = row.start_time
                end = row.end_time
            days.append(
                WeekDayOut(
                    date=day_date,
                    weekday=day_date.weekday(),
                    status=status,  # type: ignore[arg-type]
                    start=start,
                    end=end,
                    meal_excluded=(
                        status == "all_day"
                        and (volunteer.id, day_date) in excluded_meals
                    ),
                )
            )
        week_rows.append(
            WeekVolunteerOut(
                id=volunteer.id,
                name=volunteer.name,
                email=volunteer.email,
                is_active=volunteer.is_active,
                submitted=response is not None,
                days=days,
            )
        )

    period_options = [
        PeriodOptionOut(
            start=start,
            end=period_end(start),
            is_current=start == current_period_start(today),
        )
        for start in starts
    ]
    return WeekViewOut(
        period_start=period_start,
        period_end=period_end(period_start),
        today=today,
        opening_hours=opening_hours_out(load_opening_hours(session)),
        options=period_options,
        volunteers=week_rows,
    )

