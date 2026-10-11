"""The PostgreSQL adapters behind the write path's ports (spine AD-2, AD-4, AD-8, AD-20)."""

from collections.abc import Iterator
from datetime import timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.domain.enums import AvailabilityState, EventStatus, OverrideScope, Role
from app.repositories.directory import SqlActorReader, SqlClubReader, SqlResourceReader
from app.repositories.scheduling import (
    CAMPUS_SCHEDULE_LOCK_KEY,
    SqlEventStore,
    SqlOverrideStore,
    SqlRevisionWriter,
    SqlScheduleLock,
)
from app.services.errors import StaleRevisionError
from app.services.ports import EventRecord, OverrideRecord
from tests.conftest import upgrade
from tests.integration.support import (
    END,
    NOW,
    START,
    insert,
    make_club,
    make_evidence,
    make_resource,
    make_user,
)

pytestmark = pytest.mark.integration


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
        self.venue = make_resource(conn)
        self.evidence = make_evidence(conn, self.user)

    def event(self, **changes: object) -> EventRecord:
        base = EventRecord(
            id=uuid4(),
            club_id=self.club,
            title="Robotics Demo Day",
            description="Student teams demo their projects",
            start_at=START,
            end_at=END,
            resource_id=self.venue,
            expected_attendance=80,
            audience_tags=("all-years", "robotics"),
            status=EventStatus.DRAFT,
            revision=1,
            created_by=self.user,
            verified_by=None,
            verified_at=None,
            evidence_id=None,
            is_synthetic=True,
            created_at=NOW,
            updated_at=NOW,
        )
        return base.but(**changes)


@pytest.fixture
def world(session: Session) -> World:
    return World(session)


# ---- events ---------------------------------------------------------------------------


def test_an_event_round_trips_through_the_database(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    record = world.event()
    store.insert(record)
    assert store.get(record.id) == record


def test_a_confirmed_event_round_trips_with_its_verification(
    session: Session, world: World
) -> None:
    store = SqlEventStore(session)
    record = world.event(
        status=EventStatus.CONFIRMED,
        verified_by=world.user,
        verified_at=NOW,
        evidence_id=world.evidence,
    )
    store.insert(record)
    assert store.get(record.id) == record


def test_an_unknown_event_is_none(session: Session) -> None:
    assert SqlEventStore(session).get(uuid4()) is None


def test_event_listing_filters_orders_and_counts_before_pagination(
    session: Session, world: World
) -> None:
    store = SqlEventStore(session)
    early = world.event(title="Early")
    late = world.event(
        title="Late", start_at=START + timedelta(days=1), end_at=END + timedelta(days=1)
    )
    for record in (late, early):
        store.insert(record)

    items, total = store.list_events(
        club_id=world.club,
        status=None,
        resource_id=None,
        starts_after=None,
        starts_before=None,
        draft_clubs=None,
        limit=1,
        offset=1,
    )

    assert total == 2
    assert [item.id for item in items] == [late.id]


def test_drafts_of_other_clubs_are_left_out_of_both_the_page_and_the_total(
    session: Session, world: World
) -> None:
    store = SqlEventStore(session)
    other_club = make_club(session.connection())
    mine = world.event(title="Mine", status=EventStatus.DRAFT)
    theirs_draft = world.event(title="Their draft", club_id=other_club, status=EventStatus.DRAFT)
    theirs_public = world.event(
        title="Their public",
        club_id=other_club,
        status=EventStatus.PROPOSED,
        start_at=START + timedelta(days=1),
        end_at=END + timedelta(days=1),
    )
    for record in (mine, theirs_draft, theirs_public):
        store.insert(record)

    def titles(clubs: frozenset[UUID] | None, limit: int = 10) -> tuple[list[str], int]:
        items, total = store.list_events(
            club_id=None,
            status=None,
            resource_id=None,
            starts_after=None,
            starts_before=None,
            draft_clubs=clubs,
            limit=limit,
            offset=0,
        )
        return sorted(item.title for item in items), total

    assert titles(frozenset({world.club})) == (["Mine", "Their public"], 2)
    assert titles(frozenset()) == (["Their public"], 1)
    assert titles(None) == (["Mine", "Their draft", "Their public"], 3)
    assert titles(frozenset({world.club}), limit=1)[1] == 2


def test_an_update_at_the_expected_revision_persists(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    record = world.event()
    store.insert(record)
    moved = record.but(status=EventStatus.PROPOSED, revision=2, updated_at=NOW + timedelta(hours=1))
    store.update(moved, expected_revision=1)
    assert store.get(record.id) == moved


def test_a_stale_update_changes_nothing_and_reports_the_real_revision(
    session: Session, world: World
) -> None:
    store = SqlEventStore(session)
    record = world.event(revision=3)
    store.insert(record)
    with pytest.raises(StaleRevisionError) as stale:
        store.update(record.but(title="Changed", revision=4), expected_revision=1)
    assert (stale.value.expected, stale.value.actual) == (1, 3)
    assert store.get(record.id) == record


def test_updating_an_event_that_does_not_exist_is_stale(session: Session, world: World) -> None:
    with pytest.raises(StaleRevisionError) as stale:
        SqlEventStore(session).update(world.event(), expected_revision=1)
    assert stale.value.actual is None


def test_two_writers_cannot_both_win_the_same_revision(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    record = world.event()
    store.insert(record)
    store.update(record.but(title="First", revision=2), expected_revision=1)
    with pytest.raises(StaleRevisionError):
        store.update(record.but(title="Second", revision=2), expected_revision=1)
    stored = store.get(record.id)
    assert stored is not None
    assert stored.title == "First"


# ---- the window query -----------------------------------------------------------------


def test_the_window_excludes_inactive_events(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    active = world.event(status=EventStatus.SUBMITTED)
    store.insert(active)
    for status in (EventStatus.REJECTED, EventStatus.CANCELLED, EventStatus.COMPLETED):
        store.insert(world.event(status=status))
    found = store.list_scheduling_candidates(
        starts_before=END + timedelta(hours=1), ends_after=START - timedelta(hours=1)
    )
    assert [e.id for e in found] == [active.id]


def test_the_window_edges_are_exclusive(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    window_start = START
    window_end = END
    ends_exactly_at_start = world.event(
        start_at=window_start - timedelta(hours=2), end_at=window_start
    )
    starts_exactly_at_end = world.event(start_at=window_end, end_at=window_end + timedelta(hours=1))
    overlaps_by_a_minute = world.event(
        start_at=window_end - timedelta(minutes=1), end_at=window_end + timedelta(hours=1)
    )
    for record in (ends_exactly_at_start, starts_exactly_at_end, overlaps_by_a_minute):
        store.insert(record)
    found = store.list_scheduling_candidates(starts_before=window_end, ends_after=window_start)
    assert {e.id for e in found} == {overlaps_by_a_minute.id}


def test_the_window_is_ordered_by_start_time(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    late = world.event(start_at=START + timedelta(hours=1), end_at=END + timedelta(hours=1))
    early = world.event()
    store.insert(late)
    store.insert(early)
    found = store.list_scheduling_candidates(
        starts_before=END + timedelta(days=1), ends_after=START - timedelta(days=1)
    )
    assert [e.id for e in found] == [early.id, late.id]


# ---- revisions and overrides ----------------------------------------------------------


def test_a_revision_is_stored_once_per_event_and_number(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    record = world.event()
    store.insert(record)
    writer = SqlRevisionWriter(session)

    def add_revision() -> None:
        writer.add(
            revision_id=uuid4(),
            event_id=record.id,
            revision=1,
            previous=None,
            current={"status": "DRAFT"},
            actor_id=world.user,
            reason="created",
            created_at=NOW,
        )

    add_revision()
    row = session.execute(
        text("SELECT current, reason FROM core.event_revisions WHERE event_id = :e"),
        {"e": record.id},
    ).one()
    assert row.current == {"status": "DRAFT"}
    assert row.reason == "created"
    with pytest.raises(IntegrityError):
        add_revision()


def test_overrides_are_found_by_either_event_of_the_pair(session: Session, world: World) -> None:
    store = SqlEventStore(session)
    a, b, c = world.event(), world.event(), world.event()
    for event in (a, b, c):
        store.insert(event)
    low, high = sorted((a.id, b.id), key=lambda u: u.int)
    overrides = SqlOverrideStore(session)
    record = OverrideRecord(
        id=uuid4(),
        scope=OverrideScope.CAMPUS_GAP,
        event_a_id=low,
        event_b_id=high,
        reason="Approved",
        authorized_by=world.user,
        evidence_id=None,
        created_at=NOW,
    )
    overrides.add(record)
    assert overrides.for_event(a.id) == [record]
    assert overrides.for_event(b.id) == [record]
    assert overrides.for_event(c.id) == []
    assert overrides.exists(OverrideScope.CAMPUS_GAP, low, high) is True
    assert overrides.exists(OverrideScope.VENUE_OVERLAP, low, high) is False


# ---- directory ------------------------------------------------------------------------


def test_clubs_and_venues_are_looked_up_by_id(session: Session, world: World) -> None:
    assert SqlClubReader(session).exists(world.club) is True
    assert SqlClubReader(session).exists(uuid4()) is False
    resources = SqlResourceReader(session)
    assert resources.availability_of(world.venue) is AvailabilityState.UNKNOWN
    assert resources.availability_of(uuid4()) is None


def test_a_venue_with_evidence_reports_its_stored_availability(session: Session) -> None:
    venue = make_resource(session.connection(), availability_state="CONFIRMED")
    assert SqlResourceReader(session).availability_of(venue) is AvailabilityState.CONFIRMED


def test_resources_can_be_filtered_and_paginated(session: Session) -> None:
    conn = session.connection()
    first = make_resource(conn, name="Auditorium", kind="VENUE")
    make_resource(conn, name="Lab One", kind="EQUIPMENT")
    reader = SqlResourceReader(session)

    items, total = reader.list_resources(kind=None, query="audit", limit=10, offset=0)

    assert total == 1
    assert [item.id for item in items] == [first]
    assert reader.get(first) is not None


def test_an_actor_is_built_from_the_users_rows(session: Session) -> None:
    conn = session.connection()
    user, admin = make_user(conn), make_user(conn, admin=True)
    club_a, club_b = make_club(conn), make_club(conn)
    insert(conn, "memberships", user_id=user, club_id=club_a, role="ORGANIZER", created_at=NOW)
    insert(conn, "memberships", user_id=user, club_id=club_b, role="CLUB_ADMIN", created_at=NOW)
    reader = SqlActorReader(session)

    actor = reader.load_actor(user)
    assert actor is not None
    assert actor.campus_admin is False
    assert dict(actor.memberships) == {club_a: Role.ORGANIZER, club_b: Role.CLUB_ADMIN}
    assert actor.via_agent is False

    boss = reader.load_actor(admin)
    assert boss is not None
    assert (boss.campus_admin, dict(boss.memberships)) == (True, {})


def test_an_actor_acting_through_a_delegation_is_marked_as_the_agent(session: Session) -> None:
    user = make_user(session.connection())
    actor = SqlActorReader(session).load_actor(user, via_agent=True)
    assert actor is not None
    assert actor.via_agent is True


def test_an_unknown_user_has_no_actor(session: Session) -> None:
    assert SqlActorReader(session).load_actor(UUID(int=1)) is None


def test_a_user_identity_includes_only_database_backed_memberships(session: Session) -> None:
    conn = session.connection()
    user = make_user(conn)
    first, second = make_club(conn), make_club(conn)
    insert(conn, "memberships", user_id=user, club_id=second, role="ORGANIZER", created_at=NOW)
    insert(conn, "memberships", user_id=user, club_id=first, role="CLUB_ADMIN", created_at=NOW)

    identity = SqlActorReader(session).load_identity_by_email(f"{user}@example.invalid")

    assert identity is not None
    assert (identity.id, identity.display_name, identity.campus_admin, identity.is_synthetic) == (
        user,
        "Test User",
        False,
        True,
    )
    assert {(membership.club_id, membership.role) for membership in identity.memberships} == {
        (first, Role.CLUB_ADMIN),
        (second, Role.ORGANIZER),
    }
    assert SqlActorReader(session).load_identity(UUID(int=1)) is None


# ---- the campus lock ------------------------------------------------------------------


def _lock_is_free(engine: Engine) -> bool:
    """Ask from a second connection whether the campus lock could be taken right now."""
    with engine.connect() as other:
        taken = other.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": CAMPUS_SCHEDULE_LOCK_KEY}
        ).scalar_one()
        other.rollback()
    return bool(taken)


def test_the_campus_lock_is_held_until_the_transaction_ends(engine: Engine) -> None:
    upgrade(engine)
    assert _lock_is_free(engine) is True
    with Session(engine) as holder:
        SqlScheduleLock(holder).acquire()
        assert _lock_is_free(engine) is False
        holder.commit()
    assert _lock_is_free(engine) is True


def test_a_rollback_releases_the_campus_lock(engine: Engine) -> None:
    upgrade(engine)
    with Session(engine) as holder:
        SqlScheduleLock(holder).acquire()
        assert _lock_is_free(engine) is False
        holder.rollback()
    assert _lock_is_free(engine) is True
