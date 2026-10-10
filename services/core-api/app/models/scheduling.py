"""Events and the history that explains them (spine AD-4, AD-6, AD-7, AD-8, AD-17, AD-20).

The database backs up rules the application also enforces: an interval must run forwards, a
CONFIRMED event always has a verifier and evidence, and the history tables cannot be changed
after the fact. Statuses are text with a named CHECK, not a native enum, so adding a value is
an ordinary migration.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import EventStatus, OverrideScope
from app.models.base import Base
from app.models.directory import Timestamp, in_values


class EvidenceRecord(Base):
    """Proof offered for an official confirmation or an override. Immutable once written."""

    __tablename__ = "evidence_records"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(40))
    reference: Mapped[str] = mapped_column(Text)
    issuer: Mapped[str | None] = mapped_column(String(200))
    captured_at: Mapped[datetime] = mapped_column(Timestamp)
    recorded_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("start_at < end_at", name="start_before_end"),
        CheckConstraint(in_values("status", EventStatus), name="status"),
        CheckConstraint("revision >= 1", name="revision_positive"),
        CheckConstraint(
            "expected_attendance IS NULL OR expected_attendance >= 0",
            name="attendance_non_negative",
        ),
        # A CONFIRMED event always says who verified it, when, and on what evidence.
        CheckConstraint(
            "status <> 'CONFIRMED' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL "
            "AND evidence_id IS NOT NULL)",
            name="confirmed_is_verified",
        ),
        Index("ix_events_resource_id_start_at", "resource_id", "start_at"),
        Index("ix_events_club_id", "club_id"),
        Index("ix_events_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    club_id: Mapped[UUID] = mapped_column(ForeignKey("clubs.id"))
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    start_at: Mapped[datetime] = mapped_column(Timestamp)
    end_at: Mapped[datetime] = mapped_column(Timestamp)
    resource_id: Mapped[UUID | None] = mapped_column(ForeignKey("resources.id"))
    expected_attendance: Mapped[int | None] = mapped_column(Integer)
    audience_tags: Mapped[list[str]] = mapped_column(ARRAY(String(40)), server_default=text("'{}'"))
    status: Mapped[str] = mapped_column(String(20))
    revision: Mapped[int] = mapped_column(Integer)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    verified_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(Timestamp)
    evidence_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence_records.id"))
    is_synthetic: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(Timestamp)
    updated_at: Mapped[datetime] = mapped_column(Timestamp)


class EventRevision(Base):
    """Previous and new values of every change. History is never read by the engine."""

    __tablename__ = "event_revisions"
    __table_args__ = (
        UniqueConstraint("event_id", "revision", name="uq_event_revisions_event_revision"),
        CheckConstraint("revision >= 1", name="revision_positive"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"))
    revision: Mapped[int] = mapped_column(Integer)
    previous: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    current: Mapped[dict[str, Any]] = mapped_column(JSONB)
    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class AuditEvent(Base):
    """One row per attempted mutation, successful or refused. Immutable once written."""

    __tablename__ = "audit_events"
    __table_args__ = (
        CheckConstraint("via IN ('USER', 'AGENT')", name="via"),
        Index("ix_audit_events_entity", "entity_type", "entity_id"),
        Index("ix_audit_events_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    actor_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(60))
    entity_type: Mapped[str] = mapped_column(String(40))
    entity_id: Mapped[UUID | None] = mapped_column()
    outcome: Mapped[str] = mapped_column(String(40))
    reason_code: Mapped[str | None] = mapped_column(String(60))
    request_id: Mapped[str] = mapped_column(String(128))
    via: Mapped[str] = mapped_column(String(10))
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class IdempotencyKey(Base):
    """A stored response, so a retried request returns the same result without a second write."""

    __tablename__ = "idempotency_keys"

    actor_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), primary_key=True)
    key: Mapped[str] = mapped_column(String(128), primary_key=True)
    request_hash: Mapped[str] = mapped_column(String(64))
    status_code: Mapped[int] = mapped_column(Integer)
    response: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(Timestamp)


class ScheduleOverride(Base):
    """An administrator's exception for one constraint on one pair of events (spine AD-6).

    The pair is stored in canonical order (``event_a_id < event_b_id``) so there is exactly one
    row per pair and scope.
    """

    __tablename__ = "schedule_overrides"
    __table_args__ = (
        UniqueConstraint(
            "scope", "event_a_id", "event_b_id", name="uq_schedule_overrides_pair_scope"
        ),
        CheckConstraint(in_values("scope", OverrideScope), name="scope"),
        CheckConstraint("event_a_id < event_b_id", name="pair_order"),
        CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    scope: Mapped[str] = mapped_column(String(20))
    event_a_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"))
    event_b_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"))
    reason: Mapped[str] = mapped_column(Text)
    authorized_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    evidence_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence_records.id"))
    created_at: Mapped[datetime] = mapped_column(Timestamp)
