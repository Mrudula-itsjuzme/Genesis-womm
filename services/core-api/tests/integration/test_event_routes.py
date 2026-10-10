"""End-to-end HTTP coverage for Core's event write route."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from app.container import build_container
from app.main import create_app
from tests.conftest import upgrade
from tests.fakes import make_settings
from tests.integration.support import NOW, insert, make_club, make_user

pytestmark = pytest.mark.integration


def test_a_seeded_organizer_can_login_and_create_a_draft_over_http(engine: Engine) -> None:
    upgrade(engine)
    with engine.begin() as connection:
        user = make_user(connection)
        club = make_club(connection)
        insert(
            connection, "memberships", user_id=user, club_id=club, role="ORGANIZER", created_at=NOW
        )

    settings = make_settings(database_url=engine.url.render_as_string(hide_password=False))
    with TestClient(create_app(settings, build_container(settings))) as client:
        login = client.post("/api/v1/auth/demo-login", json={"email": f"{user}@example.invalid"})
        assert login.status_code == 200, login.text
        response = client.post(
            "/api/v1/events",
            json={
                "club_id": str(club),
                "title": "HTTP Demo Day",
                "start_at": "2026-10-20T09:00:00+05:30",
                "end_at": "2026-10-20T11:00:00+05:30",
            },
            headers={"Authorization": f"Bearer {login.json()['access_token']}"},
        )

    assert response.status_code == 201, response.text
    assert response.json()["event"]["status"] == "DRAFT"
    with engine.connect() as connection:
        assert connection.execute(text("SELECT count(*) FROM core.events")).scalar_one() == 1
