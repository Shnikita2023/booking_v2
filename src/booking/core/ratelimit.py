"""Simple in-memory rate limiter middleware."""

import time
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Global registry for test reset
_instances: list["RateLimitMiddleware"] = []


def reset_all_rate_limiters() -> None:
    """Reset all rate limiter instances (for tests)."""
    for inst in _instances:
        inst.reset()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Per-IP rate limiter with sliding window.

    Args:
        paths: URL path prefixes to protect.
        max_requests: Maximum requests per window.
        window_seconds: Window duration in seconds.
    """

    def __init__(
        self,
        app: Any,
        paths: list[str] | None = None,
        max_requests: int = 10,
        window_seconds: int = 60,
    ) -> None:
        super().__init__(app)
        self._paths = paths or ["/api/v1/auth/"]
        self._max_requests = max_requests
        self._window = window_seconds
        self._requests: dict[str, list[float]] = defaultdict(list)
        _instances.append(self)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _is_rate_limited(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self._window
        self._requests[client_ip] = [
            t for t in self._requests[client_ip] if t > cutoff
        ]
        if len(self._requests[client_ip]) >= self._max_requests:
            return True
        self._requests[client_ip].append(now)
        return False

    async def dispatch(
        self, request: Request, call_next: Callable[[Request], Any]
    ) -> Response:
        path = request.url.path
        if not any(path.startswith(p) for p in self._paths):
            result: Response = await call_next(request)
            return result

        client_ip = self._get_client_ip(request)
        if self._is_rate_limited(client_ip):
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again later."},
            )
        result = await call_next(request)
        return result

    def reset(self) -> None:
        """Clear all rate limit counters (for tests)."""
        self._requests.clear()
