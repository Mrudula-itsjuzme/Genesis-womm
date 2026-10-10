from app.parsing.pdf import ParsedPage
from app.schemas.retrieval import EvidenceChunk


class StructureChunker:
    """Splits parsed pages into bounded chunks fitting the 256-token embedding window."""

    def __init__(self, target_chunk_size: int = 180, chunk_overlap: int = 30):
        if chunk_overlap >= target_chunk_size:
            raise ValueError("chunk_overlap must be less than target_chunk_size")
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def _approx_token_count(self, text: str) -> int:
        return len(text.split())

    def chunk_pages(
        self,
        pages: list[ParsedPage],
        document_id: str,
        title: str,
        source_url: str,
        document_version: str = "2025",
        source_id: str | None = None,
    ) -> list[EvidenceChunk]:
        effective_doc_id = document_id or source_id or ""
        chunks: list[EvidenceChunk] = []

        for page in pages:
            if not page.text:
                continue

            words = page.text.split()
            if not words:
                continue

            # If page fits within target chunk size, keep it as single chunk
            if len(words) <= self.target_chunk_size:
                evidence_id = f"{effective_doc_id}-p{page.page_number}-c01"
                chunks.append(
                    EvidenceChunk(
                        evidence_id=evidence_id,
                        document_id=effective_doc_id,
                        title=title,
                        source_url=source_url,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        section=page.section_breadcrumb or "",
                        excerpt=page.text,
                        document_version=document_version,
                    )
                )
            else:
                # Sliding window chunking
                start_idx = 0
                chunk_seq = 1
                step = max(1, self.target_chunk_size - self.chunk_overlap)
                while start_idx < len(words):
                    end_idx = min(start_idx + self.target_chunk_size, len(words))
                    chunk_text = " ".join(words[start_idx:end_idx])
                    evidence_id = f"{effective_doc_id}-p{page.page_number}-c{chunk_seq:02d}"

                    chunks.append(
                        EvidenceChunk(
                            evidence_id=evidence_id,
                            document_id=effective_doc_id,
                            title=title,
                            source_url=source_url,
                            page_start=page.page_number,
                            page_end=page.page_number,
                            section=page.section_breadcrumb or "",
                            excerpt=chunk_text,
                            document_version=document_version,
                        )
                    )

                    if end_idx >= len(words):
                        break
                    start_idx += step
                    chunk_seq += 1

        return chunks
