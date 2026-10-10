import uuid
import time
import logging
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.responses import JSONResponse

logger = logging.getLogger("campuscue.rag.api")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        start_time = time.perf_counter()

        try:
            response: Response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            response.headers["X-Request-ID"] = request_id
            logger.info(
                "%s %s -> status=%d duration=%.2fms req_id=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                request_id,
            )
            return response
        except RuntimeError as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error("Service error on %s: %s (req_id=%s)", request.url.path, exc, request_id)
            return JSONResponse(
                status_code=503,
                content={
                    "code": "RAG_LLM_UNAVAILABLE",
                    "message": str(exc),
                    "details": [],
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )
        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.exception("Unhandled server error on %s: %s (req_id=%s)", request.url.path, exc, request_id)
            return JSONResponse(
                status_code=500,
                content={
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An internal server error occurred.",
                    "details": [],
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )
