"""Alembic 1.20 with SQLAlchemy 2.1 on PostgreSQL 18 (smoke test for spine AD-20)."""

import pytest
from alembic import command
from sqlalchemy import Engine, text

from tests.conftest import alembic_config, code_head, upgrade

pytestmark = pytest.mark.integration


def _schemas(engine: Engine) -> set[str]:
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT schema_name FROM information_schema.schemata")
        ).scalars()
        return set(rows)


def test_server_is_postgres_18(engine: Engine) -> None:
    with engine.connect() as connection:
        assert connection.execute(text("SHOW server_version_num")).scalar_one().startswith("18")


def test_upgrade_creates_core_schemas_and_records_the_head(engine: Engine) -> None:
    upgrade(engine)
    assert {"core", "student_private"} <= _schemas(engine)
    with engine.connect() as connection:
        version = connection.execute(
            text("SELECT version_num FROM core.alembic_version_core")
        ).scalar_one()
    assert version == code_head()


def test_upgrade_is_idempotent(engine: Engine) -> None:
    upgrade(engine)
    upgrade(engine)
    with engine.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM core.alembic_version_core"))
        assert count.scalar_one() == 1


def test_downgrade_removes_student_private_but_keeps_the_version_table(engine: Engine) -> None:
    upgrade(engine)
    with engine.connect() as connection:
        command.downgrade(alembic_config(connection), "base")
    assert "student_private" not in _schemas(engine)
    assert "core" in _schemas(engine)
    with engine.connect() as connection:
        remaining = connection.execute(text("SELECT count(*) FROM core.alembic_version_core"))
        assert remaining.scalar_one() == 0


def test_models_and_migrations_agree(engine: Engine) -> None:
    upgrade(engine)
    with engine.connect() as connection:
        command.check(alembic_config(connection))


def test_one_shot_migrate_needs_only_database_url(
    postgres_url: str, engine: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    for key in ("SESSION_SIGNING_KEY", "DELEGATION_SIGNING_KEY", "INTERNAL_API_KEY"):
        monkeypatch.delenv(key, raising=False)
    command.upgrade(alembic_config(), "head")
    assert "student_private" in _schemas(engine)


def test_offline_sql_generation_works(
    postgres_url: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("DATABASE_URL", postgres_url)
    command.upgrade(alembic_config(), "head", sql=True)
    sql = capsys.readouterr().out
    assert "CREATE SCHEMA IF NOT EXISTS student_private" in sql
    assert "alembic_version_core" in sql
