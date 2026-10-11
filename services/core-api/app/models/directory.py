"""Who can act and what can be booked: users, clubs, memberships and sourced resources.

Roles are stored here and turned into an ``Actor`` per request (spine AD-21); a role claimed by
a client never reaches the database. Business timestamps are supplied by the injected Clock,
so there are no clock-based column defaults.
"""

from datetime import date, datetime, time
from enum import StrEnum
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import AvailabilityState, FreshnessState, ResourceKind
from app.models.base import Base

Timestamp = DateTime(timezone=True)


def in_values(column: str, values: type[StrEnum]) -> str:
    """A CHECK expression listing the enum's values, so the database rejects anything else."""
    listed = ", ".join(f"'{member.value}'" for member in values)
    return f"{column} IN ({listed})"


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    campus_admin: Mapped[bool] = mapped_column(Boolean, server_default=text("false"))
    is_synthetic: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class ResourceInterest(Base):
    """A user's stated interest in a shared resource, never a reservation."""

    __tablename__ = "resource_interests"
    __table_args__ = (CheckConstraint("start_time < end_time", name="start_before_end"),)

    id: Mapped[UUID] = mapped_column(primary_key=True)
    requester_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(60))
    purpose: Mapped[str] = mapped_column(String(160))
    preferred_date: Mapped[date] = mapped_column(Date)
    start_time: Mapped[time] = mapped_column(Time)
    end_time: Mapped[time] = mapped_column(Time)
    requirements: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class Club(Base):
    __tablename__ = "clubs"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True)
    is_synthetic: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class Membership(Base):
    """A user's role in one club. Only ORGANIZER and CLUB_ADMIN are club roles."""

    __tablename__ = "memberships"
    __table_args__ = (
        CheckConstraint("role IN ('ORGANIZER', 'CLUB_ADMIN', 'FACULTY_ADVISOR')", name="club_role"),
    )

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    club_id: Mapped[UUID] = mapped_column(ForeignKey("clubs.id"), primary_key=True)
    role: Mapped[str] = mapped_column(String(20))
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class Resource(Base):
    """A sourced campus resource. Availability is UNKNOWN until evidence says otherwise."""

    __tablename__ = "resources"
    __table_args__ = (
        CheckConstraint(in_values("kind", ResourceKind), name="kind"),
        CheckConstraint(in_values("availability_state", AvailabilityState), name="availability"),
        CheckConstraint(in_values("freshness_state", FreshnessState), name="freshness"),
        CheckConstraint("capacity IS NULL OR capacity >= 0", name="capacity_non_negative"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(20))
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(String(200))
    capacity: Mapped[int | None] = mapped_column(Integer)
    availability_state: Mapped[str] = mapped_column(String(20), server_default=text("'UNKNOWN'"))
    freshness_state: Mapped[str] = mapped_column(String(20), server_default=text("'UNKNOWN'"))
    source_id: Mapped[str] = mapped_column(String(100))
    source_url: Mapped[str | None] = mapped_column(Text)
    collected_at: Mapped[datetime | None] = mapped_column(Timestamp)
    last_checked_at: Mapped[datetime | None] = mapped_column(Timestamp)
    is_synthetic: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(Timestamp)
