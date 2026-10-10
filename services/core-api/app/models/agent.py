"""Proposals the Agent files for a human to confirm (spine AD-9).

A row records what the Agent suggested, the conflicts a dry run found when it was filed, and,
once a person decides, who decided and what confirming created. The Agent can only ever insert a
PROPOSED row; the database refuses any other state without the matching decision.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums import AgentActionStatus, AgentActionType
from app.models.base import Base
from app.models.directory import Timestamp, in_values


class AgentActionRow(Base):
    __tablename__ = "agent_actions"
    __table_args__ = (
        CheckConstraint(in_values("type", AgentActionType), name="type"),
        CheckConstraint(in_values("status", AgentActionStatus), name="status"),
        CheckConstraint("length(trim(summary)) > 0", name="summary_not_blank"),
        CheckConstraint(
            "expected_revision IS NULL OR expected_revision >= 1",
            name="expected_revision_positive",
        ),
        CheckConstraint(
            "status <> 'PROPOSED' OR (decided_by IS NULL AND decided_at IS NULL "
            "AND result_entity_type IS NULL AND result_entity_id IS NULL)",
            name="proposed_is_undecided",
        ),
        CheckConstraint(
            "status <> 'EXECUTED' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL "
            "AND result_entity_type IS NOT NULL AND result_entity_id IS NOT NULL)",
            name="executed_has_result",
        ),
        CheckConstraint(
            "status <> 'REJECTED' OR (decided_by IS NOT NULL AND decided_at IS NOT NULL)",
            name="rejected_has_decision",
        ),
        Index("ix_agent_actions_requested_by_created_at", "requested_by", "created_at"),
        Index("ix_agent_actions_target_event_id", "target_event_id"),
        Index("ix_agent_actions_status", "status"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True)
    type: Mapped[str] = mapped_column(String(30))
    status: Mapped[str] = mapped_column(String(20))
    summary: Mapped[str] = mapped_column(String(300))
    requested_by: Mapped[UUID] = mapped_column(ForeignKey("users.id"))
    club_id: Mapped[UUID] = mapped_column(ForeignKey("clubs.id"))
    target_event_id: Mapped[UUID | None] = mapped_column(ForeignKey("events.id"))
    expected_revision: Mapped[int | None] = mapped_column(Integer)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    conflicts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, server_default=text("'[]'::jsonb")
    )
    decided_by: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    decided_at: Mapped[datetime | None] = mapped_column(Timestamp)
    result_entity_type: Mapped[str | None] = mapped_column(String(40))
    result_entity_id: Mapped[UUID | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(Timestamp)
    updated_at: Mapped[datetime] = mapped_column(Timestamp)
