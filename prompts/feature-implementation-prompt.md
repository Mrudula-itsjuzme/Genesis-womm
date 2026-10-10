# Coding Agent Prompt: Implement a CampusCue Feature

Read `AGENTS.md`, `PROJECT.md`, `PLAN.md`, and `CONTEXT_ARCHITECTURE.md` first. Then read the relevant file in `Implementation_Plans/`.

Task: [Describe one bounded feature]

Before coding:
1. Inspect repository state and relevant implementation.
2. Identify the owning service, exact contracts, data migrations, and dependent workstreams.
3. If a detailed implementation plan does not exist, create it first. Include objective, non-goals, preconditions, exact files, ordered steps, contracts, tests, risks, definition of done, and deviation log.
4. State unresolved assumptions. Do not treat unverified campus practices as official policy.

Implementation requirements:
- Preserve service boundaries.
- Core API owns scheduling truth, authorization, persistent state and audit.
- Agent uses typed allowlisted tools; no direct database access.
- RAG citations must come from indexed source metadata.
- Validate all input and mutation permissions server-side.
- Add tests for success, boundary, error, stale state and authorization paths relevant to the feature.
- Update OpenAPI and contract fixtures in the same change.
- Do not add unrelated dependencies or reformat unrelated files.
- Never invent test results, source citations, approvals or venue availability.

Verification:
- Run focused tests, lint/format/type checks actually configured.
- Report exact commands and outcomes.
- Record any deviation from the implementation plan.
- Do not commit, deploy, or alter Git history unless explicitly instructed.

Final response:
1. Summary
2. Files changed
3. Tests run and results
4. Contract/schema/migration impacts
5. Known limitations
6. Plan deviations
7. Next action
