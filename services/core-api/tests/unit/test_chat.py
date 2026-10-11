"""One turn with the planning assistant (spine AD-3, AD-9, AD-10, AD-12).

Core mints a short delegation for the signed-in person, relays the turn, and then treats the
Agent's reply as untrusted: the proposals it mentions are re-loaded from Core's own database, so
the person only ever sees real proposals that are really theirs.
"""

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.clients.delegation import PyJwtDelegationService
from app.domain.authz import Actor
from app.domain.enums import AgentActionStatus, AgentActionType, AvailabilityState, Role
from app.domain.lifecycle import NotAuthorizedError
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.agent_actions import AgentActionService, NewAgentAction
from app.services.chat import MAX_PROPOSALS_PER_REPLY, ChatService
from app.services.conflict_checks import ConflictCheckService
from app.services.delegation import DelegationService
from app.services.errors import AgentOutputInvalidError, AgentUnavailableError
from app.services.ports import ChatClub, ChatContext, ChatTurn
from app.services.schedule_write import RequestContext, ScheduleWriteService
from tests.fakes import InMemoryDatabase, SequentialIds
from tests.unit.test_schedule_write import (
    CERTIFIED,
    CLUB_A,
    CLUB_B,
    HALL,
    LAB,
    NOW,
    ORGANIZER,
    OTHER_CLUB,
    STRANGER,
    at,
)

POLICY = Policy(campus_gap=timedelta(minutes=120))
KEY = "d" * 64
AGENT = Actor(user_id=ORGANIZER.user_id, memberships=ORGANIZER.memberships, via_agent=True)
TURN = ChatTurn(messages=(("user", "Plan a robotics demo day"),), event_id=None)


@dataclass
class FakeGateway:
    reply: dict[str, Any] = field(default_factory=lambda: {"message": "Here is a plan."})
    failure: Exception | None = None
    calls: list[tuple[ChatTurn, str, str]] = field(default_factory=list)

    def chat(self, turn: ChatTurn, *, delegation_token: str, request_id: str) -> dict[str, Any]:
        self.calls.append((turn, delegation_token, request_id))
        if self.failure is not None:
            raise self.failure
        return self.reply


@dataclass
class Rig:
    db: InMemoryDatabase
    chat: ChatService
    actions: AgentActionService
    gateway: FakeGateway


@pytest.fixture
def rig() -> Rig:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {
        HALL: AvailabilityState.UNKNOWN,
        LAB: AvailabilityState.UNKNOWN,
        CERTIFIED: AvailabilityState.CONFIRMED,
    }
    ids, clock = SequentialIds(), FixedClock(NOW)
    writes = ScheduleWriteService(db.uow, clock=clock, ids=ids, policy=POLICY)
    actions = AgentActionService(
        db.uow,
        checks=ConflictCheckService(db.uow, clock=clock, policy=POLICY),
        writes=writes,
        clock=clock,
        ids=ids,
    )
    gateway = FakeGateway()
    chat = ChatService(
        delegation=DelegationService(db.uow, PyJwtDelegationService(KEY)),
        gateway=gateway,
        actions=actions,
    )
    return Rig(db, chat, actions, gateway)


def ctx(actor: Actor, request_id: str = "req-chat-1") -> RequestContext:
    return RequestContext(actor=actor, request_id=request_id)


def propose(rig: Rig, agent: Actor = AGENT, club: UUID = CLUB_A, title: str = "Demo") -> UUID:
    command = NewAgentAction(
        type=AgentActionType.CREATE_EVENT_DRAFT,
        summary=f"Draft {title}",
        payload={
            "club_id": str(club),
            "title": title,
            "start_at": at(10).isoformat(),
            "end_at": at(12).isoformat(),
        },
    )
    return rig.actions.file(ctx(agent, request_id=f"agent-{uuid4()}"), command).action.id


def mentions(*ids: object, message: str = "I drafted something.") -> dict[str, Any]:
    forged = [{"action_id": str(i), "status": "EXECUTED", "summary": "forged"} for i in ids]
    return {"message": message, "proposed_actions": forged}


# ---- starting a turn -------------------------------------------------------------------


def test_the_turn_is_relayed_with_a_delegation_for_the_signed_in_person(rig: Rig) -> None:
    rig.chat.chat(ctx(ORGANIZER, "req-77"), TURN)

    [(turn, token, request_id)] = rig.gateway.calls
    assert turn == TURN
    assert request_id == "req-77"
    assert PyJwtDelegationService(KEY).verify(token) == ORGANIZER.user_id


def test_someone_with_no_role_cannot_start_a_turn_and_nothing_is_relayed(rig: Rig) -> None:
    with pytest.raises(NotAuthorizedError):
        rig.chat.chat(ctx(STRANGER), TURN)

    assert rig.gateway.calls == []


def test_a_delegated_principal_cannot_start_a_turn_of_its_own(rig: Rig) -> None:
    with pytest.raises(NotAuthorizedError):
        rig.chat.chat(ctx(AGENT), TURN)

    assert rig.gateway.calls == []


def test_the_reply_comes_back_without_the_agents_own_account_of_proposals(rig: Rig) -> None:
    rig.gateway.reply = {"trace": [], **mentions(uuid4(), message="Plan ready.")}

    reply = rig.chat.chat(ctx(ORGANIZER), TURN)

    assert reply.body["message"] == "Plan ready."
    assert "proposed_actions" not in reply.body
    assert reply.proposed_actions == ()


# ---- not trusting the reply ------------------------------------------------------------


def test_proposals_in_the_reply_are_replaced_by_the_ones_core_holds(rig: Rig) -> None:
    real = propose(rig)
    rig.actions.reject(ctx(ORGANIZER), real)
    rig.gateway.reply = mentions(real)  # the Agent claims it is EXECUTED

    reply = rig.chat.chat(ctx(ORGANIZER), TURN)

    [shown] = reply.proposed_actions
    assert shown.id == real
    assert shown.status is AgentActionStatus.REJECTED


def test_invented_and_foreign_proposals_are_dropped(rig: Rig) -> None:
    mine = propose(rig, title="Mine")
    theirs = propose(
        rig,
        agent=Actor(user_id=OTHER_CLUB.user_id, memberships=OTHER_CLUB.memberships, via_agent=True),
        club=CLUB_B,
        title="Theirs",
    )
    rig.gateway.reply = mentions(uuid4(), theirs, mine)

    reply = rig.chat.chat(ctx(ORGANIZER), TURN)

    assert [a.id for a in reply.proposed_actions] == [mine]


@pytest.mark.parametrize(
    "bad",
    [
        {"proposed_actions": "none"},
        {"proposed_actions": ""},
        {"proposed_actions": {}},
        {"proposed_actions": None},
        {"proposed_actions": ["a-string"]},
        {"proposed_actions": [{"no_id": 1}]},
        {"proposed_actions": [{"action_id": "not-a-uuid"}]},
        {"proposed_actions": [{"action_id": 7}]},
        {"proposed_actions": [{"action_id": str(uuid4())}] * (MAX_PROPOSALS_PER_REPLY + 1)},
    ],
    ids=[
        "not a list",
        "empty string",
        "empty object",
        "null",
        "element not an object",
        "no id",
        "bad uuid",
        "id not text",
        "too many",
    ],
)
def test_a_reply_whose_proposals_are_malformed_is_unusable(rig: Rig, bad: dict[str, Any]) -> None:
    rig.gateway.reply = {"message": "x", **bad}

    with pytest.raises(AgentOutputInvalidError):
        rig.chat.chat(ctx(ORGANIZER), TURN)


def test_a_reply_with_no_proposals_key_is_fine(rig: Rig) -> None:
    rig.gateway.reply = {"message": "Just an answer."}

    assert rig.chat.chat(ctx(ORGANIZER), TURN).proposed_actions == ()


@pytest.mark.parametrize(
    "bad_reply",
    [
        {},
        {"message": None},
        {"message": {"nested": "not text"}},
        {"message": "   "},
        {"message": "x" * 4001},
        {"message": "valid", "citations": [{"evidence_id": "only-one-field"}]},
        {"message": "valid", "trace": [{"tool": "check_event_conflicts"}]},
    ],
    ids=[
        "missing-message",
        "null-message",
        "object-message",
        "blank-message",
        "long-message",
        "bad-citation",
        "bad-trace",
    ],
)
def test_a_reply_with_invalid_visible_content_is_rejected(
    rig: Rig, bad_reply: dict[str, object]
) -> None:
    rig.gateway.reply = bad_reply

    with pytest.raises(AgentOutputInvalidError):
        rig.chat.chat(ctx(ORGANIZER), TURN)


# ---- failures --------------------------------------------------------------------------


def test_an_unreachable_assistant_is_reported_as_such(rig: Rig) -> None:
    rig.gateway.failure = AgentUnavailableError("connection refused")

    with pytest.raises(AgentUnavailableError):
        rig.chat.chat(ctx(ORGANIZER), TURN)


def test_a_turn_writes_nothing_by_itself(rig: Rig) -> None:
    commits = rig.db.commits

    rig.chat.chat(ctx(ORGANIZER), TURN)

    assert rig.db.commits == commits
    assert rig.db.state.events == {}
    assert rig.db.state.audit == []


# ---- the context the assistant is given --------------------------------------------------


@dataclass
class FakeContextSource:
    built: ChatContext
    asked_for: list[Actor] = field(default_factory=list)

    def build(self, actor: Actor) -> ChatContext:
        self.asked_for.append(actor)
        return self.built


def with_context(rig: Rig, source: FakeContextSource) -> ChatService:
    return ChatService(
        delegation=DelegationService(rig.db.uow, PyJwtDelegationService(KEY)),
        gateway=rig.gateway,
        actions=rig.actions,
        context=source,
    )


def test_the_turn_carries_the_context_core_built_for_that_person(rig: Rig) -> None:
    built = ChatContext(now=NOW, clubs=(ChatClub(CLUB_A, "Robotics", Role.ORGANIZER),), venues=())
    source = FakeContextSource(built)

    with_context(rig, source).chat(ctx(ORGANIZER), TURN)

    [(turn, _, _)] = rig.gateway.calls
    assert turn == ChatTurn(messages=TURN.messages, event_id=None, context=built)
    assert source.asked_for == [ORGANIZER]


def test_nothing_is_looked_up_for_someone_who_may_not_start_a_turn(rig: Rig) -> None:
    source = FakeContextSource(ChatContext(now=NOW, clubs=(), venues=()))

    with pytest.raises(NotAuthorizedError):
        with_context(rig, source).chat(ctx(STRANGER), TURN)

    assert source.asked_for == []
    assert rig.gateway.calls == []
