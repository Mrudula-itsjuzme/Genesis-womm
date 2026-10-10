"""Core's HTTP client for the RAG service's proposal ingestion (Implementation Plan 07).

The RAG service publishes no OpenAPI file yet, so the routes are pinned here as they exist in
services/rag-api (app/api/routes/ingest_proposal.py). When it publishes a contract, replace the
literals below with a check against it.
"""

import json
from collections.abc import Iterator
from uuid import uuid4

import httpx
import pytest
import respx
import structlog

from app.clients.rag_ingest import HttpRagIngest

BASE = "http://rag.test"
PROPOSAL = uuid4()
EVENT = uuid4()
PRESIGNED = "https://minio.local/proposals/p1.pdf?X-Amz-Signature=very-secret"
PAYLOAD = {"proposal_id": str(PROPOSAL), "event_id": str(EVENT), "presigned_url": PRESIGNED}
INGEST = f"{BASE}/v1/ingest/proposal"
DELETE = f"{BASE}/v1/ingest/proposal/{PROPOSAL}"


@pytest.fixture
def rag() -> Iterator[HttpRagIngest]:
    with httpx.Client(base_url=BASE, headers={"X-Internal-Key": "k" * 40}) as client:
        yield HttpRagIngest(client)


# ---- ingest ----------------------------------------------------------------------------


@respx.mock
def test_ingest_posts_the_payload_to_the_proposal_route(rag: HttpRagIngest) -> None:
    route = respx.post(INGEST).respond(200, json={"status": "success"})

    assert rag.ingest(PAYLOAD) is True

    sent = route.calls.last.request
    assert json.loads(sent.content) == PAYLOAD
    assert sent.headers["x-internal-key"] == "k" * 40


@pytest.mark.parametrize("status", [201, 400, 404, 422, 500, 502, 503])
@respx.mock
def test_ingest_succeeds_only_on_a_plain_200(rag: HttpRagIngest, status: int) -> None:
    respx.post(INGEST).respond(status, json={})

    assert rag.ingest(PAYLOAD) is False


@pytest.mark.parametrize(
    "error",
    [httpx.ConnectError("refused"), httpx.ReadTimeout("silent"), httpx.RemoteProtocolError("x")],
    ids=lambda e: type(e).__name__,
)
@respx.mock
def test_ingest_never_raises_on_a_network_failure(rag: HttpRagIngest, error: Exception) -> None:
    respx.post(INGEST).mock(side_effect=error)

    assert rag.ingest(PAYLOAD) is False


# ---- delete ----------------------------------------------------------------------------


@respx.mock
def test_delete_names_the_proposal_in_the_path_and_the_event_in_the_body(
    rag: HttpRagIngest,
) -> None:
    route = respx.delete(DELETE).respond(200, json={"status": "success"})

    assert rag.delete(PROPOSAL, EVENT) is True

    assert json.loads(route.calls.last.request.content) == {"event_id": str(EVENT)}


@respx.mock
def test_delete_treats_not_found_as_already_gone(rag: HttpRagIngest) -> None:
    respx.delete(DELETE).respond(404, json={})

    assert rag.delete(PROPOSAL, EVENT) is True


@pytest.mark.parametrize("status", [400, 401, 422, 500, 503])
@respx.mock
def test_delete_reports_any_other_answer_as_not_done(rag: HttpRagIngest, status: int) -> None:
    respx.delete(DELETE).respond(status, json={})

    assert rag.delete(PROPOSAL, EVENT) is False


@respx.mock
def test_delete_never_raises_on_a_network_failure(rag: HttpRagIngest) -> None:
    respx.delete(DELETE).mock(side_effect=httpx.ConnectTimeout("slow"))

    assert rag.delete(PROPOSAL, EVENT) is False


# ---- what is logged --------------------------------------------------------------------


@respx.mock
def test_a_failure_is_logged_without_the_presigned_url_or_the_reply(
    rag: HttpRagIngest,
) -> None:
    respx.post(INGEST).respond(500, text="internal secret-reply")

    with structlog.testing.capture_logs() as logs:
        rag.ingest(PAYLOAD)

    assert logs, "a failed ingest should leave a trace"
    rendered = json.dumps(logs, default=str)
    assert "very-secret" not in rendered
    assert "secret-reply" not in rendered
    assert str(PROPOSAL) in rendered
