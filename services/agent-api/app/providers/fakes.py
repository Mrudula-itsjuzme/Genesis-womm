from typing import Any

from app.ports.llm import LlmPort, LlmResponse
from app.providers.demo_planner import plan
from app.schemas.chat import ChatMessage


class FakeLlmProvider(LlmPort):
    def __init__(
        self, responses: list[LlmResponse] | None = None, *, demo_mode: bool = False
    ) -> None:
        self.responses = list(responses or [])
        self.demo_mode = demo_mode
        self.calls: list[list[ChatMessage]] = []
        self.system_prompts: list[str] = []

    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LlmResponse:
        self.calls.append(list(messages))
        self.system_prompts.append(system_prompt)
        if self.responses:
            return self.responses.pop(0)
        if self.demo_mode:
            return plan(messages, system_prompt)
        return LlmResponse(text="fake response", tool_calls=[])
