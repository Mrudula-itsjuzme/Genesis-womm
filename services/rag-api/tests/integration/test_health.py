import pytest
from fastapi.testclient import TestClient
from app.main import app


client = TestClient(app)


@pytest.fixture(name="client")
def client_fixture():
    return TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rag-api"


def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True


def test_request_id_header_present(client):
    response = client.get("/health", headers={"X-Request-ID": "test-req-999"})
    assert response.status_code == 200
    assert response.headers.get("x-request-id") == "test-req-999"


def test_request_id_generated_when_missing(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert "x-request-id" in response.headers
    assert len(response.headers["x-request-id"]) > 0


def test_validation_error_envelope(client):
    response = client.post(
        "/v1/retrieval/search",
        json={"query": ""},
        headers={"X-Request-ID": "val-err-123"},
    )
    assert response.status_code == 422
    assert response.headers.get("x-request-id") == "val-err-123"
    data = response.json()
    assert data["code"] == "VALIDATION_ERROR"
    assert data["message"] == "Invalid request parameters"
    assert "details" in data
    assert data["request_id"] == "val-err-123"


def test_runtime_error_503_envelope(client, monkeypatch):
    from app.api.routes import retrieval

    def mock_search(*args, **kwargs):
        raise RuntimeError("Upstream LLM unavailable")

    monkeypatch.setattr(retrieval.dense_engine, "search", mock_search)

    response = client.post(
        "/v1/retrieval/search",
        json={"query": "test query"},
        headers={"X-Request-ID": "err-503-req"},
    )
    assert response.status_code == 503
    assert response.headers.get("x-request-id") == "err-503-req"
    data = response.json()
    assert data["code"] == "RAG_LLM_UNAVAILABLE"
    assert data["message"] == "Upstream LLM unavailable"
    assert data["details"] == []
    assert data["request_id"] == "err-503-req"

