"""Read-only sourced resource catalogue use case."""

from collections.abc import Callable
from uuid import UUID

from app.domain.enums import ResourceKind
from app.services.errors import NotFoundError
from app.services.ports import ResourceRecord, UnitOfWork


class ResourceReadService:
    def __init__(self, uow_factory: Callable[[], UnitOfWork]) -> None:
        self._uow_factory = uow_factory

    def get(self, resource_id: UUID) -> ResourceRecord:
        with self._uow_factory() as uow:
            resource = uow.resources.get(resource_id)
        if resource is None:
            raise NotFoundError("resource", resource_id)
        return resource

    def list(
        self, *, kind: ResourceKind | None, query: str | None, limit: int, offset: int
    ) -> tuple[list[ResourceRecord], int]:
        with self._uow_factory() as uow:
            return uow.resources.list_resources(kind=kind, query=query, limit=limit, offset=offset)
