import pytest
from app.schemas.retrieval import EvidenceChunk
from app.retrieval.sparse import SparseRetriever


def test_sparse_retriever_exact_keyword_match():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=1,
            page_end=1,
            excerpt="ICTS provides microphones, projection systems, and campus network assistance.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=2,
            page_end=2,
            excerpt="Sports equipment must be returned before 6 PM.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="ICTS microphones projection", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score


def test_sparse_retriever_empty_index_returns_empty():
    retriever = SparseRetriever()
    assert retriever.search(query="ICTS", top_k=5) == []

    retriever.index([])
    assert retriever.search(query="ICTS", top_k=5) == []


def test_sparse_retriever_empty_query_returns_empty():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=1,
            page_end=1,
            excerpt="ICTS assistance.",
        )
    ]
    retriever.index(chunks)
    assert retriever.search(query="", top_k=5) == []
    assert retriever.search(query="   !@#$ ", top_k=5) == []


def test_sparse_retriever_top_k_limiting():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id=f"c{i}",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=i,
            page_end=i,
            excerpt=f"Rule {i} regarding campus facilities and ICTS equipment reservation.",
        )
        for i in range(1, 10)
    ]
    retriever.index(chunks)
    results = retriever.search(query="ICTS facilities", top_k=3)

    assert len(results) == 3


def test_sparse_retriever_higher_term_frequency_scores_higher():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=1,
            page_end=1,
            excerpt="Audio microphones microphones microphones setup guide.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=2,
            page_end=2,
            excerpt="Audio microphones setup guide.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="microphones", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score


def test_sparse_retriever_case_insensitivity():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=1,
            page_end=1,
            excerpt="ICTS Network Support Services.",
        )
    ]
    retriever.index(chunks)
    results_upper = retriever.search(query="ICTS NETWORK", top_k=1)
    results_lower = retriever.search(query="icts network", top_k=1)

    assert len(results_upper) == 1
    assert len(results_lower) == 1
    assert results_upper[0].score == results_lower[0].score
