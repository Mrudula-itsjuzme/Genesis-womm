import json
import re

import pytest
import structlog
from fastapi import FastAPI
from fastapi.testclient import TestClient
from structlog.testing import capture_logs

from app.api.middleware import REQUEST_ID_HEADER, RequestIdMiddleware
from app.logging import configure_logging, redact_sensitive_keys


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestIdMiddleware)

    @app.get("/items/{item_id}")
    def read_item(item_id: str) -> dict[str, str]:
        return {"item_id": item_id}

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("secret internals")

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(make_app(), raise_server_exceptions=False)


def test_generates_a_request_id_when_absent(client: TestClient) -> None:
    response = client.get("/items/a")
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers[REQUEST_ID_HEADER])


def test_echoes_a_valid_inbound_request_id(client: TestClient) -> None:
    response = client.get("/items/a", headers={REQUEST_ID_HEADER: "web-123.abc_DEF"})
    assert response.headers[REQUEST_ID_HEADER] == "web-123.abc_DEF"


@pytest.mark.parametrize("bad", ["x" * 129, "has space", "semi;colon", "tab\tchar", "<script>"])
def test_replaces_a_malformed_inbound_request_id(client: TestClient, bad: str) -> None:
    response = client.get("/items/a", headers={REQUEST_ID_HEADER: bad})
    assert response.headers[REQUEST_ID_HEADER] != bad
    assert re.fullmatch(r"[0-9a-f]{32}", response.headers[REQUEST_ID_HEADER])


def test_header_is_present_on_unmatched_routes(client: TestClient) -> None:
    response = client.get("/nope")
    assert response.status_code == 404
    assert REQUEST_ID_HEADER in response.headers


def test_access_log_has_the_agreed_fields_and_nothing_sensitive(client: TestClient) -> None:
    with capture_logs() as logs:
        client.get(
            "/items/42?token=hunter2",
            headers={"Authorization": "Bearer abc.def.ghi", REQUEST_ID_HEADER: "req-1"},
        )
    (entry,) = [log for log in logs if log["event"] == "request"]
    assert entry["request_id"] == "req-1"
    assert entry["method"] == "GET"
    assert entry["route"] == "/items/{item_id}"
    assert entry["status"] == 200
    assert entry["actor_id"] is None
    assert isinstance(entry["latency_ms"], float)
    rendered = json.dumps(entry)
    assert "hunter2" not in rendered
    assert "abc.def.ghi" not in rendered
    # The route is logged as a template, never the concrete path with its identifiers.
    assert "/items/42" not in rendered


def test_unhandled_error_is_logged_as_500_without_leaking_the_message(
    client: TestClient,
) -> None:
    with capture_logs() as logs:
        response = client.get("/boom")
    assert response.status_code == 500
    (entry,) = [log for log in logs if log["event"] == "request"]
    assert entry["status"] == 500
    assert "secret internals" not in json.dumps(entry)


def test_redaction_masks_sensitive_keys_only() -> None:
    event = {"event": "x", "Authorization": "Bearer t", "token": "t", "route": "/a", "status": 200}
    result = redact_sensitive_keys(None, "info", dict(event))
    assert result["Authorization"] == "[redacted]"
    assert result["token"] == "[redacted]"
    assert result["route"] == "/a"
    assert result["status"] == 200


def test_configure_logging_emits_json(capsys: pytest.CaptureFixture[str]) -> None:
    configure_logging("INFO")
    structlog.get_logger().info("hello", request_id="r1", password="pw")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)
    assert payload["event"] == "hello"
    assert payload["request_id"] == "r1"
    assert payload["password"] == "[redacted]"
    assert payload["level"] == "info"
    assert payload["timestamp"].endswith("Z")
