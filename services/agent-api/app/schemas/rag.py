"""Mirror of the RAG API's retrieval and knowledge schemas.

Source: docs/superpowers/plans/2026-10-10-rag-service.md. The RAG owner has no OpenAPI file
yet, so this is the Agent's reading of that plan; correct it when `contracts/rag-api.openapi.yaml`
lands. Citations are assembled by RAG from indexed metadata, never by a model.
"""

from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.chat import Citation
from app.schemas.enums import AccessLevel


class EvidenceChunk(BaseModel):
    evidence_id: str
    document_id: str
    title: str
    source_url: str
    page_start: int
    page_end: int
    section: str = ""
    excerpt: str
    document_version: str = "2025"
    score: float = 0.0


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=50)
    access_level: AccessLevel = AccessLevel.CAMPUS_PUBLIC


class SearchResponse(BaseModel):
    query: str
    candidates: list[EvidenceChunk]
    request_id: str | None = None


class AnswerRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=10)
    access_level: AccessLevel = AccessLevel.CAMPUS_PUBLIC


class AnswerResponse(BaseModel):
    query: str
    answer: str
    status: Literal["grounded", "insufficient_evidence"]
    citations: list[Citation]
    request_id: str | None = None
