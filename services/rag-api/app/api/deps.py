from functools import lru_cache

import numpy as np

from app.config import settings
from app.generation.groq_client import GroundedGenerator
from app.ingest import load_persisted_corpus
from app.retrieval.chroma import ChromaStore
from app.retrieval.dense import DenseRetriever
from app.retrieval.sparse import SparseRetriever
from app.schemas.retrieval import EvidenceChunk

_SEED_CHUNKS = [
    EvidenceChunk(
        evidence_id="osa-2025-p12-c01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=12,
        page_end=12,
        section="Chapter 3 > Event Approvals",
        excerpt="Student club events must be submitted to the Student Affairs office at least 14 days prior to the proposed event date.",
        document_version="2025",
    ),
    EvidenceChunk(
        evidence_id="osa-2025-p15-c01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=15,
        page_end=15,
        section="Chapter 4 > Facility & Venue Bookings",
        excerpt="Official facility requisitions must specify AV requirements, seating arrangement, and ICTS support personnel needs.",
        document_version="2025",
    ),
]


def _get_initial_corpus() -> tuple[list[EvidenceChunk], np.ndarray | None]:
    chunks, embeddings = load_persisted_corpus()
    if chunks:
        return chunks, embeddings
    return _SEED_CHUNKS, None


@lru_cache
def get_dense_retriever() -> DenseRetriever:
    use_mock = settings.rag_embedding_provider != "local"
    retriever = DenseRetriever(use_mock_embeddings=use_mock)
    chunks, embeddings = _get_initial_corpus()
    if embeddings is not None and not use_mock and len(chunks) == len(embeddings):
        with retriever._lock:
            retriever.chunks = list(chunks)
            retriever.embeddings = embeddings
    else:
        retriever.index(chunks)
    return retriever


@lru_cache
def get_sparse_retriever() -> SparseRetriever:
    retriever = SparseRetriever()
    chunks, _ = _get_initial_corpus()
    retriever.index(chunks)
    return retriever


@lru_cache
def get_grounded_generator() -> GroundedGenerator:
    return GroundedGenerator()


@lru_cache
def get_chroma_store() -> ChromaStore:
    use_mock = settings.rag_embedding_provider != "local"
    persist_dir = settings.data_dir / "chroma_db"
    return ChromaStore(persist_directory=persist_dir, use_mock=use_mock)

