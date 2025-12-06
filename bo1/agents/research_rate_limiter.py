"""Rate limiter for research API calls (Brave/Tavily).

Implements token bucket algorithm to prevent hitting API rate limits.
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting a specific API.

    Attributes:
        max_requests: Maximum requests per time window
        time_window_seconds: Time window in seconds
        burst_size: Maximum burst size (token bucket capacity)
    """

    max_requests: int
    time_window_seconds: int
    burst_size: int | None = None

    def __post_init__(self) -> None:
        """Set default burst size if not specified."""
        if self.burst_size is None:
            self.burst_size = self.max_requests


# Default rate limit configurations based on API tier
# These are conservative defaults - adjust based on your API plan
RATE_LIMIT_CONFIGS = {
    "brave_free": RateLimitConfig(
        max_requests=1,  # Brave free tier: 1 request per second
        time_window_seconds=1,
        burst_size=1,  # No bursting - strict 1 req/s
    ),
    "brave_basic": RateLimitConfig(
        max_requests=100,  # 100 requests per minute
        time_window_seconds=60,
        burst_size=120,
    ),
    "tavily_free": RateLimitConfig(
        max_requests=5,  # 5 requests per minute (free tier)
        time_window_seconds=60,
        burst_size=8,
    ),
    "tavily_basic": RateLimitConfig(
        max_requests=50,  # 50 requests per minute
        time_window_seconds=60,
        burst_size=60,
    ),
}


class TokenBucketRateLimiter:
    """Token bucket rate limiter for API calls.

    Implements the token bucket algorithm:
    - Tokens are added at a fixed rate (refill_rate)
    - Each API call consumes 1 token
    - If bucket is empty, caller must wait

    Thread-safe using asyncio.Lock.

    Example:
        >>> limiter = TokenBucketRateLimiter("brave_free")
        >>> await limiter.acquire()  # Wait for token if needed
        >>> # Make API call
        >>> limiter.release()  # Not needed for token bucket, kept for compatibility
    """

    def __init__(
        self,
        api_name: Literal["brave_free", "brave_basic", "tavily_free", "tavily_basic"],
        config: RateLimitConfig | None = None,
    ) -> None:
        """Initialize rate limiter.

        Args:
            api_name: Name of API (used to get default config)
            config: Optional custom rate limit configuration
        """
        self.api_name = api_name
        self.config = config or RATE_LIMIT_CONFIGS.get(api_name, RATE_LIMIT_CONFIGS["brave_free"])

        # Token bucket state
        self.tokens = float(self.config.burst_size or self.config.max_requests)
        self.max_tokens = float(self.config.burst_size or self.config.max_requests)
        self.refill_rate = (
            self.config.max_requests / self.config.time_window_seconds
        )  # tokens/second
        self.last_refill = time.monotonic()

        # Lock for thread safety
        self._lock = asyncio.Lock()

        logger.info(
            f"Rate limiter initialized for {api_name}: "
            f"{self.config.max_requests} requests/{self.config.time_window_seconds}s "
            f"(burst: {self.config.burst_size}, refill: {self.refill_rate:.2f} tokens/s)"
        )

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_refill

        # Add tokens based on elapsed time
        new_tokens = elapsed * self.refill_rate
        self.tokens = min(self.max_tokens, self.tokens + new_tokens)
        self.last_refill = now

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens from bucket, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire (default: 1)

        Returns:
            Wait time in seconds (0 if no wait was needed)

        Example:
            >>> wait_time = await limiter.acquire()
            >>> if wait_time > 0:
            ...     logger.info(f"Rate limited: waited {wait_time:.2f}s")
        """
        async with self._lock:
            # Refill tokens based on time passed
            self._refill_tokens()

            # Check if we have enough tokens
            if self.tokens >= tokens:
                self.tokens -= tokens
                return 0.0

            # Calculate wait time needed
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.refill_rate

            logger.debug(
                f"Rate limit: waiting {wait_time:.2f}s for {tokens} tokens "
                f"(current: {self.tokens:.2f}/{self.max_tokens:.2f})"
            )

            # Wait for tokens to refill
            await asyncio.sleep(wait_time)

            # Refill again after waiting
            self._refill_tokens()

            # Consume tokens
            self.tokens -= tokens

            return wait_time

    def release(self) -> None:
        """Release is a no-op for token bucket (kept for compatibility)."""
        pass

    def get_available_tokens(self) -> float:
        """Get current number of available tokens.

        Returns:
            Number of tokens currently in bucket
        """
        # Refill before returning (don't need lock for reading)
        now = time.monotonic()
        elapsed = now - self.last_refill
        new_tokens = elapsed * self.refill_rate
        current_tokens = min(self.max_tokens, self.tokens + new_tokens)
        return current_tokens


# Global rate limiter instances (singleton pattern)
_rate_limiters: dict[str, TokenBucketRateLimiter] = {}


def get_rate_limiter(
    api_name: Literal["brave_free", "brave_basic", "tavily_free", "tavily_basic"],
) -> TokenBucketRateLimiter:
    """Get or create rate limiter for an API.

    Uses singleton pattern to ensure single rate limiter per API.

    Args:
        api_name: Name of API

    Returns:
        Rate limiter instance

    Example:
        >>> limiter = get_rate_limiter("brave_free")
        >>> await limiter.acquire()
    """
    if api_name not in _rate_limiters:
        _rate_limiters[api_name] = TokenBucketRateLimiter(api_name)

    return _rate_limiters[api_name]
