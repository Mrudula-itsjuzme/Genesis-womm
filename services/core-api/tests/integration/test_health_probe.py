import pytest
from sqlalchemy import Engine, create_engine

from app.repositories.health import SqlReadinessProbe
from app.services.readiness import ReadinessService
from tests.conftest import upgrade

pytestmark = pytest.mark.integration


def test_reachable_but_unmigrated_database_is_not_ready(engine: Engine) -> None:
    probe = SqlReadinessProbe(engine)
    assert probe.database_reachable() is True
    assert probe.applied_migration() is None
    assert ReadinessService(probe, expected_head="0001").check().ready is False


def test_migrated_database_is_ready(engine: Engine) -> None:
    upgrade(engine)
    probe = SqlReadinessProbe(engine)
    assert probe.applied_migration() == "0001"
    assert ReadinessService(probe, expected_head="0001").check().ready is True


def test_wrong_expected_head_is_not_ready(engine: Engine) -> None:
    upgrade(engine)
    report = ReadinessService(SqlReadinessProbe(engine), expected_head="0002").check()
    assert report.ready is False
    assert report.migration_head == "0001"


def test_unreachable_database_is_not_ready() -> None:
    dead = create_engine(
        "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none",
        connect_args={"connect_timeout": 1},
    )
    report = ReadinessService(SqlReadinessProbe(dead), expected_head="0001").check()
    assert report.ready is False
    assert report.checks == {"database": False, "migrations": False}
    dead.dispose()
