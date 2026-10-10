"""Deterministic fakes for Core's outbound ports (spine AD-2)."""

from typing import Any

from pydantic import SecretStr

from app.settings import Settings


def make_settings(**overrides: Any) -> Settings:
    """Hermetic settings: never reads the developer's .env or real secrets."""
    values: dict[str, Any] = {
        "session_signing_key": SecretStr("s" * 40),
        "delegation_signing_key": SecretStr("d" * 40),
        "internal_api_key": SecretStr("i" * 40),
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class FakeReadinessProbe:
    """Stands in for the database; counts calls so tests can assert what was skipped."""

    def __init__(self, *, reachable: bool = True, applied: str | None = "0001") -> None:
        self._reachable = reachable
        self._applied = applied
        self.applied_calls = 0

    def database_reachable(self) -> bool:
        return self._reachable

    def applied_migration(self) -> str | None:
        self.applied_calls += 1
        return self._applied
