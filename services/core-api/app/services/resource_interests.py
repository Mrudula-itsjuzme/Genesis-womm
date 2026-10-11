"""Create personal resource-interest records without implying availability or allocation."""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime, time
from types import TracebackType
from typing import Protocol, Self
from uuid import UUID

from app.domain.authz import Actor
from app.domain.time import Clock
from app.services.ports import IdSource


@dataclass(frozen=True)
class ResourceInterestRecord:
    id: UUID
    requester_id: UUID
    category: str
    purpose: str
    preferred_date: date
    start_time: time
    end_time: time
    requirements: str | None
    created_at: datetime


class ResourceInterestStore(Protocol):
    def add(self, record: ResourceInterestRecord) -> None: ...


class ResourceInterestUnitOfWork(Protocol):
    @property
    def resource_interests(self) -> ResourceInterestStore: ...

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None: ...

    def commit(self) -> None: ...


class ResourceInterestService:
    def __init__(
        self, uow_factory: Callable[[], ResourceInterestUnitOfWork], *, clock: Clock, ids: IdSource
    ) -> None:
        self._uow_factory, self._clock, self._ids = uow_factory, clock, ids

    def create(
        self,
        actor: Actor,
        *,
        category: str,
        purpose: str,
        preferred_date: date,
        start_time: time,
        end_time: time,
        requirements: str | None,
    ) -> ResourceInterestRecord:
        record = ResourceInterestRecord(
            id=self._ids.new_id(),
            requester_id=actor.user_id,
            category=category,
            purpose=purpose,
            preferred_date=preferred_date,
            start_time=start_time,
            end_time=end_time,
            requirements=requirements,
            created_at=self._clock.now(),
        )
        with self._uow_factory() as uow:
            uow.resource_interests.add(record)
            uow.commit()
        return record
