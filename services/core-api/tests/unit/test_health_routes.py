import tomllib
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import __version__
from app.api.middleware import REQUEST_ID_HEADER
from app.container import Container
from app.main import create_app
from app.schemas.common import ErrorEnvelope
from app.services.readiness import ReadinessService
from tests.fakes import FakeReadinessProbe, make_settings

SERVICE_ROOT = Path(__file__).resolve().parents[2]


def client_for(probe: FakeReadinessProbe, expected_head: str = "0001") -> TestClient:
    container = Container(engine=None, readiness=ReadinessService(probe, expected_head))
    app = create_app(make_settings(), container)
    return TestClient(app, raise_server_exceptions=False)


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((SERVICE_ROOT / "pyproject.toml").read_text())
    assert __version__ == pyproject["project"]["version"]


def test_health_is_liveness_only_and_ignores_the_database() -> None:
    probe = FakeReadinessProbe(reachable=False)
    response = client_for(probe).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "core-api", "version": __version__}
    assert probe.applied_calls == 0


def test_ready_reports_checks_when_everything_is_up() -> None:
    response = client_for(FakeReadinessProbe(applied="0001")).get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"database": True, "migrations": True},
        "migration_head": "0001",
        "expected_head": "0001",
        "informational": {},
    }


def test_ready_is_503_with_the_envelope_when_the_database_is_down() -> None:
    response = client_for(FakeReadinessProbe(reachable=False)).get(
        "/ready", headers={REQUEST_ID_HEADER: "probe-1"}
    )
    assert response.status_code == 503
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.code.value == "DEPENDENCY_UNAVAILABLE"
    assert envelope.request_id == "probe-1"
    assert {"check": "database", "ok": False} in envelope.details
    assert {"check": "migrations", "ok": False} in envelope.details


def test_ready_is_503_when_migrations_are_behind() -> None:
    response = client_for(FakeReadinessProbe(applied="0000")).get("/ready")
    assert response.status_code == 503
    assert {"check": "migrations", "ok": False} in response.json()["details"]
    assert {"check": "database", "ok": True} in response.json()["details"]


@pytest.mark.parametrize("path", ["/health", "/ready"])
def test_probes_carry_a_request_id(path: str) -> None:
    assert REQUEST_ID_HEADER in client_for(FakeReadinessProbe()).get(path).headers


def test_openapi_describes_the_probes() -> None:
    schema = client_for(FakeReadinessProbe()).get("/openapi.json").json()
    assert schema["info"]["title"] == "CampusCue Core API"
    assert schema["info"]["version"] == __version__
    ready = schema["paths"]["/ready"]["get"]["responses"]
    assert "200" in ready
    assert ready["503"]["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ErrorEnvelope"
    }
