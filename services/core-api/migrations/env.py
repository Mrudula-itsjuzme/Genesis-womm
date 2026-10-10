"""Alembic environment for Core (spine AD-20).

Migrations run through the explicit ``migrate`` one-shot, never at API start-up. The one-shot
needs only ``DATABASE_URL``, not the application's signing keys, so this module reads it
directly. Tests may pass a live connection through ``config.attributes["connection"]``.
"""

import os
from typing import Any

from alembic import context
from sqlalchemy import Connection, create_engine, pool, text
from sqlalchemy.schema import SchemaItem

import app.models  # noqa: F401  (registers every table on Base.metadata)
from app.models.base import CORE_SCHEMA, VERSION_TABLE, Base

config = context.config
target_metadata = Base.metadata


def _url() -> str:
    url = os.environ.get("DATABASE_URL") or config.get_main_option("sqlalchemy.url")
    if not url:
        raise RuntimeError("DATABASE_URL is not set")
    return url


def _include_name(name: str | None, type_: str, parent_names: dict[str, str | None]) -> bool:
    """Compare only schema `core`; other schemas belong to other owners or later plans."""
    if type_ == "schema":
        return name == CORE_SCHEMA
    return True


def _include_object(
    obj: SchemaItem, name: str | None, type_: str, reflected: bool, compare_to: SchemaItem | None
) -> bool:
    """Alembic's own bookkeeping table is not part of the model."""
    return not (type_ == "table" and reflected and name == VERSION_TABLE)


def _configure(**kwargs: Any) -> None:
    context.configure(
        target_metadata=target_metadata,
        version_table=VERSION_TABLE,
        version_table_schema=CORE_SCHEMA,
        compare_type=True,
        include_schemas=True,
        include_name=_include_name,
        include_object=_include_object,
        **kwargs,
    )


def run_migrations_offline() -> None:
    _configure(url=_url(), literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def _run(connection: Connection) -> None:
    # The version table lives in `core`, so that schema must exist before Alembic starts.
    connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{CORE_SCHEMA}"'))
    connection.commit()
    _configure(connection=connection)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied = config.attributes.get("connection")
    if supplied is not None:
        _run(supplied)
        return
    engine = create_engine(_url(), poolclass=pool.NullPool)
    with engine.connect() as connection:
        _run(connection)
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
