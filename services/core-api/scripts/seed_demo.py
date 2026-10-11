"""Install the deterministic, non-production data used by the CampusCue demo."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sqlalchemy import Engine, create_engine, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.directory import Club, Membership, Resource, User
from app.models.scheduling import Event, EvidenceRecord
from app.settings import load_settings

SEED_TIME = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
EVENT_START = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)
# The demo day. Two official (CONFIRMED) events anchor it, so a request for the same morning in
# the auditorium collides with both: it overlaps the lecture, and it ends only an hour before
# the hardware demo starts across campus.
DEMO_DAY_LECTURE_START = datetime(
    2026, 11, 20, 9, 30, tzinfo=timezone(timedelta(hours=5, minutes=30))
)
DEMO_DAY_HARDWARE_START = datetime(
    2026, 11, 20, 13, 0, tzinfo=timezone(timedelta(hours=5, minutes=30))
)
EVIDENCE_VENUE_CONFIRMATION = UUID("50000000-0000-4000-8000-000000000001")


@dataclass(frozen=True)
class DemoUser:
    id: UUID
    email: str
    display_name: str
    campus_admin: bool = False


DEMO_USERS = (
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000001"),
        "campus-admin@demo.invalid",
        "Dr. Ananya Rao",
        True,
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000002"),
        "club-admin@demo.invalid",
        "Rohan Kapoor",
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000003"),
        "organizer@demo.invalid",
        "Maya Iyer",
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000005"),
        "student@demo.invalid",
        "Nisha Verma",
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000004"), "outsider@demo.invalid", "Kabir Shah"
    ),
)

CLUB_EVENTS = UUID("20000000-0000-4000-8000-000000000001")
CLUB_ROBOTICS = UUID("20000000-0000-4000-8000-000000000002")
RESOURCE_AUDITORIUM = UUID("30000000-0000-4000-8000-000000000001")
RESOURCE_SEMINAR_HALL = UUID("30000000-0000-4000-8000-000000000002")
RESOURCE_COURTYARD = UUID("30000000-0000-4000-8000-000000000003")
type DemoEvent = tuple[UUID, UUID, str, datetime, datetime, UUID | None]


def _add_if_missing(session: Session, model: type[object], identifier: UUID, row: object) -> None:
    if session.get(model, identifier) is None:
        session.add(row)


def seed_demo_data(engine: Engine) -> None:
    """Add demo-only records without changing an already-seeded database."""
    with Session(engine) as session:
        for user in DEMO_USERS:
            _add_if_missing(
                session,
                User,
                user.id,
                User(
                    id=user.id,
                    email=user.email,
                    display_name=user.display_name,
                    campus_admin=user.campus_admin,
                    is_synthetic=True,
                    created_at=SEED_TIME,
                ),
            )
        session.flush()

        for club_id, name in (
            (CLUB_EVENTS, "Student Activities Council"),
            (CLUB_ROBOTICS, "Robotics and Automation Society"),
        ):
            _add_if_missing(
                session,
                Club,
                club_id,
                Club(id=club_id, name=name, is_synthetic=True, created_at=SEED_TIME),
            )
        session.flush()

        memberships = (
            (DEMO_USERS[1].id, CLUB_EVENTS, "CLUB_ADMIN"),
            (DEMO_USERS[2].id, CLUB_EVENTS, "ORGANIZER"),
            (DEMO_USERS[2].id, CLUB_ROBOTICS, "ORGANIZER"),
        )
        # The Web demo signs in with @example.invalid identities created by seed_demo().
        # When both seed routines run through Compose, give those identities the same access to
        # the event-bearing clubs as their @demo.invalid fixture counterparts.
        web_memberships = (
            (demo_id("club-admin"), CLUB_EVENTS, "CLUB_ADMIN"),
            (demo_id("organizer"), CLUB_EVENTS, "ORGANIZER"),
            (demo_id("organizer"), CLUB_ROBOTICS, "ORGANIZER"),
        )
        memberships += tuple(
            membership
            for membership in web_memberships
            if session.get(User, membership[0]) is not None
        )
        for user_id, club_id, role in memberships:
            if session.get(Membership, {"user_id": user_id, "club_id": club_id}) is None:
                session.add(
                    Membership(user_id=user_id, club_id=club_id, role=role, created_at=SEED_TIME)
                )
        session.flush()

        resources = (
            (
                RESOURCE_AUDITORIUM,
                "VENUE",
                "Tagore Auditorium",
                "CONFIRMED",
                "CURRENT",
                450,
            ),
            (
                RESOURCE_SEMINAR_HALL,
                "VENUE",
                "Saraswati Seminar Hall",
                "REQUESTED",
                "CURRENT",
                120,
            ),
            (
                RESOURCE_COURTYARD,
                "VENUE",
                "Central Quadrangle",
                "UNKNOWN",
                "STALE",
                300,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000004"),
                "EQUIPMENT",
                "Epson Projector Kit",
                "CONFIRMED",
                "CURRENT",
                None,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000005"),
                "EQUIPMENT",
                "Bose PA System",
                "REQUESTED",
                "REVIEW_REQUIRED",
                None,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000006"),
                "SERVICE",
                "Campus AV Services",
                "UNKNOWN",
                "UNKNOWN",
                None,
            ),
        )
        for resource_identifier, kind, name, availability, freshness, capacity in resources:
            _add_if_missing(
                session,
                Resource,
                resource_identifier,
                Resource(
                    id=resource_identifier,
                    kind=kind,
                    name=name,
                    description="Demo resource; not campus operational data.",
                    location="Northbridge Campus",
                    capacity=capacity,
                    availability_state=availability,
                    freshness_state=freshness,
                    source_id="demo-seed",
                    source_url=None,
                    collected_at=SEED_TIME,
                    last_checked_at=SEED_TIME,
                    is_synthetic=True,
                    created_at=SEED_TIME,
                ),
            )
        session.flush()

        events: tuple[DemoEvent, ...] = (
            (
                UUID("40000000-0000-4000-8000-000000000001"),
                CLUB_EVENTS,
                "Campus Design Expo",
                EVENT_START,
                EVENT_START + timedelta(hours=2),
                RESOURCE_AUDITORIUM,
            ),
            (
                UUID("40000000-0000-4000-8000-000000000002"),
                CLUB_ROBOTICS,
                "RoboTech Showcase",
                EVENT_START + timedelta(hours=1),
                EVENT_START + timedelta(hours=3),
                RESOURCE_AUDITORIUM,
            ),
            (
                UUID("40000000-0000-4000-8000-000000000003"),
                CLUB_EVENTS,
                "Event Planning Workshop",
                EVENT_START + timedelta(days=2),
                EVENT_START + timedelta(days=2, hours=1),
                RESOURCE_SEMINAR_HALL,
            ),
            (
                UUID("40000000-0000-4000-8000-000000000004"),
                CLUB_ROBOTICS,
                "AV Equipment Briefing",
                EVENT_START + timedelta(days=4),
                EVENT_START + timedelta(days=4, hours=1),
                None,
            ),
        )
        for event_id, club_id, title, start_at, end_at, event_resource_id in events:
            _add_if_missing(
                session,
                Event,
                event_id,
                Event(
                    id=event_id,
                    club_id=club_id,
                    title=title,
                    description="Demo event; no real attendees or operational booking.",
                    start_at=start_at,
                    end_at=end_at,
                    resource_id=event_resource_id,
                    expected_attendance=50,
                    audience_tags=["synthetic-demo"],
                    status="DRAFT",
                    revision=1,
                    created_by=DEMO_USERS[2].id,
                    verified_by=None,
                    verified_at=None,
                    evidence_id=None,
                    is_synthetic=True,
                    created_at=SEED_TIME,
                    updated_at=SEED_TIME,
                ),
            )
        session.flush()

        _add_if_missing(
            session,
            EvidenceRecord,
            EVIDENCE_VENUE_CONFIRMATION,
            EvidenceRecord(
                id=EVIDENCE_VENUE_CONFIRMATION,
                kind="EMAIL_REFERENCE",
                reference="demo/venue-confirmation-1",
                issuer="Northbridge Student Affairs",
                captured_at=SEED_TIME,
                recorded_by=DEMO_USERS[0].id,
                created_at=SEED_TIME,
            ),
        )
        session.flush()

        confirmed: tuple[DemoEvent, ...] = (
            (
                UUID("40000000-0000-4000-8000-000000000005"),
                CLUB_EVENTS,
                "Distinguished Alumni Lecture",
                DEMO_DAY_LECTURE_START,
                DEMO_DAY_LECTURE_START + timedelta(hours=2),
                RESOURCE_AUDITORIUM,
            ),
            (
                UUID("40000000-0000-4000-8000-000000000006"),
                CLUB_ROBOTICS,
                "Autonomous Systems Demonstration",
                DEMO_DAY_HARDWARE_START,
                DEMO_DAY_HARDWARE_START + timedelta(hours=1, minutes=30),
                RESOURCE_SEMINAR_HALL,
            ),
        )
        for event_id, club_id, title, start_at, end_at, event_resource_id in confirmed:
            _add_if_missing(
                session,
                Event,
                event_id,
                Event(
                    id=event_id,
                    club_id=club_id,
                    title=title,
                    description="Demo event; no real attendees or operational booking.",
                    start_at=start_at,
                    end_at=end_at,
                    resource_id=event_resource_id,
                    expected_attendance=120,
                    audience_tags=["synthetic-demo"],
                    status="CONFIRMED",
                    revision=1,
                    created_by=DEMO_USERS[1].id,
                    verified_by=DEMO_USERS[0].id,
                    verified_at=SEED_TIME,
                    evidence_id=EVIDENCE_VENUE_CONFIRMATION,
                    is_synthetic=True,
                    created_at=SEED_TIME,
                    updated_at=SEED_TIME,
                ),
            )
        session.commit()


def demo_id(name: str) -> UUID:
    return uuid5(NAMESPACE_URL, "campuscue:synthetic-demo:" + name)


def seed_demo(session: Session, app_env: str) -> None:
    if app_env not in {"local", "test", "demo"}:
        raise ValueError("synthetic seeds are allowed only in local, test, or demo")
    now = datetime.now(UTC)
    for club_id, name in (
        (CLUB_EVENTS, "Student Activities Council"),
        (CLUB_ROBOTICS, "Robotics and Automation Society"),
    ):
        session.execute(
            insert(Club)
            .values(id=club_id, name=name, is_synthetic=True, created_at=now)
            .on_conflict_do_nothing()
        )
    for name, display_name, memberships in (
        ("organizer", "Maya Iyer", ((CLUB_EVENTS, "ORGANIZER"), (CLUB_ROBOTICS, "ORGANIZER"))),
        ("club-admin", "Rohan Kapoor", ((CLUB_EVENTS, "CLUB_ADMIN"),)),
        ("campus-admin", "Dr. Ananya Rao", ()),
    ):
        user_id = demo_id(name)
        email = name + "@example.invalid"
        existing = session.scalar(select(User).where(User.email == email))
        if existing is not None and (existing.id != user_id or not existing.is_synthetic):
            raise ValueError("demo email conflicts with an existing directory identity")
        session.execute(
            insert(User)
            .values(
                id=user_id,
                email=email,
                display_name=display_name,
                campus_admin=not memberships,
                is_synthetic=True,
                created_at=now,
            )
            .on_conflict_do_nothing()
        )
        for club_id, role in memberships:
            session.execute(
                insert(Membership)
                .values(user_id=user_id, club_id=club_id, role=role, created_at=now)
                .on_conflict_do_nothing()
            )
    for name in ("Cauvery Hall", "Narmada Hall"):
        session.execute(
            insert(Resource)
            .values(
                id=demo_id(name),
                kind="VENUE",
                name=name,
                description="Demo venue; not institutional data.",
                location="Northbridge Campus",
                capacity=100,
                availability_state="UNKNOWN",
                freshness_state="UNKNOWN",
                source_id="synthetic-demo",
                source_url=None,
                collected_at=now,
                last_checked_at=None,
                is_synthetic=True,
                created_at=now,
            )
            .on_conflict_do_nothing()
        )


def main() -> None:
    settings = load_settings()
    engine = create_engine(settings.database_url, pool_pre_ping=True)
    try:
        with Session(engine) as session:
            seed_demo(session, settings.app_env)
            session.commit()
        seed_demo_data(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
