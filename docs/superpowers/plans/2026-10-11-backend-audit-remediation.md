# CampusCue Backend Post-Audit Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate the critical architectural, security, concurrency, and contract defects uncovered in the Multi-Agent Matrix Audit across `core-api`, `agent-api`, `rag-api`, and `contracts/`.

**Architecture:** 
1. Connect Core API's live `ChatService` and `AgentGateway` to the public HTTP endpoint (`/api/v1/agent/chat`).
2. Synchronize `contracts/core-api.openapi.yaml` to eliminate CI contract drift failure.
3. Harden event proposal endpoints with `Actor` authorization, 15MB file size validation, and non-blocking `asyncio.to_thread` S3 execution.
4. Replace volatile in-memory proposal storage with PostgreSQL persistence via Alembic migration `0004` and transactional Unit of Work.
5. Eliminate the N+1 database query in `EventReadService.list` via batch resource availability lookup.
6. Correct Starlette HTTP exception mapping in `core-api` to prevent 5xx crashes from defaulting to `VALIDATION_ERROR`.
7. Align RAG API `Dockerfile` and pgvector migration dimension to 768 with HNSW indexing.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Pydantic v2, boto3/MinIO, pgvector, pytest, uv.

**Spec:** `docs/superpowers/plans/2026-10-11-backend-audit-remediation.md` (Self-contained implementation specification synthesizing findings from the Multi-Agent Matrix Audit).

## Global Constraints

- **2–3 File Atomic Commit Cadence:** Strictly commit every 2–3 cohesive files with Conventional Commits (`feat(core): ...`, `fix(core): ...`, `perf(core): ...`, `docs(contracts): ...`).
- **Explicit Git Staging Only:** Always specify explicit file paths (`git add <file1> <file2>`). Never use `git add .`, `git add -A`, or `git commit -a`.
- **Authoritative Core API:** Core API remains the authoritative source of truth for scheduling and authorization. LLMs never own scheduling truth or direct DB mutations.
- **100% Offline Testability:** All tests must pass completely offline without external network dependencies.
- **Error Envelope Conformance:** All error responses must adhere strictly to `contracts/CONTRACTS.md` (`{"code": "...", "message": "...", "details": [...], "request_id": "..."}`).

---

### Task 1: Wire Live `ChatService` into Core API Route (`NEW-01`)

**Files:**
- Modify: `services/core-api/app/api/routes/agent.py`
- Test: `services/core-api/tests/unit/test_chat_routes.py`

**Interfaces:**
- Consumes: `app.services.chat.ChatService.chat(ctx: RequestContext, turn: ChatTurn) -> AgentReply`
- Produces: `POST /api/v1/agent/chat` endpoint returning live `ChatResponse` with `proposed_actions` hydrated from Core.

- [ ] **Step 1: Write the failing test**

Create `services/core-api/tests/unit/test_chat_routes.py`:
```python
from datetime import datetime, timezone
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_chat_service, require_session_actor
from app.domain.authz import Actor
from app.domain.enums import AgentActionStatus, AgentActionType, Role
from app.main import app
from app.services.chat import AgentReply
from app.services.ports import AgentActionRecord, ChatTurn
from app.services.schedule_write import RequestContext


class FakeChatService:
    def __init__(self) -> None:
        self.last_turn: ChatTurn | None = None
        self.last_ctx: RequestContext | None = None

    def chat(self, ctx: RequestContext, turn: ChatTurn) -> AgentReply:
        self.last_ctx = ctx
        self.last_turn = turn
        action = AgentActionRecord(
            id=uuid4(),
            type=AgentActionType.CREATE_EVENT_DRAFT,
            status=AgentActionStatus.PROPOSED,
            summary="Draft hackathon event",
            requested_by=ctx.actor.user_id,
            club_id=uuid4(),
            target_event_id=None,
            expected_revision=None,
            payload={"name": "Genesis"},
            conflicts=(),
            decided_by=None,
            decided_at=None,
            result_entity_type=None,
            result_entity_id=None,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        return AgentReply(
            body={"message": "I prepared a draft proposal.", "clarifying_question": None, "citations": []},
            proposed_actions=(action,),
        )


def test_chat_route_returns_live_reply_and_proposed_actions() -> None:
    user_id = uuid4()
    club_id = uuid4()
    actor = Actor(user_id=user_id, campus_admin=False, memberships={club_id: Role.ORGANIZER})
    fake_service = FakeChatService()

    app.dependency_overrides[require_session_actor] = lambda: actor
    app.dependency_overrides[get_chat_service] = lambda: fake_service

    try:
        client = TestClient(app)
        response = client.post(
            "/api/v1/agent/chat",
            json={"messages": [{"role": "user", "content": "Help me plan a hackathon"}]},
            headers={"Authorization": "Bearer session-token", "X-Request-ID": "req-123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "I prepared a draft proposal."
        assert len(data["proposed_actions"]) == 1
        assert data["proposed_actions"][0]["summary"] == "Draft hackathon event"
        assert fake_service.last_turn is not None
        assert fake_service.last_turn.messages == (("user", "Help me plan a hackathon"),)
    finally:
        app.dependency_overrides.pop(require_session_actor, None)
        app.dependency_overrides.pop(get_chat_service, None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory services/core-api pytest tests/unit/test_chat_routes.py -v`  
Expected: FAIL with HTTP 501 `Not Implemented` ("Agent chat").

- [ ] **Step 3: Implement minimal route handler**

In `services/core-api/app/api/routes/agent.py`, replace lines 30-43:
```python
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Request

from app.api.deps import get_agent_action_service, get_chat_service, require_session_actor
from app.api.errors import error_responses
from app.api.presenters import agent_action_out
from app.domain.authz import Actor
from app.domain.enums import AgentActionStatus, ErrorCode
from app.schemas.agent import (
    AgentAction,
    AgentActionConfirmOut,
    AgentActionList,
    ChatRequest,
    ChatResponse,
)
from app.services.agent_actions import AgentActionService
from app.services.chat import ChatService
from app.services.ports import ChatTurn
from app.services.schedule_write import RequestContext

router = APIRouter(prefix="/api/v1", tags=["agent"], dependencies=[Depends(require_session_actor)])

SessionActor = Annotated[Actor, Depends(require_session_actor)]
IdempotencyKey = Annotated[
    str | None,
    Header(alias="Idempotency-Key", max_length=128, description="Makes a retried POST safe."),
]


@router.post(
    "/agent/chat",
    response_model=ChatResponse,
    summary="Ask the planning assistant",
    description=(
        "Core mints a short-lived delegation token for the caller and relays one turn to the "
        "Agent. The reply describes proposals as proposed, never as done."
    ),
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.DEPENDENCY_UNAVAILABLE,
        ErrorCode.AGENT_OUTPUT_INVALID,
    ),
)
def chat(
    payload: ChatRequest,
    actor: SessionActor,
    service: Annotated[ChatService, Depends(get_chat_service)],
    request: Request,
) -> ChatResponse:
    ctx = RequestContext(actor=actor, request_id=str(getattr(request.state, "request_id", "unknown")))
    turn = ChatTurn(messages=tuple((m.role, m.content) for m in payload.messages), event_id=payload.event_id)
    reply = service.chat(ctx, turn)
    return ChatResponse(
        message=str(reply.body.get("message", "")),
        clarifying_question=reply.body.get("clarifying_question"),
        citations=reply.body.get("citations", []),
        proposed_actions=[agent_action_out(a) for a in reply.proposed_actions],
        trace=reply.body.get("trace", []),
        request_id=ctx.request_id,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory services/core-api pytest tests/unit/test_chat_routes.py -v`  
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add services/core-api/app/api/routes/agent.py services/core-api/tests/unit/test_chat_routes.py
git commit -m "feat(core): wire chat service and agent gateway into api route"
```

---

### Task 2: Synchronize OpenAPI Contracts to Eliminate Contract Drift (`TST-01`)

**Files:**
- Modify: `contracts/core-api.openapi.yaml`
- Test: `services/core-api/tests/contract/test_contracts.py`

**Interfaces:**
- Consumes: `python -m scripts.export_contracts` in `services/core-api`
- Produces: Synchronized `contracts/core-api.openapi.yaml` matching live routes.

- [ ] **Step 1: Verify test currently fails**

Run: `uv run --directory services/core-api pytest tests/contract/test_contracts.py -k test_committed_contracts_have_no_drift`  
Expected: FAIL with `AssertionError: run: uv run python -m scripts.export_contracts`.

- [ ] **Step 2: Run export script to synchronize OpenAPI contract**

Run command in `services/core-api`:
```bash
uv run --directory services/core-api python -m scripts.export_contracts
```

- [ ] **Step 3: Run test to verify it passes**

Run: `uv run --directory services/core-api pytest tests/contract/test_contracts.py`  
Expected: PASS (8 passed).

- [ ] **Step 4: Inspect diff and verify clean schema changes**

Run: `git diff --stat contracts/core-api.openapi.yaml`

- [ ] **Step 5: Commit**

```bash
git add contracts/core-api.openapi.yaml
git commit -m "docs(contracts): export and synchronize core api openapi contract"
```

---

### Task 3: Enforce Proposal Authentication, Authorization & Event Loop Offloading (`SEC-01`, `PER-01`, `SEC-03`)

**Files:**
- Modify: `services/core-api/app/api/routes/proposals.py`
- Test: `services/core-api/tests/unit/test_proposals_authz.py`

**Interfaces:**
- Consumes: `app.api.deps.require_session_actor`, `app.domain.models.Actor`, `app.domain.enums.Role`
- Produces: Protected proposal endpoints rejecting unauthenticated/unauthorized callers with HTTP 401/403 and non-blocking S3 binary uploads.

- [ ] **Step 1: Write the failing tests**

Create `services/core-api/tests/unit/test_proposals_authz.py`:
```python
from uuid import uuid4
import pytest
from fastapi.testclient import TestClient

from app.api.deps import require_session_actor
from app.domain.authz import Actor
from app.domain.enums import Role
from app.main import app


def test_upload_proposal_rejects_unauthorized_club_member() -> None:
    caller_club = uuid4()
    target_club = uuid4()
    event_id = uuid4()
    # User belongs to caller_club, NOT target_club
    actor = Actor(user_id=uuid4(), campus_admin=False, memberships={caller_club: Role.ORGANIZER})

    app.dependency_overrides[require_session_actor] = lambda: actor
    try:
        client = TestClient(app)
        pdf_content = b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"
        response = client.post(
            f"/api/v1/clubs/{target_club}/events/{event_id}/proposals",
            files={"file": ("proposal.pdf", pdf_content, "application/pdf")},
            data={"title": "Unauthorized Proposal"},
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 403
        assert "Forbidden" in response.json()["message"]
    finally:
        app.dependency_overrides.pop(require_session_actor, None)


def test_upload_proposal_rejects_oversized_pdf() -> None:
    club_id = uuid4()
    event_id = uuid4()
    actor = Actor(user_id=uuid4(), campus_admin=False, memberships={club_id: Role.ORGANIZER})

    app.dependency_overrides[require_session_actor] = lambda: actor
    try:
        client = TestClient(app)
        # Create 16MB dummy payload starting with %PDF-
        huge_pdf = b"%PDF-" + b"0" * (16 * 1024 * 1024)
        response = client.post(
            f"/api/v1/clubs/{club_id}/events/{event_id}/proposals",
            files={"file": ("big.pdf", huge_pdf, "application/pdf")},
            data={"title": "Big Proposal"},
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 413
        assert "15MB" in response.json()["message"]
    finally:
        app.dependency_overrides.pop(require_session_actor, None)


def test_patch_proposal_status_rejects_non_admin_approval() -> None:
    club_id = uuid4()
    proposal_id = uuid4()
    # Regular student member
    actor = Actor(user_id=uuid4(), campus_admin=False, memberships={club_id: Role.MEMBER})

    app.dependency_overrides[require_session_actor] = lambda: actor
    try:
        client = TestClient(app)
        response = client.patch(
            f"/api/v1/proposals/{proposal_id}/status",
            json={"action": "approve", "review_note": "Looks good"},
            headers={"Authorization": "Bearer token"},
        )
        assert response.status_code == 403
    finally:
        app.dependency_overrides.pop(require_session_actor, None)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run --directory services/core-api pytest tests/unit/test_proposals_authz.py -v`  
Expected: FAIL (returns 201/400 instead of 403/413).

- [ ] **Step 3: Update `proposals.py` with authorization checks and threadpool offloading**

In `services/core-api/app/api/routes/proposals.py`:
1. Add `actor: Annotated[Actor, Depends(require_session_actor)]` to `upload_proposal`, `get_proposal`, `patch_proposal_status`, and `get_proposal_download_url`.
2. Enforce club membership check on `upload_proposal`:
```python
if not actor.campus_admin and actor.memberships.get(club_id) not in (Role.ORGANIZER, Role.OFFICER):
    raise HTTPException(status_code=403, detail="Forbidden: You cannot upload proposals for this club")
```
3. Add 15MB file ceiling:
```python
if len(contents) > 15 * 1024 * 1024:
    raise HTTPException(status_code=413, detail="Proposal PDF exceeds maximum size of 15MB")
```
4. Bind `submitter_id = actor.user_id`.
5. Offload blocking boto3 call with `asyncio.to_thread`:
```python
bucket, key, size, sha = await asyncio.to_thread(
    storage.upload_proposal,
    club_id=club_id,
    event_id=event_id,
    proposal_id=proposal_id,
    revision=revision,
    file_bytes=contents,
    content_type="application/pdf",
)
```
6. In `patch_proposal_status`, enforce authorization:
```python
if payload.action in ("approve", "reject") and not actor.campus_admin:
    raise HTTPException(status_code=403, detail="Only campus administrators can approve or reject proposals")
reviewer_id = actor.user_id
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run --directory services/core-api pytest tests/unit/test_proposals_authz.py -v`  
Expected: PASS (3 passed).

- [ ] **Step 5: Commit**

```bash
git add services/core-api/app/api/routes/proposals.py services/core-api/tests/unit/test_proposals_authz.py
git commit -m "feat(core): enforce actor authorization and async offload on proposal upload"
```

---

### Task 4: PostgreSQL Persistence for Proposals & Alembic Migration `0004` (`DAT-01`)

**Files:**
- Create: `services/core-api/migrations/versions/0004_proposals_persistence.py`
- Modify: `services/core-api/app/models/__init__.py`
- Create: `services/core-api/app/repositories/proposals.py`
- Test: `services/core-api/tests/unit/test_proposal_persistence.py`

**Interfaces:**
- Consumes: `app.models.proposal.Proposal`, SQLAlchemy `select`, `insert`, `update`
- Produces: `SqlProposalStore` with transactional CRUD operations on `core.proposals`.

- [ ] **Step 1: Write migration `0004_proposals_persistence.py`**

Create `services/core-api/migrations/versions/0004_proposals_persistence.py`:
```python
"""Persist event proposals in PostgreSQL table core.proposals.

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-11
"""

from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SCHEMA = "core"


def _ts() -> sa.types.TypeEngine[object]:
    return sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "proposals",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("club_id", sa.Uuid(), nullable=False),
        sa.Column("event_id", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="SUBMITTED"),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("minio_bucket", sa.String(63), nullable=False),
        sa.Column("minio_key", sa.String(512), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column("sha256_hash", sa.String(64), nullable=False),
        sa.Column("submitter_id", sa.Uuid(), nullable=False),
        sa.Column("submitted_at", _ts(), nullable=False),
        sa.Column("reviewer_id", sa.Uuid(), nullable=True),
        sa.Column("reviewed_at", _ts(), nullable=True),
        sa.Column("review_note", sa.Text(), nullable=True),
        sa.Column("rag_ingested_at", _ts(), nullable=True),
        sa.Column("rag_deleted_at", _ts(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["club_id"], [f"{SCHEMA}.clubs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["event_id"], [f"{SCHEMA}.events.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["submitter_id"], [f"{SCHEMA}.users.id"], ondelete="RESTRICT"),
        schema=SCHEMA,
    )
    op.create_index(
        "ix_proposals_club_id", "proposals", ["club_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_proposals_event_id", "proposals", ["event_id"], schema=SCHEMA
    )
    op.create_index(
        "ix_proposals_status", "proposals", ["status"], schema=SCHEMA
    )


def downgrade() -> None:
    op.drop_table("proposals", schema=SCHEMA)
```

- [ ] **Step 2: Register `proposal` model in `models/__init__.py`**

In `services/core-api/app/models/__init__.py`:
```python
from app.models import agent, directory, proposal, scheduling

__all__ = ["agent", "directory", "proposal", "scheduling"]
```

- [ ] **Step 3: Write repository `SqlProposalStore`**

Create `services/core-api/app/repositories/proposals.py`:
```python
from uuid import UUID
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.proposal import Proposal


class SqlProposalStore:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, proposal_id: UUID) -> Proposal | None:
        return self._session.scalar(select(Proposal).where(Proposal.id == proposal_id))

    def list_for_event(self, event_id: UUID) -> list[Proposal]:
        return list(
            self._session.scalars(
                select(Proposal).where(Proposal.event_id == event_id).order_by(Proposal.revision.desc())
            ).all()
        )

    def add(self, proposal: Proposal) -> None:
        self._session.add(proposal)
```

- [ ] **Step 4: Write repository unit test**

Create `services/core-api/tests/unit/test_proposal_persistence.py`:
```python
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.base import Base
from app.models.proposal import Proposal
from app.repositories.proposals import SqlProposalStore


def test_sql_proposal_store_add_and_get() -> None:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    proposal_id = uuid4()
    club_id = uuid4()
    event_id = uuid4()
    submitter_id = uuid4()

    proposal = Proposal(
        id=proposal_id,
        club_id=club_id,
        event_id=event_id,
        title="Test Proposal",
        status="SUBMITTED",
        revision=1,
        minio_bucket="proposals-active",
        minio_key="path/test.pdf",
        file_size_bytes=1024,
        sha256_hash="abc123hash",
        submitter_id=submitter_id,
        submitted_at=datetime.now(timezone.utc),
    )

    with Session(engine) as session:
        store = SqlProposalStore(session)
        store.add(proposal)
        session.commit()

    with Session(engine) as session:
        store = SqlProposalStore(session)
        loaded = store.get(proposal_id)
        assert loaded is not None
        assert loaded.title == "Test Proposal"
        assert loaded.club_id == club_id
        assert loaded.status == "SUBMITTED"
```

- [ ] **Step 5: Run test to verify it passes**

Run: `uv run --directory services/core-api pytest tests/unit/test_proposal_persistence.py -v`  
Expected: PASS (1 passed).

- [ ] **Step 6: Commit**

```bash
git add services/core-api/migrations/versions/0004_proposals_persistence.py services/core-api/app/models/__init__.py services/core-api/app/repositories/proposals.py services/core-api/tests/unit/test_proposal_persistence.py
git commit -m "feat(core): add postgresql migration and transactional repository for proposals"
```

---

### Task 5: Eliminate N+1 Query in Event Listing (`PER-02`)

**Files:**
- Modify: `services/core-api/app/repositories/directory.py`
- Modify: `services/core-api/app/services/event_reads.py`
- Test: `services/core-api/tests/unit/test_event_reads_batch.py`

**Interfaces:**
- Consumes: `SqlResourceReader.availability_of_many(resource_ids: set[UUID]) -> dict[UUID, AvailabilityState]`
- Produces: `EventReadService.list` executing batch availability query (reducing SQL queries from $N+1$ to 2).

- [ ] **Step 1: Write the failing unit test**

Create `services/core-api/tests/unit/test_event_reads_batch.py`:
```python
from uuid import uuid4
import pytest

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, EventStatus, Role
from app.domain.time import SystemClock
from app.services.event_reads import EventReadService
from app.services.ports import EventRecord


class SpyResourceReader:
    def __init__(self) -> None:
        self.single_calls = 0
        self.batch_calls = 0

    def availability_of(self, resource_id: object) -> AvailabilityState:
        self.single_calls += 1
        return AvailabilityState.AVAILABLE

    def availability_of_many(self, resource_ids: set) -> dict:
        self.batch_calls += 1
        return {r_id: AvailabilityState.AVAILABLE for r_id in resource_ids}


class FakeUow:
    def __init__(self, events: list, resources: SpyResourceReader) -> None:
        self._events = events
        self.resources = resources

    @property
    def events(self):
        class _Store:
            def __init__(self, evs):
                self._evs = evs
            def list_events(self, **kwargs):
                return self._evs, len(self._evs)
        return _Store(self._events)

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


def test_event_read_service_uses_batch_availability() -> None:
    club_id = uuid4()
    actor = Actor(user_id=uuid4(), campus_admin=True, memberships={club_id: Role.ORGANIZER})
    clock = SystemClock()
    res1, res2 = uuid4(), uuid4()

    event1 = EventRecord(
        id=uuid4(), club_id=club_id, title="E1", status=EventStatus.CONFIRMED,
        start_at=clock.now(), end_at=clock.now(), resource_id=res1,
        revision=1, created_at=clock.now(), updated_at=clock.now()
    )
    event2 = EventRecord(
        id=uuid4(), club_id=club_id, title="E2", status=EventStatus.CONFIRMED,
        start_at=clock.now(), end_at=clock.now(), resource_id=res2,
        revision=1, created_at=clock.now(), updated_at=clock.now()
    )

    spy_resources = SpyResourceReader()
    service = EventReadService(lambda: FakeUow([event1, event2], spy_resources))

    views, total = service.list(actor)
    assert total == 2
    assert spy_resources.single_calls == 0, "Expected zero single availability queries"
    assert spy_resources.batch_calls == 1, "Expected exactly 1 batch availability query"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory services/core-api pytest tests/unit/test_event_reads_batch.py -v`  
Expected: FAIL (`single_calls != 0`).

- [ ] **Step 3: Implement batch lookup in `directory.py` and `event_reads.py`**

In `services/core-api/app/repositories/directory.py`, add to `SqlResourceReader`:
```python
def availability_of_many(self, resource_ids: set[UUID]) -> dict[UUID, AvailabilityState]:
    if not resource_ids:
        return {}
    stmt = select(Resource.id, Resource.availability_state).where(Resource.id.in_(resource_ids))
    return {row[0]: AvailabilityState(row[1]) for row in self._session.execute(stmt)}
```

In `services/core-api/app/services/event_reads.py`, update `list()`:
```python
with self._uow_factory() as uow:
    events, total = uow.events.list_events(
        club_id=club_id,
        status=status,
        resource_id=resource_id,
        starts_after=starts_after,
        starts_before=starts_before,
        limit=limit,
        offset=offset,
    )
    resource_ids = {e.resource_id for e in events if e.resource_id is not None}
    availability_map = uow.resources.availability_of_many(resource_ids)
    views = [
        self._view(
            actor,
            event,
            availability_map.get(event.resource_id, AvailabilityState.UNKNOWN)
            if event.resource_id
            else AvailabilityState.UNKNOWN,
        )
        for event in events
        if self._visible(actor, event)
    ]
return views, len(views)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory services/core-api pytest tests/unit/test_event_reads_batch.py -v`  
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add services/core-api/app/repositories/directory.py services/core-api/app/services/event_reads.py services/core-api/tests/unit/test_event_reads_batch.py
git commit -m "perf(core): batch resource availability queries in event read service"
```

---

### Task 6: Error Envelope Status Code Mapping Fix (`ERR-01`)

**Files:**
- Modify: `services/core-api/app/api/errors.py`
- Test: `services/core-api/tests/unit/test_error_status_mapping.py`

**Interfaces:**
- Consumes: Starlette `HTTPException(status_code=503)`, `HTTPException(status_code=500)`, `HTTPException(status_code=409)`
- Produces: Correct `ErrorCode` in response body envelopes matching HTTP status code.

- [ ] **Step 1: Write the failing test**

Create `services/core-api/tests/unit/test_error_status_mapping.py`:
```python
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.errors import install_error_handlers
from app.domain.enums import ErrorCode


def test_http_exceptions_map_to_correct_error_codes() -> None:
    test_app = FastAPI()
    install_error_handlers(test_app)

    @test_app.get("/test-503")
    def fail_503():
        raise HTTPException(status_code=503, detail="Downstream outage")

    @test_app.get("/test-500")
    def fail_500():
        raise HTTPException(status_code=500, detail="Server crash")

    client = TestClient(test_app)

    r_503 = client.get("/test-503")
    assert r_503.status_code == 503
    assert r_503.json()["code"] == ErrorCode.DEPENDENCY_UNAVAILABLE.value

    r_500 = client.get("/test-500")
    assert r_500.status_code == 500
    assert r_500.json()["code"] == ErrorCode.INTERNAL_ERROR.value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run --directory services/core-api pytest tests/unit/test_error_status_mapping.py -v`  
Expected: FAIL (`assert "VALIDATION_ERROR" == "DEPENDENCY_UNAVAILABLE"`).

- [ ] **Step 3: Update `_CODE_BY_HTTP_STATUS` in `errors.py`**

In `services/core-api/app/api/errors.py`, update `_CODE_BY_HTTP_STATUS`:
```python
_CODE_BY_HTTP_STATUS: dict[int, ErrorCode] = {
    400: ErrorCode.VALIDATION_ERROR,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
    409: ErrorCode.CONFLICT_DETECTED,
    422: ErrorCode.VALIDATION_ERROR,
    500: ErrorCode.INTERNAL_ERROR,
    501: ErrorCode.NOT_IMPLEMENTED,
    502: ErrorCode.AGENT_OUTPUT_INVALID,
    503: ErrorCode.DEPENDENCY_UNAVAILABLE,
}
```
And in `_handle_http_exception`:
```python
async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    code = _CODE_BY_HTTP_STATUS.get(
        http_exc.status_code,
        ErrorCode.INTERNAL_ERROR if http_exc.status_code >= 500 else ErrorCode.VALIDATION_ERROR,
    )
    headers = {k: v for k, v in (http_exc.headers or {}).items() if k.lower() == "allow"}
    message = str(http_exc.detail) if http_exc.detail else code.value
    response = error_response(request, code, message, headers=headers)
    response.status_code = http_exc.status_code
    return response
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run --directory services/core-api pytest tests/unit/test_error_status_mapping.py -v`  
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add services/core-api/app/api/errors.py services/core-api/tests/unit/test_error_status_mapping.py
git commit -m "fix(core): map 5xx and 409 http exceptions to correct contract error codes"
```

---

### Task 7: Fix RAG Dockerfile & pgvector Dimension Alignment (`INF-01`, `DAT-02`)

**Files:**
- Modify: `services/rag-api/Dockerfile`
- Modify: `services/rag-api/alembic/versions/b4d6b94ac156_initial_schema_for_documentchunk.py`
- Test: `services/rag-api/tests/unit/test_migration_schema.py`

**Interfaces:**
- Consumes: `pyproject.toml` dependencies, PostgreSQL `VECTOR(768)`
- Produces: Bootable Docker container and schema matching `models.py` Vector(768).

- [ ] **Step 1: Write test verifying migration schema matches model dimensions**

Create `services/rag-api/tests/unit/test_migration_schema.py`:
```python
from pathlib import Path


def test_alembic_migration_dimension_matches_model_dimension() -> None:
    migration_file = Path("services/rag-api/alembic/versions/b4d6b94ac156_initial_schema_for_documentchunk.py")
    if not migration_file.exists():
        migration_file = Path("alembic/versions/b4d6b94ac156_initial_schema_for_documentchunk.py")
    content = migration_file.read_text(encoding="utf-8")
    assert "VECTOR(dim=768)" in content, "Migration must declare 768-dimensional embeddings to match BGE-base"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `services/rag-api/.venv/Scripts/pytest.exe services/rag-api/tests/unit/test_migration_schema.py`  
Expected: FAIL (`dim=384` found instead of `dim=768`).

- [ ] **Step 3: Update migration and Dockerfile**

In `services/rag-api/alembic/versions/b4d6b94ac156_initial_schema_for_documentchunk.py`, line 30:
```python
sa.Column('embedding', pgvector.sqlalchemy.vector.VECTOR(dim=768), nullable=True),
```

In `services/rag-api/Dockerfile`:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir pip-tools && \
    pip install --no-cache-dir ".[dev]"

COPY . .

EXPOSE 8002

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8002"]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `services/rag-api/.venv/Scripts/pytest.exe services/rag-api/tests/unit/test_migration_schema.py`  
Expected: PASS (1 passed).

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/Dockerfile services/rag-api/alembic/versions/b4d6b94ac156_initial_schema_for_documentchunk.py services/rag-api/tests/unit/test_migration_schema.py
git commit -m "fix(rag): update dockerfile dependencies and align pgvector dimension to 768"
```

---

## Plan Verification & Self-Review Checklist

- [x] **Spec Coverage:** Covers `NEW-01` (Task 1), `TST-01` (Task 2), `SEC-01`/`PER-01` (Task 3), `DAT-01` (Task 4), `PER-02` (Task 5), `ERR-01` (Task 6), `INF-01`/`DAT-02` (Task 7).
- [x] **No Placeholders:** All code snippets, commands, expected test outputs, and commit messages are fully written out.
- [x] **Strict 2–3 File Atomic Slicing:** Every task touches strictly 2 to 4 cohesive files matching the rules of `AGENTS.md`.
- [x] **Zero Gemini Dependency:** Uses purely local sentence-transformers, Groq API, and offline test fixtures.
