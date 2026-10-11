"""Change proposals and explicitly registered organizer commitments/tasks (AD-14)."""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.directory import Timestamp


class EventItem(Base):
    __tablename__ = "event_items"
    __table_args__ = (
        UniqueConstraint("event_id", "id", name="uq_event_items_event_id_id"),
        CheckConstraint("kind IN ('COMMITMENT', 'TASK')", name="kind"),
        CheckConstraint("length(trim(title)) > 0", name="title_not_blank"),
        CheckConstraint(
            "(kind = 'TASK' AND status IN ('OPEN', 'CLOSED')) OR "
            "(kind = 'COMMITMENT' AND status IN ('DRAFT', 'REQUESTED', 'ACKNOWLEDGED', "
            "'CONDITIONALLY_CONFIRMED', 'CONFIRMED', 'NEEDS_REVALIDATION', 'CLOSED'))",
            name="status",
        ),
        CheckConstraint(
            "status <> 'CONFIRMED' OR (verified_by IS NOT NULL AND verified_at IS NOT NULL "
            "AND evidence_id IS NOT NULL)",
            name="confirmed_is_verified",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True)
    kind: Mapped[str] = mapped_column(String(20))
    title: Mapped[str] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(30))
    needs_revalidation: Mapped[bool] = mapped_column(Boolean)
    reported_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    verified_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    verified_at: Mapped[datetime | None] = mapped_column(Timestamp)
    evidence_id: Mapped[UUID | None] = mapped_column(ForeignKey("evidence_records.id"))
    created_at: Mapped[datetime] = mapped_column(Timestamp)
    updated_at: Mapped[datetime] = mapped_column(Timestamp)


class EventDependency(Base):
    __tablename__ = "event_dependencies"
    __table_args__ = (
        ForeignKeyConstraint(
            ["event_id", "dependent_id"], ["event_items.event_id", "event_items.id"]
        ),
        CheckConstraint(
            "field_path IN ('start_at', 'end_at', 'resource_id', 'expected_attendance')",
            name="field_path",
        ),
        CheckConstraint("rule_code = 'FIELD_CHANGE'", name="rule_code"),
    )
    event_id: Mapped[UUID] = mapped_column(primary_key=True)
    dependent_id: Mapped[UUID] = mapped_column(primary_key=True)
    field_path: Mapped[str] = mapped_column(String(40), primary_key=True)
    rule_code: Mapped[str] = mapped_column(String(40))


class ChangeProposal(Base):
    __tablename__ = "change_proposals"
    __table_args__ = (
        CheckConstraint("base_revision >= 1", name="base_revision_positive"),
        CheckConstraint("status IN ('STAGED', 'APPLIED')", name="status"),
        CheckConstraint("length(trim(reason)) > 0", name="reason_not_blank"),
        CheckConstraint(
            "status <> 'APPLIED' OR (applied_by IS NOT NULL AND applied_at IS NOT NULL)",
            name="applied_has_actor",
        ),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True)
    event_id: Mapped[UUID] = mapped_column(ForeignKey("events.id"), index=True)
    base_revision: Mapped[int] = mapped_column(Integer)
    reason: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))
    changes: Mapped[dict[str, Any]] = mapped_column(JSONB)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    impact: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(Timestamp)
    applied_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    applied_at: Mapped[datetime | None] = mapped_column(Timestamp)
