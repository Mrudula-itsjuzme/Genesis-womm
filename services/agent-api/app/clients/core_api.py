from uuid import UUID

import httpx
from pydantic import ValidationError

from app.ports.core import CallContext, CoreToolsPort
from app.ports.errors import (
    ContractViolationError,
    DeniedError,
    DependencyUnavailableError,
    IdempotencyMismatchError,
    NotFoundError,
    StaleRevisionError,
)
from app.schemas.common import ErrorEnvelope
from app.schemas.core import (
    AgentAction,
    AgentActionCreate,
    AgentConflictCheckRequest,
    ConflictCheckOut,
    EventOut,
)
from app.schemas.enums import ErrorCode


class HttpCoreClient(CoreToolsPort):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def _headers(self, ctx: CallContext, idempotency_key: str | None = None) -> dict[str, str]:
        h = {
            "Authorization": f"Bearer {ctx.delegation_token}",
            "X-Request-ID": ctx.request_id,
        }
        if idempotency_key:
            h["Idempotency-Key"] = idempotency_key
        return h

    def _map_error(self, response: httpx.Response) -> None:
        if response.is_success:
            return

        if response.status_code == 403:
            raise DeniedError("Operation denied")
        if response.status_code == 404:
            raise NotFoundError("Resource not found")

        try:
            envelope = ErrorEnvelope.model_validate(response.json())
        except Exception:
            raise DependencyUnavailableError(
                "core-api", f"unexpected status {response.status_code}"
            ) from None

        if envelope.code == ErrorCode.STALE_REVISION:
            raise StaleRevisionError(envelope.message)
        if envelope.code == ErrorCode.IDEMPOTENCY_MISMATCH:
            raise IdempotencyMismatchError(envelope.message)

        if response.status_code >= 500:
            raise DependencyUnavailableError("core-api", envelope.message)

        raise DependencyUnavailableError("core-api", f"unhandled error: {envelope.code}")

    async def check_event_conflicts(
        self, request: AgentConflictCheckRequest, ctx: CallContext
    ) -> ConflictCheckOut:
        try:
            response = await self._client.post(
                "/internal/v1/agent/check-conflicts",
                json=request.model_dump(mode="json", exclude_none=True),
                headers=self._headers(ctx),
            )
        except httpx.RequestError as e:
            raise DependencyUnavailableError("core-api", str(e)) from e

        self._map_error(response)

        try:
            return ConflictCheckOut.model_validate(response.json())
        except ValidationError as e:
            raise ContractViolationError(f"core-api returned invalid contract: {e}") from e

    async def get_event_details(self, event_id: UUID, ctx: CallContext) -> EventOut:
        try:
            response = await self._client.get(
                f"/internal/v1/events/{event_id}",
                headers=self._headers(ctx),
            )
        except httpx.RequestError as e:
            raise DependencyUnavailableError("core-api", str(e)) from e

        self._map_error(response)

        try:
            return EventOut.model_validate(response.json())
        except ValidationError as e:
            raise ContractViolationError(f"core-api returned invalid contract: {e}") from e

    async def file_agent_action(
        self, action: AgentActionCreate, ctx: CallContext, idempotency_key: str
    ) -> AgentAction:
        try:
            response = await self._client.post(
                "/internal/v1/agent/actions",
                json=action.model_dump(mode="json", exclude_none=True),
                headers=self._headers(ctx, idempotency_key=idempotency_key),
            )
        except httpx.RequestError as e:
            raise DependencyUnavailableError("core-api", str(e)) from e

        self._map_error(response)

        try:
            return AgentAction.model_validate(response.json())
        except ValidationError as e:
            raise ContractViolationError(f"core-api returned invalid contract: {e}") from e
