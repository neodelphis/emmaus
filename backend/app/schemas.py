from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, PlainSerializer, field_validator

TimeOfDay = Annotated[time, PlainSerializer(lambda value: value.strftime("%H:%M"))]

WeekdayNumber = Annotated[int, Field(ge=1, le=5)]


class AdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=256)


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=10, max_length=256)
    password: str = Field(min_length=12, max_length=256)


class CreateAdminIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=12, max_length=256)


class OpeningHoursOut(BaseModel):
    weekday: int
    open: TimeOfDay
    close: TimeOfDay


class OpeningHoursIn(BaseModel):
    weekday: WeekdayNumber
    open: time
    close: time


class OpeningHoursUpdateIn(BaseModel):
    hours: list[OpeningHoursIn]

    @field_validator("hours")
    @classmethod
    def _all_weekdays_once(cls, value: list[OpeningHoursIn]) -> list[OpeningHoursIn]:
        weekdays = [item.weekday for item in value]
        if sorted(weekdays) != [1, 2, 3, 4, 5]:
            raise ValueError("Les horaires des cinq jours (mardi à samedi) doivent être fournis.")
        return value


class DayAnswerOut(BaseModel):
    kind: Literal["all_day", "slot"]
    start: TimeOfDay | None = None
    end: TimeOfDay | None = None


class DayViewOut(BaseModel):
    date: date
    weekday: int
    editable: bool
    answer: DayAnswerOut | None = None
    suggestion: DayAnswerOut | None = None


class PeriodViewOut(BaseModel):
    start: date
    end: date
    submitted: bool
    submitted_at: datetime | None = None
    days: list[DayViewOut]


class VolunteerAccessOut(BaseModel):
    volunteer_name: str
    today: date
    opening_hours: list[OpeningHoursOut]
    periods: list[PeriodViewOut]


class DaySaveIn(BaseModel):
    date: date
    kind: Literal["unavailable", "all_day", "slot"]
    start: time | None = None
    end: time | None = None


class PeriodSaveIn(BaseModel):
    days: list[DaySaveIn] = Field(max_length=5)


class VolunteerCreateIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    email: EmailStr | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Le nom est obligatoire.")
        return value


class VolunteerUpdateIn(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if not value:
            raise ValueError("Le nom est obligatoire.")
        return value


class VolunteerOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr | None
    is_active: bool
    has_link: bool
    created_at: datetime


class VolunteerCreatedOut(VolunteerOut):
    link: str


class LinkOut(BaseModel):
    link: str


class WeekDayOut(BaseModel):
    date: date
    weekday: int
    status: Literal["unanswered", "unavailable", "all_day", "slot"]
    start: TimeOfDay | None = None
    end: TimeOfDay | None = None


class WeekVolunteerOut(BaseModel):
    id: UUID
    name: str
    email: EmailStr | None
    is_active: bool
    submitted: bool
    days: list[WeekDayOut]


class PeriodOptionOut(BaseModel):
    start: date
    end: date
    is_current: bool


class WeekViewOut(BaseModel):
    period_start: date
    period_end: date
    today: date
    opening_hours: list[OpeningHoursOut]
    options: list[PeriodOptionOut]
    volunteers: list[WeekVolunteerOut]


class MessageOut(BaseModel):
    message: str
