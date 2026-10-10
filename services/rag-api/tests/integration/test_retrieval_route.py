import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(name="client")
def client_fixture():
    return TestClient(app)


def test_search_endpoint_returns_candidates():
    payload = {"query": "venue approval deadline", "top_k": 3}
    response = client.post("/v1/retrieval/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert data["query"] == "venue approval deadline"
    assert len(data["candidates"]) > 0

    first_cand = data["candidates"][0]
    assert "evidence_id" in first_cand
    assert "document_id" in first_cand
    assert "excerpt" in first_cand
    assert "score" in first_cand
    assert first_cand["score"] > 0.0


def test_search_endpoint_respects_top_k():
    payload = {"query": "facility and venue", "top_k": 1}
    response = client.post("/v1/retrieval/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["candidates"]) <= 1


def test_search_endpoint_rejects_empty_query():
    payload = {"query": "", "top_k": 3}
    response = client.post("/v1/retrieval/search", json=payload)
    assert response.status_code == 422


def test_retrieval_search_with_injected_engine(client):
    response = client.post(
        "/v1/retrieval/search", json={"query": "facility booking", "top_k": 2}
    )
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert len(data["candidates"]) <= 2
    assert "request_id" in data
    assert data["request_id"] is not None


def test_retrieval_search_with_dependency_override(client):
    from app.api.deps import get_dense_retriever
    from app.retrieval.dense import DenseRetriever

    mock_dense = DenseRetriever(use_mock_embeddings=True)
    app.dependency_overrides[get_dense_retriever] = lambda: mock_dense
    try:
        response = client.post(
            "/v1/retrieval/search",
            json={"query": "facility booking", "top_k": 2},
        )
        assert response.status_code == 200
        data = response.json()
        assert "candidates" in data
        assert "request_id" in data
        assert data["request_id"] is not None
    finally:
        app.dependency_overrides.pop(get_dense_retriever, None)
