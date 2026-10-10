import tomllib
from pathlib import Path
from typing import Literal

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app import __version__
from app.api.middleware import REQUEST_ID_HEADER
from app.container import Container
from app.main import create_app
from app.orchestration.readiness import ReadinessService
from app.schemas.common import ErrorEnvelope
from app.settings import Settings

SERVICE_ROOT = Path(__file__).resolve().parents[2]


def client_for(provider: Literal["groq", "fake"], groq_key: str = "") -> TestClient:
    settings = Settings(
        _env_file=None, agent_model_provider=provider, groq_api_key=SecretStr(groq_key)
    )
    container = Container(
        readiness=ReadinessService(
            provider=settings.agent_model_provider, has_credential=bool(groq_key)
        )
    )
    return TestClient(create_app(settings, container), raise_server_exceptions=False)


def test_version_matches_pyproject() -> None:
    pyproject = tomllib.loads((SERVICE_ROOT / "pyproject.toml").read_text())
    assert __version__ == pyproject["project"]["version"]


def test_health_is_liveness_only() -> None:
    response = client_for("groq", groq_key="").get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "agent-api", "version": __version__}


def test_fake_provider_is_ready_without_any_credential_or_network() -> None:
    response = client_for("fake").get("/ready")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"model_provider": True},
        "informational": {"model_provider": "fake"},
    }


def test_groq_with_a_key_is_ready() -> None:
    assert client_for("groq", groq_key="gsk_dummy").get("/ready").status_code == 200


def test_groq_without_a_key_is_503_with_the_envelope() -> None:
    response = client_for("groq", groq_key="").get("/ready", headers={REQUEST_ID_HEADER: "p-1"})
    assert response.status_code == 503
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.code.value == "DEPENDENCY_UNAVAILABLE"
    assert envelope.request_id == "p-1"
    assert {"check": "model_provider", "ok": False} in envelope.details


def test_readiness_never_leaks_the_credential() -> None:
    text = client_for("groq", groq_key="gsk_supersecret").get("/ready").text
    assert "gsk_supersecret" not in text


@pytest.mark.parametrize("path", ["/health", "/ready"])
def test_probes_carry_a_request_id(path: str) -> None:
    assert REQUEST_ID_HEADER in client_for("fake").get(path).headers


def test_openapi_describes_the_probes() -> None:
    schema = client_for("fake").get("/openapi.json").json()
    assert schema["info"]["title"] == "CampusCue Agent API"
    assert schema["info"]["version"] == __version__
    assert schema["paths"]["/ready"]["get"]["responses"]["503"]["content"]["application/json"][
        "schema"
    ] == {"$ref": "#/components/schemas/ErrorEnvelope"}
