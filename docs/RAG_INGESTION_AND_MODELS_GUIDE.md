# CampusCue RAG Service: Ingestion, Chunking & Local Models Guide

**Pilot:** Amrita Vishwa Vidyapeetham, Coimbatore  
**Target Service:** `services/rag-api/`  
**Last Updated:** October 2026  

---

## 1. Overview & Local Model Catalog

To ensure low latency, zero external API costs for retrieval, and strict adherence to the **LLM-Free Retrieval Invariant** (`POST /v1/retrieval/search` must execute deterministically without an LLM), CampusCue runs all embedding, sparse retrieval, and re-ranking models **entirely locally**.

All required models have been pre-downloaded and verified in the local HuggingFace cache:

| Model Role | HuggingFace Identifier | Dimension / Output | Local Footprint | Purpose |
|---|---|---|---|---|
| **Dense Embeddings** | `sentence-transformers/all-MiniLM-L6-v2` | 384d normalized vector | ~90 MB | Semantic similarity search via dot product cosine similarity |
| **Cross-Encoder Re-ranker** | `cross-encoder/ms-marco-MiniLM-L-6-v2` | Relevance logit score | ~90 MB | Stage 2 joint-attention candidate re-ranking |
| **Neural Sparse (SPLADE)** | `naver/splade-cocondenser-ensembledistil` | 30,522d sparse term weights | ~250 MB | Semantic term expansion without losing exact keyword precision |
| **Exact Keyword (Sparse)** | In-memory BM25 (`SparseRetriever`) | Term frequency / IDF | 0 MB (Code) | Deterministic matching for acronyms, room numbers, and policy codes |

> [!NOTE]
> Local model weights are cached under `~/.cache/huggingface/hub/` on Windows/Linux and do not require internet access once loaded.

---

## 2. Structure-Aware Chunking Pipeline (`COR-01`)

### 2.1 The 256-Token Sequence Boundary
The dense embedding model (`all-MiniLM-L6-v2`) enforces a hard maximum sequence limit of **256 WordPiece tokens**. Chunks exceeding 256 tokens are silently truncated by BERT, causing severe information loss.

In `services/rag-api/app/chunking/structure.py`, the chunker is calibrated as follows:
- **Target chunk size:** `180 words` (~230–240 WordPiece tokens)
- **Overlap:** `30 words` (~40 WordPiece tokens)
- **Result:** 100% of chunk content is preserved within the 256-token window without truncation.

### 2.2 Provenance & Evidence Invariants
Every chunk created by `StructureChunker` generates a deterministic `EvidenceChunk` with:
- `evidence_id`: Formatted as `{document_id}-p{page_start}-c{index:02d}` (e.g., `osa_handbook_cbr-p02-c01`).
- `document_id`: Canonical document identifier from `SOURCE_REGISTRY.md`.
- `title`: Document or chapter title.
- `source_url`: Canonical public URL for auditability.
- `page_start` & `page_end`: Physical PDF page numbers.
- `section`: Heading or breadcrumb path (e.g., `"Event Approvals > Facility Booking"`).
- `excerpt`: The exact extracted text segment.

---

## 3. Step-by-Step: How to Run Ingestion & Chunking

### Step 1: Execute the Ingest Pipeline
Run the ingestion CLI from the repository root:

```powershell
services/rag-api/.venv/Scripts/python.exe services/rag-api/app/ingest.py
```

### What Happens During Ingestion:
1. **Source Retrieval:** Fetches approved sources from `SOURCE_REGISTRY.md`:
   - `osa_handbook_cbr`: `https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf` (27 pages)
   - `student_affairs_welfare`: `https://intranet.cb.amrita.edu/students-affairs-welfare`
   - `campus_infrastructure`: `https://www.amrita.edu/campus/coimbatore/infrastructure/`
2. **Parsing:**
   - PDF pages are extracted page-by-page via `PDFParser` preserving page boundaries.
   - HTML pages are cleaned via `BeautifulSoup` (stripping navigation, headers, footers, scripts).
3. **Calibrated Chunking:** `StructureChunker(target_chunk_size=180, chunk_overlap=30)` outputs **78 high-fidelity chunks**.
4. **Dense Vectorization:** Computes normalized 384d vectors using local `SentenceTransformer('all-MiniLM-L6-v2')`.
5. **Corpus Persistence:** Saves artifacts to `services/rag-api/data/`:
   - `corpus_chunks.jsonl` (78 chunks, JSON Lines)
   - `dense_embeddings.npy` (Matrix shape `(78, 384)`, float32)
6. **PostgreSQL Sync (Optional):** If PostgreSQL is running (`docker compose up -d postgres`), chunks are automatically synced to the `document_chunks` table.

---

## 4. How to Use the Models in Code

### 4.1 Hybrid Retrieval (Dense + BM25 with Reciprocal Rank Fusion)
```python
from app.ingest import load_persisted_corpus
from app.retrieval.dense import DenseRetriever
from app.retrieval.sparse import SparseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion

# 1. Load precomputed corpus and vectors
chunks, embeddings = load_persisted_corpus()

# 2. Initialize retrievers
dense = DenseRetriever(model_name="all-MiniLM-L6-v2")
dense.chunks = chunks
dense.embeddings = embeddings

sparse = SparseRetriever()
sparse.index(chunks)

# 3. Execute search
query = "What is the procedure for booking an auditorium?"
dense_results = dense.search(query, top_k=10)
sparse_results = sparse.search(query, top_k=10)

# 4. Deterministic Reciprocal Rank Fusion (k=60)
fused_candidates = reciprocal_rank_fusion(dense_results, sparse_results, k=60, top_k=5)

for c in fused_candidates:
    print(f"[{c.evidence_id}] Score: {c.score} | Page {c.page_start}: {c.excerpt[:120]}...")
```

### 4.2 Cross-Encoder Re-ranking (`CrossEncoderReranker`)
For maximum precision, pipe the candidate pool into the cross-encoder:

```python
from app.retrieval.rerank import CrossEncoderReranker

# Initialize local cross-encoder
reranker = CrossEncoderReranker(model_name="cross-encoder/ms-marco-MiniLM-L-6-v2")

# Stage 2: Re-rank the fused candidate pool
reranked_chunks = reranker.rerank(
    query="What is the procedure for booking an auditorium?",
    candidates=fused_candidates,
    top_k=3,
)

for c in reranked_chunks:
    print(f"[{c.evidence_id}] Cross-Attention Score: {c.score} | {c.title}")
```

### 4.3 Running SPLADE Neural Sparse Expansion
To expand queries with lexical synonyms before search:

```python
import torch
from transformers import AutoModelForMaskedLM, AutoTokenizer

model_id = "naver/splade-cocondenser-ensembledistil"
tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForMaskedLM.from_pretrained(model_id)

def get_splade_vector(text: str) -> dict[str, float]:
    tokens = tokenizer(text, return_tensors="pt")
    with torch.no_grad():
        logits = model(**tokens).logits
    # ReLU + log(1 + ReLU) max-pooled over sequence
    weights = torch.max(torch.log(1 + torch.relu(logits)), dim=1)[0].squeeze()
    
    top_indices = torch.topk(weights, k=30).indices.tolist()
    sparse_vector = {
        tokenizer.decode([idx]): round(weights[idx].item(), 4)
        for idx in top_indices if weights[idx] > 0
    }
    return sparse_vector

# Example expansion:
# Query: "OD for hackathon" -> expands with weights for "attendance", "permission", "duty", "leave"
sparse_dict = get_splade_vector("OD for hackathon")
```

---

## 5. Adding New Handbook Chapters or External URLs

To ingest new official documents:

1. Open `services/rag-api/app/ingest.py`.
2. Append the new document to `APPROVED_SOURCES`:
   ```python
   APPROVED_SOURCES.append({
       "source_id": "hostel_handbook_2026",
       "title": "Hostel Code of Conduct & Timings",
       "url": "https://webfiles.amrita.edu/2025/hostel-rules.pdf",
       "format": "pdf",  # or "html"
   })
   ```
3. Re-run:
   ```powershell
   services/rag-api/.venv/Scripts/python.exe services/rag-api/app/ingest.py
   ```
4. The service will parse the new pages, chunk them with `StructureChunker`, compute dense embeddings, and update `data/corpus_chunks.jsonl` and `data/dense_embeddings.npy`.

---

## 6. Offline Testing & Verification

CampusCue requires 100% offline testability. When running unit and integration tests, models switch automatically to deterministic mocks:
- `DenseRetriever(use_mock_embeddings=True)` uses MD5 word-hashing.
- `CrossEncoderReranker(use_mock=True)` preserves input rank.
- All 87 test cases pass with zero internet connection:
  ```powershell
  services/rag-api/.venv/Scripts/pytest.exe -c services/rag-api/pyproject.toml services/rag-api/tests/ -v
  ```
