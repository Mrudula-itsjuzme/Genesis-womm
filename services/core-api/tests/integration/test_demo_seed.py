"""The demo fixture is safe, deterministic, can be applied more than once, and has conflicts
that Core itself reports (not just rows whose times happen to overlap)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import sessionmaker

from app.domain.authz import Actor
from app.domain.enums import ConflictConstraint, ConflictType, EventStatus, Role, Severity
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.conflict_checks import ConflictCheckResult, ConflictCheckService
from scripts.seed_demo import (
    CLUB_EVENTS,
    DEMO_USERS,
    RESOURCE_AUDITORIUM,
    RESOURCE_COURTYARD,
    seed_demo_data,
)
from tests.conftest import upgrade

pytestmark = pytest.mark.integration

IST = timezone(timedelta(hours=5, minutes=30))
ORGANIZER = Actor(user_id=DEMO_USERS[2].id, memberships={CLUB_EVENTS: Role.ORGANIZER})


def _count(engine: Engine, table: str) -> int:
    with engine.connect() as connection:
        return int(connection.scalar(text(f"SELECT count(*) FROM core.{table}")) or 0)  # noqa: S608


def _checker(engine: Engine) -> ConflictCheckService:
    sessions = sessionmaker(bind=engine, expire_on_commit=False)
    return ConflictCheckService(
        lambda: SqlUnitOfWork(sessions),
        clock=FixedClock(datetime(2026, 10, 11, tzinfo=UTC)),
        policy=Policy(campus_gap=timedelta(minutes=120)),
    )


def test_demo_seed_is_idempotent_and_synthetic(engine: Engine) -> None:
    upgrade(engine)

    seed_demo_data(engine)
    seed_demo_data(engine)

    assert {
        table: _count(engine, table)
        for table in ("users", "clubs", "resources", "events", "evidence_records")
    } == {"users": 5, "clubs": 2, "resources": 6, "events": 6, "evidence_records": 1}
    with engine.connect() as connection:
        emails = connection.scalars(text("SELECT email FROM core.users ORDER BY email")).all()
        unsafe = connection.scalar(
            text(
                "SELECT count(*) FROM core.users "
                "WHERE is_synthetic IS NOT TRUE OR email NOT LIKE '%.invalid'"
            )
        )
        unsafe_events = connection.scalar(
            text("SELECT count(*) FROM core.events WHERE is_synthetic IS NOT TRUE")
        )
    assert emails == sorted(user.email for user in DEMO_USERS)
    assert "student@demo.invalid" in emails
    assert (unsafe, unsafe_events) == (0, 0)


def _morning_of_the_demo_day(engine: Engine, **extra: EventStatus) -> ConflictCheckResult:
    """The request the demo makes: the auditorium, 10:00 to 12:00 on the demo day."""
    upgrade(engine)
    seed_demo_data(engine)
    return _checker(engine).check_candidate(
        ORGANIZER,
        club_id=CLUB_EVENTS,
        start_at=datetime(2026, 11, 20, 10, 0, tzinfo=IST),
        end_at=datetime(2026, 11, 20, 12, 0, tzinfo=IST),
        resource_id=RESOURCE_AUDITORIUM,
        **extra,
    )


def test_a_draft_in_the_demo_slot_gets_warnings_for_both_constraints(engine: Engine) -> None:
    result = _morning_of_the_demo_day(engine)

    assert {c.type for c in result.conflicts} == {ConflictType.TENTATIVE_OVERLAP}
    assert {c.constraint for c in result.conflicts} == {
        ConflictConstraint.VENUE_OVERLAP,
        ConflictConstraint.CAMPUS_GAP,
    }
    assert {c.severity for c in result.conflicts} == {Severity.WARNING}


def test_confirming_in_the_demo_slot_is_blocked_until_someone_authorized_overrides(
    engine: Engine,
) -> None:
    result = _morning_of_the_demo_day(engine, as_status=EventStatus.CONFIRMED)

    assert {c.type for c in result.conflicts} == {
        ConflictType.VENUE_OVERLAP,
        ConflictType.CAMPUS_GAP_VIOLATION,
    }
    assert all(c.severity is Severity.BLOCKING and c.override_required for c in result.conflicts)


def test_a_free_auditorium_slot_has_no_conflicts(engine: Engine) -> None:
    upgrade(engine)
    seed_demo_data(engine)

    result = _checker(engine).check_candidate(
        ORGANIZER,
        club_id=CLUB_EVENTS,
        start_at=datetime(2026, 11, 24, 15, 0, tzinfo=IST),
        end_at=datetime(2026, 11, 24, 16, 0, tzinfo=IST),
        resource_id=RESOURCE_AUDITORIUM,
    )

    assert result.conflicts == ()


def test_a_venue_with_no_availability_source_says_so_instead_of_claiming_it_is_free(
    engine: Engine,
) -> None:
    upgrade(engine)
    seed_demo_data(engine)

    result = _checker(engine).check_candidate(
        ORGANIZER,
        club_id=CLUB_EVENTS,
        start_at=datetime(2026, 11, 24, 15, 0, tzinfo=IST),
        end_at=datetime(2026, 11, 24, 16, 0, tzinfo=IST),
        resource_id=RESOURCE_COURTYARD,
    )

    assert [(c.type, c.severity) for c in result.conflicts] == [
        (ConflictType.UNKNOWN_AVAILABILITY, Severity.INFO)
    ]
