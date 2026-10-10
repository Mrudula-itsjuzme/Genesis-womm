"""Request identity and the structured access log (spine AD-19).

A pure ASGI middleware, not ``BaseHTTPMiddleware``, so it adds no body buffering and
sees the status of responses produced by exception handlers.
"""

import re
import time
import uuid
from typing import Any

import structlog
from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,128}")

log = structlog.get_logger("access")


def _inbound_request_id(scope: Scope) -> str | None:
    wanted = REQUEST_ID_HEADER.lower().encode()
    for name, value in scope["headers"]:
        if name == wanted:
            candidate = value.decode("latin-1")
            return candidate if _VALID_REQUEST_ID.fullmatch(candidate) else None
    return None


class RequestIdMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _inbound_request_id(scope) or uuid.uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        outcome: dict[str, Any] = {"status": 500}
        started = time.perf_counter()

        async def send_with_request_id(message: Message) -> None:
            if message["type"] == "http.response.start":
                outcome["status"] = message["status"]
                MutableHeaders(scope=message)[REQUEST_ID_HEADER] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        finally:
            route = scope.get("route")
            log.info(
                "request",
                request_id=request_id,
                method=scope["method"],
                route=getattr(route, "path", "unmatched"),
                status=outcome["status"],
                latency_ms=round((time.perf_counter() - started) * 1000, 3),
                actor_id=None,
            )
