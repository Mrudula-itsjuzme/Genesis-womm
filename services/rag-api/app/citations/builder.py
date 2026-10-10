from typing import List
from app.schemas.retrieval import EvidenceChunk
from app.schemas.knowledge import Citation


class CitationBuilder:
    """Constructs verifiable Citation objects strictly from retrieved database chunk metadata."""

    @staticmethod
    def build(chunks: List[EvidenceChunk]) -> List[Citation]:
        citations: List[Citation] = []
        for chunk in chunks:
            citations.append(
                Citation(
                    evidence_id=chunk.evidence_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    source_url=chunk.source_url,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    excerpt=chunk.excerpt,
                    document_version=chunk.document_version,
                )
            )
        return citations
