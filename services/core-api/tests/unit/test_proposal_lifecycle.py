from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.domain.enums import ProposalStatus
from app.domain.time import FixedClock
from app.models.proposal import Proposal
from app.services.minio_client import MinIOProposalStorage
from app.services.proposal_lifecycle import ProposalLifecycleManager

FIXED_TIME = datetime(2026, 10, 11, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def mock_storage() -> MagicMock:
    storage = MagicMock(spec=MinIOProposalStorage)
    storage.generate_presigned_download_url.return_value = "https://minio.local/presigned-pdf-url"
    storage.archive_proposal.return_value = "proposals-archive/club/event/prop/v1.pdf"
    return storage


@pytest.fixture
def mock_http_client() -> MagicMock:
    client = MagicMock()
    return client


@pytest.fixture
def fixed_clock() -> FixedClock:
    return FixedClock(FIXED_TIME)


@pytest.fixture
def lifecycle_mgr(
    mock_storage: MagicMock, mock_http_client: MagicMock, fixed_clock: FixedClock
) -> ProposalLifecycleManager:
    return ProposalLifecycleManager(
        minio_storage=mock_storage,
        clock=fixed_clock,
        rag_api_url="http://rag-api:8002",
        http_client=mock_http_client,
    )


@pytest.fixture
def sample_proposal() -> Proposal:
    return Proposal(
        event_id=uuid4(),
        club_id=uuid4(),
        submitted_by=uuid4(),
        title="Sample Tech Symposium",
        minio_bucket="campuscue-proposals-dev",
        minio_key="proposals/c1/e1/p1/v1.pdf",
        status=ProposalStatus.SUBMITTED,
    )


def test_approve_proposal(
    lifecycle_mgr: ProposalLifecycleManager, sample_proposal: Proposal
) -> None:
    reviewer = uuid4()
    updated = lifecycle_mgr.approve_proposal(
        sample_proposal, reviewer_id=reviewer, review_note="Looks great!"
    )
    assert updated.status == ProposalStatus.APPROVED
    assert updated.reviewed_by == reviewer
    assert updated.review_note == "Looks great!"
    assert updated.reviewed_at == FIXED_TIME


def test_reject_proposal(
    lifecycle_mgr: ProposalLifecycleManager, sample_proposal: Proposal
) -> None:
    reviewer = uuid4()
    updated = lifecycle_mgr.reject_proposal(
        sample_proposal, reviewer_id=reviewer, review_note="Budget exceeds limit"
    )
    assert updated.status == ProposalStatus.REJECTED
    assert updated.reviewed_by == reviewer


def test_request_revision(
    lifecycle_mgr: ProposalLifecycleManager, sample_proposal: Proposal
) -> None:
    reviewer = uuid4()
    updated = lifecycle_mgr.request_revision(
        sample_proposal, reviewer_id=reviewer, review_note="Add safety plan"
    )
    assert updated.status == ProposalStatus.REVISION_REQUESTED
    assert updated.reviewed_by == reviewer


def test_dispatch_rag_ingest_success(
    lifecycle_mgr: ProposalLifecycleManager,
    sample_proposal: Proposal,
    mock_http_client: MagicMock,
    mock_storage: MagicMock,
) -> None:
    sample_proposal.status = ProposalStatus.APPROVED
    sample_proposal.reviewed_by = uuid4()

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"status": "success", "chunks_ingested": 12}
    mock_http_client.post.return_value = mock_resp

    result = lifecycle_mgr.dispatch_rag_ingest(sample_proposal)
    assert result is True
    assert sample_proposal.status == ProposalStatus.CHUNKED
    assert sample_proposal.rag_ingested_at == FIXED_TIME

    mock_storage.generate_presigned_download_url.assert_called_once()
    mock_http_client.post.assert_called_once()
    call_args = mock_http_client.post.call_args
    assert call_args.args[0] == "http://rag-api:8002/v1/ingest/proposal"
    assert call_args.kwargs["json"]["presigned_url"] == "https://minio.local/presigned-pdf-url"


def test_dispatch_rag_ingest_fails_if_not_approved(
    lifecycle_mgr: ProposalLifecycleManager,
    sample_proposal: Proposal,
) -> None:
    sample_proposal.status = ProposalStatus.SUBMITTED
    with pytest.raises(ValueError, match="Only APPROVED proposals can be ingested"):
        lifecycle_mgr.dispatch_rag_ingest(sample_proposal)


def test_24h_cleanup_eligibility_boundary(lifecycle_mgr: ProposalLifecycleManager) -> None:
    now = FIXED_TIME

    # Exactly 23 hours 59 minutes ago -> not eligible
    concluded_23h = now - timedelta(hours=23, minutes=59)
    assert lifecycle_mgr.is_eligible_for_24h_cleanup(concluded_23h, now=now) is False

    # Exactly 24 hours ago -> eligible
    concluded_24h = now - timedelta(hours=24)
    assert lifecycle_mgr.is_eligible_for_24h_cleanup(concluded_24h, now=now) is True

    # 48 hours ago -> eligible
    concluded_48h = now - timedelta(hours=48)
    assert lifecycle_mgr.is_eligible_for_24h_cleanup(concluded_48h, now=now) is True

    # None concluded_at -> not eligible
    assert lifecycle_mgr.is_eligible_for_24h_cleanup(None, now=now) is False


def test_execute_lifecycle_cleanup(
    lifecycle_mgr: ProposalLifecycleManager,
    sample_proposal: Proposal,
    mock_http_client: MagicMock,
    mock_storage: MagicMock,
) -> None:
    now = FIXED_TIME
    concluded_at = now - timedelta(hours=25)

    sample_proposal.status = ProposalStatus.CHUNKED

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_http_client.request.return_value = mock_resp

    result = lifecycle_mgr.execute_lifecycle_cleanup(
        sample_proposal, event_concluded_at=concluded_at, now=now
    )
    assert result is True
    assert sample_proposal.status == ProposalStatus.ARCHIVED
    assert sample_proposal.rag_deleted_at == FIXED_TIME

    # Check RAG delete call
    mock_http_client.request.assert_called_once_with(
        "DELETE",
        f"http://rag-api:8002/v1/ingest/proposal/{sample_proposal.id}",
        json={"event_id": str(sample_proposal.event_id)},
    )
    # Check MinIO archive call
    mock_storage.archive_proposal.assert_called_once_with(
        source_bucket=sample_proposal.minio_bucket,
        source_key=sample_proposal.minio_key,
    )
