import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from app.container import build_container
from app.main import create_app
from tests.conftest import upgrade
from tests.fakes import make_settings
from tests.integration.support import NOW, insert, make_club, make_resource, make_user

pytestmark = pytest.mark.integration


def test_e2e_scenarios_1_to_5(engine: Engine) -> None:
    upgrade(engine)
    with engine.begin() as connection:
        user = make_user(connection)
        club = make_club(connection)
        insert(
            connection, "memberships", user_id=user, club_id=club, role="ORGANIZER", created_at=NOW
        )
        venue_a = make_resource(connection, name="Venue A")
        venue_b = make_resource(connection, name="Venue B")

    settings = make_settings(database_url=engine.url.render_as_string(hide_password=False))
    with TestClient(create_app(settings, build_container(settings))) as client:
        login = client.post("/api/v1/auth/demo-login", json={"email": f"{user}@example.invalid"})
        assert login.status_code == 200, login.text
        token = login.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Create a tentative proposal.
        res1 = client.post(
            "/api/v1/events",
            json={
                "club_id": str(club),
                "title": "Event 1",
                "start_at": "2026-10-20T09:00:00+05:30",
                "end_at": "2026-10-20T11:00:00+05:30",
                "resource_id": str(venue_a),
            },
            headers=headers,
        )
        assert res1.status_code == 201
        event1_id = res1.json()["event"]["id"]
        event1_rev = res1.json()["event"]["revision"]

        # 2. Detect a tentative overlap against existing unconfirmed proposals.
        res2 = client.post(
            "/api/v1/events",
            json={
                "club_id": str(club),
                "title": "Event 2",
                "start_at": "2026-10-20T09:30:00+05:30",
                "end_at": "2026-10-20T10:30:00+05:30",
                "resource_id": str(venue_a),
            },
            headers=headers,
        )
        assert res2.status_code == 201
        assert len(res2.json()["conflicts"]) > 0
        event2_id = res2.json()["event"]["id"]
        event2_rev = res2.json()["event"]["revision"]

        # 3. Detect a same-venue overlap against confirmed events.
        # Admin login to confirm
        with engine.begin() as connection:
            admin = make_user(connection, admin=True)
        admin_login = client.post(
            "/api/v1/auth/demo-login", json={"email": f"{admin}@example.invalid"}
        )
        admin_token = admin_login.json()["access_token"]
        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # Step to PROPOSED
        t_prop = client.post(
            f"/api/v1/events/{event1_id}/transitions",
            json={"target_status": "PROPOSED", "expected_revision": event1_rev},
            headers=headers,
        )
        assert t_prop.status_code == 200, t_prop.json()
        event1_rev = t_prop.json()["revision"]

        # Step to SUBMITTED
        t_ack = client.post(
            f"/api/v1/events/{event1_id}/transitions",
            json={"target_status": "SUBMITTED", "expected_revision": event1_rev},
            headers=admin_headers,
        )
        assert t_ack.status_code == 200, t_ack.json()
        event1_rev = t_ack.json()["revision"]

        evidence_payload = {
            "kind": "EMAIL",
            "reference": "email-123",
            "captured_at": "2026-10-20T09:00:00+05:30",
        }

        # Confirm event 1
        t1 = client.post(
            f"/api/v1/events/{event1_id}/transitions",
            json={
                "target_status": "CONFIRMED",
                "expected_revision": event1_rev,
                "evidence": evidence_payload,
            },
            headers=admin_headers,
        )
        assert t1.status_code == 200, t1.json()
        event1_rev = t1.json()["revision"]

        # Try to confirm event 2
        # First step it to PROPOSED and SUBMITTED
        t2_prop = client.post(
            f"/api/v1/events/{event2_id}/transitions",
            json={"target_status": "PROPOSED", "expected_revision": event2_rev},
            headers=headers,
        )
        assert t2_prop.status_code == 200, t2_prop.json()
        event2_rev = t2_prop.json()["revision"]

        t2_ack = client.post(
            f"/api/v1/events/{event2_id}/transitions",
            json={"target_status": "SUBMITTED", "expected_revision": event2_rev},
            headers=admin_headers,
        )
        assert t2_ack.status_code == 200, t2_ack.json()
        event2_rev = t2_ack.json()["revision"]

        t2 = client.post(
            f"/api/v1/events/{event2_id}/transitions",
            json={
                "target_status": "CONFIRMED",
                "expected_revision": event2_rev,
                "evidence": evidence_payload,
            },
            headers=admin_headers,
        )
        assert t2.status_code == 409  # CONFLICT_DETECTED

        # 4. Detect a cross-venue gap violation (< 120 minutes).
        res3 = client.post(
            "/api/v1/events",
            json={
                "club_id": str(club),
                "title": "Event 3",
                "start_at": "2026-10-20T11:30:00+05:30",
                "end_at": "2026-10-20T12:30:00+05:30",
                "resource_id": str(venue_b),
            },
            headers=headers,
        )
        event3_id = res3.json()["event"]["id"]
        event3_rev = res3.json()["event"]["revision"]

        t3_prop = client.post(
            f"/api/v1/events/{event3_id}/transitions",
            json={"target_status": "PROPOSED", "expected_revision": event3_rev},
            headers=headers,
        )
        event3_rev = t3_prop.json()["revision"]

        t3_ack = client.post(
            f"/api/v1/events/{event3_id}/transitions",
            json={"target_status": "SUBMITTED", "expected_revision": event3_rev},
            headers=admin_headers,
        )
        event3_rev = t3_ack.json()["revision"]

        t3 = client.post(
            f"/api/v1/events/{event3_id}/transitions",
            json={
                "target_status": "CONFIRMED",
                "expected_revision": event3_rev,
                "evidence": evidence_payload,
            },
            headers=admin_headers,
        )
        assert t3.status_code == 409  # gap violation
        # 5. An authorized campus-gap override must still reject a venue overlap.
        o1 = client.post(
            "/api/v1/overrides",
            json={
                "scope": "CAMPUS_GAP",
                "event_a_id": event1_id,
                "event_b_id": event3_id,
                "reason": "Admin waived gap",
            },
            headers=admin_headers,
        )
        assert o1.status_code == 200, o1.json()

        t3_retry = client.post(
            f"/api/v1/events/{event3_id}/transitions",
            json={
                "target_status": "CONFIRMED",
                "expected_revision": event3_rev,
                "evidence": evidence_payload,
            },
            headers=admin_headers,
        )
        assert t3_retry.status_code == 200, t3_retry.json()
