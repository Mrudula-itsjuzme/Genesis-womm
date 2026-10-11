import io
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from app.api.deps import get_chroma_store
from app.main import app
from app.retrieval.chroma import ChromaStore
from fastapi.testclient import TestClient
from pypdf import PdfWriter


def generate_test_pdf_bytes(text_content: str) -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    buf = io.BytesIO()
    writer.write(buf)
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


def test_private_proposal_search_requires_authenticated_club_scope(
    test_client: TestClient, mock_chroma: ChromaStore
) -> None:
    app.dependency_overrides[get_chroma_store] = lambda: mock_chroma
    try:
        for payload in [
            {"query": "student names", "collection": "proposals"},
            {"query": "faculty contact", "collection": "proposals", "event_id": str(uuid4())},
            {"query": "student names", "event_id": str(uuid4())},
        ]:
            response = test_client.post("/v1/retrieval/search", json=payload)
            assert response.status_code == 403
            assert "candidates" not in response.json()
    finally:
        app.dependency_overrides.clear()
