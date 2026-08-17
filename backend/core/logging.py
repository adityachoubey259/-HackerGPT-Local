"""Structured logging configuration."""

from __future__ import annotations

import logging
import sys
from typing import Any, cast

import structlog

from backend.core.config import LoggingSettings

SECRET_FIELD_HINTS = ("secret", "token", "password", "api_key", "authorization")


def redact_sensitive_values(
    _logger: logging.Logger,
    _method_name: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    for key in list(event_dict):
        if any(hint in key.lower() for hint in SECRET_FIELD_HINTS):
            event_dict[key] = "[REDACTED]"
    return event_dict


def configure_logging(settings: LoggingSettings) -> None:
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.level),
        force=True,
    )

    processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        redact_sensitive_values,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    processors.append(
        structlog.processors.JSONRenderer()
        if settings.json_logs
        else structlog.dev.ConsoleRenderer()
    )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(getattr(logging, settings.level)),
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    return cast(structlog.stdlib.BoundLogger, structlog.get_logger(name))
