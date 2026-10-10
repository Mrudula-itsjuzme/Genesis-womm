"""Structured JSON logging (spine AD-19).

Logs never carry request bodies, tokens, keys, student-private fields or document text.
The redaction processor is a backstop; callers should not log those values at all.
"""

import logging
import sys
from typing import Any

import structlog
from structlog.typing import EventDict, WrappedLogger

_SENSITIVE_KEYS = frozenset(
    {
        "authorization",
        "cookie",
        "set-cookie",
        "x-internal-key",
        "password",
        "token",
        "api_key",
        "secret",
        "body",
    }
)


def redact_sensitive_keys(_logger: WrappedLogger | None, _method: str, event: EventDict) -> Any:
    for key in list(event):
        if key.lower() in _SENSITIVE_KEYS:
            event[key] = "[redacted]"
    return event


def configure_logging(level: str) -> None:
    numeric_level = logging.getLevelNamesMapping().get(level.upper(), logging.INFO)
    logging.basicConfig(format="%(message)s", stream=sys.stdout, level=numeric_level, force=True)
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            redact_sensitive_keys,
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=False,
    )
