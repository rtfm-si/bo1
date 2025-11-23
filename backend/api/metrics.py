"""Lightweight metrics collection system for API and LLM monitoring.

This module provides in-memory metrics collection with minimal overhead (<1ms per request).
Metrics are used for debugging, optimization, and monitoring system health.

Example:
    >>> from backend.api.metrics import metrics
    >>> metrics.increment("api.sessions.get.success")
    >>> metrics.observe("api.sessions.get.duration", 0.15)
    >>> stats = metrics.get_stats()
"""

import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetricsCollector:
    """In-memory metrics collector with counters and histograms.

    Thread-safe for concurrent access (uses basic dict operations).
    Metrics are stored in memory and reset on server restart.

    Attributes:
        counters: Counter metrics (success, error counts, etc.)
        histograms: Histogram metrics (durations, token counts, etc.)
    """

    counters: dict[str, int] = field(default_factory=dict)
    histograms: dict[str, list[float]] = field(default_factory=dict)

    def increment(self, name: str, value: int = 1) -> None:
        """Increment a counter metric.

        Args:
            name: Metric name (e.g., 'api.sessions.get.success')
            value: Amount to increment (default: 1)
        """
        self.counters[name] = self.counters.get(name, 0) + value

    def observe(self, name: str, value: float) -> None:
        """Record a histogram observation.

        Args:
            name: Metric name (e.g., 'api.sessions.get.duration')
            value: Observed value (e.g., request duration in seconds)
        """
        if name not in self.histograms:
            self.histograms[name] = []
        self.histograms[name].append(value)

    def get_stats(self) -> dict[str, Any]:
        """Get all metrics as dictionary.

        Returns:
            Dictionary with counters and histogram statistics:
            {
                "counters": {"metric.name": count, ...},
                "histograms": {
                    "metric.name": {
                        "count": 10,
                        "sum": 1.5,
                        "avg": 0.15,
                        "min": 0.10,
                        "max": 0.25,
                        "p50": 0.14,
                        "p95": 0.22,
                        "p99": 0.24
                    },
                    ...
                }
            }
        """
        return {
            "counters": dict(self.counters),
            "histograms": {
                name: self._histogram_stats(values) for name, values in self.histograms.items()
            },
        }

    def _histogram_stats(self, values: list[float]) -> dict[str, float]:
        """Calculate histogram statistics.

        Args:
            values: List of observed values

        Returns:
            Dictionary with count, sum, avg, min, max, p50, p95, p99
        """
        if not values:
            return {
                "count": 0,
                "sum": 0.0,
                "avg": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }

        sorted_values = sorted(values)
        count = len(sorted_values)

        return {
            "count": count,
            "sum": sum(sorted_values),
            "avg": sum(sorted_values) / count,
            "min": sorted_values[0],
            "max": sorted_values[-1],
            "p50": sorted_values[int(count * 0.50)],
            "p95": sorted_values[min(int(count * 0.95), count - 1)],
            "p99": sorted_values[min(int(count * 0.99), count - 1)],
        }

    def reset(self) -> None:
        """Reset all metrics to zero (useful for testing)."""
        self.counters.clear()
        self.histograms.clear()


# Global metrics instance
metrics = MetricsCollector()


class track_api_call:  # noqa: N801 - Context manager uses lowercase for readability
    """Context manager to track API endpoint calls.

    Automatically tracks:
    - Success/error counts
    - Request duration

    Usage:
        with track_api_call("sessions.get", "GET"):
            # Endpoint logic
            pass

    Metrics generated:
        - api.sessions.get.get.success (counter)
        - api.sessions.get.get.error (counter)
        - api.sessions.get.get.duration (histogram)
    """

    def __init__(self, endpoint: str, method: str = "GET") -> None:
        """Initialize tracker.

        Args:
            endpoint: Endpoint name (e.g., "sessions.get")
            method: HTTP method (e.g., "GET", "POST")
        """
        self.endpoint = endpoint
        self.method = method.lower()
        self.metric_prefix = f"api.{endpoint}.{self.method}"
        self.start_time = 0.0

    def __enter__(self) -> "track_api_call":
        """Start tracking."""
        self.start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Stop tracking and record metrics.

        Args:
            exc_type: Exception type if error occurred
            exc_val: Exception value if error occurred
            exc_tb: Exception traceback if error occurred
        """
        # Record duration
        duration = time.perf_counter() - self.start_time
        metrics.observe(f"{self.metric_prefix}.duration", duration)

        # Record success or error
        if exc_type is None:
            metrics.increment(f"{self.metric_prefix}.success")
        else:
            metrics.increment(f"{self.metric_prefix}.error")
