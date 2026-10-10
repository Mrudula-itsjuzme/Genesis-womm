"""Two sessions racing (spine AD-4): enforcement is not claimed until this passes.

The pre-check in one session cannot see the other session's uncommitted confirmation. Without
the campus lock both pass and both commit, double-booking the venue. The control test turns
the lock off and expects exactly that, so a green result for the real run means something.
"""

from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from threading import Barrier, BrokenBarrierError, Thread
from types import TracebackType
from typing import Self

import pytest

from app.repositories.unit_of_work import SqlUnitOfWork
from app.services.errors import ConflictDetectedError
from app.services.ports import EventRecord
from app.services.schedule_store import (
    EventWriter,
    OverrideWriter,
    RevisionWriter,
    ScheduleLock,
)
from app.services.schedule_write import NewEvent, WriteResult
from tests.integration.world import PROOF, E, World, at, ctx, draft, submitted

pytestmark = pytest.mark.integration

RENDEZVOUS_SECONDS = 1.5
JOIN_SECONDS = 30


class _NoLock:
    def acquire(self) -> None:
        return None


class _RendezvousEvents:
    """Waits for the other session just before writing, to force the check/write interleaving."""

    def __init__(self, inner: EventWriter, barrier: Barrier) -> None:
        self._inner = inner
        self._barrier = barrier

    def insert(self, record: EventRecord) -> None:
        self._inner.insert(record)

    def update(self, record: EventRecord, *, expected_revision: int) -> None:
        # With the lock the other session is parked waiting for it, so this times out and we
        # proceed alone. Without the lock the other session arrives and both write at once.
        with suppress(BrokenBarrierError):
            self._barrier.wait(timeout=RENDEZVOUS_SECONDS)
        self._inner.update(record, expected_revision=expected_revision)


@dataclass(frozen=True)
class _Writers:
    lock: ScheduleLock
    events: EventWriter
    revisions: RevisionWriter
    overrides: OverrideWriter


class RacingUnitOfWork:
    """A real PostgreSQL unit of work, optionally without the lock and with a rendezvous."""

    def __init__(self, inner: SqlUnitOfWork, barrier: Barrier, *, take_lock: bool) -> None:
        self._inner = inner
        self.events = inner.events
        self.clubs = inner.clubs
        self.resources = inner.resources
        self.overrides = inner.overrides
        self.actors = inner.actors
        self.audit = inner.audit
        self.evidence = inner.evidence
        self.idempotency = inner.idempotency
        self.schedule = _Writers(
            lock=inner.schedule.lock if take_lock else _NoLock(),
            events=_RendezvousEvents(inner.schedule.events, barrier),
            revisions=inner.schedule.revisions,
            overrides=inner.schedule.overrides,
        )

    def __enter__(self) -> Self:
        self._inner.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self._inner.__exit__(exc_type, exc, tb)

    def commit(self) -> None:
        self._inner.commit()


def run_in_parallel(attempts: list[Callable[[], str]]) -> list[str]:
    """Start every attempt at the same moment and collect what each reported."""
    start = Barrier(len(attempts))
    results: list[str] = [""] * len(attempts)

    def runner(index: int, attempt: Callable[[], str]) -> None:
        start.wait(timeout=10)
        try:
            results[index] = attempt()
        except Exception as error:  # reported to the test, which asserts on it
            results[index] = f"error: {error!r}"

    threads = [Thread(target=runner, args=(i, a)) for i, a in enumerate(attempts)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=JOIN_SECONDS)
    assert not any(thread.is_alive() for thread in threads), "a session is stuck"
    return results


# ---- two sessions, one venue ----------------------------------------------------------


def double_booking_pair(world: World) -> tuple[WriteResult, WriteResult]:
    first = submitted(world, start=(10, 0), end=(12, 0))
    second = submitted(world, world.other, club=world.club_b, start=(11, 0), end=(13, 0))
    return first, second


def race(world: World, *, take_lock: bool) -> list[str]:
    first, second = double_booking_pair(world)
    barrier = Barrier(2)
    svc = world.service_over(
        lambda: RacingUnitOfWork(SqlUnitOfWork(world.factory), barrier, take_lock=take_lock)
    )

    def confirming(event: WriteResult, name: str) -> Callable[[], str]:
        def attempt() -> str:
            try:
                svc.transition_event(
                    ctx(world.campus, request_id=name),
                    event.event.id,
                    E.CONFIRMED,
                    expected_revision=event.event.revision,
                    evidence=PROOF,
                )
            except ConflictDetectedError:
                return "refused"
            return "confirmed"

        return attempt

    return sorted(run_in_parallel([confirming(first, "a"), confirming(second, "b")]))


def test_with_the_lock_exactly_one_of_two_racing_confirmations_wins(world: World) -> None:
    assert race(world, take_lock=True) == ["confirmed", "refused"]
    assert world.count("events", "status = 'CONFIRMED'") == 1


def test_with_the_lock_the_loser_is_audited_and_leaves_no_evidence(world: World) -> None:
    race(world, take_lock=True)
    assert world.count("evidence_records") == 1
    assert (
        world.count("audit_events", "outcome = 'REFUSED' AND reason_code = 'CONFLICT_DETECTED'")
        == 1
    )


def test_control_without_the_lock_both_confirm_and_the_venue_is_double_booked(
    world: World,
) -> None:
    """If this did not double-book, the harness could not see the race at all."""
    assert race(world, take_lock=False) == ["confirmed", "confirmed"]
    assert world.count("events", "status = 'CONFIRMED'") == 2


# ---- many sessions --------------------------------------------------------------------


def test_eight_sessions_racing_for_one_slot_produce_exactly_one_winner(world: World) -> None:
    events = [
        submitted(
            world,
            world.other if index % 2 else world.organizer,
            club=world.club_b if index % 2 else world.club_a,
            start=(10, 0),
            end=(12, 0),
        )
        for index in range(8)
    ]

    def confirming(event: WriteResult) -> Callable[[], str]:
        def attempt() -> str:
            try:
                world.svc.transition_event(
                    ctx(world.campus),
                    event.event.id,
                    E.CONFIRMED,
                    expected_revision=event.event.revision,
                    evidence=PROOF,
                )
            except ConflictDetectedError:
                return "refused"
            return "confirmed"

        return attempt

    results = run_in_parallel([confirming(event) for event in events])
    assert sorted(results) == ["confirmed"] + ["refused"] * 7
    assert world.count("events", "status = 'CONFIRMED'") == 1


def test_compatible_confirmations_all_succeed_together(world: World) -> None:
    # Exactly 120 minutes apart: the lock serialises them but must not make any of them fail.
    slots = [((6, 0), (7, 0)), ((9, 0), (10, 0)), ((12, 0), (13, 0)), ((15, 0), (16, 0))]
    events = [submitted(world, start=start, end=end) for start, end in slots]

    def confirming(event: WriteResult) -> Callable[[], str]:
        def attempt() -> str:
            world.svc.transition_event(
                ctx(world.campus),
                event.event.id,
                E.CONFIRMED,
                expected_revision=event.event.revision,
                evidence=PROOF,
            )
            return "confirmed"

        return attempt

    assert run_in_parallel([confirming(e) for e in events]) == ["confirmed"] * len(slots)
    assert world.count("events", "status = 'CONFIRMED'") == len(slots)


def test_tentative_proposals_never_fail_however_many_arrive_at_once(world: World) -> None:
    def creating(index: int) -> Callable[[], str]:
        def attempt() -> str:
            draft(world, start=(10, 0), end=(12, 0))
            return "saved"

        return attempt

    results = run_in_parallel([creating(i) for i in range(8)])
    assert results == ["saved"] * 8
    assert world.count("events") == 8


def test_a_retry_storm_with_one_key_creates_exactly_one_event(world: World) -> None:
    command = NewEvent(
        club_id=world.club_a,
        title="Retried",
        start_at=at(10),
        end_at=at(12),
        resource_id=world.hall,
    )

    def sending() -> str:
        result = world.svc.create_event(ctx(world.organizer, key="storm-1"), command)
        return "replayed" if result.replayed else "created"

    results = run_in_parallel([sending for _ in range(6)])
    assert sorted(results) == ["created"] + ["replayed"] * 5
    assert world.count("events") == 1
    assert world.count("audit_events", "outcome = 'SUCCESS'") == 1
