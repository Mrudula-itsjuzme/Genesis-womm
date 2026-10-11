"""One conversational turn with the planning assistant (spine AD-3, AD-9, AD-10, AD-12).

Core mints a short delegation for the signed-in person and relays the turn. The Agent's reply is
untrusted input: it may claim proposals that do not exist, belong to someone else, or have
already been decided. So Core ignores what the reply says about them and re-loads each mentioned
proposal from its own database, keeping only the signed-in person's.
"""

from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, ValidationError

from app.domain.enums import ToolOutcome
from app.services.agent_actions import AgentActionService
from app.services.delegation import DelegationService
from app.services.errors import AgentOutputInvalidError
from app.services.ports import AgentActionRecord, AgentGateway, ChatTurn
from app.services.schedule_write import RequestContext

# A turn is bounded to a handful of tool calls, so a reply naming more proposals than this is
# not something the Agent produced honestly.
MAX_PROPOSALS_PER_REPLY = 20
_MESSAGE_TEXT = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]


class _Citation(BaseModel):
    evidence_id: str
    document_id: str
    title: str
    source_url: str
    page_start: int
    page_end: int
    excerpt: str
    document_version: str


class _ToolTraceEntry(BaseModel):
    tool: str
    args: dict[str, Any]
    outcome: ToolOutcome
    latency_ms: int
    request_id: str


class _ProposedActionReference(BaseModel):
    """Only the action id is trusted as a reference to Core's own record."""

    model_config = ConfigDict(extra="ignore")

    action_id: UUID


class _AgentReplyPayload(BaseModel):
    """The subset of an Agent response that is visible to a browser client."""

    model_config = ConfigDict(extra="ignore")

    message: _MESSAGE_TEXT
    clarifying_question: str | None = None
    citations: list[_Citation] = Field(default_factory=list)
    proposed_actions: list[_ProposedActionReference] = Field(default_factory=list)
    trace: list[_ToolTraceEntry] = Field(default_factory=list)


@dataclass(frozen=True)
class AgentReply:
    body: dict[str, Any]  # the Agent's reply minus its own account of proposals
    proposed_actions: tuple[AgentActionRecord, ...]  # Core's copies of the real ones


class ChatService:
    def __init__(
        self,
        *,
        delegation: DelegationService,
        gateway: AgentGateway,
        actions: AgentActionService,
    ) -> None:
        self._delegation = delegation
        self._gateway = gateway
        self._actions = actions

    def chat(self, ctx: RequestContext, turn: ChatTurn) -> AgentReply:
        issued = self._delegation.issue(ctx.actor, ctx.request_id)
        reply = self._gateway.chat(turn, delegation_token=issued.token, request_id=ctx.request_id)
        try:
            payload = _AgentReplyPayload.model_validate(reply)
        except ValidationError as error:
            raise AgentOutputInvalidError(
                "agent reply did not match the expected schema"
            ) from error
        mentioned = _mentioned_ids(payload.model_dump(mode="json")["proposed_actions"])
        body = payload.model_dump(mode="json", exclude={"proposed_actions"})
        return AgentReply(body, tuple(self._actions.owned_by(ctx.actor, mentioned)))


def _mentioned_ids(proposed: object) -> list[UUID]:
    if not isinstance(proposed, list) or len(proposed) > MAX_PROPOSALS_PER_REPLY:
        raise AgentOutputInvalidError("proposed_actions must be a short list")
    ids: list[UUID] = []
    for item in proposed:
        raw = item.get("action_id") if isinstance(item, dict) else None
        if not isinstance(raw, str):
            raise AgentOutputInvalidError("a proposed action named no id")
        try:
            ids.append(UUID(raw))
        except ValueError as error:
            raise AgentOutputInvalidError("a proposed action named a bad id") from error
    return ids
