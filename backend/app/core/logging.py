"""
QueueWise AI — Structured Logging Configuration

Uses structlog for JSON-formatted structured logging in production
and human-readable colored output in development.
"""
import logging
import sys
import structlog
from app.core.config import settings


def setup_logging() -> None:
    """Configure structured logging based on environment settings."""

    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Shared processors
    shared_processors: list = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.StackInfoRenderer(),
        structlog.processors.TimeStamper(fmt="iso"),
    ]

    if settings.log_format == "json":
        renderer = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stdout),
        cache_logger_on_first_use=True,
    )

    # Also configure standard library logging for third-party libs
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = __name__) -> structlog.BoundLogger:
    """Get a named structured logger."""
    return structlog.get_logger(name)
