"""Plain-JSON forms of events and conflicts, and the request hash.

Used for revision snapshots, stored idempotent responses and the idempotency request hash.
Times are written as UTC so the same instant always serialises, and hashes, the same way.
"""

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from app.domain.enums import ConflictConstraint, ConflictType, EventStatus, OverrideScope, Severity
from app.domain.intervals import Interval
from app.domain.scheduling import Conflict
from app.services.ports import EventRecord, OverrideRecord


def _utc(value: datetime) -> str:
    return value.astimezone(UTC).isoformat()


def _optional_utc(value: datetime | None) -> str | None:
    return None if value is None else _utc(value)


def _optional_time(value: str | None) -> datetime | None:
    return None if value is None else datetime.fromisoformat(value)


def _optional_uuid(value: str | None) -> UUID | None:
    return None if value is None else UUID(value)


def event_snapshot(record: EventRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "club_id": str(record.club_id),
        "title": record.title,
        "description": record.description,
        "start_at": _utc(record.start_at),
        "end_at": _utc(record.end_at),
        "resource_id": None if record.resource_id is None else str(record.resource_id),
        "expected_attendance": record.expected_attendance,
        "audience_tags": list(record.audience_tags),
        "status": record.status.value,
        "revision": record.revision,
        "created_by": str(record.created_by),
        "verified_by": None if record.verified_by is None else str(record.verified_by),
        "verified_at": _optional_utc(record.verified_at),
        "evidence_id": None if record.evidence_id is None else str(record.evidence_id),
        "is_synthetic": record.is_synthetic,
        "created_at": _utc(record.created_at),
        "updated_at": _utc(record.updated_at),
    }


def event_from_json(data: Mapping[str, Any]) -> EventRecord:
    return EventRecord(
        id=UUID(data["id"]),
        club_id=UUID(data["club_id"]),
        title=data["title"],
        description=data["description"],
        start_at=datetime.fromisoformat(data["start_at"]),
        end_at=datetime.fromisoformat(data["end_at"]),
        resource_id=_optional_uuid(data["resource_id"]),
        expected_attendance=data["expected_attendance"],
        audience_tags=tuple(data["audience_tags"]),
        status=EventStatus(data["status"]),
        revision=data["revision"],
        created_by=UUID(data["created_by"]),
        verified_by=_optional_uuid(data["verified_by"]),
        verified_at=_optional_time(data["verified_at"]),
        evidence_id=_optional_uuid(data["evidence_id"]),
        is_synthetic=data["is_synthetic"],
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
    )


def conflict_to_json(conflict: Conflict) -> dict[str, Any]:
    return {
        "type": conflict.type.value,
        "severity": conflict.severity.value,
        "constraint": None if conflict.constraint is None else conflict.constraint.value,
        "event_ids": [str(i) for i in conflict.event_ids],
        "window_start": _utc(conflict.window.start),
        "window_end": _utc(conflict.window.end),
        "message": conflict.message,
        "override_required": conflict.override_required,
    }


def conflict_from_json(data: Mapping[str, Any]) -> Conflict:
    constraint = data["constraint"]
    return Conflict(
        type=ConflictType(data["type"]),
        severity=Severity(data["severity"]),
        constraint=None if constraint is None else ConflictConstraint(constraint),
        event_ids=tuple(UUID(i) for i in data["event_ids"]),
        window=Interval(
            datetime.fromisoformat(data["window_start"]),
            datetime.fromisoformat(data["window_end"]),
        ),
        message=data["message"],
        override_required=data["override_required"],
    )


def override_to_json(record: OverrideRecord) -> dict[str, Any]:
    return {
        "id": str(record.id),
        "scope": record.scope.value,
        "event_a_id": str(record.event_a_id),
        "event_b_id": str(record.event_b_id),
        "reason": record.reason,
        "authorized_by": str(record.authorized_by),
        "evidence_id": None if record.evidence_id is None else str(record.evidence_id),
        "created_at": _utc(record.created_at),
    }


def override_from_json(data: Mapping[str, Any]) -> OverrideRecord:
    return OverrideRecord(
        id=UUID(data["id"]),
        scope=OverrideScope(data["scope"]),
        event_a_id=UUID(data["event_a_id"]),
        event_b_id=UUID(data["event_b_id"]),
        reason=data["reason"],
        authorized_by=UUID(data["authorized_by"]),
        evidence_id=_optional_uuid(data["evidence_id"]),
        created_at=datetime.fromisoformat(data["created_at"]),
    )


def _canonical(value: Any) -> Any:
    if isinstance(value, datetime):
        return _utc(value)
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(k): _canonical(v) for k, v in value.items()}
    if isinstance(value, list | tuple | set | frozenset):
        items = [_canonical(v) for v in value]
        return sorted(items, key=str) if isinstance(value, set | frozenset) else items
    return value


def request_hash(action: str, payload: Mapping[str, Any]) -> str:
    """A stable fingerprint of a request, for telling a true retry from a reused key."""
    canonical = json.dumps(
        {"action": action, "payload": _canonical(payload)},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode()).hexdigest()
