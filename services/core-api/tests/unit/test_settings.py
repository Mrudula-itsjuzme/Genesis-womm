from typing import Any

import pytest
from pydantic import SecretStr, ValidationError

from app.settings import Settings

SESSION = "s" * 40
DELEGATION = "d" * 40
INTERNAL = "i" * 40


def make(**overrides: Any) -> Settings:
    values: dict[str, Any] = {
        "session_signing_key": SecretStr(SESSION),
        "delegation_signing_key": SecretStr(DELEGATION),
        "internal_api_key": SecretStr(INTERNAL),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def test_defaults_match_the_spine() -> None:
    settings = make()
    assert settings.app_env == "local"
    assert settings.campus_gap_minutes == 120
    assert settings.database_url.startswith("postgresql+psycopg://")


def test_reads_environment_variables(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CAMPUS_GAP_MINUTES", "90")
    monkeypatch.setenv("APP_ENV", "test")
    settings = make()
    assert settings.campus_gap_minutes == 90
    assert settings.app_env == "test"


def test_unknown_environment_is_rejected() -> None:
    with pytest.raises(ValidationError):
        make(app_env="prod")


def test_signing_keys_must_differ() -> None:
    with pytest.raises(ValidationError, match="distinct"):
        make(delegation_signing_key=SecretStr(SESSION))


@pytest.mark.parametrize("field", ["session_signing_key", "delegation_signing_key"])
def test_signing_keys_need_32_characters(field: str) -> None:
    with pytest.raises(ValidationError, match="32"):
        make(**{field: SecretStr("short")})


@pytest.mark.parametrize(
    "field", ["session_signing_key", "delegation_signing_key", "internal_api_key"]
)
def test_demo_rejects_local_only_placeholder_keys(field: str) -> None:
    placeholder = SecretStr("local-only-" + "x" * 30)
    with pytest.raises(ValidationError, match="local-only"):
        make(app_env="demo", **{field: placeholder})


def test_internal_key_is_required_outside_local() -> None:
    with pytest.raises(ValidationError, match="INTERNAL_API_KEY"):
        make(app_env="demo", internal_api_key=SecretStr(""))


def test_internal_key_may_be_empty_in_local() -> None:
    assert make(app_env="local", internal_api_key=SecretStr("")).app_env == "local"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("session_signing_key", "dev-" + "x" * 36),
        ("delegation_signing_key", "dev-" + "x" * 36),
        ("internal_api_key", "dev-" + "x" * 36),
        ("minio_access_key", "campuscue_admin"),
        ("minio_secret_key", "campuscue_secret"),
    ],
)
def test_demo_rejects_development_secrets_and_default_object_storage_credentials(
    field: str, value: str
) -> None:
    with pytest.raises(ValidationError):
        make(app_env="demo", **{field: SecretStr(value)})


def test_agent_client_timeout_must_exceed_turn_deadline() -> None:
    with pytest.raises(ValidationError, match="timeout"):
        make(agent_turn_deadline_s=20.0, agent_client_timeout_s=20.0)


def test_secrets_do_not_leak_in_repr() -> None:
    text = repr(make())
    assert SESSION not in text
    assert DELEGATION not in text
    assert INTERNAL not in text


def test_campus_gap_must_be_positive() -> None:
    with pytest.raises(ValidationError):
        make(campus_gap_minutes=0)


def test_database_url_must_use_psycopg_driver() -> None:
    with pytest.raises(ValidationError, match="psycopg"):
        make(database_url="postgresql://u:p@h/db")


def test_object_storage_links_are_signed_for_the_browser_reachable_address_by_default() -> None:
    settings = make()

    assert settings.minio_endpoint == "minio:9000"
    assert settings.minio_public_endpoint == "localhost:9000"
