"""Bounded tool-calling orchestration engine (spine AD-11).

Enforces:
- Explicit tool allowlist (AD-10): unknown tools are rejected, never called.
- Max tool-call count per turn.
- Per-tool timeout.
- Tool output size cap.
- Failed tools are recorded as ERROR/TIMEOUT/DENIED in the trace; never described as success.
- Delegation token is forwarded to Core unmodified; the engine never decodes it.
"""

from __future__ import annotations

import asyncio
import json
import re
from dataclasses import dataclass
from typing import Any
from uuid import UUID

import structlog

from app.orchestration.context import CAMPUS_OFFSET, flat_line
from app.orchestration.plain import plain_text
from app.ports.clock import Clock
from app.ports.core import CallContext, CoreToolsPort
from app.ports.errors import (
    ContractViolationError,
    DeniedError,
    DependencyUnavailableError,
    NotFoundError,
    StaleRevisionError,
)
from app.ports.llm import LlmPort, LlmResponse, ToolCall
from app.ports.rag import RagPort
from app.schemas.chat import (
    ChatMessage,
    ChatResponse,
    Citation,
    ToolTraceEntry,
)
from app.schemas.core import (
    AgentAction,
    AgentActionCreate,
    AgentConflictCheckRequest,
    Conflict,
)
from app.schemas.enums import AgentActionType, Severity, ToolOutcome
from app.schemas.rag import AnswerRequest
from app.tools.allowlist import ALLOWED_TOOL_NAMES, TOOL_SCHEMAS

log = structlog.get_logger("orchestration.engine")


class OrchestrationEngine:
    """Stateless, bounded LLM-tool loop for one conversation turn."""

    def __init__(
        self,
        llm: LlmPort,
        core: CoreToolsPort,
        rag: RagPort,
        clock: Clock,
        *,
        max_tool_calls: int = 6,
        tool_timeout_s: float = 5.0,
        max_tool_bytes: int = 16_384,
        turn_deadline_s: float = 20.0,
    ) -> None:
        self._llm = llm
        self._core = core
        self._rag = rag
        self._clock = clock
        self._max_tool_calls = max_tool_calls
        self._tool_timeout_s = tool_timeout_s
        self._max_tool_bytes = max_tool_bytes
        self._turn_deadline_s = turn_deadline_s

    async def run(
        self,
        messages: list[ChatMessage],
        ctx: CallContext,
        system_prompt: str,
    ) -> ChatResponse:
        """Run bounded LLM-tool loop. Returns a validated ChatResponse.

        The whole turn has a deadline shorter than Core's wait, so a slow model is stopped here
        and reported as unavailable instead of being abandoned while it keeps running.
        """
        try:
            async with asyncio.timeout(self._turn_deadline_s):
                return await self._run(messages, ctx, system_prompt)
        except TimeoutError as error:
            log.warning("turn_deadline_exceeded", request_id=ctx.request_id)
            raise DependencyUnavailableError("assistant", "taking too long") from error

    async def _run(
        self,
        messages: list[ChatMessage],
        ctx: CallContext,
        system_prompt: str,
    ) -> ChatResponse:
        mutable = [_defang(message) for message in messages]
        typed = [m.content for m in messages if m.role == "user"]
        turn = _TurnState(go_ahead=bool(typed) and _GO_AHEAD.search(typed[-1]) is not None)
        trace: list[ToolTraceEntry] = []
        citations: list[Citation] = []
        proposed_actions: list[AgentAction] = []
        tool_calls_used = 0

        while True:
            response: LlmResponse = await self._llm.complete(mutable, TOOL_SCHEMAS, system_prompt)

            # No tool calls → done
            if not response.tool_calls:
                text = plain_text(response.text or "")
                return ChatResponse(
                    message=text,
                    clarifying_question=self._extract_clarifying(text),
                    citations=citations,
                    proposed_actions=proposed_actions,
                    trace=trace,
                    request_id=ctx.request_id,
                )

            # Guard: enforce max tool calls
            if tool_calls_used >= self._max_tool_calls:
                log.warning("max_tool_calls_reached", request_id=ctx.request_id)
                return ChatResponse(
                    message=(
                        "I've reached the maximum number of tool lookups for this turn. "
                        "Please refine your request and try again."
                    ),
                    citations=citations,
                    proposed_actions=proposed_actions,
                    trace=trace,
                    request_id=ctx.request_id,
                )

            # Append the assistant turn with tool calls
            assistant_content = (
                response.text if (response.text and response.text.strip()) else "Calling tools..."
            )
            mutable.append(ChatMessage(role="assistant", content=assistant_content))

            # Dispatch each tool call
            for tc in response.tool_calls:
                tool_calls_used += 1
                result_text, _outcome, new_citations, action = await self._dispatch(
                    tc, ctx, trace, turn
                )
                citations.extend(new_citations)
                if action is not None:
                    proposed_actions.append(action)
                # Append tool result as user message (standard ReAct pattern)
                mutable.append(ChatMessage(role="user", content=f"[Tool {tc.name}]: {result_text}"))

    # ------------------------------------------------------------------
    # Tool dispatch
    # ------------------------------------------------------------------

    async def _dispatch(
        self,
        tc: ToolCall,
        ctx: CallContext,
        trace: list[ToolTraceEntry],
        turn: _TurnState,
    ) -> tuple[str, ToolOutcome, list[Citation], AgentAction | None]:
        """Dispatch one tool call; always appends a trace entry."""
        start_instant = self._clock.now()

        # Allowlist guard
        if tc.name not in ALLOWED_TOOL_NAMES:
            outcome = ToolOutcome.INVALID_ARGUMENTS
            latency = int((self._clock.now() - start_instant).total_seconds() * 1000)
            trace.append(
                ToolTraceEntry(
                    tool=tc.name,
                    args={},
                    outcome=outcome,
                    latency_ms=latency,
                    request_id=ctx.request_id,
                )
            )
            return f"Error: tool '{tc.name}' is not on the allowlist.", outcome, [], None

        try:
            result, new_citations, action = await asyncio.wait_for(
                self._call_tool(tc, ctx, turn),
                timeout=self._tool_timeout_s,
            )
            # Enforce output size cap
            if len(result) > self._max_tool_bytes:
                result = result[: self._max_tool_bytes] + "…[truncated]"
            outcome = ToolOutcome.OK
        except TimeoutError:
            result = f"Error: {tc.name} timed out after {self._tool_timeout_s}s."
            new_citations = []
            action = None
            outcome = ToolOutcome.TIMEOUT
        except DeniedError as e:
            result = f"Error: permission denied — {e}"
            new_citations = []
            action = None
            outcome = ToolOutcome.DENIED
        except (
            DependencyUnavailableError,
            NotFoundError,
            StaleRevisionError,
            ContractViolationError,
        ) as e:
            result = f"Error: {tc.name} failed — {e}"
            new_citations = []
            action = None
            outcome = ToolOutcome.ERROR

        latency = int((self._clock.now() - start_instant).total_seconds() * 1000)
        # Sanitise args: never log token-bearing or secrets fields
        safe_args = {k: v for k, v in tc.arguments.items() if k != "delegation_token"}
        trace.append(
            ToolTraceEntry(
                tool=tc.name,
                args=safe_args,
                outcome=outcome,
                latency_ms=latency,
                request_id=ctx.request_id,
            )
        )
        return result, outcome, new_citations, action

    async def _call_tool(
        self, tc: ToolCall, ctx: CallContext, turn: _TurnState
    ) -> tuple[str, list[Citation], AgentAction | None]:
        args = tc.arguments

        if tc.name == "check_event_conflicts":
            result, citations = await self._check_conflicts(args, ctx, turn)
            return result, citations, None

        if tc.name == "get_event_details":
            result, citations = await self._get_event(args, ctx)
            return result, citations, None

        if tc.name == "search_campus_policy":
            result, citations = await self._search_policy(args, ctx)
            return result, citations, None

        if tc.name == "file_event_draft_proposal":
            return await self._file_draft(args, ctx, turn)

        if tc.name == "file_change_request_proposal":
            return await self._file_change(args, ctx)

        # Should never reach here due to allowlist guard above
        raise ValueError(f"unhandled tool: {tc.name}")

    # ------------------------------------------------------------------
    # Individual tool implementations
    # ------------------------------------------------------------------

    async def _check_conflicts(
        self, args: dict[str, Any], ctx: CallContext, turn: _TurnState
    ) -> tuple[str, list[Citation]]:
        request = AgentConflictCheckRequest(
            event_id=_opt_uuid(args.get("event_id")),
            club_id=_opt_uuid(args.get("club_id")),
            start_at=args.get("start_at"),
            end_at=args.get("end_at"),
            resource_id=_opt_uuid(args.get("resource_id")),
        )
        result = await self._core.check_event_conflicts(request, ctx)
        turn.checked = True
        turn.flagged = any(
            c.severity in (Severity.WARNING, Severity.BLOCKING) for c in result.conflicts
        )
        if not result.conflicts:
            return "No conflicts detected. The slot appears available (advisory check only).", []
        named = await self._name_other_events(result.conflicts, ctx)
        lines = [f"Found {len(result.conflicts)} conflict(s):"]
        for c in result.conflicts:
            other = named.get(c.event_ids[1]) if len(c.event_ids) > 1 else None
            lines.append(
                f"  - [{c.severity.upper()}] {c.type}: {c.message} "
                f"(override_required={c.override_required})" + (f" with {other}" if other else "")
            )
        if result.has_blocking:
            lines.append(
                "At least one conflict is BLOCKING. "
                "An authorized admin override is required to proceed."
            )
        return "\n".join(lines), []

    async def _name_other_events(
        self, conflicts: list[Conflict], ctx: CallContext
    ) -> dict[UUID, str]:
        """Title, status and campus time of the other event in each conflict.

        Core lists the event being checked first, so the other event is always the second id. Read
        through the same facade as any other tool, so Core's visibility rules decide what may be
        named. A lookup that fails leaves the conflict itself untouched.
        """
        wanted: list[UUID] = []
        for c in conflicts:
            other = c.event_ids[1] if len(c.event_ids) > 1 else None
            if other is not None and other not in wanted:
                wanted.append(other)
        named: dict[UUID, str] = {}
        for event_id in wanted[:_MAX_NAMED_EVENTS]:
            try:
                event = await asyncio.wait_for(
                    self._core.get_event_details(event_id, ctx), timeout=self._tool_timeout_s
                )
            except (
                DeniedError,
                NotFoundError,
                DependencyUnavailableError,
                ContractViolationError,
                TimeoutError,
            ):
                continue
            start = event.start_at.astimezone(CAMPUS_OFFSET)
            end = event.end_at.astimezone(CAMPUS_OFFSET)
            named[event_id] = (
                f'"{flat_line(event.title)}" ({event.status}, '
                f"{start:%a %d %b %H:%M}-{end:%H:%M} IST)"
            )
        return named

    async def _get_event(
        self, args: dict[str, Any], ctx: CallContext
    ) -> tuple[str, list[Citation]]:
        event_id = UUID(str(args["event_id"]))
        event = await self._core.get_event_details(event_id, ctx)
        data = {
            "id": str(event.id),
            "title": event.title,
            "status": event.status,
            "start_at": str(event.start_at),
            "end_at": str(event.end_at),
            "venue_availability": event.venue_availability,
            "revision": event.revision,
            "description": event.description,
        }
        return json.dumps(data), []

    async def _search_policy(
        self, args: dict[str, Any], ctx: CallContext
    ) -> tuple[str, list[Citation]]:
        query = str(args["query"])
        top_k = min(int(args.get("top_k", 4)), 10)
        response = await self._rag.answer(
            AnswerRequest(query=query, top_k=top_k),
            request_id=ctx.request_id,
        )
        if response.status == "insufficient_evidence":
            return (
                "The OSA handbook does not contain enough information to answer this question. "
                "Do not invent a policy answer.",
                [],
            )
        return response.answer, list(response.citations)

    async def _file_draft(
        self, args: dict[str, Any], ctx: CallContext, turn: _TurnState
    ) -> tuple[str, list[Citation], AgentAction]:
        if turn.flagged and not turn.go_ahead:
            raise DeniedError(
                "the conflict check found warnings or blocking conflicts and the person has not "
                "told you to go ahead. Explain the conflicts and ask whether to propose it anyway "
                "or to try another time or venue."
            )
        if not turn.checked and not turn.go_ahead:
            raise DeniedError("check the slot with check_event_conflicts before filing a proposal.")
        action_create = AgentActionCreate(
            type=AgentActionType.CREATE_EVENT_DRAFT,
            summary=str(args["summary"]),
            payload=dict(args.get("payload") or {}),
        )
        idempotency_key = f"{ctx.request_id}:draft"
        action = await self._core.file_agent_action(action_create, ctx, idempotency_key)
        return (
            f"Draft proposal filed (action_id={action.action_id}, status={action.status}). "
            "Nothing is booked — a human must confirm this proposal.",
            [],
            action,
        )

    async def _file_change(
        self, args: dict[str, Any], ctx: CallContext
    ) -> tuple[str, list[Citation], AgentAction]:
        action_create = AgentActionCreate(
            type=AgentActionType.REQUEST_EVENT_CHANGE,
            summary=str(args["summary"]),
            target_event_id=UUID(str(args["event_id"])),
            expected_revision=int(args["expected_revision"]),
            payload=dict(args.get("payload") or {}),
        )
        idempotency_key = f"{ctx.request_id}:change:{args.get('event_id')}"
        action = await self._core.file_agent_action(action_create, ctx, idempotency_key)
        return (
            f"Change proposal filed (action_id={action.action_id}, status={action.status}). "
            "Nothing changes — a human must confirm this proposal.",
            [],
            action,
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_clarifying(text: str) -> str | None:
        """Heuristic: if the reply is entirely a question, surface it as clarifying_question."""
        stripped = text.strip()
        if stripped.endswith("?") and len(stripped.splitlines()) <= 3:
            return stripped
        return None


# The person's own words that mean "file it despite what you found". Typed by the person in their
# latest message; nothing the model or a tool says can set it.
_GO_AHEAD = re.compile(r"\b(go ahead|proceed|anyway|file it|propose it|do it|yes)\b", re.I)


@dataclass
class _TurnState:
    """What this turn has established, so filing can be refused in code and not just in a prompt."""

    go_ahead: bool
    checked: bool = False
    flagged: bool = False  # the latest check found a warning or a block


# At most this many other events are named per check; the rest stay listed without detail.
_MAX_NAMED_EVENTS = 3

# Tool results reach the model as lines that begin "[Tool name]". A caller's own messages may
# not begin that way, or a person could write a result the system never produced.
_FORGED_TOOL_RESULT = re.compile(r"(?m)^(\s*)\[Tool\b")


def _defang(message: ChatMessage) -> ChatMessage:
    content = _FORGED_TOOL_RESULT.sub(r"\1[quoted Tool", message.content)
    return (
        message if content == message.content else message.model_copy(update={"content": content})
    )


def _opt_uuid(value: Any) -> UUID | None:
    if value is None:
        return None
    try:
        return UUID(str(value))
    except (ValueError, AttributeError):
        return None
