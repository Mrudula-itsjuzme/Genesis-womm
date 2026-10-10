"""The Agent's HTTP client for the RAG service.

The RAG service publishes no OpenAPI file yet, so the routes are pinned here as they exist in
services/rag-api (app/api/routes/retrieval.py and knowledge.py). When RAG publishes a contract,
replace the literals below with a check against it, as test_core_client.py does for Core.
"""

import json
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
import respx

from app.clients.rag_api import HttpRagClient
from app.ports.errors import ContractViolationError, DependencyUnavailableError
from app.schemas.rag import AnswerRequest, SearchRequest

BASE = "http://rag.test"
SEARCH = f"{BASE}/v1/retrieval/search"
ANSWER = f"{BASE}/v1/knowledge/answer"

CHUNK: dict[str, Any] = {
    "evidence_id": "doc-1#p3#c2",
    "document_id": "doc-1",
    "title": "Student Handbook",
    "source_url": "https://example.invalid/handbook.pdf",
    "page_start": 3,
    "page_end": 3,
    "section": "Events",
    "excerpt": "Events need prior approval.",
    "document_version": "2025",
    "score": 0.82,
}
CITATION = {k: v for k, v in CHUNK.items() if k not in {"section", "score"}}


@pytest.fixture
async def rag() -> AsyncIterator[HttpRagClient]:
    async with httpx.AsyncClient(base_url=BASE) as client:
        yield HttpRagClient(client)


@respx.mock
async def test_search_posts_to_the_retrieval_route_and_parses_candidates(
    rag: HttpRagClient,
) -> None:
    route = respx.post(SEARCH).respond(
        json={"query": "event approval", "candidates": [CHUNK], "request_id": "req-9"}
    )
    result = await rag.search(SearchRequest(query="event approval", top_k=3), "req-9")

    assert [c.evidence_id for c in result.candidates] == ["doc-1#p3#c2"]
    sent = route.calls.last.request
    assert sent.headers["x-request-id"] == "req-9"
    assert json.loads(sent.content) == {
        "query": "event approval",
        "top_k": 3,
        "access_level": "CAMPUS_PUBLIC",
    }


@respx.mock
async def test_answer_posts_to_the_knowledge_route_and_keeps_citations_verbatim(
    rag: HttpRagClient,
) -> None:
    respx.post(ANSWER).respond(
        json={
            "query": "approval?",
            "answer": "Prior approval is required.",
            "status": "grounded",
            "citations": [CITATION],
        }
    )
    result = await rag.answer(AnswerRequest(query="approval?"), "req-1")

    assert result.status == "grounded"
    assert result.citations[0].model_dump() == CITATION


@pytest.mark.parametrize("status", [400, 422, 500, 503])
@respx.mock
async def test_a_failing_rag_service_is_a_dependency_failure(
    rag: HttpRagClient, status: int
) -> None:
    respx.post(SEARCH).respond(status, json={"detail": "nope"})
    with pytest.raises(DependencyUnavailableError):
        await rag.search(SearchRequest(query="x"), "req-1")


@respx.mock
async def test_an_unreachable_rag_service_is_a_dependency_failure(rag: HttpRagClient) -> None:
    respx.post(ANSWER).mock(side_effect=httpx.ConnectTimeout("slow"))
    with pytest.raises(DependencyUnavailableError):
        await rag.answer(AnswerRequest(query="x"), "req-1")


@respx.mock
async def test_a_body_that_breaks_the_contract_is_a_violation(rag: HttpRagClient) -> None:
    respx.post(ANSWER).respond(json={"query": "x", "answer": "y", "status": "made-up"})
    with pytest.raises(ContractViolationError):
        await rag.answer(AnswerRequest(query="x"), "req-1")
