from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.container import Container
from app.domain.time import FixedClock
from app.main import create_app
from app.services.ports import UserIdentity
from app.services.resource_interests import ResourceInterestService
from tests.fakes import FakeReadinessProbe, SequentialIds, make_settings


class SessionForInterestRoute:
    def __init__(self, identity: UserIdentity) -> None:
        self.identity = identity

    def resolve_access_token(self, token: str) -> UserIdentity | None:
        return self.identity if token == "resource-token" else None


class Store:
    def __init__(self) -> None:
        self.records: list[Any] = []

    def add(self, record: Any) -> None:
        self.records.append(record)


class UnitOfWork:
    def __init__(self, store: Store) -> None:
        self.resource_interests = store

    def __enter__(self) -> "UnitOfWork":
        return self

    def __exit__(self, *_: Any) -> None:
        return None

    def commit(self) -> None:
        return None


def test_signed_in_user_can_save_an_interest_but_cannot_choose_the_requester() -> None:
    requester_id = uuid4()
    identity = UserIdentity(
        id=requester_id,
        email="organizer@example.invalid",
        display_name="Demo Organizer",
        campus_admin=False,
        memberships=(),
        is_synthetic=True,
    )
    store = Store()
    interests = ResourceInterestService(
        lambda: UnitOfWork(store),
        clock=FixedClock(datetime(2026, 10, 11, tzinfo=UTC)),
        ids=SequentialIds(),
    )
    client = TestClient(
        create_app(
            make_settings(),
            Container(
                readiness=cast(Any, FakeReadinessProbe()),
                sessions=cast(Any, SessionForInterestRoute(identity)),
                resource_interests=interests,
            ),
        ),
        raise_server_exceptions=False,
    )
    payload = {
        "category": "Vlsi boards",
        "purpose": "validate a low-power design",
        "preferred_date": "2026-10-20",
        "start_time": "10:00",
        "end_time": "12:00",
    }

    response = client.post(
        "/api/v1/resources/interests",
        json=payload,
        headers={"Authorization": "Bearer resource-token"},
    )
    assert response.status_code == 201, response.text
    assert response.json()["requester_id"] == str(requester_id)
    assert response.json()["category"] == "Vlsi boards"
    assert len(store.records) == 1

    spoofed = client.post(
        "/api/v1/resources/interests",
        json={**payload, "requester_id": str(UUID(int=2))},
        headers={"Authorization": "Bearer resource-token"},
    )
    assert spoofed.status_code == 422, spoofed.text

    invalid_window = client.post(
        "/api/v1/resources/interests",
        json={**payload, "end_time": "10:00"},
        headers={"Authorization": "Bearer resource-token"},
    )
    assert invalid_window.status_code == 422, invalid_window.text
    assert invalid_window.json()["details"][0]["loc"][-1] == "end_time"
