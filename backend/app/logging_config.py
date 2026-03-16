"""Structured logging configuration using structlog.

Call ``setup_logging()`` once at application startup (before creating the
FastAPI app).  Use ``get_logger(__name__)`` in modules to obtain a logger.

If *structlog* is not installed the helpers fall back to stdlib logging so
the rest of the application keeps working.
"""

from __future__ import annotations

import logging
import sys

try:
    import structlog

    _HAS_STRUCTLOG = True
except ImportError:  # pragma: no cover
    _HAS_STRUCTLOG = False


def setup_logging(*, json_output: bool | None = None, log_level: str = "INFO") -> None:
    """Configure structlog + stdlib logging.

    Parameters
    ----------
    json_output:
        If *True* render JSON lines (good for production log aggregators).
        If *False* render coloured console output (nice for local dev).
        When *None* (the default) the value is derived from the
        ``ENVIRONMENT`` setting: ``"production"`` → JSON, else console.
    log_level:
        Root log level name (e.g. ``"DEBUG"``, ``"INFO"``).
    """

    if not _HAS_STRUCTLOG:
        # Fallback: just configure stdlib
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            stream=sys.stdout,
        )
        return

    if json_output is None:
        from app.config import settings

        json_output = settings.ENVIRONMENT == "production"

    # Shared processors used by *both* structlog and stdlib pre-chain
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        renderer: structlog.types.Processor = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer()

    # Configure structlog
    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Route stdlib logging through structlog's formatter so *all* log
    # output (third-party libs included) gets the same treatment.
    formatter = structlog.stdlib.ProcessorFormatter(
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
        foreign_pre_chain=shared_processors,
    )

    root_logger = logging.getLogger()
    root_logger.handlers.clear()
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # Quieten noisy third-party loggers
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str | None = None):
    """Return a logger.

    When structlog is available this returns a ``structlog.stdlib.BoundLogger``
    that participates in context-var binding (request_id, etc.).
    Otherwise it returns a plain ``logging.Logger``.
    """

    if _HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return logging.getLogger(name)
