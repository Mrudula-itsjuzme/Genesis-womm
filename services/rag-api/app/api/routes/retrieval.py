from fastapi import APIRouter
from app.schemas.retrieval import SearchRequest, SearchResponse, EvidenceChunk
from app.retrieval.dense import DenseRetriever
from app.retrieval.sparse import SparseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion

router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])

# In-memory service state for initial demo/testing
dense_engine = DenseRetriever(use_mock_embeddings=True)
sparse_engine = SparseRetriever()

# Default seed demo data if index is empty
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

dense_engine.index(_SEED_CHUNKS)
sparse_engine.index(_SEED_CHUNKS)


@router.post("/search", response_model=SearchResponse)
def search(request: SearchRequest):
    dense_res = dense_engine.search(request.query, top_k=request.top_k * 2)
    sparse_res = sparse_engine.search(request.query, top_k=request.top_k * 2)
    fused = reciprocal_rank_fusion(dense_res, sparse_res, top_k=request.top_k)

    return SearchResponse(query=request.query, candidates=fused)
