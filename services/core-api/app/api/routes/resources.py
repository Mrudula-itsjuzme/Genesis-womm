from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.api.deps import (
    get_resource_interest_service,
    get_resource_read_service,
    require_session_actor,
)
from app.api.errors import error_responses
from app.api.presenters import resource_out
from app.domain.authz import Actor
from app.domain.enums import ErrorCode, ResourceKind
from app.schemas.resources import (
    ResourceInterestCreate,
    ResourceInterestOut,
    ResourceList,
    ResourceOut,
)
from app.services.resource_interests import ResourceInterestService
from app.services.resource_reads import ResourceReadService

router = APIRouter(
    prefix="/api/v1/resources",
    tags=["resources"],
    dependencies=[Depends(require_session_actor)],
)

ResourceReaderDependency = Annotated[ResourceReadService, Depends(get_resource_read_service)]
ResourceInterestDependency = Annotated[
    ResourceInterestService, Depends(get_resource_interest_service)
]


@router.post(
    "/interests",
    status_code=201,
    response_model=ResourceInterestOut,
    summary="Save a personal shared-resource interest (not a reservation)",
    responses=error_responses(ErrorCode.UNAUTHENTICATED, ErrorCode.VALIDATION_ERROR),
)
def create_resource_interest(
    payload: ResourceInterestCreate,
    actor: Annotated[Actor, Depends(require_session_actor)],
    interests: ResourceInterestDependency,
) -> ResourceInterestOut:
    return ResourceInterestOut.model_validate(
        interests.create(actor, **payload.model_dump()), from_attributes=True
    )


@router.get(
    "",
    response_model=ResourceList,
    summary="List sourced campus resources",
    description="Every row carries its source and freshness. Availability is UNKNOWN by default.",
    responses=error_responses(ErrorCode.UNAUTHENTICATED, ErrorCode.VALIDATION_ERROR),
)
def list_resources(
    resources: ResourceReaderDependency,
    kind: ResourceKind | None = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> ResourceList:
    records, total = resources.list(kind=kind, query=q, limit=limit, offset=offset)
    return ResourceList(
        items=[resource_out(record) for record in records],
        limit=limit,
        offset=offset,
        total=total,
    )


@router.get(
    "/{resource_id}",
    response_model=ResourceOut,
    summary="Get one resource",
    responses=error_responses(
        ErrorCode.UNAUTHENTICATED, ErrorCode.NOT_FOUND, ErrorCode.VALIDATION_ERROR
    ),
)
def get_resource(
    resource_id: UUID,
    resources: ResourceReaderDependency,
) -> ResourceOut:
    return resource_out(resources.get(resource_id))
