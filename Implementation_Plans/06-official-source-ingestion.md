# Implementation Plan 06: Official Source Ingestion

**Status:** Planned
**Owner:** RAG and Core workstreams
**Dependencies:** Plan 00, Plan 02, approved source access, `SOURCE_REGISTRY.md`

## Objective

Implement an authorized, provenance-preserving ingestion pipeline for Amrita Coimbatore sources. It must route reviewed policy documents to RAG and structured events, calendars, resources, services, and club records to PostgreSQL.

## Non-goals

- Circumvent login requirements, robots rules, terms, or rate limits.
- Treat published calendars as live venue-availability systems.
- Collect student lists, roll numbers, personal phone numbers, or other unnecessary personal data.
- Treat historical club activities as current operational events without review.
- Add an institutional attendance or booking integration.

## Source split

| Pipeline | Inputs | Output |
|---|---|---|
| RAG policy corpus | OSA handbook and reviewed Student Affairs procedural guidance | Versioned, page-cited policy chunks |
| Structured campus catalog | Event pages, academic calendar, ICS feed, facilities, ICTS, contacts and club pages | Source-backed PostgreSQL records with freshness state |

The source registry is the allowlist. A parser may only process a registered URL and must report a disallowed source rather than fetch it.

## Expected files

- `services/rag-api/app/ingestion/source_registry.py`
- `services/rag-api/app/parsing/pdf.py`
- `services/rag-api/app/parsing/html.py`
- `services/core-api/app/ingestion/ics.py`
- `services/core-api/app/ingestion/structured_sources.py`
- `services/core-api/app/models/source.py`
- `services/core-api/app/models/catalog.py`
- `services/core-api/tests/ingestion/`
- `services/rag-api/tests/ingestion/`
- `contracts/source-ingestion.yaml`

## Ordered steps

1. Translate `SOURCE_REGISTRY.md` into an explicit, version-controlled source allowlist with pipeline, parser, access class, extraction purpose, and refresh cadence.
2. Define a source-fetch record: URL, source ID, retrieval time, response status, content type, content hash, parser version, published or updated value when available, parse outcome, review state, and error category.
3. Add an HTTP fetch adapter that honors access controls, conditional retrieval when supported, request timeouts, and source-specific rate limits. Do not implement login bypasses.
4. Build the PDF adapter for the OSA handbook. Preserve page number and heading path before passing chunks to RAG ingestion.
5. Build a constrained HTML extraction adapter for the approved catalog pages. Extract only the fields documented in the registry and retain original source links.
6. Build the ICS adapter. Preserve UID, recurrence, timezone, start and end values, sequence, and last-modified fields when present. Upsert by source ID plus UID.
7. Normalize structured output into events, academic-calendar entries, facilities, services, contacts, and clubs. Mark fields missing rather than guessing them.
8. Add deduplication and supersession rules. Source-specific stable IDs win; fuzzy title/date matching can create a review task but cannot silently merge records.
9. Add freshness states: `CURRENT`, `STALE`, `HISTORICAL`, `PARSE_FAILED`, `REVIEW_REQUIRED`, and `UNKNOWN`. No state may imply venue availability.
10. Enforce privacy filters before persistence and before search exposure. Keep personal data out of the pipeline unless it is necessary, authorized, and documented.
11. Add admin-only run and status endpoints, parser diagnostics, and source-level audit entries. Do not expose credentials or raw restricted content.
12. Seed deterministic fixtures from permitted, synthetic or minimized extracts. Test parser variation without depending on live network calls.

## Acceptance criteria

- Policy chunks preserve source URL, document version, page or section metadata, hash, and ingestion timestamps.
- Events, calendar entries, resources, services, and clubs each retain a source record and freshness state in PostgreSQL.
- An ICS update does not create duplicate active entries for the same source UID.
- Historical club pages cannot create a `CURRENT` event without a dated current source or reviewer action.
- A blank, stale, or inaccessible source cannot be presented as evidence of venue availability.
- The pipeline rejects unknown sources and reports parse failures with source provenance.
- Tests cover malformed PDF or HTML input, missing dates, changed ICS sequence, duplicate content, access denial, privacy filtering, and stale-source presentation.

## Risks and decisions

- Public retrieval can change. The source registry records an observed access check, not a permanent availability guarantee.
- The Student Affairs page is suitable for review but must be approved as a policy document before RAG activation.
- Club pages can be useful contextual sources but are lower freshness than event calendars and should be reviewed before operational use.
- The general university Life at Amrita page is not automatically a Coimbatore-only club directory.
- Existing public sources do not establish live facility availability or an authorized institutional attendance API.

## Deviation log

- 2026-10-10: Added after a source-access review of the official endpoints listed in `SOURCE_REGISTRY.md`. Implementation has not started.
