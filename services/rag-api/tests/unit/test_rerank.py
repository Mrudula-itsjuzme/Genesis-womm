from app.retrieval.rerank import CrossEncoderReranker
from app.schemas.retrieval import EvidenceChunk


def test_cross_encoder_reranker_mock():
    reranker = CrossEncoderReranker(use_mock=True)
    chunks = [
        EvidenceChunk(
            evidence_id="doc1-p01-c00",
            document_id="doc1",
            title="Test Doc",
            source_url="https://example.com/1",
            excerpt="First chunk about venue booking",
            page_start=1,
            page_end=1,
            score=0.45,
        ),
        EvidenceChunk(
            evidence_id="doc1-p01-c01",
            document_id="doc1",
            title="Test Doc",
            source_url="https://example.com/1",
            excerpt="Second chunk about sports facilities",
            page_start=1,
            page_end=1,
            score=0.30,
        ),
    ]

    results = reranker.rerank("venue booking", chunks, top_k=1)
    assert len(results) == 1
    assert results[0].evidence_id == "doc1-p01-c00"


def test_cross_encoder_empty_candidates():
    reranker = CrossEncoderReranker(use_mock=True)
    assert reranker.rerank("query", []) == []


def test_cross_encoder_live_execution():
    reranker = CrossEncoderReranker(use_mock=False)
    chunks = [
        EvidenceChunk(
            evidence_id="doc1-p01-c00",
            document_id="doc1",
            title="Sports Facility",
            source_url="https://example.com/1",
            excerpt="The swimming pool requires a valid student id pass.",
            page_start=1,
            page_end=1,
        ),
        EvidenceChunk(
            evidence_id="doc1-p01-c01",
            document_id="doc1",
            title="Auditorium Policy",
            source_url="https://example.com/1",
            excerpt="Event permissions and auditorium bookings must be submitted 7 days in advance.",
            page_start=1,
            page_end=1,
        ),
    ]
    results = reranker.rerank("How do I book an auditorium for an event?", chunks, top_k=2)
    assert len(results) == 2
    # The auditorium chunk should be ranked #1
    assert results[0].evidence_id == "doc1-p01-c01"
    assert results[0].score is not None
    assert results[1].evidence_id == "doc1-p01-c00"
