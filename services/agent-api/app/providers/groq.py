import asyncio
import json
from collections.abc import Awaitable, Callable
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


def _retry_after(error: groq.RateLimitError) -> float | None:
    """How long Groq says to wait, if it said so in a way we can read."""
    try:
        seconds = float(error.response.headers.get("retry-after", ""))
    except ValueError:
        return None
    return seconds if seconds >= 0 else None


def _parse_arguments(raw: str | None) -> dict[str, Any]:
    try:
        arguments = json.loads(raw or "{}")
    except json.JSONDecodeError as error:
        raise ContractViolationError("the model wrote tool arguments that are not JSON") from error
    if not isinstance(arguments, dict):
        raise ContractViolationError("the model wrote tool arguments that are not an object")
    return arguments


def make_client(api_key: str, *, timeout_s: float) -> AsyncGroq:
    """No silent retries: the SDK would back off for longer than a turn is allowed to take."""
    return AsyncGroq(api_key=api_key, max_retries=0, timeout=timeout_s)


class GroqProvider(LlmPort):
    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        fallback_model: str | None = None,
        timeout_s: float = 12.0,
        reasoning_effort: str = "low",
        max_completion_tokens: int = 1024,
        rate_limit_wait_s: float = 5.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        client: Any = None,
    ) -> None:
        self._client = client if client is not None else make_client(api_key, timeout_s=timeout_s)
        self._model = model
        self._fallback_model = fallback_model or None
        self._reasoning_effort = reasoning_effort
        self._max_completion_tokens = max_completion_tokens
        self._rate_limit_wait_s = rate_limit_wait_s
        self._sleep = sleep

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

    def _options(self, model: str) -> dict[str, Any]:
        """Per-call limits on what the model may spend: the minute budget is small, and the
        reasoning models spend most of it thinking."""
        options: dict[str, Any] = {"max_completion_tokens": self._max_completion_tokens}
        if self._reasoning_effort and model.startswith("openai/gpt-oss"):
            options["reasoning_effort"] = self._reasoning_effort
        return options

    async def _create(self, api_messages: list[Any], kwargs: dict[str, Any]) -> Any:
        """One completion. A malformed tool call is retried once; a rate limit is waited out once
        when Groq says it is short and otherwise moves to the fallback model once. Nothing else
        is retried."""
        model = self._model
        retried_tool_call = waited = fell_back = False
        while True:
            try:
                response = await self._client.chat.completions.create(
                    messages=api_messages, model=model, **self._options(model), **kwargs
                )
                self._log_usage(model, response)
                return response
            except groq.BadRequestError as error:
                if not _is_malformed_tool_call(error):
                    self._log_failure(error)
                    raise DependencyUnavailableError("model") from error
                if retried_tool_call:
                    raise ContractViolationError("the model wrote an invalid tool call") from error
                retried_tool_call = True
            except groq.RateLimitError as error:
                self._log_failure(error)
                wait = _retry_after(error)
                if not waited and wait is not None and wait <= self._rate_limit_wait_s:
                    waited = True
                    await self._sleep(wait)
                elif self._fallback_model is None or fell_back:
                    raise DependencyUnavailableError("model", "busy") from error
                else:
                    fell_back, model = True, self._fallback_model
            except groq.APIError as error:
                self._log_failure(error)
                raise DependencyUnavailableError("model") from error

    @staticmethod
    def _log_usage(model: str, response: Any) -> None:
        usage = getattr(response, "usage", None)
        if usage is not None:
            log.info(
                "model_usage",
                model=model,
                prompt_tokens=getattr(usage, "prompt_tokens", None),
                completion_tokens=getattr(usage, "completion_tokens", None),
            )

    @staticmethod
    def _log_failure(error: groq.APIError) -> None:
        # The kind and status only: the provider's text can name the account or the key.
        log.warning(
            "model_request_failed",
            kind=type(error).__name__,
            status=getattr(error, "status_code", None),
        )
