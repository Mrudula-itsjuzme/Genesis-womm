# CampusCue API Contract Rules

This directory contains versioned service contracts and example payloads. OpenAPI files should be added as implementation begins and updated in the same change as schema changes.

## Shared conventions
- IDs: UUID strings for persisted entities; stable evidence IDs for indexed chunks.
- Timestamps: ISO 8601 with timezone. Campus-local inputs use `Asia/Kolkata`; persist normalized instants in UTC.
- Error envelope:
  ```json
  {
    "code": "CONFLICT_DETECTED",
    "message": "The proposed time violates a scheduling rule.",
    "details": [],
    "request_id": "..."
  }
  ```
- Every response should include a request/correlation ID via header or response envelope.
- Mutation endpoints should accept `Idempotency-Key` when retrying can duplicate a state change.
- Change endpoints include `expected_revision` or `expected_version`.
- Do not expose ORM/database objects directly as API schemas.

## Conflict object
```json
{
  "type": "CAMPUS_GAP_VIOLATION",
  "severity": "warning",
  "event_ids": ["uuid-a", "uuid-b"],
  "start_at": "2026-10-20T09:00:00+05:30",
  "end_at": "2026-10-20T11:00:00+05:30",
  "message": "The events are less than 120 minutes apart.",
  "override_required": false
}
```

`severity` is policy-dependent and must be documented. A confirmed same-venue overlap should normally be blocking; a tentative cross-club overlap is generally a warning.

## Commitment
```json
{
  "id": "uuid",
  "event_id": "uuid",
  "kind": "ICTS_SUPPORT",
  "status": "ACKNOWLEDGED",
  "reported_by": "uuid",
  "source_type": "EMAIL_REFERENCE",
  "evidence_id": "uuid-or-null",
  "verified_by": null,
  "verified_at": null,
  "notes": "Receipt acknowledged; equipment/personnel not confirmed."
}
```

## RAG citation
```json
{
  "evidence_id": "osa-2025-p12-s3-02",
  "document_id": "osa-handbook-2025",
  "title": "Student Affairs Handbook",
  "source_url": "https://example.invalid/source.pdf",
  "page_start": 12,
  "page_end": 12,
  "excerpt": "Exact text from the retrieved passage.",
  "document_version": "2025"
}
```

The `.invalid` domain is deliberately illustrative and must not be used as a real citation. Actual source metadata must come from the ingestion index.

## Agent action
```json
{
  "action_id": "uuid",
  "type": "CREATE_FOLLOWUP_DRAFT",
  "summary": "Ask ICTS to revalidate support after venue change",
  "requires_human_review": true,
  "status": "PROPOSED",
  "target_event_id": "uuid",
  "payload": {}
}
```

## Override
```json
{
  "override_scope": "CAMPUS_GAP",
  "event_ids": ["uuid-a", "uuid-b"],
  "reason": "Authorized exception for concurrent campus activities",
  "authorized_by": "uuid",
  "evidence_reference": null
}
```

The Core API must derive and validate the actor's authorization. A client-provided `authorized_by` value is not proof of authority.
