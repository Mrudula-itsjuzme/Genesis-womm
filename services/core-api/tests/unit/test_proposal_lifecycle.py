"""How a proposal moves through review and into (and out of) RAG (Implementation Plan 07).

The manager works on a plain record and talks to object storage and RAG only through ports, so
these run with simple fakes and no network.
"""

from collections.abc import Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import pytest

from app.domain.enums import ProposalStatus
from app.domain.lifecycle import InvalidTransitionError
from app.domain.time import FixedClock
from app.services.ports import ProposalRecord
from app.services.proposal_lifecycle import ProposalLifecycleManager

NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)
REVIEWER = uuid4()
S = ProposalStatus


@dataclass
class FakeStorage:
    presigned: str = "https://minio.local/presigned-pdf-url"
    presign_calls: list[tuple[str, str, int]] = field(default_factory=list)
    archived: list[tuple[str, str]] = field(default_factory=list)

    def upload_proposal(self, *args: Any, **kwargs: Any) -> tuple[str, str, int, str]:
        raise AssertionError("the lifecycle never uploads")

    def generate_presigned_download_url(
        self, bucket: str, object_key: str, expires_in_seconds: int = 900
    ) -> str:
        self.presign_calls.append((bucket, object_key, expires_in_seconds))
        return self.presigned

    def archive_proposal(self, source_bucket: str, source_key: str) -> str:
        self.archived.append((source_bucket, source_key))
        return f"archive/{source_key}"


@dataclass
class FakeRag:
    accepts: bool = True
    forgets: bool = True
    ingested: list[Mapping[str, Any]] = field(default_factory=list)
    deleted: list[tuple[UUID, UUID]] = field(default_factory=list)

    def ingest(self, payload: Mapping[str, Any]) -> bool:
        self.ingested.append(payload)
        return self.accepts

    def delete(self, proposal_id: UUID, event_id: UUID) -> bool:
        self.deleted.append((proposal_id, event_id))
        return self.forgets


@dataclass
class Rig:
    manager: ProposalLifecycleManager
    storage: FakeStorage
    rag: FakeRag


@pytest.fixture
def rig() -> Rig:
    storage, rag = FakeStorage(), FakeRag()
    return Rig(
        ProposalLifecycleManager(storage=storage, rag=rag, clock=FixedClock(NOW)), storage, rag
    )


def proposal(status: ProposalStatus = S.SUBMITTED, **changes: object) -> ProposalRecord:
    base = ProposalRecord(
        id=uuid4(),
        event_id=uuid4(),
        club_id=uuid4(),
        submitted_by=uuid4(),
        title="Sample Tech Symposium",
        minio_bucket="campuscue-proposals-dev",
        minio_key="proposals/c1/e1/p1/v1.pdf",
        submitted_at=NOW - timedelta(days=2),
        status=status,
    )
    for name, value in changes.items():
        setattr(base, name, value)
    return base


# ---- review decisions ------------------------------------------------------------------

DECISIONS = [
    ("approve_proposal", S.APPROVED),
    ("reject_proposal", S.REJECTED),
    ("request_revision", S.REVISION_REQUESTED),
]


@pytest.mark.parametrize(("method", "outcome"), DECISIONS)
@pytest.mark.parametrize("start", [S.SUBMITTED, S.UNDER_REVIEW])
def test_a_reviewer_decides_a_proposal_that_is_awaiting_review(
    rig: Rig, method: str, outcome: ProposalStatus, start: ProposalStatus
) -> None:
    record = proposal(start)

    decided = getattr(rig.manager, method)(record, reviewer_id=REVIEWER, review_note="Because.")

    assert decided is record
    assert decided.status is outcome
    assert (decided.reviewed_by, decided.reviewed_at, decided.review_note) == (
        REVIEWER,
        NOW,
        "Because.",
    )


@pytest.mark.parametrize(("method", "outcome"), DECISIONS)
@pytest.mark.parametrize(
    "start", [S.DRAFT, S.APPROVED, S.REJECTED, S.REVISION_REQUESTED, S.CHUNKED, S.ARCHIVED]
)
def test_a_proposal_that_is_not_awaiting_review_cannot_be_decided(
    rig: Rig, method: str, outcome: ProposalStatus, start: ProposalStatus
) -> None:
    record = proposal(start)
    before = replace(record)

    with pytest.raises(InvalidTransitionError) as refused:
        getattr(rig.manager, method)(record, reviewer_id=REVIEWER)

    assert (refused.value.current, refused.value.target) == (start, outcome)
    assert record == before, "a refused decision must leave the proposal untouched"


# ---- handing an approved proposal to RAG -----------------------------------------------


def test_an_approved_proposal_is_handed_to_rag_with_a_short_lived_link(rig: Rig) -> None:
    record = proposal(S.APPROVED, reviewed_by=REVIEWER)

    assert rig.manager.dispatch_rag_ingest(record) is True

    assert rig.storage.presign_calls == [(record.minio_bucket, record.minio_key, 900)]
    [payload] = rig.rag.ingested
    assert payload == {
        "proposal_id": str(record.id),
        "event_id": str(record.event_id),
        "club_id": str(record.club_id),
        "revision": record.revision,
        "presigned_url": "https://minio.local/presigned-pdf-url",
        "title": record.title,
        "submitted_by": str(record.submitted_by),
        "approved_by": str(REVIEWER),
    }
    assert (record.status, record.rag_ingested_at) == (S.CHUNKED, NOW)


def test_a_proposal_rag_refused_stays_approved_so_it_can_be_retried(rig: Rig) -> None:
    rig.rag.accepts = False
    record = proposal(S.APPROVED, reviewed_by=REVIEWER)

    assert rig.manager.dispatch_rag_ingest(record) is False

    assert (record.status, record.rag_ingested_at) == (S.APPROVED, None)


@pytest.mark.parametrize("start", [S.DRAFT, S.SUBMITTED, S.REJECTED, S.CHUNKED, S.ARCHIVED])
def test_only_an_approved_proposal_can_be_handed_to_rag(rig: Rig, start: ProposalStatus) -> None:
    with pytest.raises(ValueError, match="Only APPROVED proposals can be ingested"):
        rig.manager.dispatch_rag_ingest(proposal(start))

    assert rig.rag.ingested == []
    assert rig.storage.presign_calls == []


# ---- the 24 hour clean-up --------------------------------------------------------------


def test_cleanup_waits_a_full_day_after_the_event_concluded(rig: Rig) -> None:
    eligible = rig.manager.is_eligible_for_24h_cleanup

    assert eligible(NOW - timedelta(hours=23, minutes=59), now=NOW) is False
    assert eligible(NOW - timedelta(hours=24), now=NOW) is True
    assert eligible(NOW - timedelta(hours=48), now=NOW) is True
    assert eligible(None, now=NOW) is False


def test_cleanup_uses_the_clock_when_no_time_is_given(rig: Rig) -> None:
    assert rig.manager.is_eligible_for_24h_cleanup(NOW - timedelta(hours=24)) is True
    assert rig.manager.is_eligible_for_24h_cleanup(NOW - timedelta(hours=23)) is False


def test_cleanup_makes_rag_forget_the_proposal_then_archives_the_file(rig: Rig) -> None:
    record = proposal(S.CHUNKED, rag_ingested_at=NOW - timedelta(days=1))

    done = rig.manager.execute_lifecycle_cleanup(
        record, event_concluded_at=NOW - timedelta(hours=25), now=NOW
    )

    assert done is True
    assert rig.rag.deleted == [(record.id, record.event_id)]
    assert rig.storage.archived == [(record.minio_bucket, record.minio_key)]
    assert (record.status, record.rag_deleted_at) == (S.ARCHIVED, NOW)


def test_cleanup_that_is_too_early_does_nothing(rig: Rig) -> None:
    record = proposal(S.CHUNKED)

    done = rig.manager.execute_lifecycle_cleanup(
        record, event_concluded_at=NOW - timedelta(hours=23), now=NOW
    )

    assert done is False
    assert (rig.rag.deleted, rig.storage.archived, record.status) == ([], [], S.CHUNKED)


def test_the_file_is_kept_when_rag_cannot_forget_the_proposal(rig: Rig) -> None:
    rig.rag.forgets = False
    record = proposal(S.CHUNKED)

    done = rig.manager.execute_lifecycle_cleanup(
        record, event_concluded_at=NOW - timedelta(hours=48), now=NOW
    )

    assert done is False
    assert rig.storage.archived == [], "never archive the file while RAG still serves it"
    assert (record.status, record.rag_deleted_at) == (S.CHUNKED, None)


@pytest.mark.parametrize("start", [S.APPROVED, S.REJECTED, S.SUBMITTED])
def test_a_proposal_rag_never_held_is_archived_without_asking_rag(
    rig: Rig, start: ProposalStatus
) -> None:
    record = proposal(start)

    done = rig.manager.execute_lifecycle_cleanup(
        record, event_concluded_at=NOW - timedelta(hours=48), now=NOW
    )

    assert done is True
    assert rig.rag.deleted == []
    assert rig.storage.archived == [(record.minio_bucket, record.minio_key)]
    assert (record.status, record.rag_deleted_at) == (S.ARCHIVED, None)
