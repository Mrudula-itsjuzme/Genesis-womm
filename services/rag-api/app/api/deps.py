from functools import lru_cache

from app.config import settings
from app.generation.groq_client import GroundedGenerator
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


@lru_cache
def get_dense_retriever() -> DenseRetriever:
    use_mock = settings.rag_embedding_provider != "local"
    retriever = DenseRetriever(use_mock_embeddings=use_mock)
    retriever.index(_SEED_CHUNKS)
    return retriever


@lru_cache
def get_sparse_retriever() -> SparseRetriever:
    retriever = SparseRetriever()
    retriever.index(_SEED_CHUNKS)
    return retriever


@lru_cache
def get_grounded_generator() -> GroundedGenerator:
    return GroundedGenerator()
