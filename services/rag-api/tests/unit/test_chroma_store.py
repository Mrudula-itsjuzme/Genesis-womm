import numpy as np
from app.retrieval.chroma import ChromaStore
from app.schemas.retrieval import EvidenceChunk


def test_chroma_store_mock_upsert_and_search():
    store = ChromaStore(use_mock=True)
    chunks = [
        EvidenceChunk(
            evidence_id="osa-p01-c00",
            document_id="osa",
            title="Handbook",
            source_url="https://example.com",
            excerpt="Auditorium booking policy requires 7 days notice.",
            page_start=1,
            page_end=1,
        )
    ]
    store.upsert_chunks(chunks, np.zeros((1, 768), dtype=np.float32))

    assert store.count() == 1
    results = store.search([0.0] * 768, top_k=1)
    assert len(results) == 1
    assert results[0].evidence_id == "osa-p01-c00"


def test_chroma_store_live_ephemeral_client():
    store = ChromaStore(persist_directory=None, collection_name="test_live_col")
    chunks = [
        EvidenceChunk(
            evidence_id="doc1-p01-c00",
            document_id="doc1",
            title="Policy A",
            source_url="https://example.com/a",
            excerpt="Sports complex timings are 6am to 9pm.",
            page_start=1,
            page_end=1,
        ),
        EvidenceChunk(
            evidence_id="doc2-p01-c00",
            document_id="doc2",
            title="Policy B",
            source_url="https://example.com/b",
            excerpt="Canteen timings are 8am to 8pm.",
            page_start=2,
            page_end=2,
        ),
    ]
    # Unit vectors
    emb1 = np.zeros(768, dtype=np.float32)
    emb1[0] = 1.0
    emb2 = np.zeros(768, dtype=np.float32)
    emb2[1] = 1.0

    embeddings = np.vstack([emb1, emb2])
    store.upsert_chunks(chunks, embeddings)

    assert store.count() == 2

    # Query matching emb1
    results = store.search(emb1, top_k=1)
    assert len(results) == 1
    assert results[0].evidence_id == "doc1-p01-c00"
    assert results[0].score is not None
    assert results[0].score > 0.99
