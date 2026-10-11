"""SQL implementation of explicit dependencies and staged change storage."""

from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.domain.enums import CommitmentStatus
from app.domain.impact import Dependency, DependentKind, FieldPath, Impact
from app.domain.lifecycle import mark_needs_revalidation
from app.models.changes import ChangeProposal, EventDependency, EventItem
from app.services.change_ports import ChangeRecord, ItemRecord


def _change(row: ChangeProposal) -> ChangeRecord:
    return ChangeRecord(
        row.id,
        row.event_id,
        row.base_revision,
        row.reason,
        row.status,
        row.changes,
        row.conflicts,
        row.impact,
        row.requested_by,
        row.created_at,
        row.applied_by,
        row.applied_at,
    )


class SqlChangeStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, proposal_id: UUID) -> ChangeRecord | None:
        row = self._session.get(ChangeProposal, proposal_id)
        return None if row is None else _change(row)

    def list_for(self, event_id: UUID, limit: int, offset: int) -> tuple[list[ChangeRecord], int]:
        query = select(ChangeProposal).where(ChangeProposal.event_id == event_id)
        total = self._session.scalar(select(func.count()).select_from(query.subquery())) or 0
        rows = self._session.scalars(
            query.order_by(ChangeProposal.created_at.desc(), ChangeProposal.id)
            .limit(limit)
            .offset(offset)
        )
        return [_change(row) for row in rows], total

    def add(self, record: ChangeRecord) -> None:
        self._session.add(ChangeProposal(**record.__dict__))
        self._session.flush()

    def apply(
        self, proposal_id: UUID, actor_id: UUID, now: datetime, impact: list[dict[str, Any]]
    ) -> bool:
        result = self._session.execute(
            update(ChangeProposal)
            .where(ChangeProposal.id == proposal_id, ChangeProposal.status == "STAGED")
            .values(status="APPLIED", applied_by=actor_id, applied_at=now, impact=impact)
            .returning(ChangeProposal.id)
        )
        return result.scalar_one_or_none() is not None

    def items(self, event_id: UUID) -> list[ItemRecord]:
        rows = self._session.scalars(
            select(EventItem)
            .where(EventItem.event_id == event_id)
            .order_by(EventItem.created_at, EventItem.id)
        ).all()
        bindings: dict[UUID, list[FieldPath]] = {}
        for dependent_id, field_path in self._session.execute(
            select(EventDependency.dependent_id, EventDependency.field_path).where(
                EventDependency.event_id == event_id
            )
        ):
            bindings.setdefault(dependent_id, []).append(cast(FieldPath, field_path))
        return [
            ItemRecord(
                row.id,
                row.event_id,
                cast(DependentKind, row.kind),
                row.title,
                row.status,
                row.needs_revalidation,
                row.reported_by,
                tuple(sorted(bindings.get(row.id, []))),
                row.created_at,
                row.updated_at,
            )
            for row in rows
        ]

    def add_item(self, record: ItemRecord) -> None:
        self._session.add(
            EventItem(
                id=record.id,
                event_id=record.event_id,
                kind=record.kind,
                title=record.title,
                status=record.status,
                needs_revalidation=record.needs_revalidation,
                reported_by=record.reported_by,
                verified_by=None,
                verified_at=None,
                evidence_id=None,
                created_at=record.created_at,
                updated_at=record.updated_at,
            )
        )
        self._session.flush()
        self._session.add_all(
            [
                EventDependency(
                    event_id=record.event_id,
                    dependent_id=record.id,
                    field_path=path,
                    rule_id="FIELD_CHANGE",
                )
                for path in record.field_paths
            ]
        )
        self._session.flush()

    def dependencies(self, event_id: UUID) -> list[Dependency]:
        return [
            Dependency(item.id, item.kind, item.title, item.status, path)
            for item in self.items(event_id)
            for path in item.field_paths
        ]

    def revalidate(self, event_id: UUID, impacts: tuple[Impact, ...], now: datetime) -> None:
        for impact in impacts:
            if not impact.revalidation_required:
                continue
            status = (
                impact.status
                if impact.dependent_kind == "TASK"
                else mark_needs_revalidation(CommitmentStatus(impact.status)).value
            )
            self._session.execute(
                update(EventItem)
                .where(
                    EventItem.id == impact.dependent_id,
                    EventItem.event_id == event_id,
                )
                .values(status=status, needs_revalidation=True, updated_at=now)
            )
