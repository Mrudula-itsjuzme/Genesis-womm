import io
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.api.deps import get_chroma_store
from app.main import app
from app.retrieval.chroma import ChromaStore
from fastapi.testclient import TestClient
from pypdf import PdfWriter


def generate_test_pdf_bytes(text: str = "Annual Tech Fest 2026 Proposal for Amrita University.") -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    # Write some minimal valid PDF bytes
    buf = io.BytesIO()
    writer.write(buf)
    # Ensure %PDF- header is present
    val = buf.getvalue()
    if not val.startswith(b"%PDF-"):
        val = b"%PDF-1.4\n" + val
    return val


@pytest.fixture
def test_client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def mock_chroma() -> ChromaStore:
    return ChromaStore(use_mock=True)


def test_ingest_and_delete_proposal_lifecycle(test_client: TestClient, mock_chroma: ChromaStore) -> None:
    app.dependency_overrides[get_chroma_store] = lambda: mock_chroma

    proposal_id = str(uuid4())
    event_id = str(uuid4())
    club_id = str(uuid4())

    pdf_bytes = generate_test_pdf_bytes("Proposing annual robotics symposium in Amrita Coimbatore Campus.")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = pdf_bytes
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        # 1. Ingest proposal
        payload = {
            "proposal_id": proposal_id,
            "event_id": event_id,
            "club_id": club_id,
            "revision": 1,
            "presigned_url": "https://minio.local/presigned-url.pdf",
            "title": "Robotics Symposium Proposal",
            "submitted_by": "user-123",
            "approved_by": "osa-admin",
        }
        resp = test_client.post("/v1/ingest/proposal", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["proposal_id"] == proposal_id
        assert data["event_id"] == event_id
        assert data["collection"] == "proposals"
        assert data["status"] == "success"

        # 2. Delete proposal chunks after lifecycle conclusion
        del_resp = test_client.request(
            "DELETE",
            f"/v1/ingest/proposal/{proposal_id}",
            json={"event_id": event_id},
        )
        assert del_resp.status_code == 200
        del_data = del_resp.json()
        assert del_data["proposal_id"] == proposal_id
        assert del_data["event_id"] == event_id
        assert del_data["status"] in ("success", "not_found")

    app.dependency_overrides.clear()
