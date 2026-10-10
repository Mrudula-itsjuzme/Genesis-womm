from app.schemas.retrieval import EvidenceChunk
from app.citations.builder import CitationBuilder


def test_citation_builder_formats_exact_metadata():
    chunks = [
        EvidenceChunk(
            evidence_id="osa-p12-c01",
            document_id="osa_handbook_cbr",
            title="Student Affairs Handbook",
            source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
            page_start=12,
            page_end=12,
            excerpt="Proposal submitted 14 days in advance.",
            document_version="2025",
        )
    ]
    citations = CitationBuilder.build(chunks)
    assert len(citations) == 1
    c = citations[0]
    assert c.evidence_id == "osa-p12-c01"
    assert c.document_id == "osa_handbook_cbr"
    assert c.title == "Student Affairs Handbook"
    assert c.page_start == 12
    assert c.page_end == 12
    assert c.source_url == (
        "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf"
    )
    assert c.excerpt == "Proposal submitted 14 days in advance."
    assert c.document_version == "2025"


def test_citation_builder_empty_list():
    citations = CitationBuilder.build([])
    assert citations == []


def test_citation_builder_multiple_chunks_preserves_order():
    chunks = [
        EvidenceChunk(
            evidence_id=f"doc-p{i}-c01",
            document_id=f"doc_{i}",
            title=f"Document {i}",
            source_url=f"https://example.com/doc_{i}.pdf",
            page_start=i,
            page_end=i + 1,
            excerpt=f"Excerpt content for chunk {i}",
            document_version="2025",
        )
        for i in range(1, 4)
    ]
    citations = CitationBuilder.build(chunks)
    assert len(citations) == 3
    for i, c in enumerate(citations, start=1):
        assert c.evidence_id == f"doc-p{i}-c01"
        assert c.document_id == f"doc_{i}"
        assert c.title == f"Document {i}"
        assert c.source_url == f"https://example.com/doc_{i}.pdf"
        assert c.page_start == i
        assert c.page_end == i + 1
        assert c.excerpt == f"Excerpt content for chunk {i}"
        assert c.document_version == "2025"
