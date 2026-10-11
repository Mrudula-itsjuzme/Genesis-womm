from datetime import timedelta
from uuid import UUID

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, EventStatus
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.event_reads import EventReadService, EventView
from app.services.ports import EventRecord
from app.services.schedule_write import ScheduleWriteService
from tests.fakes import InMemoryDatabase, SequentialIds
from tests.unit.test_schedule_write import (
    CAMPUS,
    CLUB_A,
    CLUB_B,
    HALL,
    LAB,
    NOW,
    ORGANIZER,
    OTHER_CLUB,
    World,
    draft,
)


def test_other_club_drafts_are_hidden_but_published_events_are_summarized() -> None:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {HALL: AvailabilityState.UNKNOWN, LAB: AvailabilityState.UNKNOWN}
    world = World(
        db,
        ScheduleWriteService(
            db.uow, clock=FixedClock(NOW), ids=SequentialIds(), policy=Policy(timedelta(hours=2))
        ),
        SequentialIds(),
    )
    own = draft(world).event
    _ = draft(
        world, actor=OTHER_CLUB, club=OTHER_CLUB.memberships.keys().__iter__().__next__()
    ).event
    service = EventReadService(world.db.uow)

    views, total = service.list(
        ORGANIZER,
        club_id=None,
        status=None,
        resource_id=None,
        starts_after=None,
        starts_before=None,
        limit=10,
        offset=0,
    )

    assert total == 1
    assert [view.event.id for view in views] == [own.id]
    assert views[0].availability is AvailabilityState.UNKNOWN


def _stored(db: InMemoryDatabase, n: int, club: UUID, status: EventStatus) -> EventRecord:
    record = EventRecord(
        id=UUID(int=1000 + n),
        club_id=club,
        title=f"event {n}",
        description=None,
        start_at=NOW + timedelta(days=n),
        end_at=NOW + timedelta(days=n, hours=1),
        resource_id=None,
        expected_attendance=None,
        audience_tags=(),
        status=status,
        revision=1,
        created_by=ORGANIZER.user_id,
        verified_by=None,
        verified_at=None,
        evidence_id=None,
        is_synthetic=True,
        created_at=NOW,
        updated_at=NOW,
    )
    db.state.events[record.id] = record
    return record


def _list(
    service: EventReadService, actor: Actor, *, limit: int, offset: int
) -> tuple[list[EventView], int]:
    return service.list(
        actor,
        club_id=None,
        status=None,
        resource_id=None,
        starts_after=None,
        starts_before=None,
        limit=limit,
        offset=offset,
    )


def test_the_total_counts_every_match_not_just_the_page() -> None:
    db = InMemoryDatabase()
    for n in range(5):
        _stored(db, n, CLUB_A, EventStatus.PROPOSED)
    service = EventReadService(db.uow)

    first, total = _list(service, ORGANIZER, limit=2, offset=0)
    beyond, beyond_total = _list(service, ORGANIZER, limit=2, offset=40)

    assert (len(first), total) == (2, 5)
    assert (len(beyond), beyond_total) == (0, 5)


def test_a_draft_you_cannot_see_takes_no_page_slot_and_is_not_counted() -> None:
    db = InMemoryDatabase()
    hidden = _stored(db, 0, CLUB_B, EventStatus.DRAFT)
    visible = [_stored(db, n, CLUB_B, EventStatus.PROPOSED) for n in range(1, 4)]
    service = EventReadService(db.uow)

    page_one, total = _list(service, ORGANIZER, limit=2, offset=0)
    page_two, _ = _list(service, ORGANIZER, limit=2, offset=2)

    assert total == 3
    assert [v.event.id for v in page_one] == [visible[0].id, visible[1].id]
    assert [v.event.id for v in page_two] == [visible[2].id]
    assert hidden.id not in {v.event.id for v in page_one + page_two}


def test_a_member_and_a_campus_admin_still_see_the_drafts_they_are_entitled_to() -> None:
    db = InMemoryDatabase()
    own = _stored(db, 0, CLUB_A, EventStatus.DRAFT)
    other = _stored(db, 1, CLUB_B, EventStatus.DRAFT)
    service = EventReadService(db.uow)

    mine, mine_total = _list(service, ORGANIZER, limit=10, offset=0)
    everything, all_total = _list(service, CAMPUS, limit=10, offset=0)

    assert (mine_total, [v.event.id for v in mine]) == (1, [own.id])
    assert (all_total, [v.event.id for v in everything]) == (2, [own.id, other.id])
