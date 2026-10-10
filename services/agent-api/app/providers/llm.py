from dataclasses import dataclass
from typing import Any, Protocol

from app.schemas.chat import ChatMessage


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LlmResponse:
    text: str | None
    tool_calls: list[ToolCall]


class LlmPort(Protocol):
    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LlmResponse: ...
