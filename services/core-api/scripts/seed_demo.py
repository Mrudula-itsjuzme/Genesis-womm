"""Install the deterministic, non-production data used by the CampusCue demo."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session

from app.models.directory import Club, Membership, Resource, User
from app.models.scheduling import Event
from app.settings import load_settings

SEED_TIME = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
EVENT_START = datetime(2026, 10, 20, 10, 0, tzinfo=UTC)


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
        "Synthetic Campus Admin",
        True,
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000002"),
        "club-admin@demo.invalid",
        "Synthetic Club Admin",
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000003"),
        "organizer@demo.invalid",
        "Synthetic Organizer",
    ),
    DemoUser(
        UUID("10000000-0000-4000-8000-000000000004"), "outsider@demo.invalid", "Synthetic Outsider"
    ),
)

CLUB_EVENTS = UUID("20000000-0000-4000-8000-000000000001")
CLUB_ROBOTICS = UUID("20000000-0000-4000-8000-000000000002")
RESOURCE_AUDITORIUM = UUID("30000000-0000-4000-8000-000000000001")
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
            (CLUB_EVENTS, "Synthetic Events Club"),
            (CLUB_ROBOTICS, "Synthetic Robotics Club"),
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
                "Synthetic Main Auditorium",
                "CONFIRMED",
                "CURRENT",
                450,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000002"),
                "VENUE",
                "Synthetic Seminar Hall",
                "REQUESTED",
                "CURRENT",
                120,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000003"),
                "VENUE",
                "Synthetic Open Courtyard",
                "UNKNOWN",
                "STALE",
                300,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000004"),
                "EQUIPMENT",
                "Synthetic Projector Kit",
                "CONFIRMED",
                "CURRENT",
                None,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000005"),
                "EQUIPMENT",
                "Synthetic PA System",
                "REQUESTED",
                "REVIEW_REQUIRED",
                None,
            ),
            (
                UUID("30000000-0000-4000-8000-000000000006"),
                "SERVICE",
                "Synthetic AV Support",
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
                    description="Synthetic demo resource; never campus operational data.",
                    location="Synthetic Campus",
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
                "Synthetic Design Expo",
                EVENT_START,
                EVENT_START + timedelta(hours=2),
                RESOURCE_AUDITORIUM,
            ),
            (
                UUID("40000000-0000-4000-8000-000000000002"),
                CLUB_ROBOTICS,
                "Synthetic Robotics Showcase",
                EVENT_START + timedelta(hours=1),
                EVENT_START + timedelta(hours=3),
                RESOURCE_AUDITORIUM,
            ),
            (
                UUID("40000000-0000-4000-8000-000000000003"),
                CLUB_EVENTS,
                "Synthetic Planning Workshop",
                EVENT_START + timedelta(days=2),
                EVENT_START + timedelta(days=2, hours=1),
                UUID("30000000-0000-4000-8000-000000000002"),
            ),
            (
                UUID("40000000-0000-4000-8000-000000000004"),
                CLUB_ROBOTICS,
                "Synthetic Equipment Briefing",
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
                    description="Synthetic demo event; no real attendees or operational booking.",
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
        session.commit()


def main() -> None:
    engine = create_engine(load_settings().database_url, pool_pre_ping=True)
    try:
        seed_demo_data(engine)
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
