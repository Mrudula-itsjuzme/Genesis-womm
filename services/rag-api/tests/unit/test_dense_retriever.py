import pytest
from app.schemas.retrieval import EvidenceChunk
from app.retrieval.dense import DenseRetriever


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
            excerpt="Venue booking requires submitting an application 14 days before the event.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=2,
            page_end=2,
            excerpt="Students must wear formal dress during viva examinations.",
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
            section="Hostel Rules",
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
            # Return fixed dummy embeddings with orthogonal vectors
            vectors = []
            for t in texts:
                vec = np.zeros(16, dtype=np.float32)
                if "booking" in t.lower():
                    vec[0] = 1.0
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
            excerpt="Dress code.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search("booking guide", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score

