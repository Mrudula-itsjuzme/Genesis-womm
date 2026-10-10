"""The Agent facade on real infrastructure: roles from PostgreSQL, tokens from the real services.

The unit tests prove each piece; this proves the chain. In particular it shows that what a
delegation token may do is decided by the database on every call, not by the token.
"""

from collections.abc import Iterator
from dataclasses import dataclass
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.container import Container, build_container
from app.domain.authz import Actor
from app.domain.enums import Role
from app.main import create_app
from tests.conftest import upgrade
from tests.fakes import make_settings
from tests.integration.support import NOW, insert, make_club, make_resource, make_user

pytestmark = pytest.mark.integration

INTERNAL_KEY = "i" * 40
NIL_UUID = "00000000-0000-0000-0000-000000000000"
CHECK = "/internal/v1/agent-tools/check_event_conflicts"
EVENT = "/internal/v1/agent-tools/events/{event_id}"


@dataclass
class Campus:
    client: TestClient
    container: Container
    engine: Engine
    user: UUID
    club: UUID
    venue: UUID
    session: dict[str, str]
    event_id: str

    def agent(self, actor: Actor | None = None, key: str = INTERNAL_KEY) -> dict[str, str]:
        who = actor or Actor(user_id=self.user, memberships={self.club: Role.ORGANIZER})
        assert self.container.delegation is not None
        issued = self.container.delegation.issue(who, "req-1")
        return {"X-Internal-Key": key, "Authorization": f"Bearer {issued.token}"}


@pytest.fixture
def campus(engine: Engine) -> Iterator[Campus]:
    upgrade(engine)
    with engine.begin() as conn:
        user, club, venue = make_user(conn), make_club(conn), make_resource(conn)
        insert(conn, "memberships", user_id=user, club_id=club, role="ORGANIZER", created_at=NOW)

    settings = make_settings(database_url=engine.url.render_as_string(hide_password=False))
    container = build_container(settings)
    with TestClient(create_app(settings, container), raise_server_exceptions=False) as client:
        login = client.post("/api/v1/auth/demo-login", json={"email": f"{user}@example.invalid"})
        assert login.status_code == 200, login.text
        session = {"Authorization": f"Bearer {login.json()['access_token']}"}
        created = client.post(
            "/api/v1/events",
            json={
                "club_id": str(club),
                "title": "Robotics Demo Day",
                "start_at": "2026-10-20T10:00:00+05:30",
                "end_at": "2026-10-20T12:00:00+05:30",
                "resource_id": str(venue),
            },
            headers=session,
        )
        assert created.status_code == 201, created.text
        yield Campus(
            client, container, engine, user, club, venue, session, created.json()["event"]["id"]
        )


def test_a_delegation_reads_and_checks_what_the_users_roles_allow(campus: Campus) -> None:
    headers = campus.agent()

    read = campus.client.get(EVENT.format(event_id=campus.event_id), headers=headers)
    check = campus.client.post(CHECK, json={"event_id": campus.event_id}, headers=headers)

    assert read.status_code == 200, read.text
    assert read.json()["id"] == campus.event_id
    assert check.status_code == 200, check.text
    assert check.json()["event_id"] == campus.event_id


def test_an_unsaved_candidate_is_checked_against_what_is_stored(campus: Campus) -> None:
    body = {
        "club_id": str(campus.club),
        "start_at": "2026-10-20T11:00:00+05:30",
        "end_at": "2026-10-20T13:00:00+05:30",
        "resource_id": str(campus.venue),
    }

    response = campus.client.post(CHECK, json=body, headers=campus.agent())

    assert response.status_code == 200, response.text
    out = response.json()
    assert out["event_id"] is None
    assert out["has_blocking"] is False
    overlaps = [c for c in out["conflicts"] if c["type"] == "TENTATIVE_OVERLAP"]
    # One saved draft in the same venue violates both independent constraints, as warnings.
    assert {c["constraint"] for c in overlaps} == {"VENUE_OVERLAP", "CAMPUS_GAP"}
    assert {c["severity"] for c in overlaps} == {"warning"}
    assert all(c["event_ids"] == [NIL_UUID, campus.event_id] for c in overlaps)
    assert [c["type"] for c in out["conflicts"] if c["type"] != "TENTATIVE_OVERLAP"] == [
        "UNKNOWN_AVAILABILITY"
    ]


def test_a_revoked_membership_takes_effect_while_the_token_is_still_valid(campus: Campus) -> None:
    headers = campus.agent()
    assert (
        campus.client.get(EVENT.format(event_id=campus.event_id), headers=headers).status_code
        == 200
    )

    with campus.engine.begin() as conn:
        conn.execute(
            text("DELETE FROM core.memberships WHERE user_id = :user"), {"user": campus.user}
        )

    check = campus.client.post(CHECK, json={"event_id": campus.event_id}, headers=headers)
    assert check.status_code == 403
    assert check.json()["code"] == "FORBIDDEN"


def test_a_token_for_a_user_who_no_longer_exists_is_unauthenticated(campus: Campus) -> None:
    with campus.engine.begin() as conn:
        ghost = make_user(conn)
    headers = campus.agent(Actor(user_id=ghost, memberships={campus.club: Role.ORGANIZER}))
    with campus.engine.begin() as conn:
        conn.execute(text("DELETE FROM core.users WHERE id = :user"), {"user": ghost})

    response = campus.client.get(EVENT.format(event_id=campus.event_id), headers=headers)

    assert response.status_code == 401


def test_the_token_cannot_claim_more_than_the_database_grants(campus: Campus) -> None:
    """A token minted from a forged, over-privileged actor still resolves to the real user."""
    forged = Actor(user_id=campus.user, campus_admin=True, memberships={})
    with campus.engine.begin() as conn:
        outsider_club = make_club(conn)
    body = {
        "club_id": str(outsider_club),
        "start_at": "2026-10-21T10:00:00+05:30",
        "end_at": "2026-10-21T12:00:00+05:30",
    }

    response = campus.client.post(CHECK, json=body, headers=campus.agent(forged))

    assert response.status_code == 403


def test_a_delegation_is_refused_on_every_public_route_and_a_session_on_the_facade(
    campus: Campus,
) -> None:
    delegation = campus.agent()
    public = campus.client.get(
        "/api/v1/events", headers={"Authorization": delegation["Authorization"]}
    )
    facade = campus.client.get(
        EVENT.format(event_id=campus.event_id),
        headers={"X-Internal-Key": INTERNAL_KEY, **campus.session},
    )

    assert public.status_code == 401
    assert facade.status_code == 401


def test_the_facade_refuses_a_caller_without_the_internal_key(campus: Campus) -> None:
    response = campus.client.get(
        EVENT.format(event_id=campus.event_id), headers=campus.agent(key="not-the-key")
    )

    assert response.status_code == 401
