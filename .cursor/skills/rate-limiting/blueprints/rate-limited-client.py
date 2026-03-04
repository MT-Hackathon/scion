# BLUEPRINT: rate-limited-client
# STRUCTURAL: header parsing, rate-limit detection, client wiring circuit-breaker + backoff
# ILLUSTRATIVE: base_url, endpoint path, http_client → your HTTP library

"""Full integration: rate-limited API client combining circuit breaker and exponential backoff.

Depends on:
  - circuit-breaker.py  (CircuitBreaker, CircuitBreakerOpenError)
  - exponential-backoff.py  (with_exponential_backoff, RateLimitError)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


def parse_rate_limit_headers(headers: dict[str, str]) -> dict[str, int]:
    """Extract rate limit state from response headers.

    Returns safe zero defaults when headers are absent — never raises on missing keys.
    """
    return {
        "limit": int(headers.get("X-RateLimit-Limit", 0)),
        "remaining": int(headers.get("X-RateLimit-Remaining", 0)),
        "reset": int(headers.get("X-RateLimit-Reset", 0)),
        "retry_after": int(headers.get("Retry-After", 0)),
    }


def detect_rate_limit(status_code: int, headers: dict[str, str], body: dict[str, Any]) -> bool:
    """Return True when a response signals rate limiting.

    Detection order (defense in depth):
      429 (primary) → 503 + Retry-After (secondary) → 403 + quota body (tertiary).
    """
    if status_code == 429:
        return True
    if status_code == 503 and "Retry-After" in headers:
        return True
    if status_code == 403:
        message = body.get("message", "").lower()
        if any(kw in message for kw in ("quota", "rate limit", "too many requests")):
            return True
    return False


class RateLimitedApiClient:
    """API client with circuit breaker and exponential backoff for rate limits."""

    def __init__(self, base_url: str) -> None:
        self.base_url = base_url
        self.circuit_breaker = CircuitBreaker()  # ILLUSTRATIVE: from circuit-breaker.py

    async def get(self, endpoint: str) -> dict[str, Any]:
        """GET with proactive throttle logging, detection, and full retry chain."""

        async def operation() -> dict[str, Any]:
            url = f"{self.base_url}{endpoint}"  # ILLUSTRATIVE
            response = await http_client.get(url)  # ILLUSTRATIVE: your HTTP client

            rate_info = parse_rate_limit_headers(response.headers)
            logger.info(
                "Rate limit: %d/%d remaining", rate_info["remaining"], rate_info["limit"]
            )

            if detect_rate_limit(response.status_code, response.headers, response.json()):
                retry_after = rate_info["retry_after"] or 60
                raise RateLimitError("Rate limited", retry_after=retry_after)  # ILLUSTRATIVE

            return response.json()  # ILLUSTRATIVE

        return await self.circuit_breaker.call(
            lambda: with_exponential_backoff(operation)  # ILLUSTRATIVE: from exponential-backoff.py
        )
