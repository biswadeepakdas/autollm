"""Rate limiting middleware using slowapi with Redis backend."""

from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from fastapi import Request
from fastapi.responses import JSONResponse

from app.config import settings


def _key_func(request: Request) -> str:
    """Key function for rate limiting — use IP address."""
    return get_remote_address(request)


limiter = Limiter(
    key_func=_key_func,
    default_limits=[settings.RATE_LIMIT_DEFAULT] if settings.RATE_LIMIT_ENABLED else [],
    storage_uri=settings.REDIS_URL,
    enabled=settings.RATE_LIMIT_ENABLED,
)


async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    return JSONResponse(
        status_code=429,
        content={
            "error": "rate_limit_exceeded",
            "message": f"Rate limit exceeded: {exc.detail}",
            "retry_after": str(exc.detail),
        },
    )
