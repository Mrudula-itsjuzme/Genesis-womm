"""The assistant's campus context, read from real PostgreSQL rows for a seeded person."""

from datetime import UTC, datetime

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import sessionmaker

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, Role
from app.domain.time import FixedClock
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.chat_context import ChatContextBuilder
from scripts.seed_demo import (
    CLUB_EVENTS,
    CLUB_ROBOTICS,
    DEMO_USERS,
    RESOURCE_AUDITORIUM,
    seed_demo_data,
)
from tests.conftest import upgrade

pytestmark = pytest.mark.integration

NOW = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)
ORGANIZER = DEMO_USERS[2]
OUTSIDER = next(user for user in DEMO_USERS if user.email == "outsider@demo.invalid")


def builder(engine: Engine) -> ChatContextBuilder:
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    return ChatContextBuilder(lambda: SqlUnitOfWork(sessions), clock=FixedClock(NOW))


def test_an_organizer_is_told_their_clubs_and_the_campus_venues(engine: Engine) -> None:
    upgrade(engine)
    seed_demo_data(engine)

    context = builder(engine).build(Actor(user_id=ORGANIZER.id))

    assert context.now == NOW
    assert {(club.id, club.role) for club in context.clubs} == {
        (CLUB_EVENTS, Role.ORGANIZER),
        (CLUB_ROBOTICS, Role.ORGANIZER),
    }
    assert {club.name for club in context.clubs} == {
        "Intel IoT Club",
        "Raagasudha Music Club",
    }
    venues = {venue.id: venue for venue in context.venues}
    assert len(venues) == 3, "the equipment and the service are not venues"
    assert venues[RESOURCE_AUDITORIUM].name == "Amriteswari Hall (Main Auditorium)"
    assert venues[RESOURCE_AUDITORIUM].capacity == 450
    assert venues[RESOURCE_AUDITORIUM].availability is AvailabilityState.CONFIRMED


def test_someone_in_no_club_gets_the_venues_but_no_clubs(engine: Engine) -> None:
    upgrade(engine)
    seed_demo_data(engine)

    context = builder(engine).build(Actor(user_id=OUTSIDER.id))

    assert context.clubs == ()
    assert len(context.venues) == 3
