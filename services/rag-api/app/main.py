from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

app = FastAPI(
    title="CampusCue RAG API",
    version="0.1.0",
    description="Authorized campus policy retrieval and grounded knowledge synthesis service",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
