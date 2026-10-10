import threading

import numpy as np
from app.retrieval.dense import DenseRetriever
from app.schemas.retrieval import EvidenceChunk


def test_dense_retriever_scores_matching_query():
    retriever = DenseRetriever(use_mock_embeddings=True)
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=1,
            page_end=1,
            excerpt="Venue booking deadline requires submitting an application 14 days before the event.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=2,
            page_end=2,
            excerpt="Students must wear formal dress during venue examinations.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="venue booking deadline", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score


def test_dense_retriever_empty_index_returns_empty():
    retriever = DenseRetriever(use_mock_embeddings=True)
    assert retriever.search(query="anything", top_k=5) == []

    retriever.index([])
    assert retriever.search(query="anything", top_k=5) == []


def test_dense_retriever_section_context_used_in_indexing():
    retriever = DenseRetriever(use_mock_embeddings=True)
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=1,
            page_end=1,
            section="Auditorium Reservation Policy",
            excerpt="Fill out the digital slip.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=2,
            page_end=2,
            section="Hostel Reservation Rules",
            excerpt="Silence hours begin at 10 PM.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="Auditorium Reservation", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score


def test_dense_retriever_top_k_limiting():
    retriever = DenseRetriever(use_mock_embeddings=True)
    chunks = [
        EvidenceChunk(
            evidence_id=f"c{i}",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=i,
            page_end=i,
            excerpt=f"Rule number {i} regarding campus event venue reservations.",
        )
        for i in range(1, 10)
    ]
    retriever.index(chunks)
    results = retriever.search(query="campus event venue", top_k=3)

    assert len(results) == 3


def test_dense_retriever_with_sentence_transformer_mock(monkeypatch):
    import numpy as np

    class FakeSentenceTransformer:
        def __init__(self, model_name):
            self.model_name = model_name

        def encode(self, texts, normalize_embeddings=True):
            # Return fixed dummy embeddings
            vectors = []
            for t in texts:
                vec = np.zeros(16, dtype=np.float32)
                if "booking guide" in t.lower():
                    vec[0] = 1.0
                elif "booking" in t.lower():
                    vec[0] = 0.5
                    vec[1] = 0.5
                else:
                    vec[1] = 1.0
                vectors.append(vec)
            return np.array(vectors)

    import sys
    import types
    fake_module = types.ModuleType("sentence_transformers")
    fake_module.SentenceTransformer = FakeSentenceTransformer
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    retriever = DenseRetriever(use_mock_embeddings=False)
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=1,
            page_end=1,
            excerpt="Booking guide.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=2,
            page_end=2,
            excerpt="Booking dress code.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search("booking guide", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score


def test_dense_retriever_negative_cosine_filtered():
    retriever = DenseRetriever(use_mock_embeddings=True)
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc 1",
            source_url="https://example.com/1",
            page_start=1,
            page_end=1,
            excerpt="completely distinct xyz",
        )
    ]
    retriever.index(chunks)
    # Mock embeddings dot product resulting in <= 0 should be filtered
    retriever.embeddings = np.array([[-1.0] * 64])
    results = retriever.search("unrelated query", top_k=5)
    assert len(results) == 0


def test_dense_retriever_thread_safety_during_index():
    retriever = DenseRetriever(use_mock_embeddings=True)
    initial_chunks = [
        EvidenceChunk(
            evidence_id=f"c{i}",
            document_id="doc",
            title="Title",
            source_url="https://example.com",
            page_start=1,
            page_end=1,
            excerpt=f"chunk number {i}",
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
                    excerpt=f"updated chunk {j}",
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

