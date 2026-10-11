import pytest
from fastapi.testclient import TestClient

from app.container import build_container
from app.main import create_app
from tests.fakes import make_settings
from tests.integration.world import World, draft

pytestmark = pytest.mark.integration


def test_change_routes_preserve_partial_patch_scope_and_authority(world: World) -> None:
    event = draft(world).event
    other_event = draft(world).event
    settings = make_settings(database_url=world.engine.url.render_as_string(hide_password=False))
    with TestClient(create_app(settings, build_container(settings))) as client:

        def login(email: str) -> dict[str, str]:
            response = client.post("/api/v1/auth/demo-login", json={"email": email})
            assert response.status_code == 200
            return {"Authorization": "Bearer " + response.json()["access_token"]}

        organizer = login(f"{world.organizer.user_id}@example.invalid")
        admin = login(f"{world.club_admin.user_id}@example.invalid")
        outsider = login(f"{world.other.user_id}@example.invalid")
        base = f"/api/v1/events/{event.id}"
        dependency = client.post(
            base + "/dependencies",
            headers=organizer,
            json={
                "kind": "COMMITMENT",
                "title": "Venue request",
                "field_paths": ["resource_id"],
            },
        )
        assert dependency.status_code == 201, dependency.text
        assert dependency.json()["status"] == "REQUESTED"
        payload = {"expected_revision": 1, "changes": {"resource_id": None}}
        preview = client.post(base + "/impact", headers=organizer, json=payload)
        assert preview.status_code == 200, preview.text
        assert preview.json()["changed_fields"] == ["resource_id"]
        assert len(preview.json()["impact"]) == 1
        stage = client.post(
            base + "/change-proposals",
            headers={**organizer, "Idempotency-Key": "stage"},
            json={**payload, "reason": "Clear tentative venue"},
        )
        assert stage.status_code == 201, stage.text
        assert stage.json()["changes"] == {"resource_id": None}
        proposal = stage.json()["id"]
        assert client.get(base + "/change-proposals", headers=outsider).status_code == 403
        wrong = f"/api/v1/events/{other_event.id}/change-proposals/{proposal}/apply"
        assert client.post(wrong, headers=admin, json={"expected_revision": 1}).status_code == 404
        endpoint = base + f"/change-proposals/{proposal}/apply"
        assert (
            client.post(endpoint, headers=organizer, json={"expected_revision": 1}).status_code
            == 403
        )
        applied = client.post(
            endpoint, headers={**admin, "Idempotency-Key": "apply"}, json={"expected_revision": 1}
        )
        assert applied.status_code == 200, applied.text
        assert applied.json()["event"]["revision"] == 2
        replay = client.post(
            endpoint, headers={**admin, "Idempotency-Key": "apply"}, json={"expected_revision": 1}
        )
        assert replay.status_code == 200
        assert replay.json() == applied.json()
        items = client.get(base + "/dependencies", headers=organizer).json()["items"]
        assert items[0]["needs_revalidation"]
        assert items[0]["status"] == "NEEDS_REVALIDATION"
        saved = client.get(base + "/change-proposals", headers=organizer).json()["items"]
        assert saved[0]["status"] == "APPLIED"
        assert saved[0]["changes"] == {"resource_id": None}
