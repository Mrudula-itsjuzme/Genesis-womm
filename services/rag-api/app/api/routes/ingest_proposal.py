import logging
from typing import Annotated

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_chroma_store, get_dense_retriever
from app.chunking.structure import StructureChunker
from app.parsing.pdf import PDFParser
from app.retrieval.chroma import ChromaStore
from app.retrieval.dense import DenseRetriever
from app.schemas.proposals import (
    ProposalDeletePayload,
    ProposalDeleteResponse,
    ProposalIngestPayload,
    ProposalIngestResponse,
)
from app.schemas.retrieval import EvidenceChunk

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/v1/ingest",
    tags=["proposal-ingest"],
)


@router.post(
    "/proposal",
    response_model=ProposalIngestResponse,
    status_code=status.HTTP_200_OK,
    summary="Ingest an approved event proposal PDF into proposals collection",
    description="Downloads PDF via presigned URL, parses, chunks into 180-word bounds, embeds, and upserts into ChromaDB.",
)
def ingest_proposal(
    payload: ProposalIngestPayload,
    request: Request,
    chroma_store: Annotated[ChromaStore, Depends(get_chroma_store)],
    dense_retriever: Annotated[DenseRetriever, Depends(get_dense_retriever)],
) -> ProposalIngestResponse:
    # Private event proposals can contain student and faculty personal data.
    # Do not accept unauthenticated presigned URLs or index private files until a
    # dedicated authenticated service-to-service route and ACLs exist.
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Private proposal ingestion is disabled pending authenticated access controls.",
    )

    request_id = getattr(request.state, "request_id", None)
    logger.info(
        "Ingesting proposal %s for event %s (rev %s) [req: %s]",
        payload.proposal_id,
        payload.event_id,
        payload.revision,
        request_id,
    )

    # 1. Download PDF from presigned URL
    try:
        resp = httpx.get(payload.presigned_url, timeout=30.0)
        resp.raise_for_status()
        pdf_bytes = resp.content
    except Exception as exc:
        logger.error("Failed to download proposal PDF from presigned URL: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Unable to download proposal PDF from presigned URL: {exc}",
        ) from exc

    if not pdf_bytes or not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Downloaded file is empty or not a valid PDF document",
        )

    # 2. Parse PDF pages
    parser = PDFParser()
    try:
        pages = parser.parse_bytes(pdf_bytes)
    except Exception as exc:
        logger.error("Failed to parse proposal PDF: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Failed to parse proposal PDF: {exc}",
        ) from exc

    # 3. Structure-aware chunking (180 words, 30 overlap)
    chunker = StructureChunker(target_chunk_size=180, chunk_overlap=30)
    doc_url = f"proposals/{payload.club_id}/{payload.event_id}/{payload.proposal_id}/v{payload.revision}.pdf"
    evidence_chunks = chunker.chunk_pages(
        pages=pages,
        document_id=f"proposal_{payload.proposal_id}",
        title=payload.title,
        source_url=doc_url,
    )

    if not evidence_chunks:
        # Fallback summary chunk if PDF has no extractable text stream
        evidence_chunks = [
            EvidenceChunk(
                evidence_id=f"proposal-{payload.proposal_id}-v{payload.revision}-p1-c01",
                document_id=f"proposal_{payload.proposal_id}",
                title=payload.title,
                source_url=doc_url,
                excerpt=f"Proposal Title: {payload.title}. Organized for event {payload.event_id}.",
                page_start=1,
                page_end=1,
                section="Proposal Overview",
            )
        ]

    # 4. Construct extra metadatas for collection scoping
    extra_metadatas = [
        {
            "event_id": payload.event_id,
            "club_id": payload.club_id,
            "proposal_id": payload.proposal_id,
            "revision": payload.revision,
        }
        for _ in evidence_chunks
    ]


    # 5. Generate dense embeddings
    texts = [c.excerpt for c in evidence_chunks]
    embeddings = dense_retriever.encode(texts)

    # 6. Upsert into isolated 'proposals' collection
    chroma_store.upsert_chunks(
        chunks=evidence_chunks,
        embeddings=embeddings,
        collection_name="proposals",
        extra_metadatas=extra_metadatas,
    )

    logger.info(
        "Successfully indexed %d chunks for proposal %s into proposals collection",
        len(evidence_chunks),
        payload.proposal_id,
    )

    return ProposalIngestResponse(
        proposal_id=payload.proposal_id,
        event_id=payload.event_id,
        chunks_ingested=len(evidence_chunks),
        collection="proposals",
        status="success",
    )


@router.delete(
    "/proposal/{proposal_id}",
    response_model=ProposalDeleteResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete all chunks belonging to an event proposal after lifecycle conclusion",
)
def delete_proposal(
    proposal_id: str,
    payload: ProposalDeletePayload,
    chroma_store: Annotated[ChromaStore, Depends(get_chroma_store)],
) -> ProposalDeleteResponse:
    logger.info(
        "Deleting proposal chunks for proposal %s, event %s",
        proposal_id,
        payload.event_id,
    )

    deleted_count = chroma_store.delete_where(
        where={"event_id": payload.event_id},
        collection_name="proposals",
    )

    return ProposalDeleteResponse(
        proposal_id=proposal_id,
        event_id=payload.event_id,
        chunks_deleted=deleted_count,
        status="success" if deleted_count > 0 else "not_found",
    )
