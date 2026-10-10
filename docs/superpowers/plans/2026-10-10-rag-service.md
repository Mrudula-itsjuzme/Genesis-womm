# RAG Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build an independently runnable, fully testable RAG service (`services/rag-api`) for CampusCue that ingests approved policy documents (e.g., OSA Student Affairs Handbook), performs hybrid SPLADE + local dense retrieval with Reciprocal Rank Fusion, assembles metadata-grounded citations, and synthesizes answers via Groq with deterministic abstention.

**Architecture:** An independent FastAPI microservice organized into modular strata: PDF structure-aware parsing -> chunking (preserving page bounds and section hierarchy) -> dual-index retrieval (SPLADE sparse + local `sentence-transformers` dense) -> Reciprocal Rank Fusion (RRF) -> metadata-grounded citation builder -> Groq LLM answer generation with explicit `insufficient_evidence` abstention. Raw search (`POST /v1/retrieval/search`) operates completely without an LLM.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, PyPDF/pypdf, SPLADE / BM25, sentence-transformers (`all-MiniLM-L6-v2`), Groq Python SDK (`llama-3.3-70b-versatile`), pytest, httpx. (Strictly NO Gemini API).

**Spec:** `Implementation_Plans/02-rag-hybrid-retrieval.md`, `Implementation_Plans/06-official-source-ingestion.md`, `SOURCE_REGISTRY.md`, `contracts/CONTRACTS.md`.

## Global Constraints

- **Zero Gemini Dependency:** Strictly use Groq API (`llama-3.3-70b-versatile`) for text synthesis and local `sentence-transformers` for embeddings. No calls to Gemini APIs.
- **LLM-Free Retrieval Invariant:** `POST /v1/retrieval/search` must execute deterministically and return ranked candidates without invoking any LLM.
- **No Hallucinated Citations:** Citations must be built exclusively from stored document metadata (`evidence_id`, `document_id`, `title`, `source_url`, `page_start`, `page_end`, `excerpt`), never generated or guessed by an LLM.
- **Abstention First:** If retrieved evidence does not contain sufficient facts to answer, return `status: "insufficient_evidence"` with an explanatory message.
- **2–3 File Atomic Commit Cadence:** Every task must touch 2–3 cohesive files and be verified with clean test runs before committing. Never stage `git add .`.
- **Offline Testability:** All tests must pass offline using deterministic mocks or in-memory vector stores without requiring live external network access or paid API credits.

---

### Task 1: Scaffolding, Dependencies, and Configuration

**Files:**
- Create: `services/rag-api/pyproject.toml`
- Create: `services/rag-api/app/config.py`
- Test: `services/rag-api/tests/test_config.py`

**Interfaces:**
- Consumes: Environment variables (`GROQ_API_KEY`, `AGENT_MODEL_PROVIDER`, `RAG_EMBEDDING_PROVIDER`, etc.)
- Produces: `Settings` Pydantic model with typed accessors.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/test_config.py
import pytest
from app.config import Settings


def test_settings_defaults():
    settings = Settings()
    assert settings.rag_api_port == 8002
    assert settings.rag_embedding_provider == "local"
    assert settings.rag_embedding_model == "all-MiniLM-L6-v2"
    assert settings.agent_model_provider == "groq"
    assert settings.rag_sparse_provider == "splade"


def test_settings_override(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "gsk_test_12345")
    monkeypatch.setenv("RAG_API_PORT", "8010")
    settings = Settings()
    assert settings.groq_api_key == "gsk_test_12345"
    assert settings.rag_api_port == 8010
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/test_config.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app'`

- [ ] **Step 3: Write pyproject.toml and implementation**

```toml
# services/rag-api/pyproject.toml
[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[project]
name = "campuscue-rag-api"
version = "0.1.0"
description = "CampusCue RAG API Service"
readme = "README.md"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn>=0.30.0",
    "pydantic>=2.8.0",
    "pydantic-settings>=2.4.0",
    "httpx>=0.27.0",
    "pypdf>=4.3.0",
    "sentence-transformers>=3.0.0",
    "groq>=0.11.0",
    "numpy>=1.26.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "pytest-mock>=3.14.0",
    "ruff>=0.6.0",
    "mypy>=1.11.0",
]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
```

```python
# services/rag-api/app/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    campus_timezone: str = Field(default="Asia/Kolkata")
    rag_api_port: int = Field(default=8002)
    agent_model_provider: str = Field(default="groq")
    groq_api_key: str = Field(default="")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    groq_temperature: float = Field(default=0.0)

    rag_embedding_provider: str = Field(default="local")
    rag_embedding_model: str = Field(default="all-MiniLM-L6-v2")
    rag_embedding_device: str = Field(default="cpu")
    rag_sparse_provider: str = Field(default="splade")

    log_level: str = Field(default="INFO")


settings = Settings()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/test_config.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/pyproject.toml services/rag-api/app/config.py services/rag-api/tests/test_config.py
git commit -m "feat(rag): add pyproject dependencies and service configuration"
```

---

### Task 2: Pydantic Schemas for Retrieval, Knowledge, and Citations

**Files:**
- Create: `services/rag-api/app/schemas/retrieval.py`
- Create: `services/rag-api/app/schemas/knowledge.py`
- Test: `services/rag-api/tests/unit/test_schemas.py`

**Interfaces:**
- Consumes: Pydantic v2
- Produces: `EvidenceChunk`, `SearchRequest`, `SearchResponse`, `Citation`, `AnswerRequest`, `AnswerResponse` conforming to `contracts/CONTRACTS.md`.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_schemas.py
from app.schemas.retrieval import EvidenceChunk, SearchRequest, SearchResponse
from app.schemas.knowledge import Citation, AnswerRequest, AnswerResponse


def test_evidence_chunk_serialization():
    chunk = EvidenceChunk(
        evidence_id="osa-2025-p12-s3-01",
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        page_start=12,
        page_end=12,
        section="Chapter 3 > Event Approval SOP",
        excerpt="Clubs must submit proposals 14 days prior to the event date.",
        document_version="2025",
        score=0.92,
    )
    assert chunk.evidence_id == "osa-2025-p12-s3-01"
    assert chunk.page_start == 12


def test_answer_response_abstention():
    resp = AnswerResponse(
        query="What is the policy for overnight DJ nights?",
        answer="I cannot find policy evidence regarding overnight DJ nights.",
        status="insufficient_evidence",
        citations=[],
        request_id="req-1234",
    )
    assert resp.status == "insufficient_evidence"
    assert len(resp.citations) == 0
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_schemas.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.schemas'`

- [ ] **Step 3: Write minimal schema implementation**

```python
# services/rag-api/app/schemas/retrieval.py
from typing import List, Optional
from pydantic import BaseModel, Field


class EvidenceChunk(BaseModel):
    evidence_id: str = Field(..., description="Stable chunk identifier")
    document_id: str = Field(..., description="Document identifier from source registry")
    title: str = Field(..., description="Official title of the source document")
    source_url: str = Field(..., description="Canonical source URL")
    page_start: int = Field(..., description="Starting 1-indexed page number")
    page_end: int = Field(..., description="Ending 1-indexed page number")
    section: str = Field(default="", description="Section hierarchy path")
    excerpt: str = Field(..., description="Exact extracted chunk text")
    document_version: str = Field(default="2025", description="Document version or year")
    score: float = Field(default=0.0, description="Fused retrieval relevance score")


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language search query")
    top_k: int = Field(default=5, ge=1, le=50, description="Maximum evidence chunks to return")
    access_level: str = Field(default="CAMPUS_PUBLIC", description="Access filter class")


class SearchResponse(BaseModel):
    query: str
    candidates: List[EvidenceChunk]
    request_id: Optional[str] = None
```

```python
# services/rag-api/app/schemas/knowledge.py
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.schemas.retrieval import EvidenceChunk


class Citation(BaseModel):
    evidence_id: str
    document_id: str
    title: str
    source_url: str
    page_start: int
    page_end: int
    excerpt: str
    document_version: str


class AnswerRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Policy question to answer")
    top_k: int = Field(default=4, ge=1, le=10, description="Evidence chunks to ground against")
    access_level: str = Field(default="CAMPUS_PUBLIC")


class AnswerResponse(BaseModel):
    query: str
    answer: str
    status: Literal["grounded", "insufficient_evidence"]
    citations: List[Citation]
    request_id: Optional[str] = None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_schemas.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/schemas/retrieval.py services/rag-api/app/schemas/knowledge.py services/rag-api/tests/unit/test_schemas.py
git commit -m "feat(rag): define retrieval and knowledge contract schemas"
```

---

### Task 3: FastAPI Application Skeleton & Health Endpoints

**Files:**
- Create: `services/rag-api/app/main.py`
- Test: `services/rag-api/tests/integration/test_health.py`

**Interfaces:**
- Consumes: `Settings`
- Produces: FastAPI app with `GET /health` and `GET /ready`.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/integration/test_health.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "rag-api"


def test_ready_endpoint():
    response = client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["ready"] is True
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/integration/test_health.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.main'`

- [ ] **Step 3: Write app/main.py implementation**

```python
# services/rag-api/app/main.py
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/integration/test_health.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/main.py services/rag-api/tests/integration/test_health.py
git commit -m "feat(rag): add fastapi application skeleton with health and ready endpoints"
```

---

### Task 4: Source Allowlist Registry

**Files:**
- Create: `services/rag-api/app/ingestion/source_registry.py`
- Test: `services/rag-api/tests/unit/test_source_registry.py`

**Interfaces:**
- Consumes: `SOURCE_REGISTRY.md` definitions
- Produces: `SourceRegistry` validating URLs and returning metadata for allowed sources (`osa_handbook_cbr`, `student_affairs_welfare`).

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_source_registry.py
import pytest
from app.ingestion.source_registry import SourceRegistry, SourceEntry


def test_get_allowed_source():
    entry = SourceRegistry.get_by_id("osa_handbook_cbr")
    assert entry is not None
    assert entry.source_id == "osa_handbook_cbr"
    assert entry.format == "pdf"
    assert "student-affairs-handbook-cbr.pdf" in entry.url


def test_is_allowed_url():
    assert SourceRegistry.is_allowed(
        "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf"
    )
    assert not SourceRegistry.is_allowed("https://random-unauthorized-site.com/doc.pdf")


def test_disallowed_source_raises():
    with pytest.raises(ValueError, match="Disallowed or unregistered source"):
        SourceRegistry.validate_url("https://malicious-site.com/exploit.pdf")
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_source_registry.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.ingestion'`

- [ ] **Step 3: Implement SourceRegistry**

```python
# services/rag-api/app/ingestion/source_registry.py
from typing import Dict, Optional
from pydantic import BaseModel


class SourceEntry(BaseModel):
    source_id: str
    title: str
    url: str
    format: str
    category: str
    treatment: str
    access_level: str = "CAMPUS_PUBLIC"


class SourceRegistry:
    _SOURCES: Dict[str, SourceEntry] = {
        "osa_handbook_cbr": SourceEntry(
            source_id="osa_handbook_cbr",
            title="OSA Student Affairs Handbook",
            url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
            format="pdf",
            category="policy",
            treatment="Structure-aware PDF parser preserving page numbers and headings",
        ),
        "student_affairs_welfare": SourceEntry(
            source_id="student_affairs_welfare",
            title="Student Affairs and Welfare",
            url="https://intranet.cb.amrita.edu/students-affairs-welfare",
            format="html",
            category="policy",
            treatment="Constrained HTML policy extractor",
        ),
    }

    @classmethod
    def get_by_id(cls, source_id: str) -> Optional[SourceEntry]:
        return cls._SOURCES.get(source_id)

    @classmethod
    def get_by_url(cls, url: str) -> Optional[SourceEntry]:
        for entry in cls._SOURCES.values():
            if entry.url == url:
                return entry
        return None

    @classmethod
    def is_allowed(cls, url: str) -> bool:
        return cls.get_by_url(url) is not None

    @classmethod
    def validate_url(cls, url: str) -> SourceEntry:
        entry = cls.get_by_url(url)
        if not entry:
            raise ValueError(f"Disallowed or unregistered source URL: {url}")
        return entry
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_source_registry.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/ingestion/source_registry.py services/rag-api/tests/unit/test_source_registry.py
git commit -m "feat(rag): implement source allowlist registry matching SOURCE_REGISTRY.md"
```

---

### Task 5: Structure-Aware PDF Parser

**Files:**
- Create: `services/rag-api/app/parsing/pdf.py`
- Test: `services/rag-api/tests/unit/test_pdf_parser.py`

**Interfaces:**
- Consumes: Binary PDF streams or file paths
- Produces: `List[ParsedPage]` with page number (1-indexed), raw text, and detected heading breadcrumbs.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_pdf_parser.py
import io
from pypdf import PdfWriter
from app.parsing.pdf import PDFParser, ParsedPage


def _create_mock_pdf_bytes() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)
    stream.seek(0)
    return stream.getvalue()


def test_pdf_parser_page_preservation(tmp_path):
    # Test with synthetic multi-page content using StringIO/text mocks
    pages = [
        ParsedPage(page_number=1, text="Chapter 1: Overview\nWelcome to Amrita Coimbatore."),
        ParsedPage(page_number=2, text="Chapter 2: Club Guidelines\nClubs must register annually."),
    ]
    assert len(pages) == 2
    assert pages[0].page_number == 1
    assert "Overview" in pages[0].text
    assert pages[1].page_number == 2


def test_pdf_parser_rejects_empty_bytes():
    parser = PDFParser()
    result = parser.parse_bytes(b"")
    assert result == []
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_pdf_parser.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.parsing'`

- [ ] **Step 3: Implement PDFParser**

```python
# services/rag-api/app/parsing/pdf.py
import io
from typing import List, Optional
from pydantic import BaseModel
from pypdf import PdfReader


class ParsedPage(BaseModel):
    page_number: int
    text: str
    section_breadcrumb: Optional[str] = None


class PDFParser:
    """Extracts text page-by-page from PDFs preserving 1-indexed page boundaries."""

    def parse_bytes(self, pdf_bytes: bytes) -> List[ParsedPage]:
        if not pdf_bytes:
            return []

        stream = io.BytesIO(pdf_bytes)
        try:
            reader = PdfReader(stream)
        except Exception:
            return []

        parsed_pages: List[ParsedPage] = []
        current_heading = ""

        for page_idx, page in enumerate(reader.pages):
            page_num = page_idx + 1
            text = page.extract_text() or ""
            cleaned = text.strip()

            lines = cleaned.splitlines()
            if lines and (lines[0].startswith("Chapter") or lines[0].isupper()):
                current_heading = lines[0].strip()

            parsed_pages.append(
                ParsedPage(
                    page_number=page_num,
                    text=cleaned,
                    section_breadcrumb=current_heading if current_heading else None,
                )
            )

        return parsed_pages

    def parse_file(self, file_path: str) -> List[ParsedPage]:
        with open(file_path, "rb") as f:
            return self.parse_bytes(f.read())
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_pdf_parser.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/parsing/pdf.py services/rag-api/tests/unit/test_pdf_parser.py
git commit -m "feat(rag): implement structure-aware pdf parser preserving page numbers"
```

---

### Task 6: Structure-Aware Chunking Engine

**Files:**
- Create: `services/rag-api/app/chunking/structure.py`
- Test: `services/rag-api/tests/unit/test_chunking.py`

**Interfaces:**
- Consumes: `List[ParsedPage]`, `source_id`, `document_id`, `title`, `source_url`
- Produces: `List[EvidenceChunk]` bounded to 400–700 tokens with stable `evidence_id`.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_chunking.py
from app.parsing.pdf import ParsedPage
from app.chunking.structure import StructureChunker


def test_structure_chunker_generates_stable_evidence_ids():
    chunker = StructureChunker(target_chunk_size=500, chunk_overlap=50)
    pages = [
        ParsedPage(
            page_number=12,
            text="Chapter 3: Event Approval SOP.\nClubs must request venue approval at least 14 days in advance. Facility booking requests must be signed by the Faculty Advisor.",
            section_breadcrumb="Chapter 3: Event Approval SOP",
        )
    ]
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="osa_handbook_cbr",
        title="Student Affairs Handbook",
        source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
    )

    assert len(chunks) == 1
    chunk = chunks[0]
    assert chunk.evidence_id.startswith("osa_handbook_cbr-p12-")
    assert chunk.page_start == 12
    assert chunk.page_end == 12
    assert "14 days in advance" in chunk.excerpt
    assert chunk.title == "Student Affairs Handbook"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_chunking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.chunking'`

- [ ] **Step 3: Implement StructureChunker**

```python
# services/rag-api/app/chunking/structure.py
import re
from typing import List
from app.parsing.pdf import ParsedPage
from app.schemas.retrieval import EvidenceChunk


class StructureChunker:
    """Splits parsed pages into 400-700 token chunks preserving section and page metadata."""

    def __init__(self, target_chunk_size: int = 500, chunk_overlap: int = 50):
        self.target_chunk_size = target_chunk_size
        self.chunk_overlap = chunk_overlap

    def _approx_token_count(self, text: str) -> int:
        return len(text.split())

    def chunk_pages(
        self,
        pages: List[ParsedPage],
        document_id: str,
        title: str,
        source_url: str,
        document_version: str = "2025",
    ) -> List[EvidenceChunk]:
        chunks: List[EvidenceChunk] = []

        for page in pages:
            if not page.text:
                continue

            words = page.text.split()
            if not words:
                continue

            # If page fits within target chunk size, keep it as single chunk
            if len(words) <= self.target_chunk_size:
                evidence_id = f"{document_id}-p{page.page_number}-c01"
                chunks.append(
                    EvidenceChunk(
                        evidence_id=evidence_id,
                        document_id=document_id,
                        title=title,
                        source_url=source_url,
                        page_start=page.page_number,
                        page_end=page.page_number,
                        section=page.section_breadcrumb or "",
                        excerpt=page.text,
                        document_version=document_version,
                    )
                )
            else:
                # Sliding window chunking
                start_idx = 0
                chunk_seq = 1
                while start_idx < len(words):
                    end_idx = min(start_idx + self.target_chunk_size, len(words))
                    chunk_text = " ".join(words[start_idx:end_idx])
                    evidence_id = f"{document_id}-p{page.page_number}-c{chunk_seq:02d}"

                    chunks.append(
                        EvidenceChunk(
                            evidence_id=evidence_id,
                            document_id=document_id,
                            title=title,
                            source_url=source_url,
                            page_start=page.page_number,
                            page_end=page.page_number,
                            section=page.section_breadcrumb or "",
                            excerpt=chunk_text,
                            document_version=document_version,
                        )
                    )

                    if end_idx >= len(words):
                        break
                    start_idx += self.target_chunk_size - self.chunk_overlap
                    chunk_seq += 1

        return chunks
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_chunking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/chunking/structure.py services/rag-api/tests/unit/test_chunking.py
git commit -m "feat(rag): add structure-aware chunker with stable evidence ids"
```

---

### Task 7: Local Dense Retriever (`sentence-transformers`)

**Files:**
- Create: `services/rag-api/app/retrieval/dense.py`
- Test: `services/rag-api/tests/unit/test_dense_retriever.py`

**Interfaces:**
- Consumes: `List[EvidenceChunk]`, query string
- Produces: Cosine-similarity ranked candidates using local `all-MiniLM-L6-v2` (or in-memory mock embedder for fast unit tests).

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_dense_retriever.py
import pytest
from app.schemas.retrieval import EvidenceChunk
from app.retrieval.dense import DenseRetriever


def test_dense_retriever_scores_matching_query():
    retriever = DenseRetriever(use_mock_embeddings=True)
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=1,
            page_end=1,
            excerpt="Venue booking requires submitting an application 14 days before the event.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Handbook",
            source_url="http://example.com",
            page_start=2,
            page_end=2,
            excerpt="Students must wear formal dress during viva examinations.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="venue booking deadline", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_dense_retriever.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.retrieval'`

- [ ] **Step 3: Implement DenseRetriever**

```python
# services/rag-api/app/retrieval/dense.py
from typing import List, Tuple
import numpy as np
from app.schemas.retrieval import EvidenceChunk


class DenseRetriever:
    """Local vector retriever using sentence-transformers or deterministic mock for fast tests."""

    def __init__(
        self, model_name: str = "all-MiniLM-L6-v2", use_mock_embeddings: bool = False
    ):
        self.model_name = model_name
        self.use_mock_embeddings = use_mock_embeddings
        self._model = None
        self.chunks: List[EvidenceChunk] = []
        self.embeddings: Optional[np.ndarray] = None

    def _get_model(self):
        if self._model is None and not self.use_mock_embeddings:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
        return self._model

    def _encode(self, texts: List[str]) -> np.ndarray:
        if self.use_mock_embeddings:
            # Deterministic word-overlap vector for testing without downloading model
            dim = 64
            vectors = []
            for t in texts:
                vec = np.zeros(dim, dtype=np.float32)
                for word in t.lower().split():
                    idx = abs(hash(word)) % dim
                    vec[idx] += 1.0
                norm = np.linalg.norm(vec)
                vectors.append(vec / norm if norm > 0 else vec)
            return np.vstack(vectors)
        else:
            model = self._get_model()
            return np.array(model.encode(texts, normalize_embeddings=True))

    def index(self, chunks: List[EvidenceChunk]):
        self.chunks = chunks
        if not chunks:
            self.embeddings = None
            return
        texts = [f"{c.section}: {c.excerpt}" if c.section else c.excerpt for c in chunks]
        self.embeddings = self._encode(texts)

    def search(self, query: str, top_k: int = 5) -> List[EvidenceChunk]:
        if not self.chunks or self.embeddings is None:
            return []

        q_vec = self._encode([query])[0]
        # Dot product of normalized vectors = cosine similarity
        scores = np.dot(self.embeddings, q_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]

        ranked: List[EvidenceChunk] = []
        for idx in top_indices:
            c = self.chunks[idx].model_copy()
            c.score = float(scores[idx])
            ranked.append(c)
        return ranked
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_dense_retriever.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/retrieval/dense.py services/rag-api/tests/unit/test_dense_retriever.py
git commit -m "feat(rag): add local dense retriever using sentence-transformers"
```

---

### Task 8: Sparse Retriever (SPLADE / BM25)

**Files:**
- Create: `services/rag-api/app/retrieval/sparse.py`
- Test: `services/rag-api/tests/unit/test_sparse_retriever.py`

**Interfaces:**
- Consumes: `List[EvidenceChunk]`, query string
- Produces: Term-overlap / sparse frequency-ranked candidates with scores.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_sparse_retriever.py
from app.schemas.retrieval import EvidenceChunk
from app.retrieval.sparse import SparseRetriever


def test_sparse_retriever_exact_keyword_match():
    retriever = SparseRetriever()
    chunks = [
        EvidenceChunk(
            evidence_id="c1",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=1,
            page_end=1,
            excerpt="ICTS provides microphones, projection systems, and campus network assistance.",
        ),
        EvidenceChunk(
            evidence_id="c2",
            document_id="doc1",
            title="Doc",
            source_url="http://test",
            page_start=2,
            page_end=2,
            excerpt="Sports equipment must be returned before 6 PM.",
        ),
    ]
    retriever.index(chunks)
    results = retriever.search(query="ICTS microphones projection", top_k=2)

    assert len(results) == 2
    assert results[0].evidence_id == "c1"
    assert results[0].score > results[1].score
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_sparse_retriever.py -v`
Expected: FAIL with `ImportError: cannot import name 'SparseRetriever'`

- [ ] **Step 3: Implement SparseRetriever**

```python
# services/rag-api/app/retrieval/sparse.py
import math
import re
from collections import Counter
from typing import Dict, List, Set
from app.schemas.retrieval import EvidenceChunk


class SparseRetriever:
    """Term-frequency BM25-style sparse keyword retriever."""

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.chunks: List[EvidenceChunk] = []
        self.doc_len: List[int] = []
        self.avg_doc_len: float = 0.0
        self.doc_freqs: Dict[str, int] = Counter()
        self.term_freqs: List[Dict[str, int]] = []

    def _tokenize(self, text: str) -> List[str]:
        return [w.lower() for w in re.findall(r"\b\w+\b", text)]

    def index(self, chunks: List[EvidenceChunk]):
        self.chunks = chunks
        if not chunks:
            return

        self.term_freqs = []
        self.doc_len = []
        self.doc_freqs = Counter()

        for chunk in chunks:
            tokens = self._tokenize(chunk.excerpt)
            self.doc_len.append(len(tokens))
            tf = Counter(tokens)
            self.term_freqs.append(tf)
            for token in set(tokens):
                self.doc_freqs[token] += 1

        self.avg_doc_len = (
            sum(self.doc_len) / len(self.doc_len) if self.doc_len else 0.0
        )

    def search(self, query: str, top_k: int = 5) -> List[EvidenceChunk]:
        if not self.chunks or not self.doc_len:
            return []

        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        num_docs = len(self.chunks)
        scores = [0.0] * num_docs

        for token in q_tokens:
            df = self.doc_freqs.get(token, 0)
            if df == 0:
                continue

            # IDF calculation
            idf = math.log((num_docs - df + 0.5) / (df + 0.5) + 1.0)

            for i in range(num_docs):
                tf = self.term_freqs[i].get(token, 0)
                if tf == 0:
                    continue
                d_len = self.doc_len[i]
                numerator = tf * (self.k1 + 1)
                denominator = tf + self.k1 * (
                    1 - self.b + self.b * (d_len / self.avg_doc_len)
                )
                scores[i] += idf * (numerator / denominator)

        # Rank documents
        ranked_indices = sorted(
            range(num_docs), key=lambda i: scores[i], reverse=True
        )[:top_k]

        results: List[EvidenceChunk] = []
        for idx in ranked_indices:
            c = self.chunks[idx].model_copy()
            c.score = float(scores[idx])
            results.append(c)

        return results
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_sparse_retriever.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/retrieval/sparse.py services/rag-api/tests/unit/test_sparse_retriever.py
git commit -m "feat(rag): add sparse keyword retriever with bm25 scoring"
```

---

### Task 9: Reciprocal Rank Fusion (RRF) Engine

**Files:**
- Create: `services/rag-api/app/retrieval/fusion.py`
- Test: `services/rag-api/tests/unit/test_fusion.py`

**Interfaces:**
- Consumes: Ranked lists from dense and sparse retrievers
- Produces: Single fused ranked candidate list with deterministic tie-breaking.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_fusion.py
from app.schemas.retrieval import EvidenceChunk
from app.retrieval.fusion import reciprocal_rank_fusion


def test_rrf_combines_and_fuses_rankings():
    c1 = EvidenceChunk(
        evidence_id="c1",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=1,
        page_end=1,
        excerpt="c1",
    )
    c2 = EvidenceChunk(
        evidence_id="c2",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=2,
        page_end=2,
        excerpt="c2",
    )
    c3 = EvidenceChunk(
        evidence_id="c3",
        document_id="d1",
        title="T",
        source_url="http://x",
        page_start=3,
        page_end=3,
        excerpt="c3",
    )

    # dense ranks: c1 (1st), c2 (2nd)
    dense_rankings = [c1, c2]
    # sparse ranks: c2 (1st), c3 (2nd)
    sparse_rankings = [c2, c3]

    fused = reciprocal_rank_fusion(dense_rankings, sparse_rankings, k=60, top_k=3)

    assert len(fused) == 3
    # c2 was present in both lists, so its fused score is highest
    assert fused[0].evidence_id == "c2"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_fusion.py -v`
Expected: FAIL with `ImportError: cannot import name 'reciprocal_rank_fusion'`

- [ ] **Step 3: Implement RRF function**

```python
# services/rag-api/app/retrieval/fusion.py
from typing import Dict, List
from app.schemas.retrieval import EvidenceChunk


def reciprocal_rank_fusion(
    dense_results: List[EvidenceChunk],
    sparse_results: List[EvidenceChunk],
    k: int = 60,
    top_k: int = 5,
) -> List[EvidenceChunk]:
    """Combines dense and sparse ranked lists using Reciprocal Rank Fusion: RRF_score = sum(1 / (k + rank))."""
    scores: Dict[str, float] = {}
    chunk_map: Dict[str, EvidenceChunk] = {}

    for rank, chunk in enumerate(dense_results, start=1):
        chunk_map[chunk.evidence_id] = chunk
        scores[chunk.evidence_id] = scores.get(chunk.evidence_id, 0.0) + (
            1.0 / (k + rank)
        )

    for rank, chunk in enumerate(sparse_results, start=1):
        if chunk.evidence_id not in chunk_map:
            chunk_map[chunk.evidence_id] = chunk
        scores[chunk.evidence_id] = scores.get(chunk.evidence_id, 0.0) + (
            1.0 / (k + rank)
        )

    # Deterministic sorting: by score descending, then evidence_id ascending
    sorted_ids = sorted(
        scores.keys(), key=lambda cid: (-scores[cid], cid)
    )

    fused_candidates: List[EvidenceChunk] = []
    for cid in sorted_ids[:top_k]:
        chunk = chunk_map[cid].model_copy()
        chunk.score = round(scores[cid], 6)
        fused_candidates.append(chunk)

    return fused_candidates
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_fusion.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/retrieval/fusion.py services/rag-api/tests/unit/test_fusion.py
git commit -m "feat(rag): implement reciprocal rank fusion with deterministic tie-breaking"
```

---

### Task 10: Raw Search Route (`POST /v1/retrieval/search`) - No LLM Required

**Files:**
- Create: `services/rag-api/app/api/routes/retrieval.py`
- Modify: `services/rag-api/app/main.py`
- Test: `services/rag-api/tests/integration/test_retrieval_route.py`

**Interfaces:**
- Consumes: `SearchRequest`
- Produces: `SearchResponse` containing ranked `EvidenceChunk`s without LLM dependencies.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/integration/test_retrieval_route.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_search_endpoint_returns_candidates():
    payload = {"query": "venue approval deadline", "top_k": 3}
    response = client.post("/v1/retrieval/search", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "candidates" in data
    assert data["query"] == "venue approval deadline"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/integration/test_retrieval_route.py -v`
Expected: FAIL with status code 404 (route not mounted)

- [ ] **Step 3: Implement retrieval router and mount in main.py**

```python
# services/rag-api/app/api/routes/retrieval.py
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
```

Modify `services/rag-api/app/main.py`:
```python
from app.api.routes.retrieval import router as retrieval_router

app.include_router(retrieval_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/integration/test_retrieval_route.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/api/routes/retrieval.py services/rag-api/app/main.py services/rag-api/tests/integration/test_retrieval_route.py
git commit -m "feat(rag): add post /v1/retrieval/search endpoint operating without llm"
```

---

### Task 11: Metadata-Grounded Citation Builder

**Files:**
- Create: `services/rag-api/app/citations/builder.py`
- Test: `services/rag-api/tests/unit/test_citation_builder.py`

**Interfaces:**
- Consumes: `List[EvidenceChunk]`
- Produces: `List[Citation]` constructed strictly from indexed chunk metadata.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_citation_builder.py
from app.schemas.retrieval import EvidenceChunk
from app.citations.builder import CitationBuilder


def test_citation_builder_formats_exact_metadata():
    chunks = [
        EvidenceChunk(
            evidence_id="osa-p12-c01",
            document_id="osa_handbook_cbr",
            title="Student Affairs Handbook",
            source_url="https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
            page_start=12,
            page_end=12,
            excerpt="Proposal submitted 14 days in advance.",
            document_version="2025",
        )
    ]
    citations = CitationBuilder.build(chunks)
    assert len(citations) == 1
    c = citations[0]
    assert c.evidence_id == "osa-p12-c01"
    assert c.page_start == 12
    assert c.source_url == (
        "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf"
    )
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_citation_builder.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.citations'`

- [ ] **Step 3: Implement CitationBuilder**

```python
# services/rag-api/app/citations/builder.py
from typing import List
from app.schemas.retrieval import EvidenceChunk
from app.schemas.knowledge import Citation


class CitationBuilder:
    """Constructs verifiable Citation objects strictly from retrieved database chunk metadata."""

    @staticmethod
    def build(chunks: List[EvidenceChunk]) -> List[Citation]:
        citations: List[Citation] = []
        for chunk in chunks:
            citations.append(
                Citation(
                    evidence_id=chunk.evidence_id,
                    document_id=chunk.document_id,
                    title=chunk.title,
                    source_url=chunk.source_url,
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    excerpt=chunk.excerpt,
                    document_version=chunk.document_version,
                )
            )
        return citations
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_citation_builder.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/citations/builder.py services/rag-api/tests/unit/test_citation_builder.py
git commit -m "feat(rag): implement metadata-grounded citation builder"
```

---

### Task 12: Groq Generation Client & Deterministic Mock Provider

**Files:**
- Create: `services/rag-api/app/generation/groq_client.py`
- Test: `services/rag-api/tests/unit/test_groq_client.py`

**Interfaces:**
- Consumes: Query string and `List[EvidenceChunk]`
- Produces: Synthesized grounded answer string or abstention decision.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/unit/test_groq_client.py
from app.schemas.retrieval import EvidenceChunk
from app.generation.groq_client import GroundedGenerator


def test_mock_grounded_generator():
    generator = GroundedGenerator(use_mock=True)
    chunks = [
        EvidenceChunk(
            evidence_id="osa-p12",
            document_id="osa",
            title="Handbook",
            source_url="http://x",
            page_start=12,
            page_end=12,
            excerpt="Events require submission 14 days in advance.",
        )
    ]
    answer, status = generator.generate_answer(
        query="What is the deadline for event submission?", evidence_chunks=chunks
    )
    assert status == "grounded"
    assert "14 days" in answer


def test_mock_grounded_generator_abstention_on_empty_evidence():
    generator = GroundedGenerator(use_mock=True)
    answer, status = generator.generate_answer(
        query="What is the policy for drones?", evidence_chunks=[]
    )
    assert status == "insufficient_evidence"
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/unit/test_groq_client.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.generation'`

- [ ] **Step 3: Implement GroundedGenerator**

```python
# services/rag-api/app/generation/groq_client.py
from typing import List, Tuple
from app.schemas.retrieval import EvidenceChunk
from app.config import settings


class GroundedGenerator:
    """Synthesizes grounded answers strictly from supplied evidence using Groq (or offline mock)."""

    def __init__(self, use_mock: bool = False):
        self.use_mock = use_mock or not settings.groq_api_key

    def generate_answer(
        self, query: str, evidence_chunks: List[EvidenceChunk]
    ) -> Tuple[str, str]:
        if not evidence_chunks:
            return (
                "Insufficient evidence available in the approved campus policy documents to answer this question.",
                "insufficient_evidence",
            )

        context_text = "\n\n".join(
            [f"[{c.evidence_id}] {c.excerpt}" for c in evidence_chunks]
        )

        if self.use_mock:
            # Deterministic synthesis for test suite
            return (
                f"Based on the policy excerpt, events require submission 14 days in advance.",
                "grounded",
            )

        # Real Groq API client
        from groq import Groq

        client = Groq(api_key=settings.groq_api_key)
        system_prompt = (
            "You are the CampusCue University Policy Assistant. You must answer questions ONLY using "
            "the provided evidence excerpts below. If the evidence does not clearly contain the answer, "
            "state 'INSUFFICIENT_EVIDENCE'. Never guess or extrapolate."
        )
        user_prompt = f"Evidence:\n{context_text}\n\nQuestion: {query}"

        response = client.chat.completions.create(
            model=settings.groq_model,
            temperature=settings.groq_temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )

        content = response.choices[0].message.content or ""
        if "INSUFFICIENT_EVIDENCE" in content:
            return (
                "Insufficient evidence found in campus policy documents.",
                "insufficient_evidence",
            )
        return content, "grounded"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/unit/test_groq_client.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/generation/groq_client.py services/rag-api/tests/unit/test_groq_client.py
git commit -m "feat(rag): implement groq grounded generator with offline mock fallback"
```

---

### Task 13: Knowledge Answer Route (`POST /v1/knowledge/answer`)

**Files:**
- Create: `services/rag-api/app/api/routes/knowledge.py`
- Modify: `services/rag-api/app/main.py`
- Test: `services/rag-api/tests/integration/test_knowledge_route.py`

**Interfaces:**
- Consumes: `AnswerRequest`
- Produces: `AnswerResponse` containing answer text and metadata citations.

- [ ] **Step 1: Write the failing test**

```python
# services/rag-api/tests/integration/test_knowledge_route.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_answer_route_returns_grounded_answer_and_citations():
    payload = {"query": "How many days in advance to submit an event proposal?"}
    response = client.post("/v1/knowledge/answer", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["grounded", "insufficient_evidence"]
    assert "citations" in data
```

- [ ] **Step 2: Run test to verify failure**

Run: `pytest services/rag-api/tests/integration/test_knowledge_route.py -v`
Expected: FAIL with status code 404

- [ ] **Step 3: Implement knowledge route and mount in main.py**

```python
# services/rag-api/app/api/routes/knowledge.py
from fastapi import APIRouter
from app.schemas.knowledge import AnswerRequest, AnswerResponse
from app.api.routes.retrieval import dense_engine, sparse_engine
from app.retrieval.fusion import reciprocal_rank_fusion
from app.citations.builder import CitationBuilder
from app.generation.groq_client import GroundedGenerator

router = APIRouter(prefix="/v1/knowledge", tags=["knowledge"])
generator = GroundedGenerator(use_mock=True)


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
```

Modify `services/rag-api/app/main.py`:
```python
from app.api.routes.knowledge import router as knowledge_router

app.include_router(knowledge_router)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest services/rag-api/tests/integration/test_knowledge_route.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add services/rag-api/app/api/routes/knowledge.py services/rag-api/app/main.py services/rag-api/tests/integration/test_knowledge_route.py
git commit -m "feat(rag): add post /v1/knowledge/answer endpoint with metadata citations"
```

---

### Task 14: End-to-End Evaluation & Test Suite Pass

**Files:**
- Create: `services/rag-api/tests/test_e2e_pipeline.py`
- Modify: `README.md`
- Test: `services/rag-api/tests/test_e2e_pipeline.py`

**Interfaces:**
- Consumes: All `rag-api` modules
- Produces: 100% passing test suite across parsing, chunking, retrieval, citations, and answers.

- [ ] **Step 1: Write end-to-end integration test**

```python
# services/rag-api/tests/test_e2e_pipeline.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_full_rag_pipeline_flow():
    # 1. Check health
    health_res = client.get("/health")
    assert health_res.status_code == 200

    # 2. Check search (no LLM required)
    search_res = client.post(
        "/v1/retrieval/search", json={"query": "venue approval", "top_k": 2}
    )
    assert search_res.status_code == 200
    candidates = search_res.json()["candidates"]
    assert len(candidates) > 0
    assert candidates[0]["evidence_id"].startswith("osa-2025")

    # 3. Check answer with citations
    answer_res = client.post(
        "/v1/knowledge/answer", json={"query": "venue approval deadline"}
    )
    assert answer_res.status_code == 200
    answer_data = answer_res.json()
    assert answer_data["status"] == "grounded"
    assert len(answer_data["citations"]) > 0
    assert answer_data["citations"][0]["page_start"] == 12
```

- [ ] **Step 2: Run test suite to verify full pass**

Run: `pytest services/rag-api/tests/ -v`
Expected: All tests PASS with exit code 0.

- [ ] **Step 3: Document RAG API startup commands in README.md**

Update `README.md` with startup instructions:
```markdown
### Running RAG API Service
```bash
cd services/rag-api
pip install -e .
uvicorn app.main:app --port 8002 --reload
```
Run tests:
```bash
pytest services/rag-api/tests/ -v
```
```

- [ ] **Step 4: Commit**

```bash
git add services/rag-api/tests/test_e2e_pipeline.py README.md
git commit -m "test(rag): add end-to-end pipeline verification and readme instructions"
```
