"""Typed configuration, read once at the composition root (spine AD-22).

Domain and service code never import this module; values are passed in.
Core holds no LLM credentials. The session and delegation keys are distinct and
exist only in this service.
"""

from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "demo"]

_MIN_KEY_LENGTH = 32
_LOCAL_ONLY_PREFIX = "local-only"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        extra="ignore",
        frozen=True,
    )

    app_env: AppEnv = "local"
    log_level: str = "INFO"
    # CampusCue planning rule, not verified institutional policy.
    campus_gap_minutes: int = Field(default=120, ge=1)

    database_url: str = "postgresql+psycopg://campuscue:campuscue@localhost:5432/campuscue"

    session_signing_key: SecretStr
    delegation_signing_key: SecretStr
    internal_api_key: SecretStr = SecretStr("")

    agent_api_url: str = "http://agent-api:8001"
    agent_turn_deadline_s: float = Field(default=20.0, gt=0)
    agent_client_timeout_s: float = Field(default=25.0, gt=0)

    @field_validator("database_url")
    @classmethod
    def _psycopg_driver(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use the postgresql+psycopg:// driver")
        return value

    @model_validator(mode="after")
    def _check_keys_and_timeouts(self) -> Self:
        session = self.session_signing_key.get_secret_value()
        delegation = self.delegation_signing_key.get_secret_value()
        internal = self.internal_api_key.get_secret_value()

        for name, key in (
            ("SESSION_SIGNING_KEY", session),
            ("DELEGATION_SIGNING_KEY", delegation),
        ):
            if len(key) < _MIN_KEY_LENGTH:
                raise ValueError(f"{name} must be at least {_MIN_KEY_LENGTH} characters")
        if session == delegation:
            raise ValueError("SESSION_SIGNING_KEY and DELEGATION_SIGNING_KEY must be distinct")

        if self.app_env != "local" and not internal:
            raise ValueError("INTERNAL_API_KEY is required outside APP_ENV=local")
        if self.app_env == "demo":
            for name, key in (
                ("SESSION_SIGNING_KEY", session),
                ("DELEGATION_SIGNING_KEY", delegation),
                ("INTERNAL_API_KEY", internal),
            ):
                if key.startswith(_LOCAL_ONLY_PREFIX):
                    raise ValueError(f"{name} still has the local-only placeholder value in demo")

        if self.agent_client_timeout_s <= self.agent_turn_deadline_s:
            raise ValueError("AGENT_CLIENT_TIMEOUT_S must exceed AGENT_TURN_DEADLINE_S")
        return self


def load_settings() -> Settings:
    return Settings()
