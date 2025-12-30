"""Performance monitoring service for early warning detection.

Tracks key metrics (response times, error rates, queue depths) over rolling windows.
Uses Redis sorted sets for efficient time-series storage.
Provides trend analysis and degradation scoring.
"""

import logging
import statistics
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from bo1.config import get_settings

logger = logging.getLogger(__name__)


@dataclass
class PerformanceMetric:
    """Single metric data point."""

    metric_name: str
    value: float
    timestamp: datetime
    source: str | None = None
    labels: dict[str, str] = field(default_factory=dict)


@dataclass
class MetricStats:
    """Statistical summary of metrics over a window."""

    metric_name: str
    count: int
    avg: float
    min_val: float
    max_val: float
    p50: float
    p95: float
    p99: float
    window_minutes: int
    calculated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class DegradationResult:
    """Result of degradation analysis for a metric."""

    metric_name: str
    degradation_score: float  # 0-1, higher = worse
    current_avg: float
    baseline_avg: float
    ratio: float  # current/baseline
    is_degraded: bool
    severity: str  # "none", "warn", "critical"
    details: str


@dataclass
class TrendAnalysis:
    """Trend analysis result across multiple metrics."""

    timestamp: datetime
    metrics: dict[str, DegradationResult]
    overall_health: str  # "healthy", "degraded", "critical"
    degraded_count: int
    critical_count: int


class PerformanceMonitor:
    """Monitors performance metrics and detects degradation.

    Uses Redis sorted sets for efficient time-series storage.
    Metrics are keyed by name and stored with timestamp scores.
    """

    # Redis key prefixes
    METRICS_KEY_PREFIX = "perf:metrics:"
    METRICS_TTL_SECONDS = 7 * 24 * 60 * 60  # 7 days

    # Default windows for analysis
    CURRENT_WINDOW_MINUTES = 5
    BASELINE_WINDOW_MINUTES = 25
    TREND_WINDOW_MINUTES = 30

    # Degradation thresholds
    DEGRADATION_RATIO_WARN = 1.5  # 50% worse than baseline
    DEGRADATION_RATIO_CRITICAL = 2.0  # 100% worse than baseline

    def __init__(self, redis_client: Any = None) -> None:
        """Initialize monitor.

        Args:
            redis_client: Redis client (optional, will create if not provided)
        """
        self._redis = redis_client
        self._redis_available = True

    def _get_redis(self) -> Any:
        """Get Redis client, creating if needed."""
        if self._redis is None:
            try:
                import redis

                settings = get_settings()
                self._redis = redis.from_url(settings.redis_url, decode_responses=True)
            except Exception as e:
                logger.warning(f"Redis unavailable for performance metrics: {e}")
                self._redis_available = False
                return None
        return self._redis

    def _metric_key(self, metric_name: str) -> str:
        """Get Redis key for a metric."""
        return f"{self.METRICS_KEY_PREFIX}{metric_name}"

    def record_metric(
        self,
        name: str,
        value: float,
        source: str | None = None,
        labels: dict[str, str] | None = None,
    ) -> bool:
        """Record a metric value.

        Args:
            name: Metric name (e.g., "api_response_time_ms")
            value: Metric value
            source: Optional source identifier
            labels: Optional labels

        Returns:
            True if recorded successfully
        """
        redis_client = self._get_redis()
        if not redis_client or not self._redis_available:
            return False

        try:
            key = self._metric_key(name)
            timestamp = time.time()

            # Store as JSON in sorted set with timestamp as score
            import json

            data = {
                "value": value,
                "source": source,
                "labels": labels or {},
                "ts": timestamp,
            }

            redis_client.zadd(key, {json.dumps(data): timestamp})

            # Set TTL if not already set
            ttl = redis_client.ttl(key)
            if ttl < 0:
                redis_client.expire(key, self.METRICS_TTL_SECONDS)

            return True

        except Exception as e:
            logger.warning(f"Failed to record metric {name}: {e}")
            self._redis_available = False
            return False

    def get_metric_values(self, name: str, window_minutes: int) -> list[tuple[float, float]]:
        """Get metric values within a time window.

        Args:
            name: Metric name
            window_minutes: Window size in minutes

        Returns:
            List of (value, timestamp) tuples
        """
        redis_client = self._get_redis()
        if not redis_client or not self._redis_available:
            return []

        try:
            import json

            key = self._metric_key(name)
            now = time.time()
            window_start = now - (window_minutes * 60)

            # Get all entries within window
            entries = redis_client.zrangebyscore(key, window_start, now)

            values = []
            for entry in entries:
                try:
                    data = json.loads(entry)
                    values.append((data["value"], data["ts"]))
                except (json.JSONDecodeError, KeyError):
                    continue

            return values

        except Exception as e:
            logger.warning(f"Failed to get metrics for {name}: {e}")
            return []

    def get_metric_stats(self, name: str, window_minutes: int = 30) -> MetricStats | None:
        """Calculate statistics for a metric over a window.

        Args:
            name: Metric name
            window_minutes: Window size in minutes

        Returns:
            MetricStats or None if no data
        """
        values = self.get_metric_values(name, window_minutes)
        if not values:
            return None

        # Extract just the values
        value_list = [v[0] for v in values]

        if not value_list:
            return None

        sorted_values = sorted(value_list)
        n = len(sorted_values)

        def percentile(data: list[float], p: float) -> float:
            """Calculate percentile."""
            if not data:
                return 0.0
            k = (len(data) - 1) * p / 100
            f = int(k)
            c = f + 1 if f + 1 < len(data) else f
            return data[f] + (k - f) * (data[c] - data[f]) if f != c else data[f]

        return MetricStats(
            metric_name=name,
            count=n,
            avg=statistics.mean(value_list),
            min_val=min(value_list),
            max_val=max(value_list),
            p50=percentile(sorted_values, 50),
            p95=percentile(sorted_values, 95),
            p99=percentile(sorted_values, 99),
            window_minutes=window_minutes,
        )

    def get_degradation_score(self, name: str) -> DegradationResult:
        """Calculate degradation score for a metric.

        Compares current 5-minute average to baseline 25-minute average.

        Args:
            name: Metric name

        Returns:
            DegradationResult with score and details
        """
        # Get current window stats (last 5 min)
        current_values = self.get_metric_values(name, self.CURRENT_WINDOW_MINUTES)
        current_vals = [v[0] for v in current_values]

        # Get baseline window stats (previous 25 min)
        all_values = self.get_metric_values(name, self.TREND_WINDOW_MINUTES)
        now = time.time()
        baseline_cutoff = now - (self.CURRENT_WINDOW_MINUTES * 60)
        baseline_vals = [value for value, ts in all_values if ts < baseline_cutoff]

        # Handle insufficient data
        if not current_vals or len(current_vals) < 3:
            return DegradationResult(
                metric_name=name,
                degradation_score=0.0,
                current_avg=0.0,
                baseline_avg=0.0,
                ratio=1.0,
                is_degraded=False,
                severity="none",
                details="Insufficient current data (cold start)",
            )

        if not baseline_vals or len(baseline_vals) < 10:
            return DegradationResult(
                metric_name=name,
                degradation_score=0.0,
                current_avg=statistics.mean(current_vals),
                baseline_avg=0.0,
                ratio=1.0,
                is_degraded=False,
                severity="none",
                details="Insufficient baseline data",
            )

        current_avg = statistics.mean(current_vals)
        baseline_avg = statistics.mean(baseline_vals)

        # Avoid division by zero
        if baseline_avg == 0:
            ratio = 1.0 if current_avg == 0 else 2.0
        else:
            ratio = current_avg / baseline_avg

        # Calculate score (0-1)
        # Score is 0 when ratio <= 1, scales linearly to 1 when ratio >= 2
        score = min(1.0, max(0.0, (ratio - 1.0)))

        # Determine severity
        if ratio >= self.DEGRADATION_RATIO_CRITICAL:
            severity = "critical"
            is_degraded = True
        elif ratio >= self.DEGRADATION_RATIO_WARN:
            severity = "warn"
            is_degraded = True
        else:
            severity = "none"
            is_degraded = False

        return DegradationResult(
            metric_name=name,
            degradation_score=score,
            current_avg=current_avg,
            baseline_avg=baseline_avg,
            ratio=ratio,
            is_degraded=is_degraded,
            severity=severity,
            details=f"Current avg: {current_avg:.2f}, baseline avg: {baseline_avg:.2f}, ratio: {ratio:.2f}x",
        )

    def analyze_trends(self, metric_names: list[str] | None = None) -> TrendAnalysis:
        """Analyze trends across multiple metrics.

        Args:
            metric_names: List of metric names to analyze (defaults to known metrics)

        Returns:
            TrendAnalysis with per-metric results and overall health
        """
        # Default metrics to monitor
        if metric_names is None:
            metric_names = [
                "api_response_time_ms",
                "llm_response_time_ms",
                "error_rate_percent",
                "queue_depth",
                "db_pool_usage_percent",
            ]

        results: dict[str, DegradationResult] = {}
        degraded_count = 0
        critical_count = 0

        for name in metric_names:
            result = self.get_degradation_score(name)
            results[name] = result

            if result.severity == "critical":
                critical_count += 1
                degraded_count += 1
            elif result.severity == "warn":
                degraded_count += 1

        # Determine overall health
        if critical_count > 0:
            overall_health = "critical"
        elif degraded_count > 0:
            overall_health = "degraded"
        else:
            overall_health = "healthy"

        return TrendAnalysis(
            timestamp=datetime.now(UTC),
            metrics=results,
            overall_health=overall_health,
            degraded_count=degraded_count,
            critical_count=critical_count,
        )

    def cleanup_old_metrics(self, metric_name: str | None = None) -> int:
        """Remove metrics older than TTL.

        Args:
            metric_name: Specific metric to clean, or None for all

        Returns:
            Number of entries removed
        """
        redis_client = self._get_redis()
        if not redis_client or not self._redis_available:
            return 0

        try:
            cutoff = time.time() - self.METRICS_TTL_SECONDS
            total_removed = 0

            if metric_name:
                keys = [self._metric_key(metric_name)]
            else:
                # Get all metric keys
                keys = list(redis_client.scan_iter(f"{self.METRICS_KEY_PREFIX}*"))

            for key in keys:
                removed = redis_client.zremrangebyscore(key, "-inf", cutoff)
                total_removed += removed

            return total_removed

        except Exception as e:
            logger.warning(f"Failed to cleanup old metrics: {e}")
            return 0


# Module-level singleton for convenience
_monitor: PerformanceMonitor | None = None


def get_performance_monitor() -> PerformanceMonitor:
    """Get the performance monitor singleton."""
    global _monitor
    if _monitor is None:
        _monitor = PerformanceMonitor()
    return _monitor


def record_metric(
    name: str,
    value: float,
    source: str | None = None,
    labels: dict[str, str] | None = None,
) -> bool:
    """Convenience function to record a metric."""
    return get_performance_monitor().record_metric(name, value, source, labels)
