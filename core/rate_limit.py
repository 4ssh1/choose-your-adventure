from collections import defaultdict, deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic
from typing import Deque

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response


@dataclass(frozen=True)
class RateLimitConfig:
    requests: int
    window_seconds: int


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Simple in-memory sliding-window limiter keyed by client IP."""

    def __init__(self, app, config: RateLimitConfig):
        super().__init__(app)
        self.config = config
        self._hits: dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    async def dispatch(self, request: Request, call_next) -> Response:
        if self.config.requests <= 0 or self.config.window_seconds <= 0:
            return await call_next(request)

        client_ip = self._resolve_client_ip(request)
        now = monotonic()

        with self._lock:
            bucket = self._hits[client_ip]
            cutoff = now - self.config.window_seconds

            while bucket and bucket[0] <= cutoff:
                bucket.popleft()

            if len(bucket) >= self.config.requests:
                retry_after = max(1, int(bucket[0] + self.config.window_seconds - now))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded. Try again later."},
                    headers={
                        "Retry-After": str(retry_after),
                        "X-RateLimit-Limit": str(self.config.requests),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(retry_after),
                    },
                )

            bucket.append(now)
            remaining = max(0, self.config.requests - len(bucket))
            reset_in = max(0, int(bucket[0] + self.config.window_seconds - now)) if bucket else 0

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(self.config.requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_in)
        return response

    @staticmethod
    def _resolve_client_ip(request: Request) -> str:
        forwarded_for = request.headers.get("x-forwarded-for")
        if forwarded_for:
            first_ip = forwarded_for.split(",", 1)[0].strip()
            if first_ip:
                return first_ip

        if request.client and request.client.host:
            return request.client.host

        return "unknown"
