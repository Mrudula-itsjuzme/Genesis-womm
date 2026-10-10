import httpx
from pydantic import ValidationError

from app.ports.errors import ContractViolationError, DependencyUnavailableError
from app.ports.rag import RagPort
from app.schemas.rag import AnswerRequest, AnswerResponse, SearchRequest, SearchResponse

# The RAG service publishes no OpenAPI file yet; these are its routes in services/rag-api
# (app/api/routes/retrieval.py and knowledge.py). A client test pins them.
SEARCH_PATH = "/v1/retrieval/search"
ANSWER_PATH = "/v1/knowledge/answer"


class HttpRagClient(RagPort):
    def __init__(self, client: httpx.AsyncClient) -> None:
        self._client = client

    def _headers(self, request_id: str) -> dict[str, str]:
        return {"X-Request-ID": request_id}

    async def search(self, request: SearchRequest, request_id: str) -> SearchResponse:
        try:
            response = await self._client.post(
                SEARCH_PATH,
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
                ANSWER_PATH,
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
