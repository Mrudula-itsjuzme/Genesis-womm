"""Submitting, reading and reviewing an event's proposal document (Implementation Plan 07).

Real identities and the authorization rule table decide everything here: the club submits and
reads, only a campus admin reviews, and a delegated agent does none of it.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, ProposalStatus
from app.domain.lifecycle import InvalidTransitionError, NotAuthorizedError
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.services.errors import (
    InvalidRequestError,
    NotFoundError,
    StorageUnavailableError,
)
from app.services.ports import ProposalRecord, ProposalUnitOfWork
from app.services.proposal_lifecycle import ProposalLifecycleManager
from app.services.proposals import (
    MAX_PROPOSAL_BYTES,
    ProposalService,
    ReviewAction,
)
from app.services.schedule_write import RequestContext, ScheduleWriteService
from tests.fakes import InMemoryDatabase, SequentialIds
from tests.unit.test_schedule_write import (
    CAMPUS,
    CLUB_A,
    CLUB_ADMIN,
    CLUB_B,
    HALL,
    NOW,
    ORGANIZER,
    OTHER_CLUB,
    STRANGER,
    World,
    draft,
)

PDF = b"%PDF-1.7 a proposal"
S = ProposalStatus
AGENT = Actor(user_id=ORGANIZER.user_id, memberships=ORGANIZER.memberships, via_agent=True)


@dataclass
class FakeStorage:
    fail_upload: bool = False
    uploads: list[tuple[UUID, UUID, UUID, int, bytes]] = field(default_factory=list)
    presigned: list[tuple[str, str, int]] = field(default_factory=list)
    archived: list[tuple[str, str]] = field(default_factory=list)

    def upload_proposal(
        self,
        club_id: UUID,
        event_id: UUID,
        proposal_id: UUID,
        revision: int,
        file_bytes: bytes,
        content_type: str = "application/pdf",
    ) -> tuple[str, str, int, str]:
        if self.fail_upload:
            raise ConnectionError("minio-internal:9000 refused the connection")
        self.uploads.append((club_id, event_id, proposal_id, revision, file_bytes))
        return (
            "bucket-dev",
            f"proposals/{club_id}/{event_id}/{proposal_id}/v{revision}.pdf",
            len(file_bytes),
            "a" * 64,
        )

    def generate_presigned_download_url(
        self, bucket: str, object_key: str, expires_in_seconds: int = 900
    ) -> str:
        self.presigned.append((bucket, object_key, expires_in_seconds))
        return f"https://minio.local/{object_key}?sig=abc"

    def archive_proposal(self, source_bucket: str, source_key: str) -> str:
        self.archived.append((source_bucket, source_key))
        return "archived"


@dataclass
class FakeRag:
    accepts: bool = True
    ingested: list[Mapping[str, Any]] = field(default_factory=list)

    def ingest(self, payload: Mapping[str, Any]) -> bool:
        self.ingested.append(payload)
        return self.accepts

    def delete(self, proposal_id: UUID, event_id: UUID) -> bool:
        return True


@dataclass
class Rig:
    world: World
    svc: ProposalService
    storage: FakeStorage
    rag: FakeRag
    event: UUID

    @property
    def db(self) -> InMemoryDatabase:
        return self.world.db


def build(service_class: type[ProposalService] = ProposalService) -> Rig:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {HALL: AvailabilityState.UNKNOWN}
    ids, clock = SequentialIds(), FixedClock(NOW)
    writes = ScheduleWriteService(
        db.uow, clock=clock, ids=ids, policy=Policy(campus_gap=timedelta(minutes=120))
    )
    world = World(db, writes, ids)
    event = draft(world).event.id
    storage, rag = FakeStorage(), FakeRag()
    manager = ProposalLifecycleManager(storage=storage, rag=rag, clock=clock)
    svc = service_class(db.uow, storage=storage, manager=manager, clock=clock, ids=ids)
    return Rig(world, svc, storage, rag, event)


@pytest.fixture
def rig() -> Rig:
    return build()


def ctx(actor: Actor, request_id: str = "req-1") -> RequestContext:
    return RequestContext(actor=actor, request_id=request_id)


def submit(rig: Rig, actor: Actor = ORGANIZER, **changes: Any) -> ProposalRecord:
    args: dict[str, Any] = {
        "club_id": CLUB_A,
        "event_id": rig.event,
        "title": "Robotics Demo Day proposal",
        "content": PDF,
    }
    args.update(changes)
    return rig.svc.submit(ctx(actor), **args)


def audit(rig: Rig) -> list[tuple[str, str, str | None, str]]:
    """The proposal audit trail, without the row for the event the fixture created."""
    return [
        (a.action, a.outcome, a.reason_code, a.via)
        for a in rig.db.state.audit
        if a.entity_type == "proposal"
    ]


# ---- submitting ------------------------------------------------------------------------


def test_a_club_member_submits_a_proposal_under_their_own_identity(rig: Rig) -> None:
    saved = submit(rig)

    assert (saved.status, saved.revision) == (S.SUBMITTED, 1)
    assert (saved.submitted_by, saved.club_id, saved.event_id) == (
        ORGANIZER.user_id,
        CLUB_A,
        rig.event,
    )
    assert saved.submitted_at == NOW
    assert (saved.file_size_bytes, saved.sha256_hash) == (len(PDF), "a" * 64)
    [(club, event, proposal, revision, content)] = rig.storage.uploads
    assert (club, event, proposal, revision, content) == (CLUB_A, rig.event, saved.id, 1, PDF)
    assert rig.db.state.proposals[saved.id].status is S.SUBMITTED
    assert audit(rig) == [("SUBMIT_PROPOSAL", "SUCCESS", None, "USER")]


def test_a_second_upload_for_the_same_event_is_the_next_revision(rig: Rig) -> None:
    submit(rig)

    assert submit(rig).revision == 2


def test_a_campus_admin_may_submit_for_any_club(rig: Rig) -> None:
    assert submit(rig, CAMPUS).submitted_by == CAMPUS.user_id


@pytest.mark.parametrize(
    "actor", [OTHER_CLUB, STRANGER, AGENT], ids=["other club", "no role", "agent"]
)
def test_only_a_member_of_the_clubs_own_team_may_submit(rig: Rig, actor: Actor) -> None:
    with pytest.raises(NotAuthorizedError):
        submit(rig, actor)

    assert rig.storage.uploads == []
    assert rig.db.state.proposals == {}
    assert audit(rig)[0][1:3] == ("REFUSED", "FORBIDDEN")


def test_the_event_must_exist_and_belong_to_that_club(rig: Rig) -> None:
    with pytest.raises(NotFoundError):
        submit(rig, event_id=uuid4())
    with pytest.raises(NotFoundError):
        submit(rig, OTHER_CLUB, club_id=CLUB_B)  # CLUB_B member, but the event is CLUB_A's

    assert rig.storage.uploads == []


@pytest.mark.parametrize(
    "changes",
    [
        {"content": b""},
        {"content": b"not a pdf at all"},
        {"content": b"x" * 10 + PDF},
        {"content": b"%PDF-" + b"x" * MAX_PROPOSAL_BYTES},
        {"title": ""},
        {"title": "   "},
        {"title": "t" * 256},
    ],
    ids=[
        "empty",
        "not a pdf",
        "pdf not first",
        "too large",
        "no title",
        "blank title",
        "long title",
    ],
)
def test_an_invalid_document_or_title_is_refused_before_anything_is_stored(
    rig: Rig, changes: dict[str, Any]
) -> None:
    with pytest.raises(InvalidRequestError):
        submit(rig, **changes)

    assert rig.storage.uploads == []
    assert rig.db.state.proposals == {}


def test_a_title_is_trimmed(rig: Rig) -> None:
    assert submit(rig, title="  Robotics  ").title == "Robotics"


def test_a_storage_failure_stores_no_proposal_and_leaks_nothing(rig: Rig) -> None:
    rig.storage.fail_upload = True

    with pytest.raises(StorageUnavailableError) as failed:
        submit(rig)

    assert rig.db.state.proposals == {}
    assert audit(rig) == [("SUBMIT_PROPOSAL", "REFUSED", "REFUSED", "USER")]
    assert "minio-internal" not in str(failed.value)


# ---- reading ---------------------------------------------------------------------------


def test_the_clubs_members_and_the_campus_read_a_proposal(rig: Rig) -> None:
    saved = submit(rig)

    for actor in (ORGANIZER, CLUB_ADMIN, CAMPUS):
        assert rig.svc.get(actor, saved.id).id == saved.id


@pytest.mark.parametrize(
    "actor", [OTHER_CLUB, STRANGER, AGENT], ids=["other club", "no role", "agent"]
)
def test_nobody_else_reads_it(rig: Rig, actor: Actor) -> None:
    saved = submit(rig)

    with pytest.raises(NotAuthorizedError):
        rig.svc.get(actor, saved.id)


def test_an_unknown_proposal_is_not_found(rig: Rig) -> None:
    with pytest.raises(NotFoundError):
        rig.svc.get(ORGANIZER, uuid4())


def test_a_download_link_is_short_lived_and_audited(rig: Rig) -> None:
    saved = submit(rig)

    link = rig.svc.download_url(ctx(ORGANIZER), saved.id)

    assert (link.url, link.expires_in_seconds) == (
        f"https://minio.local/{saved.minio_key}?sig=abc",
        900,
    )
    assert rig.storage.presigned == [(saved.minio_bucket, saved.minio_key, 900)]
    assert ("DOWNLOAD_PROPOSAL", "SUCCESS", None, "USER") in audit(rig)


@pytest.mark.parametrize(
    "actor", [OTHER_CLUB, STRANGER, AGENT], ids=["other club", "no role", "agent"]
)
def test_no_link_is_made_for_someone_who_may_not_read_it(rig: Rig, actor: Actor) -> None:
    saved = submit(rig)

    with pytest.raises(NotAuthorizedError):
        rig.svc.download_url(ctx(actor), saved.id)

    assert rig.storage.presigned == []


# ---- reviewing -------------------------------------------------------------------------


def test_a_campus_admin_approves_and_rag_is_told_who_approved_it(rig: Rig) -> None:
    saved = submit(rig)

    reviewed = rig.svc.review(ctx(CAMPUS), saved.id, ReviewAction.APPROVE, "Looks good")

    assert reviewed.status is S.CHUNKED
    assert (reviewed.reviewed_by, reviewed.review_note) == (CAMPUS.user_id, "Looks good")
    [payload] = rig.rag.ingested
    assert payload["approved_by"] == str(CAMPUS.user_id)
    assert payload["submitted_by"] == str(ORGANIZER.user_id)
    stored = rig.db.state.proposals[saved.id]
    assert (stored.status, stored.rag_ingested_at) == (S.CHUNKED, NOW)
    assert ("REVIEW_PROPOSAL", "SUCCESS", None, "USER") in audit(rig)


def test_when_rag_is_down_the_proposal_stays_approved_and_the_review_stands(rig: Rig) -> None:
    rig.rag.accepts = False
    saved = submit(rig)

    reviewed = rig.svc.review(ctx(CAMPUS), saved.id, ReviewAction.APPROVE, None)

    assert reviewed.status is S.APPROVED
    stored = rig.db.state.proposals[saved.id]
    assert (stored.status, stored.reviewed_by, stored.rag_ingested_at) == (
        S.APPROVED,
        CAMPUS.user_id,
        None,
    )


@pytest.mark.parametrize(
    ("action", "outcome"),
    [(ReviewAction.REJECT, S.REJECTED), (ReviewAction.REQUEST_REVISION, S.REVISION_REQUESTED)],
)
def test_a_rejection_or_revision_request_never_reaches_rag(
    rig: Rig, action: ReviewAction, outcome: ProposalStatus
) -> None:
    saved = submit(rig)

    reviewed = rig.svc.review(ctx(CAMPUS), saved.id, action, "Add a safety plan")

    assert reviewed.status is outcome
    assert rig.rag.ingested == []
    assert rig.db.state.proposals[saved.id].reviewed_by == CAMPUS.user_id


@pytest.mark.parametrize(
    "actor",
    [ORGANIZER, CLUB_ADMIN, OTHER_CLUB, STRANGER, AGENT],
    ids=["organizer", "club admin", "other club", "no role", "agent"],
)
def test_only_a_campus_admin_reviews(rig: Rig, actor: Actor) -> None:
    saved = submit(rig)

    with pytest.raises(NotAuthorizedError):
        rig.svc.review(ctx(actor), saved.id, ReviewAction.APPROVE, None)

    stored = rig.db.state.proposals[saved.id]
    assert (stored.status, stored.reviewed_by) == (S.SUBMITTED, None)
    assert rig.rag.ingested == []


def test_a_decided_proposal_cannot_be_decided_again(rig: Rig) -> None:
    saved = submit(rig)
    rig.svc.review(ctx(CAMPUS), saved.id, ReviewAction.REJECT, None)

    with pytest.raises(InvalidTransitionError):
        rig.svc.review(ctx(CAMPUS), saved.id, ReviewAction.APPROVE, None)

    assert rig.db.state.proposals[saved.id].status is S.REJECTED


def test_reviewing_an_unknown_proposal_is_not_found(rig: Rig) -> None:
    with pytest.raises(NotFoundError):
        rig.svc.review(ctx(CAMPUS), uuid4(), ReviewAction.APPROVE, None)


class Racing(ProposalService):
    """Lets another reviewer reject the proposal right after this request has read it."""

    def _load(self, uow: ProposalUnitOfWork, proposal_id: UUID) -> ProposalRecord:
        record = super()._load(uow, proposal_id)
        with self._uow_factory() as other:
            competing = other.proposals.get(proposal_id)
            assert competing is not None
            competing.status = S.REJECTED
            competing.reviewed_by, competing.reviewed_at = uuid4(), NOW
            assert other.proposals.save(competing, expected_status=S.SUBMITTED)
            other.commit()
        return record


def test_two_reviewers_deciding_at_once_cannot_both_win() -> None:
    racing = build(Racing)
    saved = submit(racing)

    with pytest.raises(InvalidTransitionError):
        racing.svc.review(ctx(CAMPUS), saved.id, ReviewAction.APPROVE, None)

    assert racing.db.state.proposals[saved.id].status is S.REJECTED
    assert racing.rag.ingested == []


def test_every_refusal_is_audited_with_its_code(rig: Rig) -> None:
    saved = submit(rig)
    for attempt in (
        lambda: rig.svc.review(ctx(ORGANIZER), saved.id, ReviewAction.APPROVE, None),
        lambda: rig.svc.review(ctx(CAMPUS), uuid4(), ReviewAction.APPROVE, None),
        lambda: rig.svc.download_url(ctx(OTHER_CLUB), saved.id),
    ):
        with pytest.raises((NotAuthorizedError, NotFoundError)):
            attempt()

    refusals = [a for a in audit(rig) if a[1] == "REFUSED"]
    assert refusals == [
        ("REVIEW_PROPOSAL", "REFUSED", "FORBIDDEN", "USER"),
        ("REVIEW_PROPOSAL", "REFUSED", "NOT_FOUND", "USER"),
        ("DOWNLOAD_PROPOSAL", "REFUSED", "FORBIDDEN", "USER"),
    ]


def test_an_empty_upload_says_it_is_empty(rig: Rig) -> None:
    with pytest.raises(InvalidRequestError, match="empty"):
        submit(rig, content=b"")
