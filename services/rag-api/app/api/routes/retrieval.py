from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.api.deps import get_dense_retriever, get_sparse_retriever
from app.retrieval.dense import DenseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion
from app.retrieval.sparse import SparseRetriever
from app.schemas.retrieval import SearchRequest, SearchResponse

router = APIRouter(prefix="/v1/retrieval", tags=["retrieval"])

# Cached service state references for backward-compatible test monkeypatching
dense_engine = get_dense_retriever()
sparse_engine = get_sparse_retriever()


@router.post("/search", response_model=SearchResponse)
def search(
    request: SearchRequest,
    req: Request,
    dense_engine: Annotated[DenseRetriever, Depends(get_dense_retriever)],
    sparse_engine: Annotated[SparseRetriever, Depends(get_sparse_retriever)],
) -> SearchResponse:
    dense_res = dense_engine.search(request.query, top_k=request.top_k * 2)
    sparse_res = sparse_engine.search(request.query, top_k=request.top_k * 2)
    fused = reciprocal_rank_fusion(dense_res, sparse_res, top_k=request.top_k)
    req_id = getattr(req.state, "request_id", None)

    return SearchResponse(query=request.query, candidates=fused, request_id=req_id)
