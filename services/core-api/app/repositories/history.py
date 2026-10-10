"""PostgreSQL adapters for the append-only record: audit, evidence and idempotency (spine AD-8).

The database refuses to update or delete audit and evidence rows, so these classes only ever
insert.
"""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.scheduling import AuditEvent, EvidenceRecord, IdempotencyKey
from app.services.ports import AuditRecord, EvidenceData, StoredResponse


class SqlAuditWriter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, record: AuditRecord) -> None:
        self._session.add(
            AuditEvent(
                id=record.id,
                actor_id=record.actor_id,
                action=record.action,
                entity_type=record.entity_type,
                entity_id=record.entity_id,
                outcome=record.outcome,
                reason_code=record.reason_code,
                request_id=record.request_id,
                via=record.via,
                created_at=record.created_at,
            )
        )
        self._session.flush()


class SqlEvidenceWriter:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, evidence: EvidenceData) -> None:
        self._session.add(
            EvidenceRecord(
                id=evidence.id,
                kind=evidence.kind,
                reference=evidence.reference,
                issuer=evidence.issuer,
                captured_at=evidence.captured_at,
                recorded_by=evidence.recorded_by,
                created_at=evidence.created_at,
            )
        )
        self._session.flush()


class SqlIdempotencyStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, actor_id: UUID, key: str) -> StoredResponse | None:
        row = self._session.execute(
            select(
                IdempotencyKey.request_hash, IdempotencyKey.status_code, IdempotencyKey.response
            ).where(IdempotencyKey.actor_id == actor_id, IdempotencyKey.key == key)
        ).first()
        if row is None:
            return None
        return StoredResponse(
            request_hash=row.request_hash, status_code=row.status_code, response=row.response
        )

    def put(self, actor_id: UUID, key: str, stored: StoredResponse, created_at: datetime) -> None:
        self._session.add(
            IdempotencyKey(
                actor_id=actor_id,
                key=key,
                request_hash=stored.request_hash,
                status_code=stored.status_code,
                response=stored.response,
                created_at=created_at,
            )
        )
        self._session.flush()
