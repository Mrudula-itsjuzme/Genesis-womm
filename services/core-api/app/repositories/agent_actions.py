"""PostgreSQL adapter for agent proposals (spine AD-9).

A proposal is inserted once as PROPOSED and decided at most once; ``decide`` is a single
compare-and-set statement, so concurrent or repeated decisions cannot both win.
"""

from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session

from app.domain.enums import AgentActionStatus, AgentActionType
from app.models.agent import AgentActionRow
from app.services.codec import conflict_from_json, conflict_to_json
from app.services.ports import AgentActionRecord


def _to_record(row: AgentActionRow) -> AgentActionRecord:
    return AgentActionRecord(
        id=row.id,
        type=AgentActionType(row.type),
        status=AgentActionStatus(row.status),
        summary=row.summary,
        requested_by=row.requested_by,
        club_id=row.club_id,
        target_event_id=row.target_event_id,
        expected_revision=row.expected_revision,
        payload=row.payload,
        conflicts=tuple(conflict_from_json(item) for item in row.conflicts),
        decided_by=row.decided_by,
        decided_at=row.decided_at,
        result_entity_type=row.result_entity_type,
        result_entity_id=row.result_entity_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlAgentActionStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, action_id: UUID) -> AgentActionRecord | None:
        row = self._session.scalars(
            select(AgentActionRow)
            .where(AgentActionRow.id == action_id)
            .execution_options(populate_existing=True)
        ).first()
        return None if row is None else _to_record(row)

    def list_for(
        self,
        requested_by: UUID,
        *,
        status: AgentActionStatus | None,
        event_id: UUID | None,
        limit: int,
        offset: int,
    ) -> tuple[list[AgentActionRecord], int]:
        conditions = [AgentActionRow.requested_by == requested_by]
        if status is not None:
            conditions.append(AgentActionRow.status == status.value)
        if event_id is not None:
            conditions.append(AgentActionRow.target_event_id == event_id)
        total = self._session.scalar(
            select(func.count()).select_from(AgentActionRow).where(*conditions)
        )
        rows = self._session.scalars(
            select(AgentActionRow)
            .where(*conditions)
            .order_by(AgentActionRow.created_at.desc(), AgentActionRow.id.desc())
            .limit(limit)
            .offset(offset)
            .execution_options(populate_existing=True)
        )
        return [_to_record(row) for row in rows], int(total or 0)

    def add(self, record: AgentActionRecord) -> None:
        self._session.add(
            AgentActionRow(
                id=record.id,
                type=record.type.value,
                status=record.status.value,
                summary=record.summary,
                requested_by=record.requested_by,
                club_id=record.club_id,
                target_event_id=record.target_event_id,
                expected_revision=record.expected_revision,
                payload=record.payload,
                conflicts=[conflict_to_json(c) for c in record.conflicts],
                decided_by=record.decided_by,
                decided_at=record.decided_at,
                result_entity_type=record.result_entity_type,
                result_entity_id=record.result_entity_id,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )
        self._session.flush()

    def decide(
        self,
        action_id: UUID,
        *,
        status: AgentActionStatus,
        decided_by: UUID,
        decided_at: datetime,
        result_entity_type: str | None,
        result_entity_id: UUID | None,
    ) -> bool:
        result = cast(
            CursorResult[tuple[()]],
            self._session.execute(
                update(AgentActionRow)
                .where(
                    AgentActionRow.id == action_id,
                    AgentActionRow.status == AgentActionStatus.PROPOSED.value,
                )
                .values(
                    status=status.value,
                    decided_by=decided_by,
                    decided_at=decided_at,
                    result_entity_type=result_entity_type,
                    result_entity_id=result_entity_id,
                    updated_at=decided_at,
                )
                .execution_options(synchronize_session=False)
            ),
        )
        return result.rowcount == 1
