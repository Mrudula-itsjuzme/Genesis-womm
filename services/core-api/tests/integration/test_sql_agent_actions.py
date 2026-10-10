"""The PostgreSQL store behind agent proposals (spine AD-9, AD-20)."""

from collections.abc import Iterator
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.domain.enums import (
    AgentActionStatus,
    AgentActionType,
    ConflictConstraint,
    ConflictType,
    Severity,
)
from app.domain.intervals import Interval
from app.domain.scheduling import Conflict
from app.repositories.agent_actions import SqlAgentActionStore
from app.services.ports import AgentActionRecord
from tests.conftest import upgrade
from tests.integration.support import NOW, START, make_club, make_event, make_user

pytestmark = pytest.mark.integration

PROPOSED = AgentActionStatus.PROPOSED
EXECUTED = AgentActionStatus.EXECUTED


@pytest.fixture
def session(engine: Engine) -> Iterator[Session]:
    upgrade(engine)
    with Session(engine, expire_on_commit=False) as session:
        yield session
        session.rollback()


class World:
    def __init__(self, session: Session) -> None:
        conn = session.connection()
        self.club = make_club(conn)
        self.user = make_user(conn)
        self.other = make_user(conn)
        self.event = make_event(conn, self.club, self.user)
        self.store = SqlAgentActionStore(session)

    def action(self, **changes: object) -> AgentActionRecord:
        base = AgentActionRecord(
            id=uuid4(),
            type=AgentActionType.CREATE_EVENT_DRAFT,
            status=PROPOSED,
            summary="Draft a robotics demo day",
            requested_by=self.user,
            club_id=self.club,
            target_event_id=None,
            expected_revision=None,
            payload={"title": "Demo Day", "club_id": str(self.club)},
            conflicts=(),
            decided_by=None,
            decided_at=None,
            result_entity_type=None,
            result_entity_id=None,
            created_at=NOW,
            updated_at=NOW,
        )
        return base.but(**changes)


@pytest.fixture
def world(session: Session) -> World:
    return World(session)


def a_conflict(other: UUID) -> Conflict:
    return Conflict(
        type=ConflictType.TENTATIVE_OVERLAP,
        severity=Severity.WARNING,
        constraint=ConflictConstraint.VENUE_OVERLAP,
        event_ids=(uuid4(), other),
        window=Interval(START, START + timedelta(hours=1)),
        message="Both events want the same venue.",
        override_required=False,
    )


def test_a_proposal_round_trips_with_its_payload_and_dry_run(world: World) -> None:
    saved = world.action(
        payload={"title": "Demo Day", "nested": {"tags": ["a", "b"]}, "n": 3},
        conflicts=(a_conflict(world.event),),
        target_event_id=world.event,
        expected_revision=2,
    )

    world.store.add(saved)

    assert world.store.get(saved.id) == saved


def test_an_unknown_proposal_is_none(world: World) -> None:
    assert world.store.get(uuid4()) is None


def test_a_person_lists_only_their_own_proposals_newest_first(world: World) -> None:
    older = world.action(created_at=NOW)
    newer = world.action(created_at=NOW + timedelta(minutes=5))
    someone_elses = world.action(requested_by=world.other)
    for record in (older, newer, someone_elses):
        world.store.add(record)

    listed, total = world.store.list_for(world.user, status=None, event_id=None, limit=50, offset=0)

    assert [r.id for r in listed] == [newer.id, older.id]
    assert total == 2


def test_listing_filters_by_status_and_event_and_pages(world: World) -> None:
    proposed = world.action(target_event_id=world.event, created_at=NOW)
    world.store.add(proposed)
    world.store.add(world.action(created_at=NOW + timedelta(minutes=1)))
    done = world.action(created_at=NOW + timedelta(minutes=2))
    world.store.add(done)
    world.store.decide(
        done.id,
        status=EXECUTED,
        decided_by=world.user,
        decided_at=NOW,
        result_entity_type="event",
        result_entity_id=world.event,
    )

    executed, _ = world.store.list_for(
        world.user, status=EXECUTED, event_id=None, limit=50, offset=0
    )
    for_event, _ = world.store.list_for(
        world.user, status=None, event_id=world.event, limit=50, offset=0
    )

    assert [r.id for r in executed] == [done.id]
    assert [r.id for r in for_event] == [proposed.id]
    page, total = world.store.list_for(world.user, status=None, event_id=None, limit=1, offset=1)
    assert total == 3
    assert len(page) == 1


def test_deciding_records_who_when_and_what_was_created(world: World) -> None:
    saved = world.action()
    world.store.add(saved)

    won = world.store.decide(
        saved.id,
        status=EXECUTED,
        decided_by=world.user,
        decided_at=NOW + timedelta(minutes=3),
        result_entity_type="event",
        result_entity_id=world.event,
    )

    assert won is True
    stored = world.store.get(saved.id)
    assert stored is not None
    assert (stored.status, stored.decided_by, stored.result_entity_id) == (
        EXECUTED,
        world.user,
        world.event,
    )
    assert stored.decided_at == NOW + timedelta(minutes=3)
    assert stored.updated_at == NOW + timedelta(minutes=3)


def test_a_proposal_can_only_be_decided_once(world: World) -> None:
    saved = world.action()
    world.store.add(saved)

    first = world.store.decide(
        saved.id,
        status=AgentActionStatus.REJECTED,
        decided_by=world.user,
        decided_at=NOW,
        result_entity_type=None,
        result_entity_id=None,
    )
    second = world.store.decide(
        saved.id,
        status=EXECUTED,
        decided_by=world.other,
        decided_at=NOW + timedelta(minutes=1),
        result_entity_type="event",
        result_entity_id=world.event,
    )

    assert (first, second) == (True, False)
    stored = world.store.get(saved.id)
    assert stored is not None
    assert (stored.status, stored.decided_by) == (AgentActionStatus.REJECTED, world.user)


def test_deciding_an_unknown_proposal_wins_nothing(world: World) -> None:
    assert not world.store.decide(
        uuid4(),
        status=AgentActionStatus.REJECTED,
        decided_by=world.user,
        decided_at=NOW,
        result_entity_type=None,
        result_entity_id=None,
    )


def test_two_sessions_deciding_at_once_cannot_both_win(engine: Engine) -> None:
    upgrade(engine)
    with Session(engine, expire_on_commit=False) as setup:
        w = World(setup)
        saved = w.action()
        w.store.add(saved)
        setup.commit()
    outcomes = []
    for decider in (w.user, w.other):
        with Session(engine, expire_on_commit=False) as session:
            outcomes.append(
                SqlAgentActionStore(session).decide(
                    saved.id,
                    status=AgentActionStatus.REJECTED,
                    decided_by=decider,
                    decided_at=NOW,
                    result_entity_type=None,
                    result_entity_id=None,
                )
            )
            session.commit()
    assert outcomes == [True, False]
