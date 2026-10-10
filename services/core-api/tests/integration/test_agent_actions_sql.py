"""The Agent proposes, a person decides, on real PostgreSQL (spine AD-9, AD-10, AD-21).

The unit tests prove each rule against an in-memory database. This proves the same flow
end to end over HTTP and under concurrency, with roles and tokens from the real services.
"""

from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.container import Container, build_container
from app.domain.authz import Actor
from app.domain.enums import AgentActionStatus, Role
from app.domain.lifecycle import InvalidTransitionError
from app.main import create_app
from app.services.schedule_write import RequestContext
from tests.conftest import upgrade
from tests.fakes import make_settings
from tests.integration.support import NOW, insert, make_club, make_resource, make_user

pytestmark = pytest.mark.integration

INTERNAL_KEY = "i" * 40
FILE = "/internal/v1/agent-actions"
ACTIONS = "/api/v1/agent-actions"


@dataclass
class Campus:
    client: TestClient
    container: Container
    engine: Engine
    user: UUID
    admin: UUID
    club: UUID
    venue: UUID
    organizer: dict[str, str]
    campus_admin: dict[str, str]

    def agent(self) -> dict[str, str]:
        assert self.container.delegation is not None
        actor = Actor(user_id=self.user, memberships={self.club: Role.ORGANIZER})
        issued = self.container.delegation.issue(actor, "req-agent")
        return {"X-Internal-Key": INTERNAL_KEY, "Authorization": f"Bearer {issued.token}"}

    def body(self, title: str = "Robotics Demo Day") -> dict[str, object]:
        return {
            "type": "CREATE_EVENT_DRAFT",
            "summary": f"Draft {title}",
            "payload": {
                "club_id": str(self.club),
                "title": title,
                "start_at": "2026-10-20T10:00:00+05:30",
                "end_at": "2026-10-20T12:00:00+05:30",
                "resource_id": str(self.venue),
            },
        }

    def file(self, idempotency_key: str | None = None) -> str:
        headers = self.agent()
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        response = self.client.post(FILE, json=self.body(), headers=headers)
        assert response.status_code == 201, response.text
        return str(response.json()["action_id"])

    def count(self, table: str, where: str = "true") -> int:
        statement = f"SELECT count(*) FROM core.{table} WHERE {where}"  # noqa: S608
        with self.engine.connect() as conn:
            return int(conn.execute(text(statement)).scalar_one())


@pytest.fixture
def campus(engine: Engine) -> Iterator[Campus]:
    upgrade(engine)
    with engine.begin() as conn:
        user, admin = make_user(conn), make_user(conn, admin=True)
        club, venue = make_club(conn), make_resource(conn)
        insert(conn, "memberships", user_id=user, club_id=club, role="ORGANIZER", created_at=NOW)

    settings = make_settings(database_url=engine.url.render_as_string(hide_password=False))
    container = build_container(settings)
    with TestClient(create_app(settings, container), raise_server_exceptions=False) as client:

        def login(person: UUID) -> dict[str, str]:
            response = client.post(
                "/api/v1/auth/demo-login", json={"email": f"{person}@example.invalid"}
            )
            assert response.status_code == 200, response.text
            return {"Authorization": f"Bearer {response.json()['access_token']}"}

        yield Campus(client, container, engine, user, admin, club, venue, login(user), login(admin))


def test_the_whole_journey_from_the_agents_proposal_to_the_event(campus: Campus) -> None:
    action_id = campus.file()

    listed = campus.client.get(ACTIONS, headers=campus.organizer).json()
    assert [a["action_id"] for a in listed["items"]] == [action_id]
    assert listed["items"][0]["status"] == "PROPOSED"
    assert campus.count("events") == 0, "a proposal is not an event"

    confirmed = campus.client.post(f"{ACTIONS}/{action_id}/confirm", headers=campus.organizer)
    assert confirmed.status_code == 200, confirmed.text
    created = confirmed.json()["created_entity_id"]
    assert confirmed.json()["action"]["status"] == "EXECUTED"

    event = campus.client.get(f"/api/v1/events/{created}", headers=campus.organizer).json()
    assert (event["status"], event["title"]) == ("DRAFT", "Robotics Demo Day")
    assert campus.count("events", f"created_by = '{campus.user}'") == 1
    assert campus.count("agent_actions", "status = 'EXECUTED'") == 1
    assert campus.count("audit_events", "action = 'FILE_AGENT_ACTION' AND via = 'AGENT'") == 1
    assert campus.count("audit_events", "action = 'CONFIRM_AGENT_ACTION' AND via = 'USER'") == 1
    assert campus.count("audit_events", "action = 'CREATE_EVENT' AND via = 'USER'") == 1


def test_a_retried_filing_over_http_is_one_proposal(campus: Campus) -> None:
    first = campus.file(idempotency_key="turn-1-call-1")
    second = campus.file(idempotency_key="turn-1-call-1")

    assert first == second
    assert campus.count("agent_actions") == 1


def test_confirming_twice_is_one_event(campus: Campus) -> None:
    action_id = campus.file()

    first = campus.client.post(f"{ACTIONS}/{action_id}/confirm", headers=campus.organizer).json()
    second = campus.client.post(f"{ACTIONS}/{action_id}/confirm", headers=campus.organizer).json()

    assert second["created_entity_id"] == first["created_entity_id"]
    assert campus.count("events") == 1


def test_a_rejected_proposal_stays_rejected(campus: Campus) -> None:
    action_id = campus.file()
    assert (
        campus.client.post(f"{ACTIONS}/{action_id}/reject", headers=campus.organizer).status_code
        == 200
    )

    again = campus.client.post(f"{ACTIONS}/{action_id}/confirm", headers=campus.organizer)

    assert again.status_code == 409
    assert again.json()["code"] == "INVALID_TRANSITION"
    assert campus.count("events") == 0


def test_a_campus_admin_cannot_confirm_someone_elses_proposal(campus: Campus) -> None:
    action_id = campus.file()

    response = campus.client.post(f"{ACTIONS}/{action_id}/confirm", headers=campus.campus_admin)

    assert response.status_code == 403
    assert campus.count("events") == 0
    assert campus.count("agent_actions", "status = 'PROPOSED'") == 1


def test_losing_the_role_before_confirming_stops_the_event(campus: Campus) -> None:
    action_id = campus.file()
    with campus.engine.begin() as conn:
        conn.execute(
            text("DELETE FROM core.memberships WHERE user_id = :user"), {"user": campus.user}
        )

    response = campus.client.post(f"{ACTIONS}/{action_id}/confirm", headers=campus.organizer)

    assert response.status_code == 403
    assert campus.count("events") == 0
    assert campus.count("agent_actions", "status = 'PROPOSED'") == 1


def human(campus: Campus) -> Actor:
    return Actor(user_id=campus.user, memberships={campus.club: Role.ORGANIZER})


def test_concurrent_confirmations_create_exactly_one_event(campus: Campus) -> None:
    action_id = UUID(campus.file())
    service = campus.container.agent_actions
    assert service is not None

    def confirm(index: int) -> UUID:
        ctx = RequestContext(actor=human(campus), request_id=f"c-{index}")
        return service.confirm(ctx, action_id).created_entity_id

    with ThreadPoolExecutor(max_workers=6) as pool:
        created = list(pool.map(confirm, range(6)))

    assert len(set(created)) == 1
    assert campus.count("events") == 1
    assert campus.count("agent_actions", "status = 'EXECUTED'") == 1
    assert (
        campus.count("audit_events", "action = 'CONFIRM_AGENT_ACTION' AND outcome = 'SUCCESS'") == 1
    )


def test_a_confirmation_racing_a_rejection_leaves_one_consistent_outcome(
    campus: Campus,
) -> None:
    action_id = UUID(campus.file())
    service = campus.container.agent_actions
    assert service is not None

    def decide(kind: str) -> str:
        ctx = RequestContext(actor=human(campus), request_id=f"race-{kind}")
        try:
            if kind == "confirm":
                service.confirm(ctx, action_id)
            else:
                service.reject(ctx, action_id)
        except InvalidTransitionError:
            return f"{kind}-lost"
        return f"{kind}-won"

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(decide, ["confirm", "reject"]))

    final = next(iter(_status(campus, action_id)))
    assert final in {AgentActionStatus.EXECUTED, AgentActionStatus.REJECTED}
    assert sum(o.endswith("-won") for o in outcomes) == 1, outcomes
    if final is AgentActionStatus.EXECUTED:
        assert campus.count("events") == 1
    assert campus.count("events") <= 1


def _status(campus: Campus, action_id: UUID) -> list[AgentActionStatus]:
    with campus.engine.connect() as conn:
        rows = conn.execute(
            text("SELECT status FROM core.agent_actions WHERE id = :id"), {"id": action_id}
        ).scalars()
        return [AgentActionStatus(row) for row in rows]
