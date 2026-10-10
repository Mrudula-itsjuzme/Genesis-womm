from uuid import uuid4

from app.domain.enums import ProposalStatus
from app.models.proposal import Proposal


def test_proposal_model_defaults() -> None:
    event_id = uuid4()
    club_id = uuid4()
    user_id = uuid4()

    proposal = Proposal(
        event_id=event_id,
        club_id=club_id,
        submitted_by=user_id,
        title="Annual Tech Symposium Proposal",
        minio_bucket="campuscue-proposals-dev",
        minio_key=f"proposals/{club_id}/{event_id}/prop-1/v1.pdf",
    )

    assert proposal.event_id == event_id
    assert proposal.club_id == club_id
    assert proposal.submitted_by == user_id
    assert proposal.revision == 1
    assert proposal.status == ProposalStatus.SUBMITTED
    assert proposal.rag_ingested_at is None
    assert proposal.rag_deleted_at is None
    assert proposal.reviewed_by is None
    assert proposal.__tablename__ == "proposals"


def test_proposal_status_enum_values() -> None:
    expected = {
        "DRAFT",
        "SUBMITTED",
        "UNDER_REVIEW",
        "APPROVED",
        "REJECTED",
        "REVISION_REQUESTED",
        "CHUNKED",
        "ARCHIVED",
    }
    actual = {s.value for s in ProposalStatus}
    assert expected == actual
