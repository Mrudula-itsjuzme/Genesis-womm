"""The database refuses rows that break the rules the application also enforces."""

from collections.abc import Callable
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config, upgrade
from tests.integration.support import (
    NOW,
    START,
    TEXT_IDS,
    insert,
    make_club,
    make_event,
    make_evidence,
    make_resource,
    make_user,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def db(engine: Engine) -> Engine:
    upgrade(engine)
    return engine


def refused(db: Engine, action: Callable[[Connection], object]) -> None:
    with pytest.raises(IntegrityError), db.begin() as conn:
        action(conn)


def seed(db: Engine) -> tuple[UUID, UUID]:
    with db.begin() as conn:
        return make_club(conn), make_user(conn)


# ---- events ---------------------------------------------------------------------------


def test_a_valid_event_is_accepted(db: Engine) -> None:
    club, user = seed(db)
    with db.begin() as conn:
        make_event(conn, club, user)


@pytest.mark.parametrize("end_offset", [timedelta(0), timedelta(minutes=-1)])
def test_an_event_must_end_after_it_starts(db: Engine, end_offset: timedelta) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, club, user, end_at=START + end_offset))


def test_an_event_status_must_be_a_known_value(db: Engine) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, club, user, status="BOOKED"))


def test_the_revision_starts_at_one(db: Engine) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, club, user, revision=0))


def test_expected_attendance_cannot_be_negative(db: Engine) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, club, user, expected_attendance=-1))


def test_an_event_needs_a_real_club_and_creator(db: Engine) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, uuid4(), user))
    refused(db, lambda c: make_event(c, club, uuid4()))


def test_an_event_venue_must_exist(db: Engine) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, club, user, resource_id=uuid4()))


def test_a_confirmed_event_must_carry_verifier_time_and_evidence(db: Engine) -> None:
    club, user = seed(db)
    refused(db, lambda c: make_event(c, club, user, status="CONFIRMED"))
    refused(db, lambda c: make_event(c, club, user, status="CONFIRMED", verified_by=user))
    with db.begin() as conn:
        evidence = make_evidence(conn, user)
    refused(
        db,
        lambda c: make_event(
            c, club, user, status="CONFIRMED", verified_by=user, evidence_id=evidence
        ),
    )
    with db.begin() as conn:
        make_event(
            conn,
            club,
            user,
            status="CONFIRMED",
            verified_by=user,
            verified_at=NOW,
            evidence_id=evidence,
        )


def test_a_tentative_event_needs_no_verification(db: Engine) -> None:
    club, user = seed(db)
    with db.begin() as conn:
        for status in ("DRAFT", "PROPOSED", "SUBMITTED", "REJECTED", "CANCELLED"):
            make_event(conn, club, user, status=status)


# ---- directory ------------------------------------------------------------------------


def test_emails_and_club_names_are_unique(db: Engine) -> None:
    with db.begin() as conn:
        insert(
            conn,
            "users",
            id=uuid4(),
            email="a@example.invalid",
            display_name="A",
            is_synthetic=True,
            created_at=NOW,
        )
        insert(conn, "clubs", id=uuid4(), name="Robotics", is_synthetic=True, created_at=NOW)
    refused(
        db,
        lambda c: insert(
            c,
            "users",
            id=uuid4(),
            email="a@example.invalid",
            display_name="B",
            is_synthetic=True,
            created_at=NOW,
        ),
    )
    refused(
        db,
        lambda c: insert(
            c, "clubs", id=uuid4(), name="Robotics", is_synthetic=True, created_at=NOW
        ),
    )


def membership(user: UUID, club: UUID, role: str) -> Callable[[Connection], None]:
    def action(conn: Connection) -> None:
        insert(conn, "memberships", user_id=user, club_id=club, role=role, created_at=NOW)

    return action


def test_a_membership_is_one_row_per_user_and_club_with_a_club_role(db: Engine) -> None:
    club, user = seed(db)
    with db.begin() as conn:
        membership(user, club, "ORGANIZER")(conn)
    refused(db, membership(user, club, "CLUB_ADMIN"))
    for bad_role in ("CAMPUS_ADMIN", "STUDENT", "organizer"):
        with db.begin() as conn:
            other_club = make_club(conn)
        refused(db, membership(user, other_club, bad_role))


def test_resource_availability_and_freshness_default_to_unknown(db: Engine) -> None:
    with db.begin() as conn:
        resource = make_resource(conn)
        row = conn.execute(
            text("SELECT availability_state, freshness_state FROM core.resources WHERE id = :id"),
            {"id": resource},
        ).one()
    assert tuple(row) == ("UNKNOWN", "UNKNOWN")


@pytest.mark.parametrize(
    "bad",
    [
        {"kind": "ROOM"},
        {"availability_state": "FREE"},
        {"availability_state": "AVAILABLE"},
        {"freshness_state": "FRESH"},
        {"capacity": -5},
    ],
)
def test_resources_reject_unknown_values(db: Engine, bad: dict[str, Any]) -> None:
    refused(db, lambda c: make_resource(c, **bad))


# ---- overrides ------------------------------------------------------------------------


def two_events(db: Engine) -> tuple[UUID, UUID, UUID]:
    club, user = seed(db)
    with db.begin() as conn:
        first = make_event(conn, club, user)
        second = make_event(conn, club, user)
    low, high = sorted((first, second))
    return low, high, user


def override(
    c: Connection, scope: str, a: UUID, b: UUID, user: UUID, reason: str = "Approved"
) -> None:
    insert(
        c,
        "schedule_overrides",
        id=uuid4(),
        scope=scope,
        event_a_id=a,
        event_b_id=b,
        reason=reason,
        authorized_by=user,
        created_at=NOW,
    )


def test_an_override_is_one_row_per_scope_and_pair(db: Engine) -> None:
    low, high, user = two_events(db)
    with db.begin() as conn:
        override(conn, "CAMPUS_GAP", low, high, user)
        override(conn, "VENUE_OVERLAP", low, high, user)
    refused(db, lambda c: override(c, "CAMPUS_GAP", low, high, user))


def test_an_override_pair_is_stored_in_canonical_order(db: Engine) -> None:
    low, high, user = two_events(db)
    refused(db, lambda c: override(c, "CAMPUS_GAP", high, low, user))
    refused(db, lambda c: override(c, "CAMPUS_GAP", low, low, user))


@pytest.mark.parametrize("reason", ["", "   "])
def test_an_override_needs_a_real_reason(db: Engine, reason: str) -> None:
    low, high, user = two_events(db)
    refused(db, lambda c: override(c, "CAMPUS_GAP", low, high, user, reason))


def test_an_override_scope_must_be_known(db: Engine) -> None:
    low, high, user = two_events(db)
    refused(db, lambda c: override(c, "IGNORE_ALL", low, high, user))


# ---- history --------------------------------------------------------------------------


def test_one_revision_number_per_event(db: Engine) -> None:
    club, user = seed(db)
    with db.begin() as conn:
        event = make_event(conn, club, user)
        insert(
            conn,
            "event_revisions",
            id=uuid4(),
            event_id=event,
            revision=1,
            current="{}",
            actor_id=user,
            created_at=NOW,
        )
    refused(
        db,
        lambda c: insert(
            c,
            "event_revisions",
            id=uuid4(),
            event_id=event,
            revision=1,
            current="{}",
            actor_id=user,
            created_at=NOW,
        ),
    )


def test_an_idempotency_key_is_unique_per_actor(db: Engine) -> None:
    _, user = seed(db)
    row = {
        "actor_id": user,
        "key": "k-1",
        "request_hash": "h",
        "status_code": 201,
        "response": "{}",
        "created_at": NOW,
    }
    with db.begin() as conn:
        insert(conn, "idempotency_keys", **row)
    refused(db, lambda c: insert(c, "idempotency_keys", **row))
    with db.begin() as conn:
        other = make_user(conn)
        insert(conn, "idempotency_keys", **{**row, "actor_id": other})


def test_an_audit_row_says_whether_a_user_or_an_agent_acted(db: Engine) -> None:
    _, user = seed(db)
    base = {
        "actor_id": user,
        "action": "CREATE_EVENT",
        "entity_type": "event",
        "outcome": "SUCCESS",
        "request_id": "r-1",
        "created_at": NOW,
    }
    with db.begin() as conn:
        insert(conn, "audit_events", id=uuid4(), via="USER", **base)
        insert(conn, "audit_events", id=uuid4(), via="AGENT", **base)
    refused(db, lambda c: insert(c, "audit_events", id=uuid4(), via="ROBOT", **base))


@pytest.mark.parametrize("table", ["event_revisions", "audit_events", "evidence_records"])
@pytest.mark.parametrize("operation", ["UPDATE", "DELETE"])
def test_history_cannot_be_changed_or_deleted(db: Engine, table: str, operation: str) -> None:
    club, user = seed(db)
    with db.begin() as conn:
        if table == "event_revisions":
            event = make_event(conn, club, user)
            insert(
                conn,
                table,
                id=uuid4(),
                event_id=event,
                revision=1,
                current="{}",
                actor_id=user,
                created_at=NOW,
            )
            change = "SET reason = 'edited'"
        elif table == "audit_events":
            insert(
                conn,
                table,
                id=uuid4(),
                actor_id=user,
                action="X",
                entity_type="event",
                outcome="SUCCESS",
                request_id="r",
                via="USER",
                created_at=NOW,
            )
            change = "SET outcome = 'EDITED'"
        else:
            make_evidence(conn, user)
            change = "SET reference = 'edited'"
    statement = f"UPDATE core.{table} {change}" if operation == "UPDATE" else None
    if statement is None:
        statement = f"DELETE FROM core.{table}"  # noqa: S608
    with pytest.raises(IntegrityError, match="append-only"), db.begin() as conn:
        conn.execute(text(statement))


# ---- shape ----------------------------------------------------------------------------


def test_every_timestamp_column_is_timezone_aware_and_every_id_a_uuid(db: Engine) -> None:
    with db.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT table_name, column_name, data_type FROM information_schema.columns "
                "WHERE table_schema = 'core' AND table_name <> 'alembic_version_core'"
            )
        ).all()
    assert rows
    for table, column, data_type in rows:
        if column.endswith("_at"):
            assert data_type == "timestamp with time zone", f"{table}.{column}"
        if (column == "id" or column.endswith("_id")) and column not in TEXT_IDS:
            assert data_type == "uuid", f"{table}.{column}"


def test_constraints_follow_the_naming_convention(db: Engine) -> None:
    with db.connect() as conn:
        names = set(
            conn.execute(
                text(
                    "SELECT conname FROM pg_constraint c "
                    "JOIN pg_namespace n ON n.oid = c.connamespace WHERE n.nspname = 'core'"
                )
            ).scalars()
        )
    assert {
        "pk_events",
        "ck_events_start_before_end",
        "ck_events_confirmed_is_verified",
        "fk_events_club_id_clubs",
        "uq_users_email",
        "ck_schedule_overrides_pair_order",
        "uq_schedule_overrides_pair_scope",
        "uq_event_revisions_event_revision",
    } <= names


def test_downgrade_removes_the_tables_and_their_triggers(db: Engine) -> None:
    with db.connect() as conn:
        command.downgrade(alembic_config(conn), "0001")
    with db.connect() as conn:
        tables = set(
            conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'core'")
            ).scalars()
        )
        functions = conn.execute(
            text(
                "SELECT count(*) FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'core' AND p.proname = 'forbid_history_change'"
            )
        ).scalar_one()
    assert tables == {"alembic_version_core"}
    assert functions == 0
