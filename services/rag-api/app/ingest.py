import json
import logging
from pathlib import Path

import bs4
import httpx
import numpy as np
from sentence_transformers import SentenceTransformer

from app.chunking.structure import StructureChunker
from app.parsing.pdf import ParsedPage, PDFParser
from app.schemas.retrieval import EvidenceChunk

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

CHUNKS_FILE = DATA_DIR / "corpus_chunks.jsonl"
EMBEDDINGS_FILE = DATA_DIR / "dense_embeddings.npy"

# Authoritative RAG policy sources approved in SOURCE_REGISTRY.md
APPROVED_SOURCES: list[dict[str, str]] = [
    {
        "source_id": "osa_handbook_cbr",
        "title": "OSA Student Affairs Handbook",
        "url": "https://webfiles.amrita.edu/2025/05/student-affairs-handbook-cbr.pdf",
        "format": "pdf",
    },
    {
        "source_id": "student_affairs_welfare",
        "title": "Student Affairs and Welfare",
        "url": "https://intranet.cb.amrita.edu/students-affairs-welfare",
        "format": "html",
    },
    {
        "source_id": "campus_infrastructure",
        "title": "Coimbatore Campus Infrastructure Directory",
        "url": "https://www.amrita.edu/campus/coimbatore/infrastructure/",
        "format": "html",
    },
]


def fetch_pdf_and_chunk(
    source_id: str, title: str, url: str, client: httpx.Client | None = None
) -> list[EvidenceChunk]:
    """Fetch PDF, preserve page numbers, and chunk with StructureChunker."""
    print(f"Fetching PDF: {title} ({url})")
    http_client = client or httpx.Client(timeout=20.0, follow_redirects=True)
    try:
        resp = http_client.get(url)
        resp.raise_for_status()
        pdf_bytes = resp.content
    finally:
        if client is None:
            http_client.close()

    parser = PDFParser()
    pages = parser.parse_bytes(pdf_bytes)
    print(f"  Parsed {len(pages)} pages from PDF.")

    chunker = StructureChunker(target_chunk_size=180, chunk_overlap=30)
    chunks = chunker.chunk_pages(pages, document_id=source_id, title=title, source_url=url)
    print(f"  Generated {len(chunks)} chunks for {source_id}.")
    return chunks


def fetch_html_and_chunk(
    source_id: str, title: str, url: str, client: httpx.Client | None = None
) -> list[EvidenceChunk]:
    """Fetch HTML page, extract clean text, and chunk with StructureChunker."""
    print(f"Fetching HTML: {title} ({url})")
    http_client = client or httpx.Client(timeout=20.0, follow_redirects=True)
    try:
        resp = http_client.get(url)
        resp.raise_for_status()
        html_text = resp.text
    finally:
        if client is None:
            http_client.close()

    soup = bs4.BeautifulSoup(html_text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "noscript"]):
        tag.decompose()

    clean_text = soup.get_text(separator="\n", strip=True)
    page = ParsedPage(page_number=1, text=clean_text, section_breadcrumb=title)

    chunker = StructureChunker(target_chunk_size=180, chunk_overlap=30)
    chunks = chunker.chunk_pages([page], document_id=source_id, title=title, source_url=url)
    print(f"  Generated {len(chunks)} chunks for {source_id}.")
    return chunks


def build_and_save_corpus(
    sources: list[dict[str, str]] | None = None,
    model_name: str = "all-MiniLM-L6-v2",
) -> tuple[list[EvidenceChunk], np.ndarray]:
    """Scrapes approved sources, creates calibrated chunks, computes dense embeddings, and saves to disk."""
    target_sources = sources or APPROVED_SOURCES
    all_chunks: list[EvidenceChunk] = []

    with httpx.Client(timeout=25.0, follow_redirects=True) as client:
        for src in target_sources:
            try:
                if src["format"] == "pdf":
                    chunks = fetch_pdf_and_chunk(src["source_id"], src["title"], src["url"], client)
                else:
                    chunks = fetch_html_and_chunk(src["source_id"], src["title"], src["url"], client)
                all_chunks.extend(chunks)
            except Exception as exc:  # noqa: BLE001
                print(f"  Warning: failed to ingest {src['source_id']}: {exc}")

    print(f"\nTotal corpus chunks generated: {len(all_chunks)}")
    if not all_chunks:
        return [], np.empty((0, 384), dtype=np.float32)

    # Compute dense embeddings using local sentence-transformers
    print(f"Computing local dense embeddings with {model_name}...")
    model = SentenceTransformer(model_name)
    texts = [f"{c.section}: {c.excerpt}" if c.section else c.excerpt for c in all_chunks]
    embeddings = np.array(model.encode(texts, normalize_embeddings=True, show_progress_bar=True))
    print(f"Dense embeddings matrix computed: {embeddings.shape}")

    # Persist chunks to JSONL
    with open(CHUNKS_FILE, "w", encoding="utf-8") as f:
        f.writelines(json.dumps(c.model_dump(), ensure_ascii=False) + "\n" for c in all_chunks)
    print(f"Saved chunks to {CHUNKS_FILE}")

    # Persist embeddings to NPY
    np.save(EMBEDDINGS_FILE, embeddings)
    print(f"Saved embeddings to {EMBEDDINGS_FILE}")

    # Optional PostgreSQL database sync if available
    _sync_to_database_if_available(all_chunks, embeddings)

    return all_chunks, embeddings


def load_persisted_corpus() -> tuple[list[EvidenceChunk], np.ndarray | None]:
    """Load previously ingested chunks and precomputed embeddings from disk if available."""
    if not CHUNKS_FILE.exists():
        return [], None

    chunks: list[EvidenceChunk] = []
    with open(CHUNKS_FILE, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                chunks.append(EvidenceChunk(**json.loads(line)))

    embeddings: np.ndarray | None = None
    if EMBEDDINGS_FILE.exists():
        embeddings = np.load(EMBEDDINGS_FILE)

    return chunks, embeddings


def _sync_to_database_if_available(chunks: list[EvidenceChunk], embeddings: np.ndarray) -> None:
    """Sync to DocumentChunk table in PostgreSQL if database engine is reachable."""
    try:
        from app.database import SessionLocal
        from app.models import DocumentChunk

        db = SessionLocal()
        try:
            # Check connection
            db.execute(DocumentChunk.__table__.select().limit(1))
            print("Syncing chunks to PostgreSQL...")
            for idx, c in enumerate(chunks):
                record = DocumentChunk(
                    id=None,
                    source_url=c.source_url,
                    content=c.excerpt,
                    embedding=embeddings[idx].tolist(),
                )
                db.add(record)
            db.commit()
            print("Successfully synced to PostgreSQL document_chunks table.")
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            print(f"PostgreSQL sync skipped (database offline or unmigrated): {exc}")
        finally:
            db.close()
    except Exception as exc:  # noqa: BLE001
        print(f"Database module not available or skipped: {exc}")


if __name__ == "__main__":
    build_and_save_corpus()
