"""Typed storage boundary for staged changes and registered operational items."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol
from uuid import UUID

from app.domain.impact import Dependency, DependentKind, FieldPath, Impact
from app.services.ports import UnitOfWork


@dataclass(frozen=True)
class ItemRecord:
    id: UUID
    event_id: UUID
    kind: DependentKind
    title: str
    status: str
    needs_revalidation: bool
    reported_by: UUID
    field_paths: tuple[FieldPath, ...]
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True)
class ChangeRecord:
    id: UUID
    event_id: UUID
    base_revision: int
    reason: str
    status: str
    changes: dict[str, Any]
    conflicts: list[dict[str, Any]]
    impact: list[dict[str, Any]]
    requested_by: UUID
    created_at: datetime
    applied_by: UUID | None = None
    applied_at: datetime | None = None


def impact_json(items: tuple[Impact, ...]) -> list[dict[str, Any]]:
    return [
        {
            "dependent_id": str(item.dependent_id),
            "dependent_kind": item.dependent_kind,
            "title": item.title,
            "status": item.status,
            "changed_fields": list(item.changed_fields),
            "reason": item.reason,
            "revalidation_required": item.revalidation_required,
        }
        for item in items
    ]


class ChangeStore(Protocol):
    def get(self, proposal_id: UUID) -> ChangeRecord | None: ...
    def list_for(
        self, event_id: UUID, limit: int, offset: int
    ) -> tuple[list[ChangeRecord], int]: ...
    def add(self, record: ChangeRecord) -> None: ...
    def apply(
        self, proposal_id: UUID, actor_id: UUID, now: datetime, impact: list[dict[str, Any]]
    ) -> bool: ...
    def items(self, event_id: UUID) -> list[ItemRecord]: ...
    def add_item(self, record: ItemRecord) -> None: ...
    def dependencies(self, event_id: UUID) -> list[Dependency]: ...
    def revalidate(self, event_id: UUID, impacts: tuple[Impact, ...], now: datetime) -> None: ...


class ChangeUnitOfWork(UnitOfWork, Protocol):
    @property
    def changes(self) -> ChangeStore: ...
