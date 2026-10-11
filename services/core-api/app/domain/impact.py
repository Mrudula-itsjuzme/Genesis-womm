"""Deterministic impact from explicitly registered event-field dependencies (AD-14)."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Literal
from uuid import UUID

FieldPath = Literal["start_at", "end_at", "resource_id", "expected_attendance"]
DependentKind = Literal["COMMITMENT", "TASK"]


@dataclass(frozen=True)
class Dependency:
    dependent_id: UUID
    dependent_kind: DependentKind
    title: str
    status: str
    field_path: FieldPath


@dataclass(frozen=True)
class Impact:
    dependent_id: UUID
    dependent_kind: DependentKind
    title: str
    status: str
    changed_fields: tuple[FieldPath, ...]
    reason: str
    revalidation_required: bool


def impact_for(changed_fields: set[str], dependencies: Iterable[Dependency]) -> tuple[Impact, ...]:
    grouped: dict[UUID, tuple[Dependency, set[FieldPath]]] = {}
    for dependency in dependencies:
        if dependency.status == "CLOSED" or dependency.field_path not in changed_fields:
            continue
        _item, fields = grouped.setdefault(dependency.dependent_id, (dependency, set()))
        fields.add(dependency.field_path)
    return tuple(
        Impact(
            dependent_id=item.dependent_id,
            dependent_kind=item.dependent_kind,
            title=item.title,
            status=item.status,
            changed_fields=tuple(sorted(fields)),
            reason="Recheck registered dependency after changing: " + ", ".join(sorted(fields)),
            revalidation_required=item.status != "DRAFT",
        )
        for _, (item, fields) in sorted(grouped.items(), key=lambda pair: pair[0].int)
    )
