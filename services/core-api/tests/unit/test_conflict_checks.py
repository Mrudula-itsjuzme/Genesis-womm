from datetime import timedelta

import pytest

from app.domain.enums import AvailabilityState, EventStatus, Severity
from app.domain.lifecycle import NotAuthorizedError
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.conflict_checks import ConflictCheckService
from app.services.schedule_write import ScheduleWriteService
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
    World,
    confirmed,
    draft,
)


@pytest.fixture
def world() -> World:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {
        HALL: AvailabilityState.UNKNOWN,
        LAB: AvailabilityState.UNKNOWN,
        CERTIFIED: AvailabilityState.CONFIRMED,
    }
    ids = SequentialIds()
    return World(
        db,
        ScheduleWriteService(
            db.uow,
            clock=FixedClock(NOW),
            ids=ids,
            policy=Policy(campus_gap=timedelta(minutes=120)),
        ),
        ids,
    )


def test_conflict_check_previews_confirmation_without_writing(world: World) -> None:
    candidate = draft(world, venue=CERTIFIED)
    _ = confirmed(
        world,
        actor=OTHER_CLUB,
        club=CLUB_B,
        start=(11, 0),
        end=(13, 0),
        venue=CERTIFIED,
    )
    service = ConflictCheckService(
        world.db.uow,
        clock=FixedClock(NOW),
        policy=Policy(campus_gap=timedelta(minutes=120)),
    )
    commits_before = world.db.commits
    log_before = len(world.db.log)

    result = service.check(ORGANIZER, candidate.event.id, as_status=EventStatus.CONFIRMED)

    assert result.event.id == candidate.event.id
    assert result.checked_at == NOW
    assert any(conflict.severity is Severity.BLOCKING for conflict in result.conflicts)
    assert world.db.commits == commits_before
    assert "lock" not in world.db.log[log_before:]


def test_conflict_check_distinguishes_an_explicit_null_resource(world: World) -> None:
    candidate = draft(world, venue=CERTIFIED)
    service = ConflictCheckService(
        world.db.uow,
        clock=FixedClock(NOW),
        policy=Policy(campus_gap=timedelta(minutes=120)),
    )

    result = service.check(
        ORGANIZER,
        candidate.event.id,
        resource_id=None,
        resource_id_was_provided=True,
    )

    assert result.event.resource_id is None
    assert result.availability is AvailabilityState.UNKNOWN


def test_conflict_check_requires_organizer_access_to_the_event_club(world: World) -> None:
    candidate = draft(world)
    service = ConflictCheckService(
        world.db.uow,
        clock=FixedClock(NOW),
        policy=Policy(campus_gap=timedelta(minutes=120)),
    )

    with pytest.raises(NotAuthorizedError):
        service.check(OTHER_CLUB, candidate.event.id)
