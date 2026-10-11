"""What the assistant is told about the person and the campus before it answers.

A model cannot plan against venues and clubs it has never been shown, and must not invent their
ids. Core reads them from its own database for the signed-in person and hands them over with the
turn, so the Agent never has to guess a UUID.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, FreshnessState, ResourceKind, Role
from app.domain.time import FixedClock
from app.services.chat_context import MAX_VENUES, ChatContextBuilder
from app.services.ports import (
    MembershipIdentity,
    ResourceRecord,
    UnitOfWork,
    UserIdentity,
)

NOW = datetime(2026, 11, 1, 3, 0, tzinfo=UTC)
USER = UUID(int=7)
CLUB = UUID(int=70)
ACTOR = Actor(user_id=USER, memberships={CLUB: Role.ORGANIZER})


def venue(n: int, state: AvailabilityState = AvailabilityState.UNKNOWN) -> ResourceRecord:
    return ResourceRecord(
        id=UUID(int=900 + n),
        kind=ResourceKind.VENUE,
        name=f"Hall {n}",
        description=None,
        location=None,
        capacity=100 + n,
        availability_state=state,
        freshness_state=FreshnessState.CURRENT,
        source_id="test",
        source_url=None,
        collected_at=None,
        last_checked_at=None,
        is_synthetic=True,
    )


@dataclass
class _Actors:
    identity: UserIdentity | None

    def load_identity(self, user_id: UUID) -> UserIdentity | None:
        return self.identity if user_id == USER else None


@dataclass
class _Resources:
    records: list[ResourceRecord]
    asked: list[dict[str, Any]] = field(default_factory=list)

    def list_resources(self, **kwargs: Any) -> tuple[list[ResourceRecord], int]:
        self.asked.append(kwargs)
        return self.records[: kwargs["limit"]], len(self.records)


@dataclass
class _Uow:
    actors: _Actors
    resources: _Resources

    def __enter__(self) -> "_Uow":
        return self

    def __exit__(self, *_: object) -> None:
        return None


def builder(
    identity: UserIdentity | None, records: list[ResourceRecord]
) -> tuple[ChatContextBuilder, _Resources]:
    resources = _Resources(records)
    uow = _Uow(_Actors(identity), resources)
    return (
        ChatContextBuilder(lambda: cast(UnitOfWork, uow), clock=FixedClock(NOW)),
        resources,
    )


IDENTITY = UserIdentity(
    id=USER,
    email="o@example.invalid",
    display_name="Organizer",
    campus_admin=False,
    memberships=(MembershipIdentity(club_id=CLUB, club_name="Robotics Club", role=Role.ORGANIZER),),
    is_synthetic=True,
)


def test_the_person_is_told_their_clubs_by_name_and_role() -> None:
    context = builder(IDENTITY, [])[0].build(ACTOR)

    assert [(c.id, c.name, c.role) for c in context.clubs] == [
        (CLUB, "Robotics Club", Role.ORGANIZER)
    ]


def test_venues_are_listed_with_capacity_and_what_core_knows_about_availability() -> None:
    records = [venue(1, AvailabilityState.CONFIRMED), venue(2)]

    context = builder(IDENTITY, records)[0].build(ACTOR)

    assert [(v.id, v.name, v.capacity, v.availability) for v in context.venues] == [
        (UUID(int=901), "Hall 1", 101, AvailabilityState.CONFIRMED),
        (UUID(int=902), "Hall 2", 102, AvailabilityState.UNKNOWN),
    ]


def test_only_venues_are_asked_for_and_only_a_bounded_number() -> None:
    records = [venue(n) for n in range(MAX_VENUES + 10)]
    built, resources = builder(IDENTITY, records)

    context = built.build(ACTOR)

    assert len(context.venues) == MAX_VENUES
    assert resources.asked == [
        {"kind": ResourceKind.VENUE, "query": None, "limit": MAX_VENUES, "offset": 0}
    ]


def test_the_clock_is_core_s_not_the_model_s() -> None:
    assert builder(IDENTITY, [])[0].build(ACTOR).now == NOW


def test_someone_the_directory_does_not_know_has_no_clubs() -> None:
    context = builder(None, [venue(1)])[0].build(ACTOR)

    assert context.clubs == ()
    assert len(context.venues) == 1
