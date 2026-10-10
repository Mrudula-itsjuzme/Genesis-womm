import threading

from app.retrieval.sparse import SparseRetriever
from app.schemas.retrieval import EvidenceChunk


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
            excerpt="Sports and ICTS equipment must be returned before 6 PM.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="ICTS microphones projection", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score


def test_sparse_retriever_zero_score_excluded():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=1,
            page_end=1,
            excerpt="ICTS provides microphones.",
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
    # Completely irrelevant query returns empty list
    results = retriever.search(query="astronomy telescope", top_k=5)
    assert results == []

    # Irrelevant chunks filtered out even if top_k is larger than matching count
    results_partial = retriever.search(query="microphones", top_k=5)
    assert len(results_partial) == 1
    assert results_partial[0].evidence_id == "c1"


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


def test_sparse_retriever_thread_safety_during_index():
    retriever = SparseRetriever()
    initial_chunks = [
        EvidenceChunk(
            evidence_id=f"c{i}",
            document_id="doc",
            title="Title",
            source_url="https://example.com",
            page_start=1,
            page_end=1,
            excerpt=f"chunk number {i} with unique words abc{i}",
        )
        for i in range(10)
    ]
    retriever.index(initial_chunks)

    errors = []

    def searcher():
        for _ in range(50):
            try:
                res = retriever.search("chunk", top_k=5)
                assert isinstance(res, list)
            except Exception as e:  # noqa: BLE001
                errors.append(e)

    def indexer():
        for i in range(10):
            new_chunks = [
                EvidenceChunk(
                    evidence_id=f"new_{j}",
                    document_id="doc",
                    title="Title",
                    source_url="https://example.com",
                    page_start=1,
                    page_end=1,
                    excerpt=f"updated chunk {j} with terms def{j}",
                )
                for j in range(5)
            ]
            retriever.index(new_chunks)

    t1 = threading.Thread(target=searcher)
    t2 = threading.Thread(target=indexer)
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    assert len(errors) == 0
