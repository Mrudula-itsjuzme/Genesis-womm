import pytest
from app.chunking.structure import StructureChunker
from app.parsing.pdf import ParsedPage


def test_structure_chunker_generates_stable_evidence_ids():
    chunker = StructureChunker(target_chunk_size=500, chunk_overlap=50)
    pages = [
        ParsedPage(
            page_number=12,
            text="Chapter 3: Event Approval SOP.\nClubs must request venue approval at least 14 days in advance. Facility booking requests must be signed by the Faculty Advisor.",
            section_breadcrumb="Chapter 3: Event Approval SOP",
        )
    ]
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.evidence_id == "osa_handbook_cbr-p12-c01"
    assert chunk.evidence_id.startswith("osa_handbook_cbr-p12-")
    assert chunk.page_start == 12
    assert chunk.page_end == 12
    assert "14 days in advance" in chunk.excerpt
    assert chunk.title == "Student Affairs Handbook"
    assert chunk.document_id == "osa_handbook_cbr"
    assert chunk.source_url == "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf"
    assert chunk.section == "Chapter 3: Event Approval SOP"
    assert chunk.document_version == "2025"


def test_structure_chunker_sliding_window_large_page():
    chunker = StructureChunker(target_chunk_size=500, chunk_overlap=50)
    # Generate 1200 distinct words
    words = [f"word{i}" for i in range(1200)]
    page_text = " ".join(words)
    pages = [
        ParsedPage(
            page_number=5,
            text=page_text,
            section_breadcrumb="Section 2.1: Financial Rules",
        )
    ]

    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="fin_handbook",
        title="Financial Handbook",
        source_url="https://example.com/fin.pdf",
    )

    # With target=500 and overlap=50, step size is 450:
    # Chunk 1: words 0..500
    # Chunk 2: words 450..950
    # Chunk 3: words 900..1200
    assert len(chunks) == 3
    assert chunks[0].evidence_id == "fin_handbook-p5-c01"
    assert chunks[1].evidence_id == "fin_handbook-p5-c02"
    assert chunks[2].evidence_id == "fin_handbook-p5-c03"

    for chunk in chunks:
        assert chunk.page_start == 5
        assert chunk.page_end == 5
        assert chunk.section == "Section 2.1: Financial Rules"

    # Verify overlap between chunk 0 and chunk 1
    c0_words = chunks[0].excerpt.split()
    c1_words = chunks[1].excerpt.split()
    assert len(c0_words) == 500
    assert len(c1_words) == 500
    assert c0_words[-50:] == c1_words[:50]

    # Verify final chunk ends with the last word
    c2_words = chunks[2].excerpt.split()
    assert c2_words[-1] == "word1199"


def test_structure_chunker_multiple_pages():
    chunker = StructureChunker(target_chunk_size=500, chunk_overlap=50)
    pages = [
        ParsedPage(
            page_number=1,
            text="Welcome to campus event organization.",
            section_breadcrumb="Intro",
        ),
        ParsedPage(
            page_number=2,
            text="Detailed booking steps and guidelines.",
            section_breadcrumb="Chapter 1: Guidelines",
        ),
    ]

    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="guide_cbr",
        title="Campus Guide",
        source_url="https://example.com/guide.pdf",
    )

    assert len(chunks) == 2
    assert chunks[0].evidence_id == "guide_cbr-p1-c01"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].section == "Intro"

    assert chunks[1].evidence_id == "guide_cbr-p2-c01"
    assert chunks[1].page_start == 2
    assert chunks[1].page_end == 2
    assert chunks[1].section == "Chapter 1: Guidelines"


def test_structure_chunker_empty_and_whitespace_pages():
    chunker = StructureChunker(target_chunk_size=500, chunk_overlap=50)
    pages = [
        ParsedPage(page_number=1, text=""),
        ParsedPage(page_number=2, text="   \n\t  "),
    ]
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="empty_doc",
        title="Empty Doc",
        source_url="https://example.com/empty.pdf",
    )
    assert chunks == []


def test_structure_chunker_section_breadcrumb_none():
    chunker = StructureChunker(target_chunk_size=500, chunk_overlap=50)
    pages = [
        ParsedPage(
            page_number=1,
            text="Text without any section breadcrumb present.",
            section_breadcrumb=None,
        )
    ]
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="doc_no_section",
        title="No Section Doc",
        source_url="https://example.com/nosect.pdf",
        document_version="2026-draft",
    )
    assert len(chunks) == 1
    assert chunks[0].section == ""
    assert chunks[0].document_version == "2026-draft"


def test_structure_chunker_invalid_overlap_raises():
    with pytest.raises(ValueError, match="chunk_overlap must be less than target_chunk_size"):
        StructureChunker(target_chunk_size=100, chunk_overlap=100)
