"""The proposal endpoints: sessions, real identities and the standard error envelope.

Paths and response shapes are the ones the proposals feature shipped with; what changed is that
every route needs a signed-in person, authorization decides who may do what, and a failing object
store or RAG service neither leaks detail nor undoes a review.
"""

import asyncio
import io
from collections.abc import Callable
from dataclasses import dataclass
from datetime import timedelta
from types import SimpleNamespace
from typing import Any, cast
from unittest.mock import AsyncMock, Mock
from uuid import UUID, uuid4

import pytest
from fastapi import Request
from fastapi.testclient import TestClient

from app.api.routes.proposals import upload_proposal
from app.container import Container
from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, ProposalStatus, Role
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.main import create_app
from app.schemas.proposals import ProposalDownloadUrlOut, ProposalOut, ProposalUploadOut
from app.services.errors import InvalidRequestError
from app.services.ports import MembershipIdentity, UserIdentity
from app.services.proposal_lifecycle import ProposalLifecycleManager
from app.services.proposals import MAX_PROPOSAL_BYTES, ProposalService
from app.services.readiness import ReadinessService
from app.services.schedule_write import ScheduleWriteService
from app.services.sessions import SessionService
from tests.fakes import FakeReadinessProbe, InMemoryDatabase, SequentialIds, make_settings
from tests.unit.test_proposals import FakeRag, FakeStorage
from tests.unit.test_schedule_write import (
    CAMPUS,
    CLUB_A,
    CLUB_B,
    HALL,
    NOW,
    ORGANIZER,
    OTHER_CLUB,
    World,
    draft,
)

PDF = b"%PDF-1.7 a proposal"
POLICY = Policy(campus_gap=timedelta(minutes=120))


def identity(actor: Actor, name: str) -> UserIdentity:
    return UserIdentity(
        id=actor.user_id,
        email=f"{name}@example.invalid",
        display_name=name,
        campus_admin=actor.campus_admin,
        memberships=tuple(
            MembershipIdentity(club_id=club, club_name=str(club), role=role)
            for club, role in actor.memberships.items()
        ),
        is_synthetic=True,
    )


class FakeSessions:
    def __init__(self) -> None:
        self._by_token = {
            "organizer": identity(ORGANIZER, "organizer"),
            "other": identity(OTHER_CLUB, "other"),
            "campus": identity(CAMPUS, "campus"),
            "faculty": identity(Actor(user_id=UUID(int=998), memberships={CLUB_A: Role.FACULTY_ADVISOR}), "faculty"),
        }

    def resolve_access_token(self, token: str) -> UserIdentity | None:
        return self._by_token.get(token)


def as_person(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@dataclass
class Rig:
    client: TestClient
    world: World
    storage: FakeStorage
    rag: FakeRag
    event: UUID

    @property
    def db(self) -> InMemoryDatabase:
        return self.world.db

    def upload(
        self,
        actor_name: str = "organizer",
        *,
        club: UUID = CLUB_A,
        event: UUID | None = None,
        content: bytes = PDF,
        title: str | None = "Robotics Demo Day proposal",
        filename: str = "proposal.pdf",
    ) -> Any:
        data = {} if title is None else {"title": title}
        return self.client.post(
            f"/api/v1/clubs/{club}/events/{event or self.event}/proposals",
            files={"file": (filename, io.BytesIO(content), "application/pdf")},
            data=data,
            headers=as_person(actor_name),
        )

    def submitted(self) -> UUID:
        response = self.upload()
        assert response.status_code == 201, response.text
        return UUID(response.json()["id"])


@pytest.fixture
def rig() -> Rig:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {HALL: AvailabilityState.UNKNOWN}
    ids, clock = SequentialIds(), FixedClock(NOW)
    world = World(db, ScheduleWriteService(db.uow, clock=clock, ids=ids, policy=POLICY), ids)
    event = draft(world).event.id
    storage, rag = FakeStorage(), FakeRag()
    service = ProposalService(
        db.uow,
        storage=storage,
        manager=ProposalLifecycleManager(storage=storage, rag=rag, clock=clock),
        clock=clock,
        ids=ids,
    )
    container = Container(
        readiness=ReadinessService(FakeReadinessProbe(), "0001"),
        sessions=cast(SessionService, FakeSessions()),
        proposals=service,
    )
    client = TestClient(create_app(make_settings(), container), raise_server_exceptions=False)
    return Rig(client, world, storage, rag, event)


# ---- credentials -----------------------------------------------------------------------


def test_every_route_needs_a_signed_in_person(rig: Rig) -> None:
    pid = rig.submitted()
    calls: list[Callable[[dict[str, str]], Any]] = [
        lambda h: rig.client.post(
            f"/api/v1/clubs/{CLUB_A}/events/{rig.event}/proposals",
            files={"file": ("p.pdf", io.BytesIO(PDF), "application/pdf")},
            headers=h,
        ),
        lambda h: rig.client.get(f"/api/v1/proposals/{pid}", headers=h),
        lambda h: rig.client.get(f"/api/v1/proposals/{pid}/download-url", headers=h),
        lambda h: rig.client.patch(
            f"/api/v1/proposals/{pid}/status", json={"action": "approve"}, headers=h
        ),
    ]

    for call in calls:
        for headers in ({}, as_person("nobody")):
            response = call(headers)
            assert response.status_code == 401
            assert response.json()["code"] == "UNAUTHENTICATED"

    assert rig.rag.ingested == []
    assert rig.db.state.proposals[pid].status is ProposalStatus.SUBMITTED


# ---- uploading -------------------------------------------------------------------------


def test_a_member_uploads_a_proposal_as_themselves(rig: Rig) -> None:
    response = rig.upload()

    assert response.status_code == 201, response.text
    out = ProposalUploadOut.model_validate(response.json())
    assert (out.status, out.revision, out.club_id, out.event_id) == (
        ProposalStatus.SUBMITTED,
        1,
        CLUB_A,
        rig.event,
    )
    assert rig.db.state.proposals[out.id].submitted_by == ORGANIZER.user_id


def test_the_title_defaults_when_none_is_sent(rig: Rig) -> None:
    response = rig.upload(title=None)

    assert response.status_code == 201
    assert response.json()["title"] == "Event Proposal"


def test_someone_from_another_club_cannot_upload(rig: Rig) -> None:
    response = rig.upload("other")

    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN"
    assert rig.storage.uploads == []


def test_an_unknown_event_is_404(rig: Rig) -> None:
    response = rig.upload(event=uuid4())

    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"content": b"Hello world"},
        {"content": b""},
        {"content": b"%PDF-" + b"x" * MAX_PROPOSAL_BYTES},
        {"title": "t" * 300},
    ],
    ids=["not a pdf", "empty", "too large", "long title"],
)
def test_an_invalid_upload_is_a_422_envelope_not_a_bare_detail(
    rig: Rig, kwargs: dict[str, Any]
) -> None:
    response = rig.upload(**kwargs)

    assert response.status_code == 422, response.text
    body = response.json()
    assert body["code"] == "VALIDATION_ERROR"
    assert "request_id" in body
    assert rig.storage.uploads == []


def test_an_oversized_upload_reads_only_one_byte_past_the_limit(rig: Rig) -> None:
    file = AsyncMock()
    file.read.return_value = b"%PDF-" + b"x" * MAX_PROPOSAL_BYTES

    with pytest.raises(InvalidRequestError):
        asyncio.run(
            upload_proposal(
                CLUB_A,
                rig.event,
                file,
                ORGANIZER,
                cast(ProposalService, Mock()),
                cast(
                    Request, SimpleNamespace(state=SimpleNamespace(request_id="oversized-upload"))
                ),
            )
        )

    file.read.assert_awaited_once_with(MAX_PROPOSAL_BYTES + 1)


def test_a_storage_failure_is_a_503_that_says_nothing_about_the_store(rig: Rig) -> None:
    rig.storage.fail_upload = True

    response = rig.upload()

    assert response.status_code == 503
    assert response.json()["code"] == "DEPENDENCY_UNAVAILABLE"
    assert "minio-internal" not in response.text
    assert "ConnectionError" not in response.text


# ---- reading ---------------------------------------------------------------------------


def test_a_member_reads_their_clubs_proposal(rig: Rig) -> None:
    pid = rig.submitted()

    response = rig.client.get(f"/api/v1/proposals/{pid}", headers=as_person("organizer"))

    assert response.status_code == 200
    out = ProposalOut.model_validate(response.json())
    assert (out.id, out.submitted_by, out.status) == (
        pid,
        ORGANIZER.user_id,
        ProposalStatus.SUBMITTED,
    )


def test_another_club_cannot_read_it_and_an_unknown_id_is_404(rig: Rig) -> None:
    pid = rig.submitted()

    assert rig.client.get(f"/api/v1/proposals/{pid}", headers=as_person("other")).status_code == 403
    missing = rig.client.get(f"/api/v1/proposals/{uuid4()}", headers=as_person("organizer"))
    assert missing.status_code == 404


def test_a_download_link_is_short_lived_and_only_for_those_who_may_read(rig: Rig) -> None:
    pid = rig.submitted()

    ok = rig.client.get(f"/api/v1/proposals/{pid}/download-url", headers=as_person("organizer"))
    denied = rig.client.get(f"/api/v1/proposals/{pid}/download-url", headers=as_person("other"))

    assert ok.status_code == 200
    link = ProposalDownloadUrlOut.model_validate(ok.json())
    assert (link.expires_in_seconds, "sig=abc" in link.download_url) == (900, True)
    assert denied.status_code == 403
    assert len(rig.storage.presigned) == 1


# ---- reviewing -------------------------------------------------------------------------


def review(rig: Rig, pid: UUID, body: dict[str, Any], actor_name: str = "campus") -> Any:
    return rig.client.patch(
        f"/api/v1/proposals/{pid}/status", json=body, headers=as_person(actor_name)
    )


def test_a_campus_admin_approves_and_the_reviewer_is_really_them(rig: Rig) -> None:
    pid = rig.submitted()

    faculty = review(rig, pid, {"action": "approve"}, actor_name="faculty")
    assert faculty.status_code == 200
    assert faculty.json()["status"] == "FACULTY_APPROVED"
    assert rig.rag.ingested == []
    response = review(rig, pid, {"action": "approve", "review_note": "Approved by campus"})

    assert response.status_code == 200, response.text
    out = ProposalOut.model_validate(response.json())
    assert out.status is ProposalStatus.CHUNKED
    assert (out.reviewed_by, out.review_note) == (CAMPUS.user_id, "Approved by campus")
    assert rig.rag.ingested[0]["approved_by"] == str(CAMPUS.user_id)


def test_when_rag_is_down_the_approval_still_stands(rig: Rig) -> None:
    rig.rag.accepts = False
    pid = rig.submitted()

    assert review(rig, pid, {"action": "approve"}, actor_name="faculty").status_code == 200
    response = review(rig, pid, {"action": "approve"})

    assert response.status_code == 200
    assert response.json()["status"] == "APPROVED"


def test_only_faculty_or_campus_admin_can_review(rig: Rig) -> None:
    pid = rig.submitted()

    for token in ("organizer", "other"):
        response = review(rig, pid, {"action": "approve"}, actor_name=token)
        assert response.status_code == 403
    assert rig.db.state.proposals[pid].status is ProposalStatus.SUBMITTED
    assert rig.rag.ingested == []


def test_campus_approval_requires_faculty_first(rig: Rig) -> None:
    pid = rig.submitted()
    response = review(rig, pid, {"action": "approve"})
    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_TRANSITION"
    assert rig.rag.ingested == []


def test_a_decided_proposal_cannot_be_decided_again(rig: Rig) -> None:
    pid = rig.submitted()
    review(rig, pid, {"action": "reject"}, actor_name="faculty")

    response = review(rig, pid, {"action": "approve"})

    assert response.status_code == 409
    assert response.json()["code"] == "INVALID_TRANSITION"


@pytest.mark.parametrize(
    "body",
    [
        {"action": "publish"},
        {"action": "approve", "review_note": "n" * 2001},
        {"action": "approve", "reviewed_by": str(uuid4())},
        {},
    ],
    ids=["unknown action", "note too long", "client-supplied reviewer", "no action"],
)
def test_a_malformed_review_is_a_422(rig: Rig, body: dict[str, Any]) -> None:
    pid = rig.submitted()

    response = review(rig, pid, body)

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert rig.db.state.proposals[pid].status is ProposalStatus.SUBMITTED


def test_reviewing_an_unknown_proposal_is_404(rig: Rig) -> None:
    assert review(rig, uuid4(), {"action": "approve"}).status_code == 404
