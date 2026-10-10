from fastapi import APIRouter
from app.schemas.knowledge import AnswerRequest, AnswerResponse
from app.api.routes.retrieval import dense_engine, sparse_engine
from app.retrieval.fusion import reciprocal_rank_fusion
from app.citations.builder import CitationBuilder
from app.generation.groq_client import GroundedGenerator

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])
generator = GroundedGenerator()


@router.post("/answer", response_model=AnswerResponse)
def answer_query(request: AnswerRequest):
    dense_res = dense_engine.search(request.query, top_k=request.top_k)
    sparse_res = sparse_engine.search(request.query, top_k=request.top_k)
    fused_candidates = reciprocal_rank_fusion(
        dense_res, sparse_res, top_k=request.top_k
    )

    answer_text, status = generator.generate_answer(
        request.query, fused_candidates
    )
    citations = (
        CitationBuilder.build(fused_candidates) if status == "grounded" else []
    )

    return AnswerResponse(
        query=request.query,
        answer=answer_text,
        status=status,
        citations=citations,
    )
