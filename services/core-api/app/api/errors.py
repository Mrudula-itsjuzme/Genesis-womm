"""The error envelope and exception handlers (spine AD-19).

Every non-2xx response is ``{code, message, details, request_id}``. Unhandled errors
return ``INTERNAL_ERROR`` with no stack, message or request body.
"""

from collections.abc import Sequence
from typing import Any, NoReturn, cast

import structlog
from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.middleware import REQUEST_ID_HEADER
from app.domain.enums import ErrorCode
from app.schemas.common import ErrorEnvelope

log = structlog.get_logger("errors")

STATUS_BY_CODE: dict[ErrorCode, int] = {
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.METHOD_NOT_ALLOWED: 405,
    ErrorCode.CONFLICT_DETECTED: 409,
    ErrorCode.STALE_REVISION: 409,
    ErrorCode.IDEMPOTENCY_MISMATCH: 422,
    ErrorCode.INVALID_TRANSITION: 409,
    ErrorCode.DUPLICATE_OVERRIDE: 409,
    ErrorCode.EVIDENCE_REQUIRED: 422,
    ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
    ErrorCode.AGENT_OUTPUT_INVALID: 502,
    ErrorCode.NOT_IMPLEMENTED: 501,
    ErrorCode.INTERNAL_ERROR: 500,
}

_CODE_BY_HTTP_STATUS: dict[int, ErrorCode] = {
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    405: ErrorCode.METHOD_NOT_ALLOWED,
}


class ApiError(Exception):
    def __init__(
        self,
        code: ErrorCode,
        message: str,
        details: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = list(details or [])

    @property
    def status_code(self) -> int:
        return STATUS_BY_CODE[self.code]


def not_implemented(feature: str) -> NoReturn:
    """Raised by routes whose contract exists but whose implementation has not landed."""
    raise ApiError(ErrorCode.NOT_IMPLEMENTED, f"{feature} is not implemented yet.")


def error_responses(*codes: ErrorCode) -> dict[int | str, dict[str, Any]]:
    """OpenAPI ``responses`` entries pointing at the shared envelope schema."""
    responses: dict[int | str, dict[str, Any]] = {}
    for code in codes:
        status = STATUS_BY_CODE[code]
        entry = responses.setdefault(status, {"model": ErrorEnvelope, "description": ""})
        names = [part for part in (entry["description"], code.value) if part]
        entry["description"] = " / ".join(names)
    return responses


def stub_errors(*extra: ErrorCode) -> dict[int | str, dict[str, Any]]:
    """Documented errors for an authenticated route that is still a typed stub."""
    return error_responses(
        ErrorCode.UNAUTHENTICATED,
        ErrorCode.FORBIDDEN,
        ErrorCode.VALIDATION_ERROR,
        ErrorCode.NOT_IMPLEMENTED,
        *extra,
    )


# Marks a route whose contract is final but whose behavior has not landed yet.
STUB_OPENAPI: dict[str, Any] = {"x-implementation-status": "stub"}


def _request_id(request: Request) -> str:
    return str(getattr(request.state, "request_id", "unknown"))


def error_response(
    request: Request,
    code: ErrorCode,
    message: str,
    details: Sequence[dict[str, Any]] = (),
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    request_id = _request_id(request)
    envelope = ErrorEnvelope(
        code=code,
        message=message,
        details=list(details),
        request_id=request_id,
    )
    response_headers = {REQUEST_ID_HEADER: request_id, **(headers or {})}
    return JSONResponse(
        status_code=STATUS_BY_CODE[code],
        content=jsonable_encoder(envelope.model_dump(mode="json")),
        headers=response_headers,
    )


async def _handle_api_error(request: Request, exc: Exception) -> JSONResponse:
    error = cast(ApiError, exc)
    return error_response(request, error.code, error.message, error.details)


async def _handle_validation_error(request: Request, exc: Exception) -> JSONResponse:
    errors = cast(RequestValidationError, exc).errors()
    # Keep only where/what/kind. `input` and `ctx` can echo user data back.
    details = [
        {"loc": list(e["loc"]), "msg": str(e["msg"]), "type": str(e["type"])} for e in errors
    ]
    return error_response(
        request, ErrorCode.VALIDATION_ERROR, "Request validation failed.", details
    )


async def _handle_http_exception(request: Request, exc: Exception) -> JSONResponse:
    http_exc = cast(StarletteHTTPException, exc)
    code = _CODE_BY_HTTP_STATUS.get(http_exc.status_code, ErrorCode.VALIDATION_ERROR)
    headers = {k: v for k, v in (http_exc.headers or {}).items() if k.lower() == "allow"}
    message = str(http_exc.detail) if http_exc.detail else code.value
    response = error_response(request, code, message, headers=headers)
    if code is ErrorCode.VALIDATION_ERROR:
        response.status_code = http_exc.status_code
    return response


async def _handle_unexpected(request: Request, exc: Exception) -> JSONResponse:
    log.error("unhandled_exception", request_id=_request_id(request), exc_info=exc)
    return error_response(request, ErrorCode.INTERNAL_ERROR, "An internal error occurred.")


def install_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _handle_api_error)
    app.add_exception_handler(RequestValidationError, _handle_validation_error)
    app.add_exception_handler(StarletteHTTPException, _handle_http_exception)
    app.add_exception_handler(Exception, _handle_unexpected)
