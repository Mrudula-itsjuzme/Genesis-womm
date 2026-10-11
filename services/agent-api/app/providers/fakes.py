from typing import Any

from app.ports.llm import LlmPort, LlmResponse, ToolCall
from app.schemas.chat import ChatMessage


class FakeLlmProvider(LlmPort):
    def __init__(
        self, responses: list[LlmResponse] | None = None, *, demo_mode: bool = False
    ) -> None:
        self.responses = list(responses or [])
        self.demo_mode = demo_mode
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
        if self.demo_mode:
            return self._demo_response(messages)
        return LlmResponse(text="fake response", tool_calls=[])

    @staticmethod
    def _demo_response(messages: list[ChatMessage]) -> LlmResponse:
        last = messages[-1].content
        if last.startswith("[Tool check_event_conflicts]"):
            return LlmResponse(
                text=None,
                tool_calls=[
                    ToolCall(
                        id="demo-file",
                        name="file_event_draft_proposal",
                        arguments={
                            "summary": "Proposed synthetic demo workshop",
                            "payload": {
                                "club_id": "20000000-0000-4000-8000-000000000001",
                                "title": "Synthetic Demo Workshop",
                                "start_at": "2026-11-20T10:00:00+05:30",
                                "end_at": "2026-11-20T12:00:00+05:30",
                                "resource_id": "30000000-0000-4000-8000-000000000002",
                            },
                        },
                    )
                ],
            )
        if last.startswith("[Tool file_event_draft_proposal]"):
            return LlmResponse(
                text=(
                    "I proposed a synthetic demo workshop. "
                    "Nothing is booked until you confirm it."
                ),
                tool_calls=[],
            )
        return LlmResponse(
            text=None,
            tool_calls=[
                ToolCall(
                    id="demo-check",
                    name="check_event_conflicts",
                    arguments={
                        "club_id": "20000000-0000-4000-8000-000000000001",
                        "start_at": "2026-11-20T10:00:00+05:30",
                        "end_at": "2026-11-20T12:00:00+05:30",
                        "resource_id": "30000000-0000-4000-8000-000000000002",
                    },
                )
            ],
        )
