"""Database pool graceful degradation manager.

Provides request queuing and load shedding when DB pool is exhausted:
- Queue requests when pool utilization > 90%
- Shed load (reject writes) when utilization > 95%
- Track degradation metrics for observability
"""

import asyncio
import logging
import random
import time
from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from threading import Lock

from bo1.constants import PoolDegradationConfig

logger = logging.getLogger(__name__)


class PoolExhaustionError(Exception):
    """Raised when pool is exhausted and queue timeout exceeded."""

    def __init__(  # noqa: D107
        self,
        message: str = "Database pool exhausted",
        queue_depth: int = 0,
        wait_estimate: float = 0.0,
    ) -> None:
        super().__init__(message)
        self.queue_depth = queue_depth
        self.wait_estimate = wait_estimate


@dataclass
class DegradationStats:
    """Pool degradation statistics."""

    is_degraded: bool = False
    should_shed_load: bool = False
    pool_utilization_pct: float = 0.0
    queue_depth: int = 0
    requests_queued_total: int = 0
    requests_shed_total: int = 0
    queue_timeouts_total: int = 0
    last_degradation_start: float | None = None
    degradation_duration_seconds: float = 0.0


class PoolDegradationManager:
    """Manages graceful degradation when DB pool is exhausted.

    Thread-safe manager that:
    - Monitors pool utilization
    - Queues requests when pool is near exhaustion
    - Sheds load (rejects writes) when severely exhausted
    - Tracks metrics for observability

    Usage:
        manager = get_degradation_manager()
        if manager.should_shed_load():
            raise_pool_exhausted()

        with manager.queued_request():
            # do database work
    """

    def __init__(self) -> None:  # noqa: D107
        self._lock = Lock()
        self._queue_semaphore = asyncio.Semaphore(PoolDegradationConfig.QUEUE_MAX_SIZE)
        self._stats = DegradationStats()
        self._current_queue_depth = 0

    def update_pool_state(
        self,
        used_connections: int,
        free_connections: int,
        max_connections: int,
    ) -> None:
        """Update pool state from health check.

        Args:
            used_connections: Connections currently in use
            free_connections: Connections available
            max_connections: Max pool size
        """
        _total = used_connections + free_connections  # noqa: F841 - reserved for future metrics
        utilization = (used_connections / max_connections * 100) if max_connections > 0 else 0.0

        with self._lock:
            was_degraded = self._stats.is_degraded
            self._stats.pool_utilization_pct = utilization
            self._stats.is_degraded = utilization >= PoolDegradationConfig.DEGRADATION_THRESHOLD_PCT
            self._stats.should_shed_load = (
                utilization >= PoolDegradationConfig.SHED_LOAD_THRESHOLD_PCT
            )

            # Track degradation duration
            if self._stats.is_degraded and not was_degraded:
                self._stats.last_degradation_start = time.monotonic()
                logger.warning(f"Pool entering degradation mode at {utilization:.1f}% utilization")
            elif not self._stats.is_degraded and was_degraded:
                if self._stats.last_degradation_start:
                    duration = time.monotonic() - self._stats.last_degradation_start
                    self._stats.degradation_duration_seconds += duration
                    logger.info(f"Pool exiting degradation mode after {duration:.1f}s")
                self._stats.last_degradation_start = None

    def is_degraded(self) -> bool:
        """Check if pool is in degradation mode.

        Returns:
            True if pool utilization >= 90%
        """
        with self._lock:
            return self._stats.is_degraded

    def should_shed_load(self) -> bool:
        """Check if writes should be rejected.

        Returns:
            True if pool utilization >= 95%
        """
        with self._lock:
            return self._stats.should_shed_load

    def get_stats(self) -> DegradationStats:
        """Get current degradation statistics.

        Returns:
            Copy of current stats
        """
        with self._lock:
            stats = DegradationStats(
                is_degraded=self._stats.is_degraded,
                should_shed_load=self._stats.should_shed_load,
                pool_utilization_pct=self._stats.pool_utilization_pct,
                queue_depth=self._current_queue_depth,
                requests_queued_total=self._stats.requests_queued_total,
                requests_shed_total=self._stats.requests_shed_total,
                queue_timeouts_total=self._stats.queue_timeouts_total,
                last_degradation_start=self._stats.last_degradation_start,
                degradation_duration_seconds=self._stats.degradation_duration_seconds,
            )
            return stats

    def get_retry_after(self) -> int:
        """Get Retry-After header value with jitter.

        Returns:
            Seconds to wait before retry (with random jitter)
        """
        base = PoolDegradationConfig.RETRY_AFTER_BASE_SECONDS
        jitter = random.randint(0, PoolDegradationConfig.RETRY_AFTER_JITTER_SECONDS)  # noqa: S311
        return base + jitter

    def record_shed_load(self) -> None:
        """Record a load shedding event."""
        with self._lock:
            self._stats.requests_shed_total += 1

    def record_queue_timeout(self) -> None:
        """Record a queue timeout event."""
        with self._lock:
            self._stats.queue_timeouts_total += 1

    @contextmanager
    def queued_request(self) -> Generator[None, None, None]:
        """Context manager for queued requests during degradation.

        Increments queue depth while request is pending, tracks metrics.

        Yields:
            None when request can proceed

        Raises:
            PoolExhaustionError: If queue is full
        """
        with self._lock:
            if self._current_queue_depth >= PoolDegradationConfig.QUEUE_MAX_SIZE:
                raise PoolExhaustionError(
                    message="Degradation queue full",
                    queue_depth=self._current_queue_depth,
                    wait_estimate=PoolDegradationConfig.QUEUE_TIMEOUT_SECONDS,
                )
            self._current_queue_depth += 1
            self._stats.requests_queued_total += 1

        try:
            yield
        finally:
            with self._lock:
                self._current_queue_depth -= 1


# Global manager instance
_degradation_manager: PoolDegradationManager | None = None


def get_degradation_manager() -> PoolDegradationManager:
    """Get or create the global degradation manager.

    Returns:
        PoolDegradationManager instance
    """
    global _degradation_manager
    if _degradation_manager is None:
        _degradation_manager = PoolDegradationManager()
    return _degradation_manager


def reset_degradation_manager() -> None:
    """Reset the global degradation manager (for testing)."""
    global _degradation_manager
    _degradation_manager = None
