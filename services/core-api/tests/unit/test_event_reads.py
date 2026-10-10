from datetime import timedelta

from app.domain.enums import AvailabilityState
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.event_reads import EventReadService
from app.services.schedule_write import ScheduleWriteService
from tests.fakes import InMemoryDatabase, SequentialIds
from tests.unit.test_schedule_write import (
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

    assert total == 2
    assert [view.event.id for view in views] == [own.id]
    assert views[0].availability is AvailabilityState.UNKNOWN
