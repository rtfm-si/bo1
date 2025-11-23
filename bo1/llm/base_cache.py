"""Base cache class for all cache implementations.

This module provides a base class that eliminates duplication across:
- LLMResponseCache (deterministic key-based caching)
- PersonaSelectionCache (semantic similarity-based caching)
- ResearcherAgent cache (semantic similarity with PostgreSQL)

All caches share:
- Hit/miss tracking
- Statistics calculation
- Enable/disable flag
- TTL configuration
- get_stats() method
"""

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BaseCache[K, V](ABC):
    """Base class for all cache implementations with hit/miss tracking.

    Provides:
    - Hit/miss statistics tracking
    - Statistics calculation (hit_rate, counts)
    - Common configuration (enabled flag, TTL)
    - Abstract methods for get/set operations

    Subclasses must implement:
    - get(key: K) -> V | None
    - set(key: K, value: V) -> None

    Examples:
        >>> class MyCache(BaseCache[str, dict]):
        ...     async def get(self, key: str) -> dict | None:
        ...         if not self.enabled:
        ...             return None
        ...         cached = self.redis.get(key)
        ...         if cached:
        ...             self._record_hit()
        ...             return json.loads(cached)
        ...         self._record_miss()
        ...         return None
        ...
        ...     async def set(self, key: str, value: dict) -> None:
        ...         if not self.enabled:
        ...             return
        ...         self.redis.setex(key, self.ttl_seconds, json.dumps(value))
    """

    def __init__(
        self,
        redis_manager: Any,
        enabled: bool,
        ttl_seconds: int,
    ) -> None:
        """Initialize base cache.

        Args:
            redis_manager: RedisManager instance for cache storage
            enabled: Whether caching is enabled
            ttl_seconds: Cache entry TTL in seconds
        """
        self.redis = redis_manager.redis
        self.enabled = enabled
        self.ttl_seconds = ttl_seconds
        self._hits = 0
        self._misses = 0

    @abstractmethod
    async def get(self, key: K) -> V | None:
        """Get cached value.

        Implementations MUST call self._record_hit() or self._record_miss()
        to maintain statistics accuracy.

        Args:
            key: Cache key

        Returns:
            Cached value if found, None otherwise
        """
        pass

    @abstractmethod
    async def set(self, key: K, value: V) -> None:
        """Set cached value with TTL.

        Args:
            key: Cache key
            value: Value to cache
        """
        pass

    def _record_hit(self) -> None:
        """Record cache hit (internal use only).

        Subclasses should call this when get() finds a cached value.
        """
        self._hits += 1

    def _record_miss(self) -> None:
        """Record cache miss (internal use only).

        Subclasses should call this when get() doesn't find a cached value.
        """
        self._misses += 1

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as decimal (0.0-1.0), or 0.0 if no requests yet

        Examples:
            >>> cache.get_stats()["hit_rate"]  # 0.65 = 65% hit rate
        """
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics.

        Returns:
            Dictionary with cache metrics:
            - enabled: Whether caching is enabled
            - hits: Number of cache hits
            - misses: Number of cache misses
            - hit_rate: Cache hit rate (0.0-1.0)
            - ttl_seconds: Cache entry TTL

        Examples:
            >>> stats = cache.get_stats()
            >>> print(f"Hit rate: {stats['hit_rate']:.1%}")
            Hit rate: 65.0%
        """
        return {
            "enabled": self.enabled,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "ttl_seconds": self.ttl_seconds,
        }

    def reset_stats(self) -> None:
        """Reset hit/miss statistics to zero.

        Useful for testing or when starting a new measurement period.
        """
        self._hits = 0
        self._misses = 0
