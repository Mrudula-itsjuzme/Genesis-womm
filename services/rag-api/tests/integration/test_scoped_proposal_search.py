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


def test_scoped_proposal_search_by_event_id(test_client: TestClient, mock_chroma: ChromaStore) -> None:
    app.dependency_overrides[get_chroma_store] = lambda: mock_chroma

    target_event_id = str(uuid4())
    other_event_id = str(uuid4())
    proposal_id_1 = str(uuid4())
    proposal_id_2 = str(uuid4())
    club_id = str(uuid4())

    pdf_target = generate_test_pdf_bytes("Target Event: Robotics Symposium in Hall A.")
    pdf_other = generate_test_pdf_bytes("Other Event: Music Concert in Open Ground.")

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.content = pdf_target
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.get", return_value=mock_resp):
        # Ingest target proposal
        resp1 = test_client.post(
            "/v1/ingest/proposal",
            json={
                "proposal_id": proposal_id_1,
                "event_id": target_event_id,
                "club_id": club_id,
                "revision": 1,
                "presigned_url": "https://minio.local/p1.pdf",
                "title": "Robotics Proposal",
                "submitted_by": "lead-rob",
            },
        )
        assert resp1.status_code == 200

        mock_resp.content = pdf_other
        resp2 = test_client.post(
            "/v1/ingest/proposal",
            json={
                "proposal_id": proposal_id_2,
                "event_id": other_event_id,
                "club_id": club_id,
                "revision": 1,
                "presigned_url": "https://minio.local/p2.pdf",
                "title": "Music Concert Proposal",
                "submitted_by": "lead-music",
            },
        )
        assert resp2.status_code == 200

    # 1. Search scoped to target_event_id
    search_target = test_client.post(
        "/v1/retrieval/search",
        json={
            "query": "Robotics",
            "collection": "proposals",
            "event_id": target_event_id,
            "top_k": 5,
        },
    )
    assert search_target.status_code == 200
    data_target = search_target.json()
    assert len(data_target["candidates"]) > 0
    assert all(target_event_id in c["source_url"] or target_event_id in c["evidence_id"] for c in data_target["candidates"])

    # 2. Search scoped to a non-existent event_id returns 0 chunks
    search_empty = test_client.post(
        "/v1/retrieval/search",
        json={
            "query": "Robotics",
            "collection": "proposals",
            "event_id": str(uuid4()),
            "top_k": 5,
        },
    )
    assert search_empty.status_code == 200
    assert len(search_empty.json()["candidates"]) == 0

    # 3. Default search queries policy corpus
    search_policy = test_client.post(
        "/v1/retrieval/search",
        json={"query": "Student club events submission deadline"},
    )
    assert search_policy.status_code == 200
    assert len(search_policy.json()["candidates"]) > 0

    app.dependency_overrides.clear()
