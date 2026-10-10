"""The database backs up the rules an agent proposal must obey (spine AD-9)."""

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config, upgrade
from tests.integration.support import NOW, make_club, make_event, make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def db(engine: Engine) -> Engine:
    upgrade(engine)
    return engine


def refused(db: Engine, action: Callable[[Connection], object]) -> None:
    with pytest.raises(IntegrityError), db.begin() as conn:
        action(conn)


def world(db: Engine) -> tuple[UUID, UUID]:
    with db.begin() as conn:
        return make_club(conn), make_user(conn)


def make_action(conn: Connection, club: UUID, user: UUID, **overrides: Any) -> UUID:
    action = uuid4()
    values: dict[str, Any] = {
        "id": action,
        "type": "CREATE_EVENT_DRAFT",
        "status": "PROPOSED",
        "summary": "Draft a robotics demo day",
        "requested_by": user,
        "club_id": club,
        "payload": "{}",
        "conflicts": "[]",
        "created_at": NOW,
        "updated_at": NOW,
    }
    values.update(overrides)
    names = ", ".join(values)
    params = ", ".join(
        f"CAST(:{n} AS jsonb)" if n in {"payload", "conflicts"} else f":{n}" for n in values
    )
    conn.execute(
        text(f"INSERT INTO core.agent_actions ({names}) VALUES ({params})"),  # noqa: S608
        values,
    )
    return action


def test_a_proposed_action_is_accepted(db: Engine) -> None:
    club, user = world(db)
    with db.begin() as conn:
        make_action(conn, club, user)


@pytest.mark.parametrize("kind", ["BOOK_EVENT", "CONFIRM_EVENT", "CREATE_OVERRIDE", "SEND_MESSAGE"])
def test_the_action_type_is_a_closed_set_with_no_authority_bearing_member(
    db: Engine, kind: str
) -> None:
    club, user = world(db)
    refused(db, lambda c: make_action(c, club, user, type=kind))


def test_an_unknown_status_is_refused(db: Engine) -> None:
    club, user = world(db)
    refused(db, lambda c: make_action(c, club, user, status="DONE"))


def test_a_blank_summary_is_refused(db: Engine) -> None:
    club, user = world(db)
    refused(db, lambda c: make_action(c, club, user, summary="   "))


def test_an_expected_revision_starts_at_one(db: Engine) -> None:
    club, user = world(db)
    refused(db, lambda c: make_action(c, club, user, expected_revision=0))


def test_a_proposed_action_has_not_been_decided(db: Engine) -> None:
    club, user = world(db)
    refused(db, lambda c: make_action(c, club, user, decided_by=user, decided_at=NOW))


def test_an_executed_action_says_who_confirmed_it_and_what_it_created(db: Engine) -> None:
    club, user = world(db)
    with db.begin() as conn:
        event = make_event(conn, club, user)
    decision: dict[str, Any] = {"status": "EXECUTED", "decided_by": user, "decided_at": NOW}
    created: dict[str, Any] = {"result_entity_type": "event", "result_entity_id": event}

    with db.begin() as conn:
        make_action(conn, club, user, **decision, **created)
    refused(db, lambda c: make_action(c, club, user, status="EXECUTED"))
    refused(db, lambda c: make_action(c, club, user, **decision))
    refused(db, lambda c: make_action(c, club, user, status="EXECUTED", **created))


def test_a_rejected_action_says_who_rejected_it(db: Engine) -> None:
    club, user = world(db)
    with db.begin() as conn:
        make_action(conn, club, user, status="REJECTED", decided_by=user, decided_at=NOW)
    refused(db, lambda c: make_action(c, club, user, status="REJECTED"))


def test_an_action_belongs_to_a_real_user_club_and_event(db: Engine) -> None:
    club, user = world(db)
    refused(db, lambda c: make_action(c, club, uuid4()))
    refused(db, lambda c: make_action(c, uuid4(), user))
    refused(db, lambda c: make_action(c, club, user, target_event_id=uuid4()))


def test_downgrade_removes_the_table_and_upgrade_restores_it(db: Engine) -> None:
    with db.connect() as connection:
        command.downgrade(alembic_config(connection), "0002")
    with db.connect() as connection:
        assert (
            connection.execute(text("SELECT to_regclass('core.agent_actions')")).scalar_one()
            is None
        )
    upgrade(db)
    with db.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('core.agent_actions')")).scalar_one()


def test_actions_are_not_append_only_because_a_decision_updates_them(db: Engine) -> None:
    club, user = world(db)
    with db.begin() as conn:
        action = make_action(conn, club, user)
        conn.execute(
            text(
                "UPDATE core.agent_actions SET status = 'REJECTED', decided_by = :u, "
                "decided_at = :t WHERE id = :id"
            ),
            {"u": user, "t": NOW, "id": action},
        )
