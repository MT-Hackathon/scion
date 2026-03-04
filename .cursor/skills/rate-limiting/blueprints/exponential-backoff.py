# BLUEPRINT: exponential-backoff
# STRUCTURAL: retry loop, delay management, Retry-After header honor, max cap enforcement
# ILLUSTRATIVE: RateLimitError → your domain exception; logger → your logging instance

"""Exponential backoff for rate-limited API operations.

Pattern: 1s initial, 2x multiplier, 60s cap, reset on success.
Retry-After from the exception takes precedence over computed delay.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Awaitable, Callable, TypeVar

T = TypeVar("T")
logger = logging.getLogger(__name__)

INITIAL_DELAY: float = 1.0
MAX_DELAY: float = 60.0
MULTIPLIER: float = 2.0
MAX_RETRIES: int = 5


async def with_exponential_backoff(
    operation: Callable[[], Awaitable[T]],
    initial_delay: float = INITIAL_DELAY,
    max_delay: float = MAX_DELAY,
    multiplier: float = MULTIPLIER,
    max_retries: int = MAX_RETRIES,
) -> T:
    """Execute operation with exponential backoff on rate limit.

    Retry-After from the error takes precedence over computed delay.
    Delay resets to initial_delay on success — not accumulated between call sites.
    """
    delay = initial_delay

    for attempt in range(max_retries):
        try:
            return await operation()
        except RateLimitError as err:  # ILLUSTRATIVE: replace with your domain exception
            if attempt == max_retries - 1:
                raise

            wait_time = min(err.retry_after or delay, max_delay)
            logger.warning(
                "Rate limited. Waiting %.1fs before retry %d/%d",
                wait_time,
                attempt + 1,
                max_retries,
            )
            await asyncio.sleep(wait_time)
            delay = min(delay * multiplier, max_delay)

    raise RateLimitError("Max retries exceeded")  # ILLUSTRATIVE
