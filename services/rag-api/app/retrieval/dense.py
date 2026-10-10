from typing import List, Optional, Tuple
import numpy as np
from app.schemas.retrieval import EvidenceChunk


class DenseRetriever:
    """Local vector retriever using sentence-transformers or deterministic mock for fast tests."""

    def __init__(
        self, model_name: str = "all-MiniLM-L6-v2", use_mock_embeddings: bool = False
    ):
        self.model_name = model_name
        self.use_mock_embeddings = use_mock_embeddings
        self._model = None
        self.chunks: List[EvidenceChunk] = []
        self.embeddings: Optional[np.ndarray] = None

    def _get_model(self):
        if self._model is None and not self.use_mock_embeddings:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _encode(self, texts: List[str]) -> np.ndarray:
        if self.use_mock_embeddings:
            # Deterministic word-overlap vector for testing without downloading model
            dim = 64
            vectors = []
            for t in texts:
                vec = np.zeros(dim, dtype=np.float32)
                for word in t.lower().split():
                    idx = abs(hash(word)) % dim
                    vec[idx] += 1.0
                norm = np.linalg.norm(vec)
                vectors.append(vec / norm if norm > 0 else vec)
            return np.vstack(vectors)
        else:
            model = self._get_model()
            return np.array(model.encode(texts, normalize_embeddings=True))

    def index(self, chunks: List[EvidenceChunk]):
        self.chunks = chunks
        if not chunks:
            self.embeddings = None
            return
        texts = [f"{c.section}: {c.excerpt}" if c.section else c.excerpt for c in chunks]
        self.embeddings = self._encode(texts)

    def search(self, query: str, top_k: int = 5) -> List[EvidenceChunk]:
        if not self.chunks or self.embeddings is None:
            return []

        q_vec = self._encode([query])[0]
        # Dot product of normalized vectors = cosine similarity
        scores = np.dot(self.embeddings, q_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]

        ranked: List[EvidenceChunk] = []
        for idx in top_indices:
            c = self.chunks[idx].model_copy()
            c.score = float(scores[idx])
            ranked.append(c)
        return ranked
