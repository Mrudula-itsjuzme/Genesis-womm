from typing import Any, cast
from uuid import uuid4

from fastapi.testclient import TestClient

from app.container import Container
from app.main import create_app
from app.services.chat import AgentReply, ChatService
from app.services.ports import ChatTurn, UserIdentity
from app.services.readiness import ReadinessService
from app.services.sessions import SessionService
from tests.fakes import FakeReadinessProbe, make_settings


class FakeSessions:
    def __init__(self, user: UserIdentity) -> None:
        self._user = user

    def resolve_access_token(self, _: str) -> UserIdentity:
        return self._user


class FakeChat:
    def __init__(self) -> None:
        self.turn: ChatTurn | None = None

    def chat(self, _: Any, turn: ChatTurn) -> AgentReply:
        self.turn = turn
        return AgentReply(
            body={"message": "I prepared a draft proposal.", "citations": [], "trace": []},
            proposed_actions=(),
        )


def test_chat_route_relays_a_turn_to_the_live_chat_service() -> None:
    user_id = uuid4()
    user = UserIdentity(
        id=user_id,
        email="organizer@example.invalid",
        display_name="Organizer",
        campus_admin=False,
        memberships=(),
        is_synthetic=True,
    )
    fake = FakeChat()
    container = Container(
        readiness=ReadinessService(FakeReadinessProbe(), "0001"),
        sessions=cast(SessionService, FakeSessions(user)),
        chat=cast(ChatService, fake),
    )
    client = TestClient(create_app(make_settings(), container))

    response = client.post(
        "/api/v1/agent/chat",
        json={"messages": [{"role": "user", "content": "Help plan a hackathon"}]},
        headers={"Authorization": "Bearer session-token", "X-Request-ID": "req-chat"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["message"] == "I prepared a draft proposal."
    assert fake.turn == ChatTurn(messages=(("user", "Help plan a hackathon"),), event_id=None)
