from datetime import timedelta
from uuid import UUID

import pytest

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, ConflictType, EventStatus, Severity
from app.domain.lifecycle import NotAuthorizedError
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.conflict_checks import (
    UNSAVED_CANDIDATE_ID,
    ConflictCheckResult,
    ConflictCheckService,
)
from app.services.errors import InvalidRequestError, NotFoundError
from app.services.schedule_write import ScheduleWriteService
from tests.fakes import InMemoryDatabase, SequentialIds
from tests.unit.test_schedule_write import (
    CAMPUS,
    CERTIFIED,
    CLUB_A,
    CLUB_B,
    HALL,
    LAB,
    NOW,
    ORGANIZER,
    OTHER_CLUB,
    STRANGER,
    World,
    at,
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


# ---- a candidate that is not saved yet (what the Agent asks about) ---------------------


def checker(world: World) -> ConflictCheckService:
    return ConflictCheckService(
        world.db.uow,
        clock=FixedClock(NOW),
        policy=Policy(campus_gap=timedelta(minutes=120)),
    )


def unsaved(
    world: World,
    actor: Actor = ORGANIZER,
    *,
    club: UUID = CLUB_A,
    start: tuple[int, int] = (11, 0),
    end: tuple[int, int] = (13, 0),
    venue: UUID | None = CERTIFIED,
    status: EventStatus | None = None,
) -> ConflictCheckResult:
    return checker(world).check_candidate(
        actor,
        club_id=club,
        start_at=at(*start),
        end_at=at(*end),
        resource_id=venue,
        as_status=status,
    )


def test_an_unsaved_draft_against_a_confirmed_event_warns_and_never_blocks(world: World) -> None:
    confirmed(world, actor=OTHER_CLUB, club=CLUB_B, venue=CERTIFIED)

    result = unsaved(world)

    assert not result.saved
    assert result.event.id == UNSAVED_CANDIDATE_ID
    assert result.event.status is EventStatus.DRAFT
    assert {c.severity for c in result.conflicts} == {Severity.WARNING}
    assert all(c.event_ids[0] == UNSAVED_CANDIDATE_ID for c in result.conflicts)


def test_an_unsaved_candidate_previews_a_confirmation_when_asked(world: World) -> None:
    confirmed(world, actor=OTHER_CLUB, club=CLUB_B, venue=CERTIFIED)

    result = unsaved(world, status=EventStatus.CONFIRMED)

    blocking = [c for c in result.conflicts if c.severity is Severity.BLOCKING]
    assert {c.type for c in blocking} == {
        ConflictType.VENUE_OVERLAP,
        ConflictType.CAMPUS_GAP_VIOLATION,
    }


def test_an_unsaved_candidate_at_an_unverified_venue_reports_unknown_availability(
    world: World,
) -> None:
    result = unsaved(world, venue=HALL)

    assert result.availability is AvailabilityState.UNKNOWN
    assert [c.type for c in result.conflicts] == [ConflictType.UNKNOWN_AVAILABILITY]


def test_a_candidate_check_writes_nothing_and_takes_no_lock(world: World) -> None:
    commits, log = world.db.commits, len(world.db.log)

    unsaved(world)

    assert world.db.commits == commits
    assert "lock" not in world.db.log[log:]
    assert "write:event" not in world.db.log[log:]


def test_another_clubs_private_draft_is_not_compared(world: World) -> None:
    draft(world, actor=OTHER_CLUB, club=CLUB_B, venue=CERTIFIED)

    result = unsaved(world, status=EventStatus.CONFIRMED)

    assert [c.type for c in result.conflicts] == []


def test_a_candidate_for_a_club_the_user_is_not_in_is_refused(world: World) -> None:
    with pytest.raises(NotAuthorizedError):
        unsaved(world, STRANGER)
    with pytest.raises(NotAuthorizedError):
        unsaved(world, OTHER_CLUB)


def test_a_refused_check_does_not_reveal_whether_the_club_exists(world: World) -> None:
    unknown_club = UUID(int=999)
    with pytest.raises(NotAuthorizedError):
        unsaved(world, ORGANIZER, club=unknown_club)


def test_an_unknown_club_is_not_found_for_someone_allowed_to_ask(world: World) -> None:
    with pytest.raises(NotFoundError):
        unsaved(world, CAMPUS, club=UUID(int=999))


def test_an_unknown_venue_is_not_found(world: World) -> None:
    with pytest.raises(NotFoundError):
        unsaved(world, venue=UUID(int=998))


@pytest.mark.parametrize(("start", "end"), [((13, 0), (11, 0)), ((11, 0), (11, 0))])
def test_a_backwards_or_empty_interval_is_a_bad_request(
    world: World, start: tuple[int, int], end: tuple[int, int]
) -> None:
    with pytest.raises(InvalidRequestError):
        unsaved(world, start=start, end=end)


def test_a_delegated_user_can_check_a_candidate_for_their_own_club(world: World) -> None:
    delegated = Actor(user_id=ORGANIZER.user_id, memberships=ORGANIZER.memberships, via_agent=True)
    assert unsaved(world, delegated).conflicts is not None


def test_the_unsaved_candidate_is_the_nil_uuid_the_agent_is_told_to_expect() -> None:
    assert str(UNSAVED_CANDIDATE_ID) == "00000000-0000-0000-0000-000000000000"
