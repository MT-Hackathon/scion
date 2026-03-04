# BLUEPRINT: circuit-breaker
# STRUCTURAL: CLOSED/OPEN/HALF_OPEN state machine, failure/success counters, cooldown timer
# ILLUSTRATIVE: RateLimitError → your rate limit exception; CircuitBreakerOpenError → your open-circuit exception

"""Circuit breaker for rate limit failures.

Thresholds (from ANCHORSKILL-RATE-LIMITING):
  - 3 consecutive failures  → OPEN
  - 60s cooldown            → HALF_OPEN
  - 1 success in HALF_OPEN  → CLOSED
  - Any failure in HALF_OPEN → OPEN (immediately)
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Circuit breaker for rate limit failures."""

    def __init__(
        self,
        failure_threshold: int = 3,   # STRUCTURAL: tune per external API SLA
        cooldown_seconds: int = 60,
        success_threshold: int = 1,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self.success_threshold = success_threshold

        self.state = CircuitState.CLOSED
        self.failures = 0
        self.successes = 0
        self.last_failure_time: datetime | None = None

    async def call(self, operation: Callable[[], Awaitable[T]]) -> T:
        """Execute operation through the circuit breaker guard."""
        if self.state == CircuitState.OPEN:
            cooldown_elapsed = (
                self.last_failure_time is not None
                and datetime.now(timezone.utc) - self.last_failure_time
                > timedelta(seconds=self.cooldown_seconds)
            )
            if not cooldown_elapsed:
                raise CircuitBreakerOpenError("Circuit breaker is open")  # ILLUSTRATIVE
            logger.info("Circuit breaker entering half-open state")
            self.state = CircuitState.HALF_OPEN

        try:
            result = await operation()
            self._on_success()
            return result
        except RateLimitError:  # ILLUSTRATIVE: replace with your domain exception
            self._on_failure()
            raise

    def _on_success(self) -> None:
        self.failures = 0
        if self.state == CircuitState.HALF_OPEN:
            self.successes += 1
            if self.successes >= self.success_threshold:
                logger.info("Circuit breaker closed after recovery")
                self.state = CircuitState.CLOSED
                self.successes = 0

    def _on_failure(self) -> None:
        self.failures += 1
        self.last_failure_time = datetime.now(timezone.utc)
        self.successes = 0

        if self.state == CircuitState.HALF_OPEN:
            logger.warning("Circuit breaker reopened after failed recovery")
            self.state = CircuitState.OPEN
        elif self.failures >= self.failure_threshold:
            logger.warning("Circuit breaker opened after %d failures", self.failures)
            self.state = CircuitState.OPEN
