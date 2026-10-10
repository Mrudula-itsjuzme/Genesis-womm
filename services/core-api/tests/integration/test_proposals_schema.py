"""The database backs up the rules a proposal must obey (Implementation Plan 07)."""

from collections.abc import Callable
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from tests.conftest import alembic_config, upgrade
from tests.integration.support import NOW, insert, make_club, make_event, make_user

pytestmark = pytest.mark.integration


@pytest.fixture
def db(engine: Engine) -> Engine:
    upgrade(engine)
    return engine


def refused(db: Engine, action: Callable[[Connection], object]) -> None:
    with pytest.raises(IntegrityError), db.begin() as conn:
        action(conn)


def world(db: Engine) -> tuple[UUID, UUID, UUID]:
    with db.begin() as conn:
        club, user = make_club(conn), make_user(conn)
        return club, user, make_event(conn, club, user)


def make_proposal(conn: Connection, club: UUID, user: UUID, event: UUID, **overrides: Any) -> UUID:
    proposal = uuid4()
    values: dict[str, Any] = {
        "id": proposal,
        "event_id": event,
        "club_id": club,
        "submitted_by": user,
        "revision": 1,
        "status": "SUBMITTED",
        "title": "Robotics Demo Day proposal",
        "minio_bucket": "campuscue-proposals-dev",
        "minio_key": f"proposals/{club}/{event}/{proposal}/v1.pdf",
        "submitted_at": NOW,
    }
    values.update(overrides)
    insert(conn, "proposals", **values)
    return proposal


def test_a_submitted_proposal_is_accepted(db: Engine) -> None:
    club, user, event = world(db)
    with db.begin() as conn:
        make_proposal(conn, club, user, event)


@pytest.mark.parametrize(
    "status",
    ["DRAFT", "SUBMITTED", "UNDER_REVIEW", "ARCHIVED"],
)
def test_every_status_that_needs_no_reviewer_is_accepted_without_one(
    db: Engine, status: str
) -> None:
    club, user, event = world(db)
    with db.begin() as conn:
        make_proposal(conn, club, user, event, status=status)


def test_an_unknown_status_is_refused(db: Engine) -> None:
    club, user, event = world(db)
    refused(db, lambda c: make_proposal(c, club, user, event, status="PUBLISHED"))


@pytest.mark.parametrize("status", ["APPROVED", "REJECTED", "REVISION_REQUESTED", "CHUNKED"])
def test_a_decided_proposal_names_its_reviewer_and_when(db: Engine, status: str) -> None:
    club, user, event = world(db)
    extra: dict[str, Any] = {"rag_ingested_at": NOW} if status == "CHUNKED" else {}
    with db.begin() as conn:
        make_proposal(
            conn, club, user, event, status=status, reviewed_by=user, reviewed_at=NOW, **extra
        )
    refused(db, lambda c: make_proposal(c, club, user, event, status=status, **extra))
    refused(
        db, lambda c: make_proposal(c, club, user, event, status=status, reviewed_by=user, **extra)
    )


def test_a_chunked_proposal_says_when_rag_took_it(db: Engine) -> None:
    club, user, event = world(db)
    refused(
        db,
        lambda c: make_proposal(
            c, club, user, event, status="CHUNKED", reviewed_by=user, reviewed_at=NOW
        ),
    )


@pytest.mark.parametrize(
    "overrides",
    [
        {"revision": 0},
        {"title": "   "},
        {"file_size_bytes": -1},
        {"sha256_hash": "abc"},
    ],
    ids=["revision zero", "blank title", "negative size", "short hash"],
)
def test_malformed_values_are_refused(db: Engine, overrides: dict[str, Any]) -> None:
    club, user, event = world(db)
    refused(db, lambda c: make_proposal(c, club, user, event, **overrides))


def test_a_proposal_belongs_to_a_real_event_club_and_user(db: Engine) -> None:
    club, user, event = world(db)
    refused(db, lambda c: make_proposal(c, club, user, uuid4()))
    refused(db, lambda c: make_proposal(c, uuid4(), user, event))
    refused(db, lambda c: make_proposal(c, club, uuid4(), event))


def test_a_reviewer_must_be_a_real_user(db: Engine) -> None:
    club, user, event = world(db)
    refused(
        db,
        lambda c: make_proposal(
            c, club, user, event, status="APPROVED", reviewed_by=uuid4(), reviewed_at=NOW
        ),
    )


def test_downgrade_removes_the_table_and_upgrade_restores_it(db: Engine) -> None:
    with db.connect() as connection:
        command.downgrade(alembic_config(connection), "0003")
    with db.connect() as connection:
        gone = connection.execute(text("SELECT to_regclass('core.proposals')")).scalar_one()
        assert gone is None
    upgrade(db)
    with db.connect() as connection:
        assert connection.execute(text("SELECT to_regclass('core.proposals')")).scalar_one()
