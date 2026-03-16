"""Request logging middleware — adds request_id and logs request start/end."""

from __future__ import annotations

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.logging_config import get_logger

# Paths to skip logging (too noisy / health-check probes)
_SKIP_PATHS: set[str] = {"/health"}

logger = get_logger("request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Generates a short request_id, binds it to structlog context, and
    logs request start / end with timing information."""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        # Generate a short unique id (first 8 chars of uuid4)
        request_id = uuid.uuid4().hex[:8]

        # Bind request_id into structlog context-vars (if structlog is available)
        try:
            import structlog

            structlog.contextvars.clear_contextvars()
            structlog.contextvars.bind_contextvars(request_id=request_id)
        except ImportError:
            pass

        path = request.url.path
        method = request.method
        client_ip = request.client.host if request.client else "unknown"

        skip = path in _SKIP_PATHS

        if not skip:
            logger.info(
                "request_started",
                method=method,
                path=path,
                client_ip=client_ip,
            )

        start = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            if not skip:
                logger.error(
                    "request_failed",
                    method=method,
                    path=path,
                    duration_ms=duration_ms,
                )
            raise

        duration_ms = round((time.perf_counter() - start) * 1000, 2)

        if not skip:
            logger.info(
                "request_finished",
                method=method,
                path=path,
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

        # Always add the header (even for skipped paths) so callers can
        # correlate responses back to logs.
        response.headers["X-Request-ID"] = request_id

        return response
