from datetime import timedelta
from uuid import uuid4

import pytest

from app.domain.lifecycle import NotAuthorizedError
from app.domain.scheduling import Policy
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.change_queries import ChangeQueries, change_candidate
from app.services.errors import InvalidRequestError, NotFoundError, StaleRevisionError
from app.services.ports import EventRecord
from app.services.schedule_write import NewEvent, RequestContext
from tests.integration.world import World, at

pytestmark = pytest.mark.integration


def event_for(world: World) -> EventRecord:
    return world.svc.create_event(
        RequestContext(world.organizer, "change-query"),
        NewEvent(world.club_a, "Synthetic change", at(10), at(12)),
    ).event


def test_partial_null_and_time_validation(world: World) -> None:
    event = event_for(world)
    candidate, changed = change_candidate(event, {"start_at": at(11)})
    assert candidate.end_at == event.end_at
    assert set(changed) == {"start_at"}
    with pytest.raises(InvalidRequestError):
        change_candidate(event, {"start_at": at(13)})
    with pytest.raises(InvalidRequestError):
        change_candidate(event, {"status": "CONFIRMED"})
    with pytest.raises(InvalidRequestError):
        change_candidate(event, {"expected_attendance": True})
    with pytest.raises(InvalidRequestError):
        change_candidate(event, {"start_at": event.start_at})


def test_preview_authorization_revision_and_no_mutation(world: World) -> None:
    event = event_for(world)
    queries = ChangeQueries(
        lambda: SqlUnitOfWork(world.factory), policy=Policy(campus_gap=timedelta(minutes=120))
    )
    preview = queries.preview(world.organizer, event.id, 1, {"start_at": at(11)})
    assert preview.event.revision == 1
    assert preview.candidate.start_at == at(11)
    assert world.count("event_revisions") == 1
    assert world.count("change_proposals") == 0
    with pytest.raises(NotAuthorizedError):
        queries.preview(world.other, event.id, 1, {"start_at": at(11)})
    with pytest.raises(StaleRevisionError):
        queries.preview(world.organizer, event.id, 2, {"start_at": at(11)})
    assert queries.items(world.organizer, event.id) == []
    assert queries.list(world.organizer, event.id, 50, 0) == ([], 0)
    with pytest.raises(NotFoundError):
        queries.get(world.organizer, uuid4())
