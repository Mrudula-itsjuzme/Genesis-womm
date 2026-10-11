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


def test_private_proposal_ingestion_is_disabled_and_does_not_fetch_pdf(test_client: TestClient, mock_chroma: ChromaStore) -> None:
    app.dependency_overrides[get_chroma_store] = lambda: mock_chroma
    payload = {
        "proposal_id": str(uuid4()),
        "event_id": str(uuid4()),
        "club_id": str(uuid4()),
        "revision": 1,
        "presigned_url": "https://example.invalid/private.pdf",
        "title": "Private faculty and student records",
        "submitted_by": "user-123",
    }
    try:
        with patch("httpx.get") as fetch:
            response = test_client.post("/v1/ingest/proposal", json=payload)
            assert response.status_code == 403
            fetch.assert_not_called()
        assert mock_chroma.count("proposals") == 0
    finally:
        app.dependency_overrides.clear()
