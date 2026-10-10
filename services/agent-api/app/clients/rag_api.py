import httpx
from pydantic import ValidationError

from app.ports.errors import ContractViolationError, DependencyUnavailableError
from app.ports.rag import RagPort
from app.schemas.rag import AnswerRequest, AnswerResponse, SearchRequest, SearchResponse


class HttpRagClient(RagPort):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def _headers(self, request_id: str) -> dict[str, str]:
        return {"X-Request-ID": request_id}

    async def search(self, request: SearchRequest, request_id: str) -> SearchResponse:
        try:
            response = await self._client.post(
                "/v1/rag/search",
                json=request.model_dump(mode="json"),
                headers=self._headers(request_id),
            )
        except httpx.RequestError as e:
            raise DependencyUnavailableError("rag-api", str(e)) from e

        if not response.is_success:
            raise DependencyUnavailableError("rag-api", f"unexpected status {response.status_code}")

        try:
            return SearchResponse.model_validate(response.json())
        except ValidationError as e:
            raise ContractViolationError(f"rag-api returned invalid contract: {e}") from e

    async def answer(self, request: AnswerRequest, request_id: str) -> AnswerResponse:
        try:
            response = await self._client.post(
                "/v1/rag/answer",
                json=request.model_dump(mode="json"),
                headers=self._headers(request_id),
            )
        except httpx.RequestError as e:
            raise DependencyUnavailableError("rag-api", str(e)) from e

        if not response.is_success:
            raise DependencyUnavailableError("rag-api", f"unexpected status {response.status_code}")

        try:
            return AnswerResponse.model_validate(response.json())
        except ValidationError as e:
            raise ContractViolationError(f"rag-api returned invalid contract: {e}") from e
