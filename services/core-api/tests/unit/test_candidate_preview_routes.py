from datetime import timedelta

from fastapi.testclient import TestClient

from app.api.deps import require_session_actor
from app.clients.tokens import PyJwtTokenService
from app.container import Container
from app.domain.enums import AvailabilityState
from app.domain.scheduling import Policy
from app.domain.time import FixedClock
from app.main import create_app
from app.services.conflict_checks import ConflictCheckService
from app.services.readiness import ReadinessService
from app.services.sessions import SessionService
from tests.fakes import FakeReadinessProbe, InMemoryDatabase, make_settings
from tests.unit.test_schedule_write import CLUB_A, CLUB_B, HALL, NOW, ORGANIZER, at


def test_candidate_preview_is_authorized_advisory_and_never_persists() -> None:
    db = InMemoryDatabase()
    db.state.clubs = {CLUB_A, CLUB_B}
    db.state.resources = {HALL: AvailabilityState.UNKNOWN}
    app = create_app(
        make_settings(),
        Container(
            sessions=SessionService(db.uow, PyJwtTokenService("s" * 40)),
            readiness=ReadinessService(FakeReadinessProbe(), "0004"),
            conflict_checks=ConflictCheckService(
                db.uow, clock=FixedClock(NOW), policy=Policy(timedelta(minutes=120))
            ),
        ),
    )
    client = TestClient(app, raise_server_exceptions=False)
    body = {
        "title": "Preview only",
        "club_id": str(CLUB_A),
        "start_at": at(11).isoformat(),
        "end_at": at(13).isoformat(),
        "resource_id": str(HALL),
    }
    route = "/api/v1/events/conflict-check"
    assert client.post(route, json=body).status_code == 401
    app.dependency_overrides[require_session_actor] = lambda: ORGANIZER
    response = client.post(route, json=body)
    assert response.status_code == 200, response.text
    assert response.json()["event_id"] is None
    assert response.json()["advisory"] is True
    assert response.json()["conflicts"][0]["type"] == "UNKNOWN_AVAILABILITY"
    assert db.commits == 0
    assert not db.state.events
    assert client.post(route, json={**body, "club_id": str(CLUB_B)}).status_code == 403
    assert client.post(route, json={**body, "end_at": body["start_at"]}).status_code == 422
