"""The Agent runs on a real clock; a frozen one would report every latency as zero."""

from datetime import UTC, timedelta
from time import sleep

from app.clients.system import SystemClock
from app.container import build_container
from app.settings import Settings


def test_the_system_clock_is_aware_utc_and_moves_forward() -> None:
    clock = SystemClock()
    first = clock.now()
    sleep(0.01)
    second = clock.now()
    assert first.utcoffset() == timedelta(0)
    assert first.tzinfo is UTC
    assert second > first


def test_the_container_gives_the_engine_the_system_clock() -> None:
    container = build_container(Settings(_env_file=None))
    assert container.engine is not None
    assert isinstance(vars(container.engine)["_clock"], SystemClock)
