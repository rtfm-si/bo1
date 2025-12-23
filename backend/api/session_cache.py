"""Session metadata cache with TTL for reducing Redis/PostgreSQL lookups.

Provides an in-memory LRU cache with TTL for session metadata, reducing
database calls during SSE reconnections and repeated requests.

Thread-safe implementation using stdlib only (no cachetools dependency).
"""

import logging
import threading
import time
from collections import OrderedDict
from collections.abc import Callable
from typing import Any, TypeVar

from prometheus_client import Counter

logger = logging.getLogger(__name__)

# Prometheus metrics
session_cache_hits = Counter(
    "session_metadata_cache_hits_total",
    "Total session metadata cache hits",
)
session_cache_misses = Counter(
    "session_metadata_cache_misses_total",
    "Total session metadata cache misses",
)

T = TypeVar("T")


class SessionMetadataCache:
    """Thread-safe LRU cache with TTL for session metadata.

    Uses OrderedDict for LRU eviction and per-entry timestamps for TTL.
    Designed for single-process deployment; multi-process would need Redis.

    Attributes:
        max_size: Maximum number of cached entries (default 1000)
        ttl_seconds: Time-to-live for entries in seconds (default 300)

    Example:
        >>> cache = SessionMetadataCache(max_size=1000, ttl_seconds=300)
        >>> metadata = cache.get_or_load(
        ...     "session-123",
        ...     lambda sid: redis_manager.load_metadata(sid)
        ... )
    """

    def __init__(
        self,
        max_size: int = 1000,
        ttl_seconds: int = 300,
    ) -> None:
        """Initialize cache with size and TTL limits.

        Args:
            max_size: Maximum entries before LRU eviction
            ttl_seconds: Entry expiration time in seconds
        """
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._ttl_seconds = ttl_seconds

    def get(self, session_id: str) -> Any | None:
        """Get cached metadata if present and not expired.

        Args:
            session_id: Session identifier

        Returns:
            Cached metadata or None if missing/expired
        """
        with self._lock:
            if session_id not in self._cache:
                return None

            value, timestamp = self._cache[session_id]

            # Check TTL expiry
            if time.monotonic() - timestamp > self._ttl_seconds:
                del self._cache[session_id]
                return None

            # Move to end for LRU
            self._cache.move_to_end(session_id)
            return value

    def set(self, session_id: str, metadata: Any) -> None:
        """Store metadata in cache.

        Args:
            session_id: Session identifier
            metadata: Session metadata dict
        """
        with self._lock:
            # Remove if exists to update timestamp
            if session_id in self._cache:
                del self._cache[session_id]

            # Evict LRU entries if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)

            # Add with current timestamp
            self._cache[session_id] = (metadata, time.monotonic())

    def invalidate(self, session_id: str) -> bool:
        """Remove entry from cache.

        Args:
            session_id: Session identifier

        Returns:
            True if entry was removed, False if not present
        """
        with self._lock:
            if session_id in self._cache:
                del self._cache[session_id]
                logger.debug(f"Invalidated cache for session {session_id}")
                return True
            return False

    def get_or_load(
        self,
        session_id: str,
        loader_fn: Callable[[str], T],
    ) -> T:
        """Get from cache or load via loader function.

        Thread-safe: if cache miss, calls loader and caches result.
        Loader function receives session_id as argument.

        Args:
            session_id: Session identifier
            loader_fn: Function to load metadata (session_id) -> metadata

        Returns:
            Cached or freshly loaded metadata

        Example:
            >>> metadata = cache.get_or_load(
            ...     session_id,
            ...     lambda sid: redis_manager.load_metadata(sid)
            ... )
        """
        # Try cache first
        cached = self.get(session_id)
        if cached is not None:
            session_cache_hits.inc()
            return cached

        # Cache miss - load and store
        session_cache_misses.inc()
        metadata = loader_fn(session_id)
        if metadata is not None:
            self.set(session_id, metadata)
        return metadata

    def clear(self) -> int:
        """Clear all cached entries.

        Returns:
            Number of entries removed
        """
        with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    def size(self) -> int:
        """Get current cache size.

        Returns:
            Number of cached entries
        """
        with self._lock:
            return len(self._cache)
