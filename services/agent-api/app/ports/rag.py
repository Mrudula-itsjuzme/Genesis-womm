"""The Agent's view of the RAG API: document evidence with code-assembled citations."""

from typing import Protocol

from app.schemas.rag import AnswerRequest, AnswerResponse, SearchRequest, SearchResponse


class RagPort(Protocol):
    async def search(self, request: SearchRequest, request_id: str) -> SearchResponse: ...

    async def answer(self, request: AnswerRequest, request_id: str) -> AnswerResponse: ...
