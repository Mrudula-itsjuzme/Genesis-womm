import json
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.api.middleware import REQUEST_ID_HEADER
from app.container import Container
from app.domain.authz import Actor
from app.domain.enums import AvailabilityState, EventStatus, FreshnessState, ResourceKind
from app.main import create_app
from app.schemas.common import ErrorEnvelope
from app.services.chat import AgentReply, ChatService
from app.services.delegation import DelegationService
from app.services.event_reads import EventReadService, EventView
from app.services.ports import ChatTurn, EventRecord, ResourceRecord, UserIdentity
from app.services.readiness import ReadinessService
from app.services.resource_reads import ResourceReadService
from app.services.schedule_write import WriteResult
from app.services.sessions import IssuedSession, SessionService
from tests.fakes import FakeReadinessProbe, make_settings

EVENT = str(uuid4())
RESOURCE = str(uuid4())
CLUB = str(uuid4())

VALID_EVENT: dict[str, Any] = {
    "club_id": CLUB,
    "title": "Robotics Demo Day",
    "start_at": "2026-10-20T09:00:00+05:30",
    "end_at": "2026-10-20T11:00:00+05:30",
}
VALID_CHAT: dict[str, Any] = {"messages": [{"role": "user", "content": "Plan a demo day"}]}


INTERNAL_KEY = "i" * 40
AGENT_HEADERS = {"X-Internal-Key": INTERNAL_KEY, "Authorization": "Bearer agent-token"}
SESSION_HEADERS = {"Authorization": "Bearer demo-token"}


def headers_for(path: str) -> dict[str, str]:
    """The credentials the route family needs: the facade takes a key plus a delegation."""
    return AGENT_HEADERS if path.startswith("/internal/v1") else SESSION_HEADERS


class FakeDelegationService:
    def resolve(self, token: str) -> Actor | None:
        return Actor(user_id=uuid4(), via_agent=True) if token == "agent-token" else None


class FakeSessionService:
    def __init__(self, issued: IssuedSession | None) -> None:
        self._issued = issued

    def issue_for_demo_email(self, email: str) -> IssuedSession | None:
        return self._issued if email == "organizer@example.invalid" else None

    def resolve_access_token(self, access_token: str) -> UserIdentity | None:
        if self._issued is not None and access_token == self._issued.access_token:
            return self._issued.user
        return None


class FakeScheduleWriteService:
    def create_event(self, context: Any, command: Any) -> WriteResult:
        now = datetime.now(UTC)
        return WriteResult(
            event=EventRecord(
                id=uuid4(),
                club_id=command.club_id,
                title=command.title,
                description=command.description,
                start_at=command.start_at,
                end_at=command.end_at,
                resource_id=command.resource_id,
                expected_attendance=command.expected_attendance,
                audience_tags=command.audience_tags,
                status=EventStatus.DRAFT,
                revision=1,
                created_by=context.actor.user_id,
                verified_by=None,
                verified_at=None,
                evidence_id=None,
                is_synthetic=False,
                created_at=now,
                updated_at=now,
            ),
            conflicts=(),
            venue_availability=AvailabilityState.UNKNOWN,
        )


class FakeEventReadService:
    def list(self, *_: Any, **__: Any) -> tuple[list[EventView], int]:
        return [], 0

    def get(self, _: Any, event_id: Any) -> EventView:
        now = datetime.now(UTC)
        return EventView(
            EventRecord(
                id=event_id,
                club_id=uuid4(),
                title="Visible event",
                description=None,
                start_at=now,
                end_at=now.replace(hour=(now.hour + 1) % 24),
                resource_id=None,
                expected_attendance=None,
                audience_tags=(),
                status=EventStatus.DRAFT,
                revision=1,
                created_by=uuid4(),
                verified_by=None,
                verified_at=None,
                evidence_id=None,
                is_synthetic=True,
                created_at=now,
                updated_at=now,
            ),
            AvailabilityState.UNKNOWN,
        )


class FakeResourceReadService:
    def __init__(self) -> None:
        self.resource = ResourceRecord(
            id=UUID(RESOURCE),
            kind=ResourceKind.VENUE,
            name="Synthetic Auditorium",
            description="Synthetic demo venue",
            location="Demo Block",
            capacity=120,
            availability_state=AvailabilityState.UNKNOWN,
            freshness_state=FreshnessState.CURRENT,
            source_id="synthetic-resource-1",
            source_url=None,
            collected_at=None,
            last_checked_at=None,
            is_synthetic=True,
        )

    def list(self, **_: Any) -> tuple[list[ResourceRecord], int]:
        return [self.resource], 1

    def get(self, _: Any) -> ResourceRecord:
        return self.resource


class FakeChatService:
    def chat(self, _: Any, __: ChatTurn) -> AgentReply:
        return AgentReply(body={"message": "A proposed plan."}, proposed_actions=())


# (method, path, json body or None)
STUBS: list[tuple[str, str, dict[str, Any] | None]] = []


@pytest.fixture(scope="module")
def client() -> TestClient:
    user = UserIdentity(
        id=uuid4(),
        email="organizer@example.invalid",
        display_name="Demo Organizer",
        campus_admin=False,
        memberships=(),
        is_synthetic=True,
    )
    container = Container(
        readiness=ReadinessService(FakeReadinessProbe(), "0001"),
        sessions=cast(
            SessionService,
            FakeSessionService(
                IssuedSession(access_token="demo-token", expires_at=datetime.now(UTC), user=user)
            ),
        ),
        schedule_write=cast(Any, FakeScheduleWriteService()),
        event_reads=cast(EventReadService, FakeEventReadService()),
        resource_reads=cast(ResourceReadService, FakeResourceReadService()),
        delegation=cast(DelegationService, FakeDelegationService()),
        chat=cast(ChatService, FakeChatService()),
        internal_api_key=INTERNAL_KEY,
    )
    return TestClient(create_app(make_settings(), container), raise_server_exceptions=False)


@pytest.fixture(scope="module")
def openapi(client: TestClient) -> dict[str, Any]:
    document: dict[str, Any] = client.get("/openapi.json").json()
    return document


@pytest.mark.parametrize(("method", "path", "body"), STUBS)
def test_stub_returns_the_501_envelope(
    client: TestClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = client.request(
        method,
        path,
        json=body,
        headers={REQUEST_ID_HEADER: "stub-1", **headers_for(path)},
    )
    assert response.status_code == 501, response.text
    envelope = ErrorEnvelope.model_validate(response.json())
    assert envelope.code.value == "NOT_IMPLEMENTED"
    assert envelope.request_id == "stub-1"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/api/v1/events", {**VALID_EVENT, "start_at": "2026-10-20T09:00:00"}),
        ("POST", "/api/v1/events", {**VALID_EVENT, "status": "CONFIRMED"}),
        ("POST", "/api/v1/agent/chat", {"messages": []}),
        ("GET", "/api/v1/events/not-a-uuid", None),
        ("GET", "/api/v1/events?limit=500", None),
    ],
)
def test_validation_runs_before_the_stub(
    client: TestClient, method: str, path: str, body: dict[str, Any] | None
) -> None:
    response = client.request(method, path, json=body, headers=headers_for(path))
    assert response.status_code == 422, response.text
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_demo_login_returns_a_bearer_token_and_server_side_profile(client: TestClient) -> None:
    response = client.post("/api/v1/auth/demo-login", json={"email": "organizer@example.invalid"})

    assert response.status_code == 200, response.text
    body = response.json()
    assert (body["access_token"], body["token_type"], body["user"]["email"]) == (
        "demo-token",
        "bearer",
        "organizer@example.invalid",
    )


def test_resource_routes_return_sourced_catalogue_records(client: TestClient) -> None:
    headers = {"Authorization": "Bearer demo-token"}

    listed = client.get("/api/v1/resources?kind=VENUE&q=auditorium", headers=headers)
    fetched = client.get(f"/api/v1/resources/{RESOURCE}", headers=headers)

    assert listed.status_code == 200, listed.text
    assert listed.json()["total"] == 1
    assert listed.json()["items"][0]["name"] == "Synthetic Auditorium"
    assert fetched.status_code == 200, fetched.text
    assert fetched.json()["synthetic"] is True


def test_demo_login_hides_whether_an_unknown_user_exists(client: TestClient) -> None:
    response = client.post("/api/v1/auth/demo-login", json={"email": "unknown@example.invalid"})

    assert response.status_code == 401, response.text
    assert response.json()["code"] == "UNAUTHENTICATED"


def test_public_routes_reject_a_missing_or_invalid_session_before_the_stub(
    client: TestClient,
) -> None:
    for headers in ({}, {"Authorization": "Bearer invalid"}):
        response = client.get("/api/v1/events", headers=headers)
        assert response.status_code == 401, response.text
        assert response.json()["code"] == "UNAUTHENTICATED"


def _operations(openapi: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    http = {"get", "post", "put", "patch", "delete"}
    return [
        (method.upper(), path, op)
        for path, item in openapi["paths"].items()
        for method, op in item.items()
        if method in http
    ]


def test_every_unimplemented_route_is_marked_as_a_stub(openapi: dict[str, Any]) -> None:
    for method, path, op in _operations(openapi):
        if (
            path in {"/health", "/ready"}
            or "/proposals" in path
            or (method, path)
            in {
                ("POST", "/api/v1/auth/demo-login"),
                ("POST", "/api/v1/agent/chat"),
                ("POST", "/api/v1/events"),
                ("GET", "/api/v1/events"),
                ("GET", "/api/v1/events/{event_id}"),
                ("POST", "/api/v1/events/{event_id}/conflict-check"),
                ("POST", "/api/v1/events/{event_id}/transitions"),
                ("POST", "/api/v1/overrides"),
                ("POST", "/internal/v1/agent-tools/check_event_conflicts"),
                ("GET", "/internal/v1/agent-tools/events/{event_id}"),
                ("POST", "/internal/v1/agent-actions"),
                ("GET", "/api/v1/agent-actions"),
                ("POST", "/api/v1/agent-actions/{action_id}/confirm"),
                ("POST", "/api/v1/agent-actions/{action_id}/reject"),
                ("GET", "/api/v1/resources"),
                ("GET", "/api/v1/resources/{resource_id}"),
            }
        ):
            assert "x-implementation-status" not in op
        else:
            assert op.get("x-implementation-status") == "stub", f"{method} {path}"


def test_stubs_cover_exactly_the_documented_routes(openapi: dict[str, Any]) -> None:
    documented = {
        (method, path.replace(EVENT, "{event_id}"))
        for method, path, _ in _operations(openapi)
        if path not in {"/health", "/ready"}
        and "/proposals" not in path
        and (method, path)
        not in {
            ("POST", "/api/v1/auth/demo-login"),
            ("POST", "/api/v1/agent/chat"),
            ("POST", "/api/v1/events"),
            ("GET", "/api/v1/events"),
            ("GET", "/api/v1/events/{event_id}"),
            ("POST", "/api/v1/events/{event_id}/conflict-check"),
            ("POST", "/api/v1/events/{event_id}/transitions"),
            ("POST", "/api/v1/overrides"),
            ("POST", "/internal/v1/agent-tools/check_event_conflicts"),
            ("GET", "/internal/v1/agent-tools/events/{event_id}"),
            ("POST", "/internal/v1/agent-actions"),
            ("GET", "/api/v1/agent-actions"),
            ("POST", "/api/v1/agent-actions/{action_id}/confirm"),
            ("POST", "/api/v1/agent-actions/{action_id}/reject"),
            ("GET", "/api/v1/resources"),
            ("GET", "/api/v1/resources/{resource_id}"),
        }
    }
    assert len(documented) == len(STUBS)


def test_validation_errors_are_documented_with_the_envelope_not_fastapis_default(
    openapi: dict[str, Any],
) -> None:
    schemas = openapi["components"]["schemas"]
    assert "HTTPValidationError" not in schemas
    for method, path, op in _operations(openapi):
        response_422 = op["responses"].get("422")
        if response_422 is not None:
            ref = response_422["content"]["application/json"]["schema"]["$ref"]
            assert ref.endswith("/ErrorEnvelope"), f"{method} {path}"


def test_public_routes_use_the_session_scheme_and_facade_routes_the_delegation_scheme(
    openapi: dict[str, Any],
) -> None:
    for method, path, op in _operations(openapi):
        schemes = {name for requirement in op.get("security", []) for name in requirement}
        if path == "/api/v1/auth/demo-login":
            assert schemes == set(), f"{method} {path}"
        elif path.startswith("/api/v1"):
            assert schemes == {"sessionBearer"}, f"{method} {path}"
        elif path.startswith("/internal/v1"):
            assert schemes == {"delegationBearer", "internalKey"}, f"{method} {path}"


def test_retry_prone_mutations_accept_an_idempotency_key(openapi: dict[str, Any]) -> None:
    for path in (
        "/api/v1/events",
        "/api/v1/agent-actions/{action_id}/confirm",
        "/internal/v1/agent-actions",
    ):
        parameters = openapi["paths"][path]["post"]["parameters"]
        assert any(p["name"] == "Idempotency-Key" and p["in"] == "header" for p in parameters)


def test_no_authority_bearing_field_exists_anywhere_in_the_contract(
    openapi: dict[str, Any],
) -> None:
    text = json.dumps(openapi)
    for forbidden in ("authorized_by", "ignore_conflicts", "access_level", "book_event"):
        assert forbidden not in text, forbidden


def test_event_create_exposes_no_status_field(openapi: dict[str, Any]) -> None:
    properties = openapi["components"]["schemas"]["EventCreate"]["properties"]
    assert "status" not in properties
    assert openapi["components"]["schemas"]["EventCreate"]["additionalProperties"] is False


def test_the_shared_enums_are_exported_once(openapi: dict[str, Any]) -> None:
    schemas = openapi["components"]["schemas"]
    assert set(schemas["ConflictType"]["enum"]) == {
        "VENUE_OVERLAP",
        "CAMPUS_GAP_VIOLATION",
        "TENTATIVE_OVERLAP",
        "DEPENDENCY_CONFLICT",
        "UNKNOWN_AVAILABILITY",
    }
    assert set(schemas["Severity"]["enum"]) == {"blocking", "warning", "info"}
