import pytest
from pydantic import ValidationError
from app.schemas.retrieval import EvidenceChunk, SearchRequest, SearchResponse
from app.schemas.knowledge import Citation, AnswerRequest, AnswerResponse


def test_evidence_chunk_serialization():
    chunk = EvidenceChunk(
        evidence_id="osa-2025-p12-s3-01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=12,
        page_end=12,
        section="Chapter 3 > Event Approval SOP",
        excerpt="Clubs must submit proposals 14 days prior to the event date.",
        document_version="2025",
        score=0.92,
    )
    assert chunk.evidence_id == "osa-2025-p12-s3-01"
    assert chunk.page_start == 12
    assert chunk.section == "Chapter 3 > Event Approval SOP"
    assert chunk.score == 0.92

    # Serialization roundtrip
    dumped = chunk.model_dump()
    assert dumped["evidence_id"] == "osa-2025-p12-s3-01"
    restored = EvidenceChunk.model_validate(dumped)
    assert restored == chunk


def test_search_request_validation():
    req = SearchRequest(query="campus quiet hours")
    assert req.query == "campus quiet hours"
    assert req.top_k == 5
    assert req.access_level == "CAMPUS_PUBLIC"

    # Validation: query min_length
    with pytest.raises(ValidationError):
        SearchRequest(query="")

    # Validation: top_k bounds
    with pytest.raises(ValidationError):
        SearchRequest(query="test", top_k=0)

    with pytest.raises(ValidationError):
        SearchRequest(query="test", top_k=51)


def test_search_response_serialization():
    chunk = EvidenceChunk(
        evidence_id="osa-2025-p12-s3-01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=12,
        page_end=12,
        section="Chapter 3 > Event Approval SOP",
        excerpt="Clubs must submit proposals 14 days prior to the event date.",
        document_version="2025",
        score=0.92,
    )
    resp = SearchResponse(
        query="event submission timeline",
        candidates=[chunk],
        request_id="req-search-01",
    )
    assert resp.query == "event submission timeline"
    assert len(resp.candidates) == 1
    assert resp.request_id == "req-search-01"
    assert resp.candidates[0].evidence_id == "osa-2025-p12-s3-01"


def test_citation_serialization():
    cit = Citation(
        evidence_id="osa-2025-p12-s3-01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=12,
        page_end=12,
        excerpt="Clubs must submit proposals 14 days prior to the event date.",
        document_version="2025",
    )
    assert cit.evidence_id == "osa-2025-p12-s3-01"
    assert cit.page_start == 12
    assert cit.excerpt == "Clubs must submit proposals 14 days prior to the event date."


def test_answer_request_validation():
    req = AnswerRequest(query="Can we host DJ night?")
    assert req.query == "Can we host DJ night?"
    assert req.top_k == 4
    assert req.access_level == "CAMPUS_PUBLIC"

    # Validation: query min_length
    with pytest.raises(ValidationError):
        AnswerRequest(query="")

    # Validation: top_k bounds (1 <= top_k <= 10)
    with pytest.raises(ValidationError):
        AnswerRequest(query="test", top_k=0)

    with pytest.raises(ValidationError):
        AnswerRequest(query="test", top_k=11)


def test_answer_response_abstention():
    resp = AnswerResponse(
        query="What is the policy for overnight DJ nights?",
        answer="I cannot find policy evidence regarding overnight DJ nights.",
        status="insufficient_evidence",
        citations=[],
        request_id="req-1234",
    )
    assert resp.status == "insufficient_evidence"
    assert len(resp.citations) == 0
    assert resp.request_id == "req-1234"


def test_answer_response_grounded():
    cit = Citation(
        evidence_id="osa-2025-p12-s3-01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=12,
        page_end=12,
        excerpt="Clubs must submit proposals 14 days prior to the event date.",
        document_version="2025",
    )
    resp = AnswerResponse(
        query="What is the deadline for event proposals?",
        answer="Clubs must submit proposals 14 days prior to the event date.",
        status="grounded",
        citations=[cit],
        request_id="req-5678",
    )
    assert resp.status == "grounded"
    assert len(resp.citations) == 1
    assert resp.citations[0].evidence_id == "osa-2025-p12-s3-01"


def test_answer_response_invalid_status():
    with pytest.raises(ValidationError):
        AnswerResponse(
            query="test",
            answer="test",
            status="hallucinated",  # Not in Literal["grounded", "insufficient_evidence"]
            citations=[],
        )
