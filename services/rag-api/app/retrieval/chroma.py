import threading
from pathlib import Path
from typing import Any

import numpy as np

from app.schemas.retrieval import EvidenceChunk


class ChromaStore:
    """Local ChromaDB vector store for persistent policy chunk embeddings."""

    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collection_name: str = "campus_policy_corpus",
        use_mock: bool = False,
    ):
        self.persist_directory = str(persist_directory) if persist_directory else None
        self.collection_name = collection_name
        self.use_mock = use_mock
        self._client: Any = None
        self._collection: Any = None
        self._lock = threading.RLock()
        self._mock_chunks: list[EvidenceChunk] = []

    def _get_collection(self) -> Any:
        if self._collection is None and not self.use_mock:
            import chromadb

            if self.persist_directory:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
            else:
                self._client = chromadb.EphemeralClient()
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name, metadata={"hnsw:space": "cosine"}
            )
        return self._collection

    def upsert_chunks(
        self, chunks: list[EvidenceChunk], embeddings: np.ndarray
    ) -> None:
        """Upsert evidence chunks and embeddings into ChromaDB."""
        if not chunks:
            return

        with self._lock:
            if self.use_mock:
                self._mock_chunks = list(chunks)
                return

            collection = self._get_collection()
            ids = [c.evidence_id for c in chunks]
            documents = [c.excerpt for c in chunks]
            metadatas = [
                {
                    "document_id": c.document_id,
                    "title": c.title,
                    "source_url": c.source_url,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "section": c.section or "",
                }
                for c in chunks
            ]
            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings.tolist(),
            )

    def search(
        self, query_embedding: np.ndarray | list[float], top_k: int = 5
    ) -> list[EvidenceChunk]:
        """Search ChromaDB using query embedding."""
        with self._lock:
            if self.use_mock:
                return [c.model_copy() for c in self._mock_chunks[:top_k]]

            collection = self._get_collection()
            emb_list: Any = (
                query_embedding.tolist()
                if isinstance(query_embedding, np.ndarray)
                else query_embedding
            )
            if isinstance(emb_list, list) and emb_list and isinstance(emb_list[0], (float, int)):
                emb_list = [emb_list]

            results = collection.query(
                query_embeddings=emb_list,
                n_results=top_k,
                include=["documents", "metadatas", "distances"],
            )

            matched_chunks: list[EvidenceChunk] = []
            if not results or not results.get("ids") or not results["ids"][0]:
                return []

            ids = results["ids"][0]
            docs = results["documents"][0] if results.get("documents") else []
            metas = results["metadatas"][0] if results.get("metadatas") else []
            distances = results["distances"][0] if results.get("distances") else []

            for idx, cid in enumerate(ids):
                meta = metas[idx] if idx < len(metas) else {}
                excerpt = docs[idx] if idx < len(docs) else ""
                dist = distances[idx] if idx < len(distances) else 0.0
                score = round(1.0 - float(dist), 6)

                matched_chunks.append(
                    EvidenceChunk(
                        evidence_id=cid,
                        document_id=str(meta.get("document_id", "unknown")),
                        title=str(meta.get("title", "")),
                        source_url=str(meta.get("source_url", "")),
                        excerpt=excerpt,
                        page_start=int(meta.get("page_start", 1)),
                        page_end=int(meta.get("page_end", 1)),
                        section=str(meta.get("section", "")),
                        score=score,
                    )
                )

            return matched_chunks

    def count(self) -> int:
        with self._lock:
            if self.use_mock:
                return len(self._mock_chunks)
            collection = self._get_collection()
            return int(collection.count())
