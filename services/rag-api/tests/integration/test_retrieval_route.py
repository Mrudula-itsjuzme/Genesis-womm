from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


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
