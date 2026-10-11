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
- Student academic-risk data is private to the authenticated student. Organizer responses must not contain student calendar titles, timetable entries, attendance values, or warning details.

## Synthetic demo identities

Local demo login is backed only by the idempotent synthetic seed (`services/core-api/scripts/seed_demo.py`). These are non-production identities; no real person or institutional address belongs in the seed.

| Email | Who | Can do |
|---|---|---|
| `organizer@demo.invalid` | Organizer in both clubs | Plan, propose, ask the assistant, confirm their own proposals |
| `club-admin@demo.invalid` | Club admin of *Synthetic Events Club* | Everything an organizer can, plus cancel and complete |
| `campus-admin@demo.invalid` | Campus admin | Confirm events, create overrides, review proposal documents |
| `outsider@demo.invalid` | Signed in, belongs to no club | Read public summaries only; cannot plan or confirm |
| `student@demo.invalid` | Student | Student portal; no club |

Clubs: *Synthetic Events Club* (`20000000-0000-4000-8000-000000000001`), *Synthetic Robotics Club* (`...0002`). Venues: *Synthetic Main Auditorium* (`30000000-0000-4000-8000-000000000001`, availability CONFIRMED), *Synthetic Seminar Hall* (`...0002`, REQUESTED), *Synthetic Open Courtyard* (`...0003`, UNKNOWN).

The **demo day is 20 November 2026**. Two CONFIRMED events anchor it: *Synthetic Guest Lecture* (auditorium, 09:30 to 11:30 IST) and *Synthetic Hardware Demo* (seminar hall, 13:00 to 14:30 IST). A draft for the auditorium from 10:00 to 12:00 collides with both (it overlaps the lecture and ends only 60 minutes before the demo): Core reports `TENTATIVE_OVERLAP` warnings for a draft, and `VENUE_OVERLAP` plus `CAMPUS_GAP_VIOLATION` blocks if it is confirmed. A free slot is the auditorium on any other day.

## Browser access (CORS)

Core allows the origins in `CORS_ALLOWED_ORIGINS` (a JSON list; default `["http://localhost:3000"]`) to call `/api/v1` with `Authorization`, `Content-Type`, `Idempotency-Key` and `X-Request-ID`, and exposes `X-Request-ID`. Methods: `GET`, `POST`, `PATCH`, `OPTIONS`. Other origins receive no CORS headers. The Agent and RAG services are not browser-facing.

## Assistant turn context

`POST /api/v1/agent/chat` takes only `messages` and an optional `event_id` from the browser. Core adds a `context` to the turn it relays to the Agent (`TurnContext` in `contracts/agent-api.openapi.yaml`): its own clock, the person's clubs (id, name, role) and the venue catalogue (id, name, capacity, availability), read from Core's database. Clients cannot supply it. The Agent tells the model to use only the ids listed there. Names are flattened and bounded before the model sees them.

## Conflict object
```json
{
  "type": "CAMPUS_GAP_VIOLATION",
  "severity": "blocking",
  "event_ids": ["uuid-a", "uuid-b"],
  "start_at": "2026-10-20T09:00:00+05:30",
  "end_at": "2026-10-20T11:00:00+05:30",
  "message": "The events are less than 120 minutes apart.",
  "override_required": true
}
```

`severity` is policy-dependent and must be documented. A `CAMPUS_GAP_VIOLATION` is blocking by default and requires an authorized administrator's scoped `CAMPUS_GAP` override. A confirmed same-venue overlap should normally be blocking; a tentative cross-club overlap is generally a warning. A campus-gap override does not bypass a venue-overlap conflict.

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

## Student event publication
```json
{
  "event_id": "uuid",
  "visibility": "CAMPUS_PUBLIC",
  "registration_mode": "EXTERNAL",
  "registration_url": "https://example.invalid/register",
  "registration_opens_at": "2026-10-10T09:00:00+05:30",
  "registration_closes_at": "2026-10-19T18:00:00+05:30",
  "published_at": "2026-10-10T09:00:00+05:30"
}
```

`registration_mode` is one of `INTERNAL`, `EXTERNAL`, or `NONE`. A publication controls student discovery only; it does not indicate university approval, confirmed venue availability, or registration completion.

## Registration-risk check
```json
{
  "event_id": "uuid",
  "can_continue": true,
  "warnings": [
    {
      "type": "EXAM_NEXT_DAY",
      "severity": "warning",
      "message": "You have an exam tomorrow at 09:00.",
      "source": "SEEDED_ACADEMIC_CALENDAR"
    },
    {
      "type": "CLASS_ATTENDANCE_RISK",
      "severity": "warning",
      "message": "This event overlaps CSE201. Your current attendance is 60%.",
      "source": "MOCK_ATTENDANCE"
    }
  ],
  "checks_completed": ["ACADEMIC_CALENDAR", "TIMETABLE", "ATTENDANCE"]
}
```

Risk types are `EXAM_OVERLAP`, `EXAM_NEXT_DAY`, `CLASS_OVERLAP`, `CLASS_ATTENDANCE_RISK`, and `ACADEMIC_DATA_UNAVAILABLE`. Warnings are advisory. The response belongs only to the current student and does not calculate or claim institutional attendance eligibility.

## Registration result
```json
{
  "event_id": "uuid",
  "status": "REDIRECTED_TO_EXTERNAL_REGISTRATION",
  "registration_id": "uuid",
  "redirect_url": "https://example.invalid/register"
}
```

Internal registration returns `REGISTERED`. External registration returns `REDIRECTED_TO_EXTERNAL_REGISTRATION`; the platform does not know whether the student completed the external form.
