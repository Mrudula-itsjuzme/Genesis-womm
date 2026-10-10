from typing import Any

import groq
from groq import AsyncGroq

from app.providers.llm import LlmPort, LlmResponse, ToolCall
from app.schemas.chat import ChatMessage


class GroqProvider(LlmPort):
    def __init__(self, api_key: str, model: str) -> None:
        self._client = AsyncGroq(api_key=api_key)
        self._model = model

    async def complete(
        self,
        messages: list[ChatMessage],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> LlmResponse:
        api_messages: list[Any] = [{"role": "system", "content": system_prompt}]
        for msg in messages:
            api_messages.append({"role": msg.role, "content": msg.content})

        kwargs: dict[str, Any] = {}
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await self._client.chat.completions.create(
                messages=api_messages,
                model=self._model,
                **kwargs,
            )
        except groq.APIError as e:
            # We might want to wrap this in a provider error, but for now we let it bubble
            # or handle it in the orchestrator.
            raise RuntimeError(f"Groq API error: {e}") from e

        choice = response.choices[0]
        response_msg = choice.message

        tool_calls = []
        if response_msg.tool_calls:
            for tc in response_msg.tool_calls:
                # Groq returns json arguments as a string.
                # Standard OpenAI-like tool calls return arguments as a string representing JSON.
                # Our interface might want dicts or just strings.
                import json

                tool_calls.append(
                    ToolCall(
                        id=tc.id,
                        name=tc.function.name,
                        arguments=json.loads(tc.function.arguments),
                    )
                )

        return LlmResponse(text=response_msg.content, tool_calls=tool_calls)
