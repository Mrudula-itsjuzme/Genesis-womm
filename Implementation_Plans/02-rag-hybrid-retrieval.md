# Implementation Plan 02: RAG Ingestion and Hybrid Retrieval

**Status:** Planned  
**Owner:** RAG workstream  
**Dependencies:** Plan 00; approved source documents; storage choice

## Objective
Build an independently runnable RAG service with approved-document ingestion, sparse + dense retrieval, fusion, citations, version tracking and measurable evaluation.

## Non-goals
- Index private organizer conversations or unapproved data.
- Infer official event/venue status.
- Claim answer correctness based only on vector similarity.
- Require an LLM for raw retrieval endpoints.

## Files expected
- `services/rag-api/app/api/routes/retrieval.py`
- `services/rag-api/app/api/routes/knowledge.py`
- `services/rag-api/app/ingestion/`
- `services/rag-api/app/parsing/`
- `services/rag-api/app/chunking/`
- `services/rag-api/app/retrieval/sparse.py`
- `services/rag-api/app/retrieval/dense.py`
- `services/rag-api/app/retrieval/fusion.py`
- `services/rag-api/app/retrieval/reranking.py`
- `services/rag-api/app/citations/`
- `services/rag-api/app/schemas/`
- `services/rag-api/tests/`
- `services/rag-api/evaluation/`

## Ordered steps
1. Define source allowlist, document access classes and version metadata.
2. Implement parser adapter interface and one approved PDF/HTML source path.
3. Preserve page numbers, headings, section paths, source URL, title, version and content hash.
4. Add structure-aware chunking; benchmark an initial 400–700-token range and modest overlap.
5. Store chunk metadata and dense vectors using `pgvector`.
6. Implement sparse retrieval using PostgreSQL full-text search or a benchmarked BM25 implementation.
7. Implement dense retrieval and access filters.
8. Implement Reciprocal Rank Fusion (RRF) and deterministic tie-breaking.
9. Add optional reranker behind an interface; do not require it for baseline operation.
10. Return raw retrieval candidates with stable evidence IDs and scores.
11. Implement grounded answer endpoint that receives only selected evidence and returns source-backed claims.
12. Build citation serialization from index metadata, not generated text.
13. Add `insufficient_evidence` behavior and tests.
14. Add document supersession, re-ingestion and parse-failure reporting.
15. Create a 30–50-question reviewed evaluation set.
16. Compare sparse-only, dense-only and hybrid using Recall@k, MRR/nDCG, citation correctness, faithfulness, abstention and latency.

## Suggested endpoints
- `POST /v1/retrieval/search`
- `POST /v1/knowledge/answer`
- `POST /v1/knowledge/ingest` (authorized admin only)
- `GET /v1/knowledge/documents`
- `GET /health`
- `GET /ready`

## Minimum metadata
`evidence_id`, `document_id`, title, source URL, page start/end, section, content hash, document version, access level, ingestion timestamp, verification timestamp and exact chunk text.

## Definition of done
- Search works without an LLM.
- Sparse, dense and hybrid results can be compared on the same test set.
- Citations resolve to stored source/page metadata.
- A response cannot invent source IDs or page numbers.
- Access filters run before context is passed to generation.
- Unanswerable questions can return insufficient evidence.
- Document re-ingestion does not silently create duplicate active versions.
- Tests cover malformed files, missing page metadata, stale versions and citation integrity.

## Risks
- PDF extraction may scramble tables or page order.
- Chunk boundaries can separate a rule from its exception.
- Embedding choice should be evaluated against campus terminology and available compute.
- Source freshness and authority need a human verification process.

## Deviation log
- Initial plan dated 2026-10-10; implementation not started.
