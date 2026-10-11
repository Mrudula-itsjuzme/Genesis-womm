import json
from typing import Any

import groq
import structlog
from groq import AsyncGroq

from app.ports.errors import ContractViolationError, DependencyUnavailableError
from app.ports.llm import LlmPort, LlmResponse, ToolCall
from app.schemas.chat import ChatMessage

log = structlog.get_logger("providers.groq")


def _is_malformed_tool_call(error: groq.BadRequestError) -> bool:
    """Groq answers a tool call the model wrote badly with a 400 coded ``tool_use_failed``."""
    body = error.body
    detail = body.get("error") if isinstance(body, dict) else None
    return isinstance(detail, dict) and detail.get("code") == "tool_use_failed"


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    try:
        arguments = json.loads(raw or "{}")
    except json.JSONDecodeError as error:
        raise ContractViolationError("the model wrote tool arguments that are not JSON") from error
    if not isinstance(arguments, dict):
        raise ContractViolationError("the model wrote tool arguments that are not an object")
    return arguments


class GroqProvider(LlmPort):
    def __init__(self, api_key: str, model: str, *, client: Any = None) -> None:
        self._client = client if client is not None else AsyncGroq(api_key=api_key)
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

        response = await self._create(api_messages, kwargs)
        response_msg = response.choices[0].message

        tool_calls = [
            ToolCall(
                id=tc.id,
                name=tc.function.name,
                arguments=_parse_arguments(tc.function.arguments),
            )
            for tc in (response_msg.tool_calls or [])
        ]
        return LlmResponse(text=response_msg.content, tool_calls=tool_calls)

    async def _create(self, api_messages: list[Any], kwargs: dict[str, Any]) -> Any:
        """One completion. A malformed tool call is retried once; nothing else is."""
        for attempt in (1, 2):
            try:
                return await self._client.chat.completions.create(
                    messages=api_messages, model=self._model, **kwargs
                )
            except groq.BadRequestError as error:
                if not _is_malformed_tool_call(error):
                    self._log_failure(error)
                    raise DependencyUnavailableError("model") from error
                if attempt == 2:
                    raise ContractViolationError("the model wrote an invalid tool call") from error
            except groq.APIError as error:
                self._log_failure(error)
                raise DependencyUnavailableError("model") from error
        raise AssertionError("unreachable")  # pragma: no cover

    @staticmethod
    def _log_failure(error: groq.APIError) -> None:
        # The kind and status only: the provider's text can name the account or the key.
        log.warning(
            "model_request_failed",
            kind=type(error).__name__,
            status=getattr(error, "status_code", None),
        )
