"""Deterministic stand-ins for Core and RAG (spine AD-2).

They let the Agent, and anyone building on it, work and test with no network, no paid model and
no other service running. They implement the same ports as the real HTTP clients will.
"""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from uuid import UUID

from app.ports.clock import Clock
from app.ports.core import CallContext
from app.ports.errors import IdempotencyMismatchError, NotFoundError, PortError
from app.schemas.chat import Citation
from app.schemas.core import (
    AgentAction,
    AgentActionCreate,
    AgentConflictCheckRequest,
    Conflict,
    ConflictCheckOut,
    EventOut,
)
from app.schemas.enums import AgentActionStatus, Severity
from app.schemas.rag import (
    AnswerRequest,
    AnswerResponse,
    EvidenceChunk,
    SearchRequest,
    SearchResponse,
)

_WORD = re.compile(r"[a-z0-9]{3,}")

INSUFFICIENT_EVIDENCE_TEXT = "The indexed documents do not contain enough information to answer."


@dataclass(frozen=True)
class RecordedCall:
    tool: str
    request_id: str
    delegation_token: str
    payload: object


class FakeCoreClient:
    """Scripted Core facade. Pass conflicts, events or an error to shape its behavior."""

    def __init__(
        self,
        *,
        clock: Clock,
        conflicts: Sequence[Conflict] = (),
        events: Mapping[UUID, EventOut] | None = None,
        error: PortError | None = None,
    ) -> None:
        self._clock = clock
        self._conflicts = list(conflicts)
        self._events = dict(events or {})
        self._error = error
        self.calls: list[RecordedCall] = []
        self.actions: list[AgentAction] = []
        self._by_key: dict[str, tuple[AgentActionCreate, AgentAction]] = {}

    def _enter(self, tool: str, ctx: CallContext, payload: object) -> None:
        self.calls.append(RecordedCall(tool, ctx.request_id, ctx.delegation_token, payload))
        if self._error is not None:
            raise self._error

    async def check_event_conflicts(
        self, request: AgentConflictCheckRequest, ctx: CallContext
    ) -> ConflictCheckOut:
        self._enter("check_event_conflicts", ctx, request)
        return ConflictCheckOut(
            event_id=request.event_id,
            advisory=True,
            has_blocking=any(c.severity is Severity.BLOCKING for c in self._conflicts),
            conflicts=list(self._conflicts),
            checked_at=self._clock.now(),
        )

    async def get_event_details(self, event_id: UUID, ctx: CallContext) -> EventOut:
        self._enter("get_event_details", ctx, event_id)
        try:
            return self._events[event_id]
        except KeyError:
            raise NotFoundError(f"event {event_id} not found") from None

    async def file_agent_action(
        self, action: AgentActionCreate, ctx: CallContext, idempotency_key: str
    ) -> AgentAction:
        self._enter("file_agent_action", ctx, action)
        if idempotency_key in self._by_key:
            original_body, original_action = self._by_key[idempotency_key]
            if original_body != action:
                raise IdempotencyMismatchError(
                    f"key {idempotency_key!r} was used with another body"
                )
            return original_action
        filed = AgentAction(
            action_id=UUID(int=len(self.actions) + 1),
            type=action.type,
            summary=action.summary,
            status=AgentActionStatus.PROPOSED,
            target_event_id=action.target_event_id,
            expected_revision=action.expected_revision,
            payload=action.payload,
            conflicts=list(self._conflicts),
            created_at=self._clock.now(),
        )
        self.actions.append(filed)
        self._by_key[idempotency_key] = (action, filed)
        return filed


class FakeRagClient:
    """Keyword-overlap retrieval over a fixed corpus. Citations are copied from the index."""

    def __init__(self, corpus: Sequence[EvidenceChunk]) -> None:
        self._corpus = list(corpus)

    def _rank(self, query: str, top_k: int) -> list[EvidenceChunk]:
        terms = set(_WORD.findall(query.lower()))
        scored = []
        for chunk in self._corpus:
            overlap = len(terms & set(_WORD.findall(chunk.excerpt.lower())))
            if overlap:
                scored.append((overlap, chunk))
        scored.sort(key=lambda pair: (-pair[0], pair[1].evidence_id))
        return [chunk.model_copy(update={"score": float(score)}) for score, chunk in scored[:top_k]]

    async def search(self, request: SearchRequest, request_id: str) -> SearchResponse:
        return SearchResponse(
            query=request.query,
            candidates=self._rank(request.query, request.top_k),
            request_id=request_id,
        )

    async def answer(self, request: AnswerRequest, request_id: str) -> AnswerResponse:
        chunks = self._rank(request.query, request.top_k)
        if not chunks:
            return AnswerResponse(
                query=request.query,
                answer=INSUFFICIENT_EVIDENCE_TEXT,
                status="insufficient_evidence",
                citations=[],
                request_id=request_id,
            )
        return AnswerResponse(
            query=request.query,
            answer=f"According to the indexed documents: {chunks[0].excerpt}",
            status="grounded",
            citations=[
                Citation(
                    evidence_id=c.evidence_id,
                    document_id=c.document_id,
                    title=c.title,
                    source_url=c.source_url,
                    page_start=c.page_start,
                    page_end=c.page_end,
                    excerpt=c.excerpt,
                    document_version=c.document_version,
                )
                for c in chunks
            ],
            request_id=request_id,
        )
