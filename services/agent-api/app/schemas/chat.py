"""The Agent's own endpoints. Core sends a turn; the Agent returns a reply plus proposals."""

from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.core import AgentAction
from app.schemas.enums import AccessLevel, ToolOutcome
from app.schemas.text import MessageText


class ChatMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: MessageText


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


class ChatResponse(BaseModel):
    message: str = Field(description="Describes proposals as proposed, never as done.")
    clarifying_question: str | None = Field(
        default=None, description="Set when a required field (date, time, venue) is missing."
    )
    citations: list[Citation] = Field(default_factory=list)
    proposed_actions: list[AgentAction] = Field(default_factory=list)
    trace: list[ToolTraceEntry] = Field(default_factory=list)
    request_id: str


class AgentTurnRequest(BaseModel):
    """Core to Agent. `access_level` is set by Core from the user's role, never by the model."""

    model_config = ConfigDict(extra="forbid")

    messages: list[ChatMessage] = Field(min_length=1, max_length=20)
    event_id: UUID | None = Field(default=None, description="Event the conversation is about.")
    access_level: AccessLevel = AccessLevel.CAMPUS_PUBLIC


class PlanEventRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    request: MessageText = Field(description="The organizer's plan in their own words.")
    club_id: UUID | None = None
    access_level: AccessLevel = AccessLevel.CAMPUS_PUBLIC


class AnalyzeChangeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    change_description: MessageText
    access_level: AccessLevel = AccessLevel.CAMPUS_PUBLIC
