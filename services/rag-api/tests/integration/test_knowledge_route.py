import pytest
from app.main import app
from fastapi.testclient import TestClient

client = TestClient(app)


@pytest.fixture(name="client")
def client_fixture():
    return TestClient(app)


def test_answer_route_returns_grounded_answer_and_citations():
    payload = {"query": "How many days in advance to submit an event proposal?"}
    response = client.post("/v1/knowledge/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["query"] == payload["query"]
    assert data["status"] in ["grounded", "insufficient_evidence"]
    assert "citations" in data
    assert isinstance(data["citations"], list)
    assert "request_id" in data
    assert data["request_id"] is not None

    if data["status"] == "grounded":
        assert len(data["citations"]) > 0
        first_citation = data["citations"][0]
        assert "evidence_id" in first_citation
        assert "document_id" in first_citation
        assert "title" in first_citation
        assert "source_url" in first_citation
        assert "page_start" in first_citation
        assert "page_end" in first_citation
        assert "excerpt" in first_citation
        assert "document_version" in first_citation


def test_answer_route_abstains_with_empty_citations_when_insufficient_evidence(monkeypatch):
    from app.api.routes import knowledge

    def mock_generate_answer(query, evidence_chunks):
        return ("Insufficient evidence found in campus policy documents.", "insufficient_evidence")

    monkeypatch.setattr(knowledge.generator, "generate_answer", mock_generate_answer)

    payload = {"query": "What is the secret policy?"}
    response = client.post("/v1/knowledge/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "insufficient_evidence"
    assert data["citations"] == []
    assert "request_id" in data
    assert data["request_id"] is not None


def test_answer_route_respects_top_k():
    payload = {"query": "venue booking requirements", "top_k": 1}
    response = client.post("/v1/knowledge/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data["citations"]) <= 1


def test_answer_route_rejects_empty_query():
    payload = {"query": ""}
    response = client.post("/v1/knowledge/answer", json=payload)
    assert response.status_code == 422


def test_answer_route_with_dependency_override(client):
    from app.api.deps import get_grounded_generator

    class InjectedMockGenerator:
        def generate_answer(self, query, candidates=None, evidence_chunks=None):
            return ("Override answer test.", "grounded")

    app.dependency_overrides[get_grounded_generator] = InjectedMockGenerator
    try:
        response = client.post(
            "/v1/knowledge/answer",
            json={"query": "test override question"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Override answer test."
        assert "request_id" in data
        assert data["request_id"] is not None
    finally:
        app.dependency_overrides.pop(get_grounded_generator, None)
