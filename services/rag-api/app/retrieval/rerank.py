import threading
from typing import Any

from app.schemas.retrieval import EvidenceChunk


class CrossEncoderReranker:
    """Local Cross-Encoder re-ranker for fine-grained joint attention scoring."""

    def __init__(
        self,
        model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2",
        use_mock: bool = False,
    ):
        self.model_name = model_name
        self.use_mock = use_mock
        self._model: Any = None
        self._lock = threading.RLock()

    def _get_model(self) -> Any:
        if self._model is None and not self.use_mock:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(self.model_name)
        return self._model

    def rerank(
        self, query: str, candidates: list[EvidenceChunk], top_k: int = 5
    ) -> list[EvidenceChunk]:
        """Reranks candidates using joint query-document cross-attention."""
        if not candidates:
            return []

        if self.use_mock:
            # Deterministic mock: preserve top_k by existing score or rank
            return [c.model_copy() for c in candidates[:top_k]]

        model = self._get_model()
        pairs = [
            [query, f"{c.section}: {c.excerpt}" if c.section else c.excerpt]
            for c in candidates
        ]
        with self._lock:
            scores = model.predict(pairs)

        scored_candidates: list[EvidenceChunk] = []
        for chunk, score in zip(candidates, scores, strict=False):
            c = chunk.model_copy()
            c.score = round(float(score), 6)
            scored_candidates.append(c)

        scored_candidates.sort(key=lambda x: (-(x.score or 0.0), x.evidence_id))
        return scored_candidates[:top_k]
