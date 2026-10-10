"""Core's HTTP client for the RAG service's proposal ingestion (Implementation Plan 07).

Proposal ingestion is best effort: an approved proposal stays approved even if RAG is down, and
the lifecycle retries later. So nothing here raises; every failure is a ``False``. What is
logged is the proposal id and the outcome, never the presigned URL or anything RAG said.
"""

from collections.abc import Mapping
from typing import Any
from uuid import UUID

import httpx
import structlog

log = structlog.get_logger(__name__)

# Routes in services/rag-api (app/api/routes/ingest_proposal.py). A unit test pins them.
INGEST_PATH = "/v1/ingest/proposal"
DELETE_PATH = "/v1/ingest/proposal/{proposal_id}"


class HttpRagIngest:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def ingest(self, payload: Mapping[str, Any]) -> bool:
        proposal_id = str(payload.get("proposal_id"))
        try:
            response = self._client.post(INGEST_PATH, json=dict(payload))
        except httpx.RequestError as error:
            log.warning(
                "rag_ingest_unreachable", proposal_id=proposal_id, kind=type(error).__name__
            )
            return False
        if response.status_code != 200:
            log.warning("rag_ingest_refused", proposal_id=proposal_id, status=response.status_code)
            return False
        return True

    def delete(self, proposal_id: UUID, event_id: UUID) -> bool:
        try:
            response = self._client.request(
                "DELETE",
                DELETE_PATH.format(proposal_id=proposal_id),
                json={"event_id": str(event_id)},
            )
        except httpx.RequestError as error:
            log.warning(
                "rag_delete_unreachable", proposal_id=str(proposal_id), kind=type(error).__name__
            )
            return False
        if response.status_code not in (200, 404):
            log.warning(
                "rag_delete_refused", proposal_id=str(proposal_id), status=response.status_code
            )
            return False
        return True
