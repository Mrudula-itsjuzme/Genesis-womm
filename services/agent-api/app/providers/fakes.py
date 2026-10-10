from typing import Any
from app.providers.llm import LlmPort, LlmResponse
from app.schemas.chat import ChatMessage


class FakeLlmProvider(LlmPort):
    def __init__(self, responses: list[LlmResponse] | None = None) -> None:
        self.responses = list(responses or [])
        self.calls: list[list[ChatMessage]] = []

    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LlmResponse:
        self.calls.append(list(messages))
        if self.responses:
            return self.responses.pop(0)
        return LlmResponse(text="fake response", tool_calls=[])
