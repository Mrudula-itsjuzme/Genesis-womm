import logging

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.middleware import RequestTracingMiddleware
from app.api.routes.knowledge import router as knowledge_router
from app.api.routes.retrieval import router as retrieval_router
from app.config import settings

logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s [%(levelname)s] %(name)s (%(filename)s:%(lineno)d): %(message)s",
)

app = FastAPI(
    title="CampusCue RAG API",
    version="0.1.0",
    description="Authorized campus policy retrieval and grounded knowledge synthesis service",
)

app.add_middleware(RequestTracingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    req_id = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=422,
        content={
            "code": "VALIDATION_ERROR",
            "message": "Invalid request parameters",
            "details": jsonable_encoder(exc.errors()),
            "request_id": req_id,
        },
        headers={"X-Request-ID": req_id} if req_id else {},
    )


app.include_router(retrieval_router)
app.include_router(knowledge_router)


@app.get("/health")
def health():
    return {"status": "ok", "service": "rag-api"}


@app.get("/ready")
def ready():
    return {
        "ready": True,
        "embedding_provider": settings.rag_embedding_provider,
        "sparse_provider": settings.rag_sparse_provider,
        "model_provider": settings.agent_model_provider,
    }
