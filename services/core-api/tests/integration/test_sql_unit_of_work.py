"""One real transaction: all of it commits, or none of it does (spine AD-8)."""

from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from app.domain.enums import EventStatus
from app.repositories.scheduling import CAMPUS_SCHEDULE_LOCK_KEY
from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.ports import AuditRecord, EventRecord, EvidenceData, StoredResponse
from tests.conftest import upgrade
from tests.integration.support import (
    END,
    NOW,
    START,
    make_club,
    make_resource,
    make_user,
)

pytestmark = pytest.mark.integration


class Seeded:
    def __init__(self, engine: Engine) -> None:
        with engine.begin() as conn:
            self.club = make_club(conn)
            self.user = make_user(conn)
            self.venue = make_resource(conn)
        self.factory = sessionmaker(engine, expire_on_commit=False)

    def uow(self) -> SqlUnitOfWork:
        return SqlUnitOfWork(self.factory)

    def event(self, **changes: object) -> EventRecord:
        base = EventRecord(
            id=uuid4(),
            club_id=self.club,
            title="Demo Day",
            description=None,
            start_at=START,
            end_at=END,
            resource_id=self.venue,
            expected_attendance=None,
            audience_tags=(),
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

    def audit(self, **changes: object) -> AuditRecord:
        base = AuditRecord(
            id=uuid4(),
            actor_id=self.user,
            action="CREATE_EVENT",
            entity_type="event",
            entity_id=None,
            outcome="SUCCESS",
            reason_code=None,
            request_id="req-1",
            via="USER",
            created_at=NOW,
        )
        return AuditRecord(**{**base.__dict__, **changes})


@pytest.fixture
def seeded(engine: Engine) -> Seeded:
    upgrade(engine)
    return Seeded(engine)


def count(engine: Engine, table: str) -> int:
    with engine.connect() as conn:
        return int(conn.execute(text(f"SELECT count(*) FROM core.{table}")).scalar_one())  # noqa: S608


# ---- commit and rollback --------------------------------------------------------------


def test_committed_work_is_visible_to_the_next_transaction(seeded: Seeded, engine: Engine) -> None:
    record = seeded.event()
    with seeded.uow() as uow:
        uow.schedule.events.insert(record)
        uow.commit()
    with seeded.uow() as uow:
        assert uow.events.get(record.id) == record


def test_leaving_without_committing_discards_everything(seeded: Seeded, engine: Engine) -> None:
    with seeded.uow() as uow:
        uow.schedule.events.insert(seeded.event())
        uow.audit.add(seeded.audit())
    assert count(engine, "events") == 0
    assert count(engine, "audit_events") == 0


def test_an_exception_discards_everything(seeded: Seeded, engine: Engine) -> None:
    def work_that_fails() -> None:
        with seeded.uow() as uow:
            uow.schedule.events.insert(seeded.event())
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        work_that_fails()
    assert count(engine, "events") == 0


def test_a_database_error_part_way_through_rolls_back_the_earlier_writes(
    seeded: Seeded, engine: Engine
) -> None:
    good = seeded.event()
    bad = seeded.event(resource_id=uuid4())  # a venue that does not exist

    def write_both() -> None:
        with seeded.uow() as uow:
            uow.schedule.events.insert(good)
            uow.schedule.events.insert(bad)
            uow.commit()

    with pytest.raises(IntegrityError):
        write_both()
    assert count(engine, "events") == 0


def test_two_transactions_do_not_see_each_others_uncommitted_work(seeded: Seeded) -> None:
    record = seeded.event()
    with seeded.uow() as writer, seeded.uow() as reader:
        writer.schedule.events.insert(record)
        assert reader.events.get(record.id) is None
        writer.commit()
    with seeded.uow() as reader:
        assert reader.events.get(record.id) is not None


# ---- the campus lock is tied to the transaction ---------------------------------------


def _lock_is_free(engine: Engine) -> bool:
    with engine.connect() as other:
        taken = other.execute(
            text("SELECT pg_try_advisory_xact_lock(:key)"), {"key": CAMPUS_SCHEDULE_LOCK_KEY}
        ).scalar_one()
        other.rollback()
    return bool(taken)


def test_the_lock_is_released_when_the_transaction_commits(seeded: Seeded, engine: Engine) -> None:
    with seeded.uow() as uow:
        uow.schedule.lock.acquire()
        assert _lock_is_free(engine) is False
        uow.commit()
    assert _lock_is_free(engine) is True


def test_the_lock_is_released_when_the_transaction_is_abandoned(
    seeded: Seeded, engine: Engine
) -> None:
    with seeded.uow() as uow:
        uow.schedule.lock.acquire()
        assert _lock_is_free(engine) is False
    assert _lock_is_free(engine) is True


def test_the_lock_is_released_when_the_transaction_fails(seeded: Seeded, engine: Engine) -> None:
    def lock_then_fail() -> None:
        with seeded.uow() as uow:
            uow.schedule.lock.acquire()
            raise RuntimeError("boom")

    with pytest.raises(RuntimeError, match="boom"):
        lock_then_fail()
    assert _lock_is_free(engine) is True


# ---- history writers ------------------------------------------------------------------


def test_audit_evidence_and_idempotency_round_trip(seeded: Seeded, engine: Engine) -> None:
    audit = seeded.audit(action="TRANSITION_EVENT", reason_code=None)
    evidence = EvidenceData(
        id=uuid4(),
        kind="EMAIL_REFERENCE",
        reference="archive/2026-10-09",
        issuer="OSA",
        captured_at=NOW,
        recorded_by=seeded.user,
        created_at=NOW,
    )
    stored = StoredResponse(request_hash="abc", status_code=201, response={"event": {"id": "x"}})
    with seeded.uow() as uow:
        uow.audit.add(audit)
        uow.evidence.add(evidence)
        uow.idempotency.put(seeded.user, "key-1", stored, NOW)
        uow.commit()
    with seeded.uow() as uow:
        assert uow.idempotency.get(seeded.user, "key-1") == stored
        assert uow.idempotency.get(seeded.user, "other") is None
    with engine.connect() as conn:
        row = conn.execute(text("SELECT action, outcome, via FROM core.audit_events")).one()
        assert tuple(row) == ("TRANSITION_EVENT", "SUCCESS", "USER")
        assert conn.execute(text("SELECT reference FROM core.evidence_records")).scalar_one() == (
            "archive/2026-10-09"
        )


def test_a_refusal_row_records_its_reason_code(seeded: Seeded, engine: Engine) -> None:
    with seeded.uow() as uow:
        uow.audit.add(seeded.audit(outcome="REFUSED", reason_code="CONFLICT_DETECTED", via="AGENT"))
        uow.commit()
    with engine.connect() as conn:
        row = conn.execute(text("SELECT outcome, reason_code, via FROM core.audit_events")).one()
    assert tuple(row) == ("REFUSED", "CONFLICT_DETECTED", "AGENT")


def test_the_same_key_cannot_be_stored_twice_for_one_actor(seeded: Seeded) -> None:
    stored = StoredResponse(request_hash="h", status_code=200, response={})
    with seeded.uow() as uow:
        uow.idempotency.put(seeded.user, "k", stored, NOW)
        uow.commit()

    def store_again() -> None:
        with seeded.uow() as uow:
            uow.idempotency.put(seeded.user, "k", stored, NOW + timedelta(seconds=1))
            uow.commit()

    with pytest.raises(IntegrityError):
        store_again()
