"""Typed configuration, read once at the composition root (spine AD-22).

The Agent holds the LLM credential and neither of Core's signing keys. The orchestration
limits default to the values fixed by spine AD-11.
"""

from typing import Literal, Self

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

AppEnv = Literal["local", "test", "demo"]
ModelProvider = Literal["groq", "fake"]

_LOCAL_ONLY_PREFIX = "local-only"
# Core abandons a turn after this long (AGENT_CLIENT_TIMEOUT_S); the Agent must finish first.
_CORE_WAIT_S = 25.0


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        extra="ignore",
        frozen=True,
    )

    app_env: AppEnv = "local"
    log_level: str = "INFO"

    # `fake` is deterministic and needs no network or paid API.
    agent_model_provider: ModelProvider = "fake"
    agent_demo_mode: bool = False
    groq_api_key: SecretStr = SecretStr("")
    groq_model: str = "openai/gpt-oss-120b"
    # Used once when the main model is rate limited. Empty disables the fallback.
    groq_fallback_model: str = "openai/gpt-oss-20b"
    groq_timeout_s: float = Field(default=12.0, gt=0)

    core_api_url: str = "http://core-api:8000"
    rag_api_url: str = "http://rag-api:8002"
    internal_api_key: SecretStr = SecretStr("")

    # Bounded orchestration (spine AD-11).
    max_tool_calls: int = Field(default=6, ge=1, le=20)
    turn_deadline_s: float = Field(default=20.0, gt=0)
    tool_timeout_s: float = Field(default=5.0, gt=0)
    max_tool_bytes: int = Field(default=16_384, ge=1_024)
    max_history_messages: int = Field(default=20, ge=1, le=50)
    max_history_bytes: int = Field(default=32_768, ge=1_024)

    @field_validator("core_api_url", "rag_api_url")
    @classmethod
    def _http_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("service URLs must start with http:// or https://")
        return value.rstrip("/")

    @model_validator(mode="after")
    def _check_cross_field_rules(self) -> Self:
        if self.tool_timeout_s > self.turn_deadline_s:
            raise ValueError("TOOL_TIMEOUT_S must not exceed TURN_DEADLINE_S")
        if self.turn_deadline_s >= _CORE_WAIT_S:
            raise ValueError(
                f"TURN_DEADLINE_S must stay under the {_CORE_WAIT_S:.0f} s Core waits for a turn"
            )
        internal = self.internal_api_key.get_secret_value()
        if self.app_env != "local" and not internal:
            raise ValueError("INTERNAL_API_KEY is required outside APP_ENV=local")
        if self.app_env == "demo" and internal.startswith(_LOCAL_ONLY_PREFIX):
            raise ValueError("INTERNAL_API_KEY still has the local-only placeholder value in demo")
        return self


def load_settings() -> Settings:
    return Settings()
