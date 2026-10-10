from typing import Literal

from pydantic import BaseModel, Field


class Citation(BaseModel):
    evidence_id: str
    document_id: str
    title: str
    source_url: str
    page_start: int
    page_end: int
    excerpt: str
    document_version: str


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Policy question to answer")
    top_k: int = Field(default=4, ge=1, le=10, description="Evidence chunks to ground against")
    access_level: str = Field(default="CAMPUS_PUBLIC")


class AnswerResponse(BaseModel):
    query: str
    answer: str
    status: Literal["grounded", "insufficient_evidence"]
    citations: list[Citation]
    request_id: str | None = None
