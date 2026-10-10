import io
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.deps import get_minio_storage
from app.api.routes import proposals
from app.domain.enums import ProposalStatus

from app.services.minio_client import MinIOProposalStorage


def create_test_client(mock_storage: MagicMock) -> tuple[TestClient, FastAPI]:
    app = FastAPI()
    app.include_router(proposals.router)
    app.dependency_overrides[get_minio_storage] = lambda: mock_storage
    client = TestClient(app)
    return client, app


def test_proposal_routes_e2e() -> None:
    mock_storage = MagicMock(spec=MinIOProposalStorage)
    mock_storage.upload_proposal.return_value = (
        "campuscue-proposals-dev",
        "proposals/c1/e1/p1/v1.pdf",
        1234,
        "a" * 64,
    )
    mock_storage.generate_presigned_download_url.return_value = (
        "https://minio.local/presigned-pdf-url?sig=abc"
    )

    client, _ = create_test_client(mock_storage)

    club_id = uuid4()
    event_id = uuid4()
    pdf_bytes = b"%PDF-1.5 sample proposal payload"

    # 1. Upload proposal
    upload_resp = client.post(
        f"/api/v1/clubs/{club_id}/events/{event_id}/proposals",
        files={"file": ("proposal.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"title": "Robotics Workshop Proposal"},
    )
    assert upload_resp.status_code == 201
    data = upload_resp.json()
    assert data["status"] == ProposalStatus.SUBMITTED
    assert data["title"] == "Robotics Workshop Proposal"
    proposal_id = data["id"]

    # 2. Get download URL
    url_resp = client.get(f"/api/v1/proposals/{proposal_id}/download-url")
    assert url_resp.status_code == 200
    assert "sig=abc" in url_resp.json()["download_url"]

    # 3. Patch status -> approve
    patch_resp = client.patch(
        f"/api/v1/proposals/{proposal_id}/status",
        json={"action": "approve", "review_note": "Approved by Faculty Sponsor"},
    )
    assert patch_resp.status_code == 200
    patch_data = patch_resp.json()
    assert patch_data["status"] == ProposalStatus.APPROVED
    assert patch_data["review_note"] == "Approved by Faculty Sponsor"

    # 4. Get proposal details
    get_resp = client.get(f"/api/v1/proposals/{proposal_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == proposal_id


def test_proposal_upload_rejects_non_pdf() -> None:
    mock_storage = MagicMock(spec=MinIOProposalStorage)
    client, _ = create_test_client(mock_storage)

    club_id = uuid4()
    event_id = uuid4()

    resp = client.post(
        f"/api/v1/clubs/{club_id}/events/{event_id}/proposals",
        files={"file": ("not_a_pdf.txt", io.BytesIO(b"Hello world"), "text/plain")},
        data={"title": "Invalid Proposal"},
    )
    assert resp.status_code == 400
    assert "valid PDF" in resp.json()["detail"]
