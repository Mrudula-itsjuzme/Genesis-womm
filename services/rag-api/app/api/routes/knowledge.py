from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request

from app.api.deps import (
    get_dense_retriever,
    get_grounded_generator,
    get_sparse_retriever,
)
from app.citations.builder import CitationBuilder
from app.generation.groq_client import GroundedGenerator
from app.retrieval.dense import DenseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.sparse import SparseRetriever
from app.schemas.knowledge import AnswerRequest, AnswerResponse

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])

# Module-level reference to the cached generator for backward compatibility
generator = get_grounded_generator()


@router.post("/answer", response_model=AnswerResponse)
def answer_query(
    request: AnswerRequest,
    req: Request,
    dense_engine: Annotated[DenseRetriever, Depends(get_dense_retriever)],
    sparse_engine: Annotated[SparseRetriever, Depends(get_sparse_retriever)],
    generator: Annotated[GroundedGenerator, Depends(get_grounded_generator)],
) -> AnswerResponse:
    dense_res = dense_engine.search(request.query, top_k=request.top_k)
    sparse_res = sparse_engine.search(request.query, top_k=request.top_k)
    fused_candidates = reciprocal_rank_fusion(
        dense_res, sparse_res, top_k=request.top_k
    )

    answer_text, raw_status = generator.generate_answer(
        request.query, fused_candidates
    )
    status: Literal["grounded", "insufficient_evidence"] = (
        "grounded" if raw_status == "grounded" else "insufficient_evidence"
    )
    citations = (
        CitationBuilder.build(fused_candidates, cited_text=answer_text)
        if status == "grounded"
        else []
    )
    req_id = getattr(req.state, "request_id", None)

    return AnswerResponse(
        query=request.query,
        answer=answer_text,
        status=status,
        citations=citations,
        request_id=req_id,
    )
