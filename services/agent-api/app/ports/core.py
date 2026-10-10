"""The Agent's view of Core: a narrow, allowlisted facade (spine AD-10).

Every call carries the user's delegation token, forwarded unmodified. The Agent never decodes,
stores or logs it, and Core authorizes each call as that user.
"""

from dataclasses import dataclass, field
from typing import Protocol
from uuid import UUID

from app.schemas.core import (
    AgentAction,
    AgentActionCreate,
    AgentConflictCheckRequest,
    ConflictCheckOut,
    EventOut,
)


@dataclass(frozen=True)
class CallContext:
    request_id: str
    delegation_token: str = field(repr=False)


class CoreToolsPort(Protocol):
    async def check_event_conflicts(
        self, request: AgentConflictCheckRequest, ctx: CallContext
    ) -> ConflictCheckOut: ...

    async def get_event_details(self, event_id: UUID, ctx: CallContext) -> EventOut: ...

    async def file_agent_action(
        self, action: AgentActionCreate, ctx: CallContext, idempotency_key: str
    ) -> AgentAction: ...
