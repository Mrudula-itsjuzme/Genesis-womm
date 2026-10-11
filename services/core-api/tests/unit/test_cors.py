from fastapi.testclient import TestClient

from app.container import Container
from app.main import create_app
from app.services.readiness import ReadinessService
from tests.fakes import FakeReadinessProbe, make_settings


def _client() -> TestClient:
    container = Container(readiness=ReadinessService(FakeReadinessProbe(), "0001"))
    return TestClient(create_app(make_settings(), container), raise_server_exceptions=False)


def test_allowed_browser_origin_receives_preflight_permissions() -> None:
    response = _client().options(
        "/api/v1/events",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": (
                "Authorization, Content-Type, Idempotency-Key, X-Request-ID"
            ),
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3000"

    actual = _client().get("/health", headers={"Origin": "http://localhost:3000"})
    assert actual.headers["access-control-expose-headers"] == "X-Request-ID"


def test_unknown_browser_origin_receives_no_allow_origin_header() -> None:
    response = _client().get("/health", headers={"Origin": "https://untrusted.example"})

    assert "access-control-allow-origin" not in response.headers
