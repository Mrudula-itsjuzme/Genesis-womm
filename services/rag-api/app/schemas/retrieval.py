from typing import List, Optional
from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    evidence_id: str = Field(..., description="Stable chunk identifier")
    document_id: str = Field(..., description="Document identifier from source registry")
    title: str = Field(..., description="Official title of the source document")
    source_url: str = Field(..., description="Canonical source URL")
    page_start: int = Field(..., description="Starting 1-indexed page number")
    page_end: int = Field(..., description="Ending 1-indexed page number")
    section: str = Field(default="", description="Section hierarchy path")
    excerpt: str = Field(..., description="Exact extracted chunk text")
    document_version: str = Field(default="2025", description="Document version or year")
    score: float = Field(default=0.0, description="Fused retrieval relevance score")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum evidence chunks to return")
    access_level: str = Field(default="CAMPUS_PUBLIC", description="Access filter class")


class SearchResponse(BaseModel):
    query: str
    candidates: List[EvidenceChunk]
    request_id: Optional[str] = None
