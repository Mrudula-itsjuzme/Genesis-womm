"""The PostgreSQL store behind event proposals (Implementation Plan 07, spine AD-20)."""

from collections.abc import Iterator
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from app.domain.enums import ProposalStatus
from app.repositories.proposals import SqlProposalStore
from app.services.ports import ProposalRecord
from tests.conftest import upgrade
from tests.integration.support import NOW, make_club, make_event, make_user

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
        self.reviewer = make_user(conn, admin=True)
        self.event = make_event(conn, self.club, self.user)
        self.other_event = make_event(conn, self.club, self.user)
        self.store = SqlProposalStore(session)

    def proposal(self, **changes: object) -> ProposalRecord:
        base = ProposalRecord(
            id=uuid4(),
            event_id=self.event,
            club_id=self.club,
            submitted_by=self.user,
            title="Robotics Demo Day proposal",
            minio_bucket="campuscue-proposals-dev",
            minio_key="proposals/c/e/p/v1.pdf",
            submitted_at=NOW,
            file_size_bytes=1234,
            sha256_hash="a" * 64,
        )
        for name, value in changes.items():
            setattr(base, name, value)
        return base


@pytest.fixture
def world(session: Session) -> World:
    return World(session)


def test_a_proposal_round_trips_with_every_field(world: World) -> None:
    saved = world.proposal(
        revision=3,
        reviewed_by=world.reviewer,
        reviewed_at=NOW + timedelta(hours=1),
        review_note="Needs a safety plan",
        rag_ingested_at=NOW + timedelta(hours=2),
        rag_deleted_at=NOW + timedelta(hours=30),
    )

    world.store.add(saved)

    assert world.store.get(saved.id) == saved


def test_an_unknown_proposal_is_none(world: World) -> None:
    assert world.store.get(uuid4()) is None


def test_the_first_upload_for_an_event_is_revision_one_and_each_event_counts_alone(
    world: World,
) -> None:
    assert world.store.next_revision(world.event) == 1

    world.store.add(world.proposal(revision=1))
    world.store.add(world.proposal(revision=2))
    world.store.add(world.proposal(event_id=world.other_event, revision=1))

    assert world.store.next_revision(world.event) == 3
    assert world.store.next_revision(world.other_event) == 2


def test_saving_records_the_review_and_the_rag_dates(world: World) -> None:
    saved = world.proposal()
    world.store.add(saved)
    saved.status = ProposalStatus.CHUNKED
    saved.reviewed_by = world.reviewer
    saved.reviewed_at = NOW + timedelta(hours=1)
    saved.review_note = "Looks good"
    saved.rag_ingested_at = NOW + timedelta(hours=2)

    won = world.store.save(saved, expected_status=ProposalStatus.SUBMITTED)

    assert won is True
    assert world.store.get(saved.id) == saved


def test_saving_does_not_overwrite_what_identifies_the_proposal(world: World) -> None:
    saved = world.proposal()
    world.store.add(saved)
    tampered = world.proposal(id=saved.id, title="A different title", club_id=uuid4())
    tampered.status = ProposalStatus.UNDER_REVIEW

    world.store.save(tampered, expected_status=ProposalStatus.SUBMITTED)

    stored = world.store.get(saved.id)
    assert stored is not None
    assert (stored.title, stored.club_id) == (saved.title, saved.club_id)


def test_a_proposal_is_saved_only_if_it_is_still_in_the_expected_state(world: World) -> None:
    saved = world.proposal()
    world.store.add(saved)
    saved.status = ProposalStatus.APPROVED
    saved.reviewed_by = world.reviewer
    saved.reviewed_at = NOW
    assert world.store.save(saved, expected_status=ProposalStatus.SUBMITTED)

    late = world.proposal(id=saved.id)
    late.status = ProposalStatus.REJECTED
    late.reviewed_by = world.reviewer
    late.reviewed_at = NOW
    lost = world.store.save(late, expected_status=ProposalStatus.SUBMITTED)

    assert lost is False
    stored = world.store.get(saved.id)
    assert stored is not None
    assert stored.status is ProposalStatus.APPROVED


def test_saving_an_unknown_proposal_wins_nothing(world: World) -> None:
    assert not world.store.save(world.proposal(), expected_status=ProposalStatus.SUBMITTED)


def test_two_sessions_reviewing_at_once_cannot_both_win(engine: Engine) -> None:
    upgrade(engine)
    with Session(engine, expire_on_commit=False) as setup:
        w = World(setup)
        saved = w.proposal()
        w.store.add(saved)
        setup.commit()
    outcomes = []
    for status in (ProposalStatus.APPROVED, ProposalStatus.REJECTED):
        with Session(engine, expire_on_commit=False) as session:
            decision = w.proposal(id=saved.id)
            decision.status = status
            decision.reviewed_by = w.reviewer
            decision.reviewed_at = NOW
            outcomes.append(
                SqlProposalStore(session).save(decision, expected_status=ProposalStatus.SUBMITTED)
            )
            session.commit()
    assert outcomes == [True, False]
