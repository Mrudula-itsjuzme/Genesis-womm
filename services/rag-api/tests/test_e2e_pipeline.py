import io

from app.api.deps import get_dense_retriever, get_sparse_retriever
from app.chunking.structure import StructureChunker
from app.main import app
from app.parsing.pdf import PDFParser
from fastapi.testclient import TestClient
from pypdf import PdfWriter


def test_full_rag_pipeline_flow():
    # 1. Parse a dynamic multi-page document
    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)
    stream = io.BytesIO()
    writer.write(stream)

    parser = PDFParser()
    pages = parser.parse_bytes(stream.getvalue())
    assert len(pages) == 1

    # 2. Chunk page content
    chunker = StructureChunker(target_chunk_size=180, chunk_overlap=30)
    pages[0].text = (
        "Chapter 3: Event Approvals\nAll student club events must be approved by OSA 14 days in advance."
    )
    chunks = chunker.chunk_pages(
        pages=pages,
        document_id="osa_test_handbook",
        title="Student Affairs Handbook",
        source_url="https://example.com/handbook.pdf",
    )
    assert len(chunks) >= 1

    # 3. Index dynamically into retrievers
    dense = get_dense_retriever()
    sparse = get_sparse_retriever()
    dense.index(chunks)
    sparse.index(chunks)

    # 4. Query via HTTP client
    client = TestClient(app)
    search_resp = client.post(
        "/v1/retrieval/search", json={"query": "event approval deadline", "top_k": 2}
    )
    assert search_resp.status_code == 200
    search_data = search_resp.json()
    assert len(search_data["candidates"]) >= 1
    assert search_data["candidates"][0]["document_id"] == "osa_test_handbook"

    # 5. Query answer route
    ans_resp = client.post(
        "/v1/knowledge/answer", json={"query": "event approval deadline", "top_k": 2}
    )
    assert ans_resp.status_code == 200
    ans_data = ans_resp.json()
    assert ans_data["status"] in ["grounded", "insufficient_evidence"]
    if ans_data["status"] == "grounded":
        assert len(ans_data["citations"]) >= 1
        assert ans_data["citations"][0]["document_id"] == "osa_test_handbook"
