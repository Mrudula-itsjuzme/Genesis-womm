"""Shared fixtures. Integration tests need Docker and fail loudly without it, never skip."""

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine, create_engine, text
from testcontainers.community.postgres import PostgresContainer

SERVICE_ROOT = Path(__file__).resolve().parents[1]
POSTGRES_IMAGE = "postgres:18"


def alembic_config(connection: object | None = None) -> Config:
    config = Config(str(SERVICE_ROOT / "alembic.ini"))
    if connection is not None:
        config.attributes["connection"] = connection
    return config


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
