from __future__ import annotations

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    SmallInteger,
    String,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base, utcnow


class AdminUser(Base):
    __tablename__ = "admin_users"
    __table_args__ = (
        CheckConstraint(
            "gender IS NULL OR gender IN ('homme', 'femme')",
            name="admin_gender_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(8))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    password_changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    session_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    reset_tokens: Mapped[list[PasswordResetToken]] = relationship(
        back_populates="admin", cascade="all, delete-orphan"
    )


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("admin_users.id", ondelete="CASCADE"), index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    admin: Mapped[AdminUser] = relationship(back_populates="reset_tokens")


class Volunteer(Base):
    __tablename__ = "volunteers"
    __table_args__ = (
        CheckConstraint(
            "gender IS NULL OR gender IN ('homme', 'femme')",
            name="volunteer_gender_allowed",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    gender: Mapped[str | None] = mapped_column(String(8))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Le jeton n'est jamais stocké en clair : empreinte pour la recherche,
    # copie chiffrée pour permettre à l'administration de renvoyer le lien.
    link_token_hash: Mapped[str | None] = mapped_column(String(64), unique=True)
    link_token_encrypted: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    responses: Mapped[list[AvailabilityResponse]] = relationship(
        back_populates="volunteer", cascade="all, delete-orphan"
    )
    meal_exclusions: Mapped[list[MealExclusion]] = relationship(
        back_populates="volunteer", cascade="all, delete-orphan"
    )


class AvailabilityResponse(Base):
    """Réponse d'un bénévole pour une période (mardi → samedi)."""

    __tablename__ = "availability_responses"
    __table_args__ = (
        UniqueConstraint("volunteer_id", "period_start", name="uq_response_volunteer_period"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    volunteer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("volunteers.id", ondelete="CASCADE"), index=True
    )
    period_start: Mapped[date] = mapped_column(Date, index=True)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    volunteer: Mapped[Volunteer] = relationship(back_populates="responses")
    days: Mapped[list[DayAvailability]] = relationship(
        back_populates="response",
        cascade="all, delete-orphan",
        order_by="DayAvailability.day_date",
    )


class DayAvailability(Base):
    """Disponibilité d'une journée. Une journée sans ligne est indisponible."""

    __tablename__ = "day_availabilities"
    __table_args__ = (
        UniqueConstraint("response_id", "day_date", name="uq_day_response_date"),
        CheckConstraint(
            "kind IN ('all_day', 'slot')", name="day_kind_allowed"
        ),
        CheckConstraint(
            "(kind = 'all_day' AND start_time IS NULL AND end_time IS NULL) "
            "OR (kind = 'slot' AND start_time IS NOT NULL AND end_time IS NOT NULL)",
            name="day_times_consistent",
        ),
        CheckConstraint(
            "start_time IS NULL OR end_time IS NULL OR start_time < end_time",
            name="day_slot_ordered",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    response_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("availability_responses.id", ondelete="CASCADE"), index=True
    )
    day_date: Mapped[date] = mapped_column(Date)
    kind: Mapped[str] = mapped_column(String(16))
    start_time: Mapped[time | None] = mapped_column(Time)
    end_time: Mapped[time | None] = mapped_column(Time)

    response: Mapped[AvailabilityResponse] = relationship(back_populates="days")

    @property
    def weekday(self) -> int:
        return self.day_date.weekday()


class MealExclusion(Base):
    """Bénévole retiré du repas de midi pour une journée donnée.

    L'absence de ligne signifie que le bénévole est inscrit au repas par défaut
    lorsqu'il est disponible toute la journée.
    """

    __tablename__ = "meal_exclusions"
    __table_args__ = (
        UniqueConstraint("volunteer_id", "day_date", name="uq_meal_volunteer_date"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    volunteer_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("volunteers.id", ondelete="CASCADE"), index=True
    )
    day_date: Mapped[date] = mapped_column(Date, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    volunteer: Mapped[Volunteer] = relationship(back_populates="meal_exclusions")


class OpeningHours(Base):
    """Heures d'ouverture pour un jour de la semaine (1 = mardi, 5 = samedi)."""

    __tablename__ = "opening_hours"
    __table_args__ = (
        CheckConstraint("weekday BETWEEN 1 AND 5", name="opening_weekday_range"),
        CheckConstraint("open_time < close_time", name="opening_times_ordered"),
    )

    weekday: Mapped[int] = mapped_column(SmallInteger, primary_key=True)
    open_time: Mapped[time] = mapped_column(Time, nullable=False)
    close_time: Mapped[time] = mapped_column(Time, nullable=False)
