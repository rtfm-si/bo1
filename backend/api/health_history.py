"""Health check history storage for debugging intermittent issues.

Stores the last N health check results with timestamps in a thread-safe
circular buffer for observability and debugging purposes.
"""

import threading
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

# Singleton instance
_health_history: "HealthCheckHistory | None" = None
_lock = threading.Lock()


@dataclass
class HealthCheckRecord:
    """Single health check result with timestamp.

    Attributes:
        timestamp: When the health check was performed (UTC)
        status: Overall health status (healthy/degraded/unhealthy)
        components: Per-component health status dict
        latency_ms: Total health check latency in milliseconds
    """

    timestamp: datetime
    status: str
    components: dict[str, Any] = field(default_factory=dict)
    latency_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to JSON-serializable dict."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "status": self.status,
            "components": self.components,
            "latency_ms": round(self.latency_ms, 2),
        }


class HealthCheckHistory:
    """Thread-safe circular buffer for health check results.

    Stores the last N health check results for debugging intermittent
    health issues. Uses a deque with maxlen for automatic eviction.

    Attributes:
        max_size: Maximum number of records to store (default 5)
    """

    def __init__(self, max_size: int = 5) -> None:
        """Initialize the health check history buffer.

        Args:
            max_size: Maximum number of records to retain
        """
        self._records: deque[HealthCheckRecord] = deque(maxlen=max_size)
        self._lock = threading.Lock()
        self._max_size = max_size

    def record(self, result: HealthCheckRecord) -> None:
        """Record a health check result.

        Thread-safe append to the circular buffer. If buffer is full,
        the oldest record is automatically evicted.

        Args:
            result: Health check result to store
        """
        with self._lock:
            self._records.append(result)

    def get_history(self) -> list[HealthCheckRecord]:
        """Get all stored health check records.

        Returns:
            List of records, newest first
        """
        with self._lock:
            # Return newest first
            return list(reversed(self._records))

    def get_count(self) -> int:
        """Get number of stored records.

        Returns:
            Number of records currently in buffer
        """
        with self._lock:
            return len(self._records)

    def get_time_window(self) -> tuple[datetime | None, datetime | None]:
        """Get the time window covered by stored records.

        Returns:
            Tuple of (oldest_timestamp, newest_timestamp), or (None, None) if empty
        """
        with self._lock:
            if not self._records:
                return (None, None)
            return (self._records[0].timestamp, self._records[-1].timestamp)

    def clear(self) -> None:
        """Clear all stored records."""
        with self._lock:
            self._records.clear()

    @property
    def max_size(self) -> int:
        """Maximum number of records to store."""
        return self._max_size


def get_health_history() -> HealthCheckHistory:
    """Get the singleton health check history instance.

    Returns:
        The global HealthCheckHistory instance
    """
    global _health_history
    if _health_history is None:
        with _lock:
            if _health_history is None:
                _health_history = HealthCheckHistory(max_size=5)
    return _health_history


def reset_health_history() -> None:
    """Reset the singleton instance (for testing)."""
    global _health_history
    with _lock:
        _health_history = None
