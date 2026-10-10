"""Wire schemas for the Agent boundary: chat, proposals and the internal tool facade."""

from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.domain.enums import AgentActionStatus, AgentActionType, ToolOutcome
from app.schemas.common import CampusDatetime
from app.schemas.events import Conflict

MessageText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=4000)
]
Summary = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=300)]


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: MessageText


class ChatRequest(BaseModel):
    """The caller supplies bounded history. The Agent is stateless between turns."""

    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    event_id: UUID | None = Field(default=None, description="Event the conversation is about.")


class Citation(BaseModel):
    """Copied verbatim from the RAG index. The model never writes these fields."""

    evidence_id: str
    document_id: str
    title: str
    source_url: str
    page_start: int
    page_end: int
    excerpt: str
    document_version: str


class ToolTraceEntry(BaseModel):
    tool: str
    args: dict[str, Any] = Field(description="Sanitized arguments; never secrets or private data.")
    outcome: ToolOutcome
    latency_ms: int
    request_id: str


class AgentAction(BaseModel):
    """A proposal. Nothing has happened until a human confirms it."""

    action_id: UUID
    type: AgentActionType
    summary: str
    requires_human_review: Literal[True] = True
    status: AgentActionStatus
    target_event_id: UUID | None
    expected_revision: int | None = Field(
        default=None, description="Event revision seen when the Agent filed the proposal."
    )
    payload: dict[str, Any] = Field(description="Opaque to clients; validated by Core per type.")
    conflicts: list[Conflict] = Field(
        default_factory=list, description="Dry-run result stored when the proposal was filed."
    )
    created_at: CampusDatetime


class ChatResponse(BaseModel):
    message: str = Field(description="Describes proposals as proposed, never as done.")
    clarifying_question: str | None = Field(
        default=None, description="Set when a required field (date, time, venue) is missing."
    )
    citations: list[Citation] = Field(default_factory=list)
    proposed_actions: list[AgentAction] = Field(default_factory=list)
    trace: list[ToolTraceEntry] = Field(default_factory=list)
    request_id: str


class AgentActionCreate(BaseModel):
    """Filed by the Agent through the internal facade. It can only create a PROPOSED action."""

    model_config = ConfigDict(extra="forbid")

    type: AgentActionType
    summary: Summary
    target_event_id: UUID | None = None
    expected_revision: int | None = Field(default=None, ge=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class AgentActionList(BaseModel):
    items: list[AgentAction]
    limit: int
    offset: int
    total: int


class AgentActionConfirmOut(BaseModel):
    action: AgentAction
    created_entity_type: str | None = Field(
        default=None, description="What confirming created, for example 'event' or 'commitment'."
    )
    created_entity_id: UUID | None = None


class AgentConflictCheckRequest(BaseModel):
    """Facade input: check a saved event, or a candidate that is not saved yet."""

    model_config = ConfigDict(extra="forbid")

    event_id: UUID | None = None
    club_id: UUID | None = Field(default=None, description="Required for an unsaved candidate.")
    start_at: CampusDatetime | None = None
    end_at: CampusDatetime | None = None
    resource_id: UUID | None = None
