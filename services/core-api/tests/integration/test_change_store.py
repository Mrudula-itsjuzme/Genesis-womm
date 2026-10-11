from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from app.repositories.changes import SqlChangeStore
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.change_ports import ItemRecord
from tests.integration.support import NOW
from tests.integration.world import World

pytestmark = pytest.mark.integration


def test_item_dependencies_are_event_scoped_and_grouped(world: World) -> None:
    from app.services.schedule_write import NewEvent, RequestContext
    from tests.integration.world import at

    event = world.svc.create_event(
        RequestContext(world.organizer, "dependency-test"),
        NewEvent(world.club_a, "Synthetic dependency", at(10), at(12)),
    ).event
    item = ItemRecord(
        uuid4(),
        event.id,
        "COMMITMENT",
        "Venue request",
        "REQUESTED",
        False,
        world.organizer.user_id,
        ("resource_id", "start_at"),
        NOW,
        NOW,
    )
    with Session(world.engine) as session:
        store = SqlChangeStore(session)
        store.add_item(item)
        session.commit()
        assert store.items(event.id) == [item]
        assert len(store.dependencies(event.id)) == 2
        assert store.items(uuid4()) == []


def test_uncommitted_items_and_bindings_roll_back_together(world: World) -> None:
    from app.services.schedule_write import NewEvent, RequestContext
    from tests.integration.world import at

    event = world.svc.create_event(
        RequestContext(world.organizer, "rollback-test"),
        NewEvent(world.club_a, "Synthetic rollback", at(10), at(12)),
    ).event
    with SqlUnitOfWork(world.factory) as uow:
        uow.changes.add_item(
            ItemRecord(
                uuid4(),
                event.id,
                "TASK",
                "Speaker schedule",
                "OPEN",
                False,
                world.organizer.user_id,
                ("start_at",),
                NOW,
                NOW,
            )
        )
    assert world.count("event_items") == 0
    assert world.count("event_dependencies") == 0
