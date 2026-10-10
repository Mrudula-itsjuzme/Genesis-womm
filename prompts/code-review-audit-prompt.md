# CampusCue Multi-Perspective Implementation Audit

Audit the changed feature against `PROJECT.md`, `PLAN.md`, `CONTEXT_ARCHITECTURE.md`, `AGENTS.md`, its implementation plan, and API contracts.

Review independently from these perspectives:
1. Domain correctness: event states, time intervals, two-hour boundary, override scope.
2. Security and authorization: role checks, IDOR, evidence trust, service-to-service boundaries.
3. Agent reliability: tool allowlist, timeouts, idempotency, stale data, no false success.
4. RAG correctness: source metadata, access filters, citation integrity, abstention.
5. Data integrity: transaction boundaries, concurrent requests, revisions and audit events.
6. API compatibility: OpenAPI, stable enums, error shapes, contract fixtures.
7. Testing and operability: missing edge cases, observability, dependency failures, reproducible setup.

Return:
- Findings ordered by severity with file/line references.
- Reproducible failure scenarios.
- Missing tests.
- Contract or migration risks.
- Required fixes versus optional improvements.
- A final verdict: Block / Fix before merge / Accept with follow-ups.

Do not invent findings. Distinguish confirmed defects from hypotheses, and do not rewrite code unless asked.
