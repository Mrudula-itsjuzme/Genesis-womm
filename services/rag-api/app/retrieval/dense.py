import hashlib
import threading

import numpy as np

from app.schemas.retrieval import EvidenceChunk


class DenseRetriever:
    """Local vector retriever using sentence-transformers or deterministic mock for fast tests."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        use_mock_embeddings: bool = False,
    ):
        self.model_name = model_name
        self.use_mock_embeddings = use_mock_embeddings
        self._model = None
        self._lock = threading.RLock()
        self.chunks: list[EvidenceChunk] = []
        self.embeddings: np.ndarray | None = None

    def _get_model(self):
        if self._model is None and not self.use_mock_embeddings:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _encode(self, texts: list[str]) -> np.ndarray:
        if self.use_mock_embeddings:
            # Deterministic, collision-resistant word-overlap vector for testing without downloading model
            dim = 64
            vectors = []
            for t in texts:
                vec = np.zeros(dim, dtype=np.float32)
                for word in t.lower().split():
                    bucket = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16) % dim
                    vec[bucket] += 1.0
                norm = np.linalg.norm(vec)
                vectors.append(vec / norm if norm > 0 else vec)
            return np.vstack(vectors)
        else:
            model = self._get_model()
            return np.array(model.encode(texts, normalize_embeddings=True))

    def index(self, chunks: list[EvidenceChunk]):
        if not chunks:
            with self._lock:
                self.chunks = []
                self.embeddings = None
            return

        texts = [f"{c.section}: {c.excerpt}" if c.section else c.excerpt for c in chunks]
        encoded_vectors = self._encode(texts)
        with self._lock:
            self.chunks = list(chunks)
            self.embeddings = encoded_vectors

    def search(self, query: str, top_k: int = 5) -> list[EvidenceChunk]:
        # Compute query vector outside the lock to avoid serializing concurrent searches
        q_vec = self._encode([query])[0]
        with self._lock:
            if not self.chunks or self.embeddings is None:
                return []

            # Dot product of normalized vectors = cosine similarity
            scores = np.dot(self.embeddings, q_vec)
            top_indices = [
                int(idx)
                for idx in np.argsort(scores)[::-1]
                if scores[idx] > 0.0
            ][:top_k]

            ranked: list[EvidenceChunk] = []
            for idx in top_indices:
                c = self.chunks[idx].model_copy()
                c.score = float(scores[idx])
                ranked.append(c)
            return ranked
