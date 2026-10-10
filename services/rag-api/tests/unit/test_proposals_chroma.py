import numpy as np
from app.retrieval.chroma import ChromaStore
from app.schemas.retrieval import EvidenceChunk


def test_chroma_multi_collection_isolation() -> None:
    store = ChromaStore(use_mock=True)

    policy_chunk = EvidenceChunk(
        evidence_id="osa-handbook-c01",
        document_id="osa_handbook",
        title="Student Affairs Handbook",
        source_url="https://amrita.edu/handbook",
        excerpt="Clubs must submit proposals 14 days in advance.",
        page_start=5,
        page_end=5,
    )

    proposal_chunk = EvidenceChunk(
        evidence_id="proposal-p1-v1-c01",
        document_id="prop_evt_101",
        title="Hackathon Proposal",
        source_url="presigned://pdf",
        excerpt="We request the main auditorium for 24 hours.",
        page_start=1,
        page_end=1,
    )

    emb = np.random.randn(1, 768).astype(np.float32)

    # 1. Upsert into default (policy) collection
    store.upsert_chunks([policy_chunk], emb)

    # 2. Upsert into proposals collection
    store.upsert_chunks([proposal_chunk], emb, collection_name="proposals")

    assert store.count() == 1
    assert store.count(collection_name="proposals") == 1

    # 3. Search proposals collection
    results = store.search(emb[0], top_k=5, collection_name="proposals")
    assert len(results) == 1
    assert results[0].evidence_id == "proposal-p1-v1-c01"

    # 4. Search policy collection
    policy_results = store.search(emb[0], top_k=5)
    assert len(policy_results) == 1
    assert policy_results[0].evidence_id == "osa-handbook-c01"


def test_chroma_delete_where() -> None:
    store = ChromaStore(use_mock=True)

    p1 = EvidenceChunk(
        evidence_id="proposal-evt-1-p1",
        document_id="doc1",
        title="Proposal 1",
        source_url="url1",
        excerpt="Excerpt 1",
        page_start=1,
        page_end=1,
    )
    p2 = EvidenceChunk(
        evidence_id="proposal-evt-2-p2",
        document_id="doc2",
        title="Proposal 2",
        source_url="url2",
        excerpt="Excerpt 2",
        page_start=1,
        page_end=1,
    )

    emb = np.random.randn(2, 768).astype(np.float32)
    store.upsert_chunks([p1, p2], emb, collection_name="proposals")

    assert store.count(collection_name="proposals") == 2

    # Delete where event_id is evt-1
    deleted = store.delete_where({"event_id": "evt-1"}, collection_name="proposals")
    assert deleted == 1
    assert store.count(collection_name="proposals") == 1

    remaining = store.search(emb[0], top_k=5, collection_name="proposals")
    assert len(remaining) == 1
    assert remaining[0].evidence_id == "proposal-evt-2-p2"
