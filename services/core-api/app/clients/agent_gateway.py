"""Core's HTTP client for the Agent (spine AD-3, AD-10, AD-19).

Synchronous, because Core is. The access level is fixed here: it comes from what Core allows,
never from the person's request or from anything the model says.
"""

from typing import Any

import httpx

from app.services.errors import AgentOutputInvalidError, AgentUnavailableError
from app.services.ports import ChatContext, ChatTurn

# A route in contracts/agent-api.openapi.yaml; a unit test pins it.
CHAT_PATH = "/v1/agent/chat"
_ACCESS_LEVEL = "CAMPUS_PUBLIC"
_CAMPUS_TIMEZONE = "Asia/Kolkata"
# The longest name the Agent accepts (contracts/agent-api.openapi.yaml). One long club name must
# not make the Agent refuse the whole turn.
_NAME_LIMIT = 200


def _context_body(context: ChatContext) -> dict[str, Any]:
    return {
        "now": context.now.isoformat(),
        "timezone": _CAMPUS_TIMEZONE,
        "clubs": [
            {"id": str(club.id), "name": club.name[:_NAME_LIMIT], "role": club.role.value}
            for club in context.clubs
        ],
        "venues": [
            {
                "id": str(venue.id),
                "name": venue.name[:_NAME_LIMIT],
                "capacity": venue.capacity,
                "availability": venue.availability.value,
            }
            for venue in context.venues
        ],
    }


class HttpAgentGateway:
    def __init__(self, client: httpx.Client) -> None:
        self._client = client

    def chat(self, turn: ChatTurn, *, delegation_token: str, request_id: str) -> dict[str, Any]:
        body: dict[str, Any] = {
            "messages": [{"role": role, "content": content} for role, content in turn.messages],
            "access_level": _ACCESS_LEVEL,
        }
        if turn.event_id is not None:
            body["event_id"] = str(turn.event_id)
        if turn.context is not None:
            body["context"] = _context_body(turn.context)
        try:
            response = self._client.post(
                CHAT_PATH,
                json=body,
                headers={
                    "Authorization": f"Bearer {delegation_token}",
                    "X-Request-ID": request_id,
                },
            )
        except httpx.RequestError as error:
            # Only the kind of failure: the full text can carry the URL.
            raise AgentUnavailableError(f"agent request failed: {type(error).__name__}") from error
        if response.status_code in (401, 403) or response.status_code >= 500:
            # A refused key or a failing Agent is Core's dependency problem, not the person's.
            raise AgentUnavailableError(f"agent answered {response.status_code}")
        if not response.is_success:
            raise AgentOutputInvalidError(f"agent rejected the turn with {response.status_code}")
        try:
            reply = response.json()
        except ValueError as error:
            raise AgentOutputInvalidError("agent reply was not JSON") from error
        if not isinstance(reply, dict):
            raise AgentOutputInvalidError("agent reply was not a JSON object")
        return reply
