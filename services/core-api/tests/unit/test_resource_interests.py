from datetime import UTC, date, datetime, time
from types import TracebackType
from typing import Self
from uuid import uuid4

from app.domain.authz import Actor
from app.domain.time import FixedClock
from app.services.resource_interests import ResourceInterestRecord, ResourceInterestService
from tests.fakes import SequentialIds

NOW = datetime(2026, 10, 11, 9, 0, tzinfo=UTC)


class InterestStore:
    def __init__(self) -> None:
        self.records: list[ResourceInterestRecord] = []

    def add(self, record: ResourceInterestRecord) -> None:
        self.records.append(record)


class InterestUnitOfWork:
    def __init__(self, store: InterestStore) -> None:
        self.resource_interests = store
        self.committed = False

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None

    def commit(self) -> None:
        self.committed = True


def test_resource_interest_is_owned_by_the_authenticated_actor() -> None:
    store = InterestStore()
    uow = InterestUnitOfWork(store)
    actor_id, supplied_id = uuid4(), uuid4()
    service = ResourceInterestService(
        lambda: uow,
        clock=FixedClock(NOW),
        ids=SequentialIds(),
    )

    record = service.create(
        Actor(user_id=actor_id),
        category="3d printing",
        purpose="prototype enclosure",
        preferred_date=date(2026, 10, 20),
        start_time=time(10, 0),
        end_time=time(12, 0),
        requirements=None,
    )

    assert record.requester_id == actor_id
    assert record.requester_id != supplied_id
    assert record.created_at == NOW
    assert store.records == [record]
    assert uow.committed is True
