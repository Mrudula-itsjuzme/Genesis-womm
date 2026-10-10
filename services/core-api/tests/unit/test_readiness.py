import pytest

from app.services.readiness import ReadinessService
from tests.fakes import FakeReadinessProbe


def test_ready_when_database_is_up_and_head_is_applied() -> None:
    report = ReadinessService(FakeReadinessProbe(applied="0001"), expected_head="0001").check()
    assert report.ready is True
    assert report.checks == {"database": True, "migrations": True}
    assert report.migration_head == "0001"
    assert report.expected_head == "0001"


def test_not_ready_and_does_not_query_migrations_when_database_is_down() -> None:
    probe = FakeReadinessProbe(reachable=False)
    report = ReadinessService(probe, expected_head="0001").check()
    assert report.ready is False
    assert report.checks == {"database": False, "migrations": False}
    assert report.migration_head is None
    assert probe.applied_calls == 0


def test_not_ready_when_no_migration_has_been_applied() -> None:
    report = ReadinessService(FakeReadinessProbe(applied=None), expected_head="0001").check()
    assert report.ready is False
    assert report.checks == {"database": True, "migrations": False}


@pytest.mark.parametrize("applied", ["0000", "0002"])
def test_not_ready_when_applied_head_differs_from_code(applied: str) -> None:
    report = ReadinessService(FakeReadinessProbe(applied=applied), expected_head="0001").check()
    assert report.ready is False
    assert report.migration_head == applied
    assert report.checks["migrations"] is False


def test_optional_dependencies_never_affect_readiness() -> None:
    # Agent, RAG and the LLM are not part of Core's readiness (spine AD-19).
    report = ReadinessService(FakeReadinessProbe(), expected_head="0001").check()
    assert set(report.checks) == {"database", "migrations"}
