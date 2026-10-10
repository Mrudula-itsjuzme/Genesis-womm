import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api.errors import (
    STATUS_BY_CODE,
    ApiError,
    error_responses,
    install_error_handlers,
    not_implemented,
)
from app.api.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from app.domain.enums import ErrorCode
from app.schemas.common import ErrorEnvelope


class Payload(BaseModel):
    name: str
    age: int


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)
    install_error_handlers(app)

    @app.post("/payload")
    def post_payload(payload: Payload) -> Payload:
        return payload

    @app.get("/conflict")
    def conflict() -> None:
        raise ApiError(
            ErrorCode.CONFLICT_DETECTED,
            "The proposed time violates a scheduling rule.",
            details=[{"type": "VENUE_OVERLAP"}],
        )

    @app.get("/stale")
    def stale() -> None:
        raise ApiError(ErrorCode.STALE_REVISION, "Event changed since you loaded it.")

    @app.get("/stub")
    def stub() -> None:
        not_implemented("event creation")

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals: postgres://user:hunter2@db/x")

    @app.get("/documented", responses=error_responses(ErrorCode.CONFLICT_DETECTED))
    def documented() -> dict[str, str]:
        return {}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(make_app(), raise_server_exceptions=False)


def assert_envelope(response_json: dict[str, object], request_id: str) -> ErrorEnvelope:
    assert set(response_json) == {"code", "message", "details", "request_id"}
    envelope = ErrorEnvelope.model_validate(response_json)
    assert envelope.request_id == request_id
    return envelope


def test_api_error_renders_the_standard_envelope(client: TestClient) -> None:
    response = client.get("/conflict", headers={REQUEST_ID_HEADER: "req-7"})
    assert response.status_code == 409
    assert response.headers["content-type"] == "application/json"
    envelope = assert_envelope(response.json(), "req-7")
    assert envelope.code is ErrorCode.CONFLICT_DETECTED
    assert envelope.details == [{"type": "VENUE_OVERLAP"}]
    assert response.headers[REQUEST_ID_HEADER] == "req-7"


def test_stale_revision_is_409_and_distinct_from_conflict(client: TestClient) -> None:
    response = client.get("/stale")
    assert response.status_code == 409
    assert response.json()["code"] == "STALE_REVISION"


def test_validation_errors_are_422_without_echoing_input(client: TestClient) -> None:
    response = client.post("/payload", json={"name": "hunter2-secret", "age": "not-a-number"})
    assert response.status_code == 422
    envelope = assert_envelope(response.json(), response.headers[REQUEST_ID_HEADER])
    assert envelope.code is ErrorCode.VALIDATION_ERROR
    assert envelope.details
    for detail in envelope.details:
        assert set(detail) == {"loc", "msg", "type"}
    assert "hunter2-secret" not in response.text
    assert "not-a-number" not in response.text


def test_unknown_route_is_a_not_found_envelope(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    envelope = assert_envelope(response.json(), response.headers[REQUEST_ID_HEADER])
    assert envelope.code is ErrorCode.NOT_FOUND


def test_wrong_method_is_405_and_keeps_the_allow_header(client: TestClient) -> None:
    response = client.delete("/conflict")
    assert response.status_code == 405
    assert response.json()["code"] == "METHOD_NOT_ALLOWED"
    assert "GET" in response.headers["allow"]


def test_unhandled_exception_hides_internals(client: TestClient) -> None:
    response = client.get("/boom", headers={REQUEST_ID_HEADER: "req-9"})
    assert response.status_code == 500
    envelope = assert_envelope(response.json(), "req-9")
    assert envelope.code is ErrorCode.INTERNAL_ERROR
    assert envelope.details == []
    assert "hunter2" not in response.text
    assert "secret internals" not in response.text
    assert "Traceback" not in response.text
    assert response.headers[REQUEST_ID_HEADER] == "req-9"


def test_not_implemented_stub_is_501_with_the_envelope(client: TestClient) -> None:
    response = client.get("/stub")
    assert response.status_code == 501
    envelope = assert_envelope(response.json(), response.headers[REQUEST_ID_HEADER])
    assert envelope.code is ErrorCode.NOT_IMPLEMENTED
    assert "event creation" in envelope.message


def test_every_error_code_has_a_status() -> None:
    assert set(STATUS_BY_CODE) == set(ErrorCode)


def test_openapi_documents_error_responses_with_the_envelope_schema(client: TestClient) -> None:
    schema = client.get("/openapi.json").json()
    response_409 = schema["paths"]["/documented"]["get"]["responses"]["409"]
    assert response_409["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorEnvelope"
    }
    assert "code" in json.dumps(schema["components"]["schemas"]["ErrorEnvelope"])
