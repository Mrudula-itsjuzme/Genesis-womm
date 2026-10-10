from app.schemas.retrieval import EvidenceChunk
from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_combines_and_fuses_rankings():
    c1 = EvidenceChunk(
        evidence_id="c1",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=1,
        page_end=1,
        excerpt="c1",
    )
    c2 = EvidenceChunk(
        evidence_id="c2",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=2,
        page_end=2,
        excerpt="c2",
    )
    c3 = EvidenceChunk(
        evidence_id="c3",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=3,
        page_end=3,
        excerpt="c3",
    )

    # dense ranks: c1 (1st), c2 (2nd)
    dense_rankings = [c1, c2]
    # sparse ranks: c2 (1st), c3 (2nd)
    sparse_rankings = [c2, c3]

    fused = reciprocal_rank_fusion(dense_rankings, sparse_rankings, k=60, top_k=3)

    assert len(fused) == 3
    # c2 was present in both lists, so its fused score is highest
    assert fused[0].evidence_id == "c2"
    # c1 was rank 1 in dense (1/61), c3 was rank 2 in sparse (1/62) -> c1 > c3
    assert fused[1].evidence_id == "c1"
    assert fused[2].evidence_id == "c3"


def test_rrf_tie_breaking_deterministic():
    # item_b is rank 1 in dense only: score = 1/(60+1)
    # item_a is rank 1 in sparse only: score = 1/(60+1)
    # Since scores are identical, deterministic tie-breaking by evidence_id ascending puts "item_a" before "item_b"
    cb = EvidenceChunk(
        evidence_id="item_b",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=1,
        page_end=1,
        excerpt="b",
    )
    ca = EvidenceChunk(
        evidence_id="item_a",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=2,
        page_end=2,
        excerpt="a",
    )

    fused = reciprocal_rank_fusion(dense_results=[cb], sparse_results=[ca], k=60, top_k=2)

    assert len(fused) == 2
    assert fused[0].evidence_id == "item_a"
    assert fused[1].evidence_id == "item_b"
    assert fused[0].score == fused[1].score == round(1.0 / 61, 6)


def test_rrf_empty_inputs():
    c = EvidenceChunk(
        evidence_id="c1",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=1,
        page_end=1,
        excerpt="c1",
    )

    # Both empty
    assert reciprocal_rank_fusion([], []) == []

    # Dense empty
    fused_sparse = reciprocal_rank_fusion([], [c], top_k=5)
    assert len(fused_sparse) == 1
    assert fused_sparse[0].evidence_id == "c1"
    assert fused_sparse[0].score == round(1.0 / 61, 6)

    # Sparse empty
    fused_dense = reciprocal_rank_fusion([c], [], top_k=5)
    assert len(fused_dense) == 1
    assert fused_dense[0].evidence_id == "c1"
    assert fused_dense[0].score == round(1.0 / 61, 6)


def test_rrf_top_k_limits():
    chunks = [
        EvidenceChunk(
            evidence_id=f"c{i}",
            document_id="d1",
            title="T",
            source_url="http://x",
            page_start=i,
            page_end=i,
            excerpt=f"c{i}",
        )
        for i in range(10)
    ]
    fused = reciprocal_rank_fusion(dense_results=chunks, sparse_results=[], top_k=3)
    assert len(fused) == 3


def test_rrf_does_not_mutate_input_chunks():
    c = EvidenceChunk(
        evidence_id="c1",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=1,
        page_end=1,
        excerpt="c1",
        score=0.0,
    )
    fused = reciprocal_rank_fusion([c], [], k=60, top_k=1)
    assert fused[0].score > 0.0
    assert c.score == 0.0
