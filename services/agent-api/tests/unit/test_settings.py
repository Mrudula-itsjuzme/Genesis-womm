from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from app.settings import Settings


def make(**overrides: Any) -> Settings:
    return Settings(_env_file=None, **overrides)


def test_defaults_match_spine_ad_11() -> None:
    settings = make()
    assert settings.app_env == "local"
    assert settings.agent_model_provider == "fake"
    assert settings.max_tool_calls == 6
    assert settings.turn_deadline_s == 20
    assert settings.tool_timeout_s == 5
    assert settings.groq_model == "llama-3.3-70b-versatile"


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_MODEL_PROVIDER", "groq")
    monkeypatch.setenv("MAX_TOOL_CALLS", "3")
    settings = make()
    assert settings.agent_model_provider == "groq"
    assert settings.max_tool_calls == 3


def test_unknown_provider_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make(agent_model_provider="openai")


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make(app_env="prod")


def test_the_agent_holds_no_core_signing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SESSION_SIGNING_KEY", "s" * 40)
    monkeypatch.setenv("DELEGATION_SIGNING_KEY", "d" * 40)
    fields = set(Settings.model_fields)
    assert not {name for name in fields if "signing" in name}
    assert "s" * 40 not in repr(make())


def test_tool_timeout_cannot_exceed_the_turn_deadline() -> None:
    with pytest.raises(ValidationError, match="TOOL_TIMEOUT_S"):
        make(tool_timeout_s=30.0, turn_deadline_s=20.0)


def test_internal_key_is_required_outside_local() -> None:
    with pytest.raises(ValidationError, match="INTERNAL_API_KEY"):
        make(app_env="test")
    assert make(app_env="test", internal_api_key=SecretStr("k" * 32)).app_env == "test"


def test_demo_rejects_the_local_only_placeholder_key() -> None:
    with pytest.raises(ValidationError, match="local-only"):
        make(app_env="demo", internal_api_key=SecretStr("local-only-internal-key"))


@pytest.mark.parametrize("field", ["core_api_url", "rag_api_url"])
def test_service_urls_must_be_http(field: str) -> None:
    with pytest.raises(ValidationError, match="http"):
        make(**{field: "core-api:8000"})


def test_service_url_trailing_slash_is_dropped() -> None:
    assert make(core_api_url="http://core-api:8000/").core_api_url == "http://core-api:8000"


def test_the_llm_key_never_appears_in_repr() -> None:
    assert "gsk_secretvalue" not in repr(make(groq_api_key=SecretStr("gsk_secretvalue")))
