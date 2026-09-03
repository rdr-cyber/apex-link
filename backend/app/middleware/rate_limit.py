"""In-memory rate limiter for authentication endpoints.

For production deployment with multiple backend instances,
replace with Redis-backed limiter (e.g., fastapi-limiter with Redis).
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException, status


class InMemoryRateLimiter:
    """Simple sliding-window rate limiter using in-memory storage.

    Usage:
        limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
        await limiter.check(request)
    """

    def __init__(self, max_requests: int = 5, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # Store: {key: [timestamp, ...]}
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_key(self, request: Request) -> str:
        """Generate a client identifier from request."""
        # Use X-Forwarded-For if behind proxy, else direct IP
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip = forwarded.split(",")[0].strip()
        else:
            ip = request.client.host if request.client else "unknown"
        return f"{ip}:{request.url.path}"

    def _cleanup(self, key: str, now: float) -> None:
        """Remove expired entries."""
        cutoff = now - self.window_seconds
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > cutoff
        ]

    async def check(self, request: Request) -> None:
        """Check rate limit. Raises HTTPException if exceeded."""
        now = time.time()
        key = self._get_client_key(request)

        self._cleanup(key, now)

        if len(self._requests[key]) >= self.max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )

        self._requests[key].append(now)


# Global instance — configured for login endpoint
login_rate_limiter = InMemoryRateLimiter(max_requests=5, window_seconds=60)
