import threading
from pathlib import Path
from typing import Any

import numpy as np

from app.schemas.retrieval import EvidenceChunk


class ChromaStore:
    """Local ChromaDB vector store supporting multiple collections (policy corpus & proposals)."""

    def __init__(
        self,
        persist_directory: str | Path | None = None,
        collection_name: str = "campus_policy_corpus",
        use_mock: bool = False,
    ):
        self.persist_directory = str(persist_directory) if persist_directory else None
        self.default_collection_name = collection_name
        self.collection_name = collection_name
        self.use_mock = use_mock
        self._client: Any = None
        self._collections: dict[str, Any] = {}
        self._lock = threading.RLock()
        self._mock_chunks: dict[str, list[EvidenceChunk]] = {collection_name: []}

    def _get_client(self) -> Any:
        if self._client is None and not self.use_mock:
            import chromadb

            if self.persist_directory:
                self._client = chromadb.PersistentClient(path=self.persist_directory)
            else:
                self._client = chromadb.EphemeralClient()
        return self._client

    def get_or_create_collection(self, name: str | None = None) -> Any:
        target_name = name or self.default_collection_name
        with self._lock:
            if self.use_mock:
                if target_name not in self._mock_chunks:
                    self._mock_chunks[target_name] = []
                return None

            if target_name not in self._collections:
                client = self._get_client()
                self._collections[target_name] = client.get_or_create_collection(
                    name=target_name, metadata={"hnsw:space": "cosine"}
                )
            return self._collections[target_name]

    def _get_collection(self) -> Any:
        return self.get_or_create_collection(self.default_collection_name)

    def upsert_chunks(
        self,
        chunks: list[EvidenceChunk],
        embeddings: np.ndarray,
        collection_name: str | None = None,
        extra_metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Upsert evidence chunks and embeddings into the specified ChromaDB collection."""
        if not chunks:
            return

        target_name = collection_name or self.default_collection_name

        with self._lock:
            if self.use_mock:
                if target_name not in self._mock_chunks:
                    self._mock_chunks[target_name] = []
                self._mock_chunks[target_name].extend([c.model_copy() for c in chunks])
                return

            collection = self.get_or_create_collection(target_name)
            ids = [c.evidence_id for c in chunks]
            documents = [c.excerpt for c in chunks]
            metadatas = []
            for idx, c in enumerate(chunks):
                meta: dict[str, Any] = {
                    "document_id": c.document_id,
                    "title": c.title,
                    "source_url": c.source_url,
                    "page_start": c.page_start,
                    "page_end": c.page_end,
                    "section": c.section or "",
                }
                if extra_metadatas and idx < len(extra_metadatas):
                    meta.update(extra_metadatas[idx])
                metadatas.append(meta)

            collection.upsert(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
                embeddings=embeddings.tolist(),
            )

    def search(
        self,
        query_embedding: np.ndarray | list[float],
        top_k: int = 5,
        collection_name: str | None = None,
        where: dict[str, Any] | None = None,
    ) -> list[EvidenceChunk]:
        """Search ChromaDB collection using query embedding and optional metadata filter."""
        target_name = collection_name or self.default_collection_name

        with self._lock:
            if self.use_mock:
                chunks = self._mock_chunks.get(target_name, [])
                if where and "event_id" in where:
                    target_event = where["event_id"]
                    # If dict filter like {"$eq": ...}
                    if isinstance(target_event, dict):
                        target_event = target_event.get("$eq")
                    chunks = [c for c in chunks if str(target_event) in c.evidence_id or str(target_event) in c.document_id]
                return [c.model_copy() for c in chunks[:top_k]]

            collection = self.get_or_create_collection(target_name)
            emb_list: Any = (
                query_embedding.tolist()
                if isinstance(query_embedding, np.ndarray)
                else query_embedding
            )
            if isinstance(emb_list, list) and emb_list and isinstance(emb_list[0], (float, int)):
                emb_list = [emb_list]

            query_kwargs: dict[str, Any] = {
                "query_embeddings": emb_list,
                "n_results": top_k,
                "include": ["documents", "metadatas", "distances"],
            }
            if where:
                query_kwargs["where"] = where

            results = collection.query(**query_kwargs)

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

    def delete_where(
        self,
        where: dict[str, Any],
        collection_name: str | None = None,
    ) -> int:
        """Deletes items matching metadata filter in the specified collection, returning count deleted."""
        target_name = collection_name or self.default_collection_name
        with self._lock:
            if self.use_mock:
                current = self._mock_chunks.get(target_name, [])
                remaining = []
                deleted_count = 0
                for c in current:
                    match = True
                    for k, v in where.items():
                        target_val = v.get("$eq") if isinstance(v, dict) else v
                        if k == "event_id" and str(target_val) in c.evidence_id or getattr(c, k, None) == target_val:
                            match = True
                        else:
                            match = False
                    if match:
                        deleted_count += 1
                    else:
                        remaining.append(c)
                self._mock_chunks[target_name] = remaining
                return deleted_count

            collection = self.get_or_create_collection(target_name)
            existing = collection.get(where=where)
            num_to_delete = len(existing.get("ids", [])) if existing else 0
            if num_to_delete > 0:
                collection.delete(where=where)
            return num_to_delete

    def count(self, collection_name: str | None = None) -> int:
        target_name = collection_name or self.default_collection_name
        with self._lock:
            if self.use_mock:
                return len(self._mock_chunks.get(target_name, []))
            collection = self.get_or_create_collection(target_name)
            return int(collection.count())
