"""Shared fixtures. Integration tests need Docker and fail loudly without it, never skip."""

from collections.abc import Iterator
from pathlib import Path

import pytest
import structlog
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, create_engine, text
from testcontainers.community.postgres import PostgresContainer

SERVICE_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18"


def alembic_config(connection: object | None = None) -> Config:
    config = Config(str(SERVICE_ROOT / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


def code_head() -> str:
    """The migration head the code ships, so tests never hard-code a revision."""
    head = ScriptDirectory.from_config(alembic_config()).get_current_head()
    assert head is not None
    return head


@pytest.fixture(autouse=True)
def _reset_structlog() -> Iterator[None]:
    """`configure_logging` changes global state; never let one test's setup leak into another.

    Without this, a test that configures logging under `capsys` leaves structlog writing to a
    stdout that is closed afterwards.
    """
    yield
    structlog.reset_defaults()


@pytest.fixture(scope="session")
def postgres_url() -> Iterator[str]:
    with PostgresContainer(POSTGRES_IMAGE, driver="psycopg") as container:
        yield container.get_connection_url()


@pytest.fixture
def engine(postgres_url: str) -> Iterator[Engine]:
    """A clean database per test: both Core schemas are dropped before and after."""
    engine = create_engine(postgres_url, pool_pre_ping=True)

    def reset() -> None:
        with engine.begin() as connection:
            connection.execute(text("DROP SCHEMA IF EXISTS core CASCADE"))
            connection.execute(text("DROP SCHEMA IF EXISTS student_private CASCADE"))

    reset()
    yield engine
    reset()
    engine.dispose()


def upgrade(engine: Engine, revision: str = "head") -> None:
    with engine.connect() as connection:
        command.upgrade(alembic_config(connection), revision)
