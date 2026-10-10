import math
import re
from collections import Counter
from typing import Dict, List
from app.schemas.retrieval import EvidenceChunk


class SparseRetriever:
    """Term-frequency BM25-style sparse keyword retriever."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[EvidenceChunk] = []
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = Counter()
        self.term_freqs: List[Dict[str, int]] = []

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b\w+\b", text)]

    def index(self, chunks: List[EvidenceChunk]):
        self.chunks = chunks
        if not chunks:
            self.term_freqs = []
            self.doc_len = []
            self.doc_freqs = Counter()
            self.avg_doc_len = 0.0
            return

        self.term_freqs = []
        self.doc_len = []
        self.doc_freqs = Counter()

        for chunk in chunks:
            tokens = self._tokenize(chunk.excerpt)
            self.doc_len.append(len(tokens))
            tf = Counter(tokens)
            self.term_freqs.append(tf)
            for token in set(tokens):
                self.doc_freqs[token] += 1

        self.avg_doc_len = (
            sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
        )

    def search(self, query: str, top_k: int = 5) -> List[EvidenceChunk]:
        if not self.chunks or not self.doc_len:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        num_docs = len(self.chunks)
        scores = [0.0] * num_docs

        for token in q_tokens:
            df = self.doc_freqs.get(token, 0)
            if df == 0:
                continue

            # IDF calculation
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)

            for i in range(num_docs):
                tf = self.term_freqs[i].get(token, 0)
                if tf == 0:
                    continue
                d_len = self.doc_len[i]
                numerator = tf * (self.k1 + 1)
                len_norm = (d_len / self.avg_doc_len) if self.avg_doc_len > 0 else 1.0
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * len_norm
                )
                if denominator > 0:
                    scores[i] += idf * (numerator / denominator)

        # Rank documents
        ranked_indices = [
            i for i in sorted(range(num_docs), key=lambda i: scores[i], reverse=True)
            if scores[i] > 0.0
        ][:top_k]

        results: List[EvidenceChunk] = []
        for idx in ranked_indices:
            c = self.chunks[idx].model_copy()
            c.score = float(scores[idx])
            results.append(c)

        return results
