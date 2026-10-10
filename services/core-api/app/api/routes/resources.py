from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import session_bearer
from app.api.errors import STUB_OPENAPI, not_implemented, stub_errors
from app.domain.enums import ErrorCode, ResourceKind
from app.schemas.resources import ResourceList, ResourceOut

router = APIRouter(
    prefix="/api/v1/resources",
    tags=["resources"],
    dependencies=[Depends(session_bearer)],
)


@router.get(
    "",
    response_model=ResourceList,
    summary="List sourced campus resources",
    description="Every row carries its source and freshness. Availability is UNKNOWN by default.",
    responses=stub_errors(),
    openapi_extra=STUB_OPENAPI,
)
def list_resources(
    kind: ResourceKind | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResourceList:
    not_implemented("Resource listing")


@router.get(
    "/{resource_id}",
    response_model=ResourceOut,
    summary="Get one resource",
    responses=stub_errors(ErrorCode.NOT_FOUND),
    openapi_extra=STUB_OPENAPI,
)
def get_resource(resource_id: UUID) -> ResourceOut:
    not_implemented("Resource lookup")
