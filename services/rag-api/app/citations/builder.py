import re

from app.schemas.knowledge import Citation
from app.schemas.retrieval import EvidenceChunk


class CitationBuilder:
    """Builds metadata-grounded citations strictly from indexed evidence chunks."""

    @staticmethod
    def build(
        chunks: list[EvidenceChunk],
        cited_text: str | None = None,
    ) -> list[Citation]:
        if not chunks:
            return []

        # If cited_text contains bracketed evidence IDs (e.g. [osa-p12-c01]), filter strictly to referenced chunks
        active_chunks = chunks
        if cited_text:
            cited_ids = set(re.findall(r"\[([a-zA-Z0-9_\-]+)\]", cited_text))
            if cited_ids:
                active_chunks = [c for c in chunks if c.evidence_id in cited_ids]

        seen_keys = set()
        citations: list[Citation] = []

        for chunk in active_chunks:
            dedup_key = (chunk.document_id, chunk.page_start, chunk.page_end)
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

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
