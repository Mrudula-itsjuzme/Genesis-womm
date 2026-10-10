from typing import Dict, List
from app.schemas.retrieval import EvidenceChunk


def reciprocal_rank_fusion(
    dense_results: List[EvidenceChunk],
    sparse_results: List[EvidenceChunk],
    k: int = 60,
    top_k: int = 5,
) -> List[EvidenceChunk]:
    """Combines dense and sparse ranked lists using Reciprocal Rank Fusion: RRF_score = sum(1 / (k + rank))."""
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, EvidenceChunk] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        chunk_map[chunk.evidence_id] = chunk
        scores[chunk.evidence_id] = scores.get(chunk.evidence_id, 0.0) + (
            1.0 / (k + rank)
        )

    for rank, chunk in enumerate(sparse_results, start=1):
        if chunk.evidence_id not in chunk_map:
            chunk_map[chunk.evidence_id] = chunk
        scores[chunk.evidence_id] = scores.get(chunk.evidence_id, 0.0) + (
            1.0 / (k + rank)
        )

    # Deterministic sorting: by score descending, then evidence_id ascending
    sorted_ids = sorted(
        scores.keys(), key=lambda cid: (-scores[cid], cid)
    )

    fused_candidates: List[EvidenceChunk] = []
    for cid in sorted_ids[:top_k]:
        chunk = chunk_map[cid].model_copy()
        chunk.score = round(scores[cid], 6)
        fused_candidates.append(chunk)

    return fused_candidates
