# CampusCue RAG API Service

The `rag-api` service provides policy-grounded document ingestion, hybrid (dense and sparse) retrieval, reciprocal rank fusion (RRF), citation synthesis, and grounded question answering with abstention support for university club operations.

## Features

- **Document Parsing & Chunking**: Preserves page numbers, titles, and section breadcrumbs across PDF source documents.
- **Source Registry**: Enforces URL whitelists and official institutional document lineage.
- **Hybrid Retrieval**: Combines dense semantic embeddings (`sentence-transformers`) and BM25-style sparse keyword matching.
- **Reciprocal Rank Fusion (RRF)**: Deterministic multi-retriever rank merging.
- **Grounded Generation & Abstention**: Generates evidence-backed answers using Groq LLM (with built-in deterministic mock mode for offline dev/test) and abstains when evidence is insufficient.
- **Strict Evidence Citations**: Emits structured citation metadata with exact page numbers, URLs, and excerpts.

## Getting Started

### Installation

```bash
cd services/rag-api
pip install -e .
```

### Running the Service

```bash
uvicorn app.main:app --port 8002 --reload
```

### Running Tests

```bash
pytest tests/ -v
```

## API Endpoints

- `GET /health`: Liveness health check.
- `GET /ready`: Readiness check reporting configured providers.
- `POST /v1/retrieval/search`: Hybrid retrieval search over indexed policy evidence.
- `POST /v1/knowledge/answer`: Grounded question answering with structured citations.
