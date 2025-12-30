"""Lightweight metrics collection system for API and LLM monitoring.

This module provides in-memory metrics collection with minimal overhead (<1ms per request).
Metrics are used for debugging, optimization, and monitoring system health.

Includes Prometheus-compatible metrics for Grafana dashboards:
- llm_request_duration_seconds: LLM request latency histogram
- llm_tokens_total: Token usage by provider/model/type
- llm_cost_dollars_total: Cost tracking by provider/model
- session_events_total: SSE event counts
- active_sse_connections: Current SSE connection gauge

Example:
    >>> from backend.api.metrics import metrics, prom_metrics
    >>> metrics.increment("api.sessions.get.success")
    >>> metrics.observe("api.sessions.get.duration", 0.15)
    >>> prom_metrics.observe_llm_request("anthropic", "claude-sonnet-4-5", "completion", 1.5)
    >>> stats = metrics.get_stats()
"""

import time
from dataclasses import dataclass, field
from typing import Any

from prometheus_client import Counter, Gauge, Histogram


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

    def decrement(self, name: str, value: int = 1) -> None:
        """Decrement a counter metric.

        Args:
            name: Metric name (e.g., 'sse.connections.active')
            value: Amount to decrement (default: 1)
        """
        self.counters[name] = self.counters.get(name, 0) - value

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
            "cache": self._get_cache_stats(),
        }

    def _get_cache_stats(self) -> dict[str, float]:
        """Calculate LLM cache statistics (P1: prompt cache monitoring).

        Returns:
            Dictionary with cache hits, misses, hit_rate, tokens_saved, cost_saved
        """
        hits = self.counters.get("llm.cache.hits", 0)
        misses = self.counters.get("llm.cache.misses", 0)
        total = hits + misses

        # Get histogram summaries for tokens and cost saved
        tokens_saved_hist = self.histograms.get("llm.cache.tokens_saved", [])
        cost_saved_hist = self.histograms.get("llm.cache.cost_saved", [])

        return {
            "hits": hits,
            "misses": misses,
            "total_calls": total,
            "hit_rate": hits / total if total > 0 else 0.0,
            "tokens_saved": sum(tokens_saved_hist) if tokens_saved_hist else 0.0,
            "cost_saved": sum(cost_saved_hist) if cost_saved_hist else 0.0,
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


# =============================================================================
# Prometheus Metrics (for Grafana dashboards)
# =============================================================================


class PrometheusMetrics:
    """Prometheus metrics for LLM and API observability.

    Uses low-cardinality labels to avoid metric explosion:
    - provider: anthropic, voyage, brave, tavily
    - model: normalized model name (e.g., "sonnet-4.5", "haiku-4.5")
    - operation: completion, embedding, search
    - token_type: input, output, cache_read, cache_write
    - event_type: contribution, synthesis, error, etc.
    - status: success, error
    """

    def __init__(self) -> None:
        """Initialize Prometheus metrics."""
        # LLM request duration histogram (in seconds)
        # Buckets aligned with plan: [0.5, 1, 2, 5, 10, 30, 60] for SLO alerting (>5s threshold)
        self.llm_request_duration = Histogram(
            "bo1_llm_request_duration_seconds",
            "LLM request latency in seconds",
            ["provider", "model", "operation"],
            buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0],
        )

        # Token usage counter
        self.llm_tokens = Counter(
            "llm_tokens_total",
            "Total tokens used by LLM calls",
            ["provider", "model", "token_type"],
        )

        # Cost counter (in dollars)
        self.llm_cost = Counter(
            "llm_cost_dollars_total",
            "Total LLM cost in USD",
            ["provider", "model"],
        )

        # SSE events counter
        self.session_events = Counter(
            "session_events_total",
            "Total SSE events emitted",
            ["event_type", "status"],
        )

        # Active SSE connections gauge
        self.active_sse_connections = Gauge(
            "active_sse_connections",
            "Current number of active SSE connections",
        )

        # Cache hit/miss counter
        self.llm_cache = Counter(
            "llm_cache_total",
            "LLM prompt cache hits and misses",
            ["result"],  # hit, miss
        )

        # Budget alerts counter
        self.budget_alerts = Counter(
            "session_budget_alerts_total",
            "Session cost budget alerts (warning at 80%, exceeded at 100%)",
            ["alert_type"],  # warning, exceeded
        )

        # Contribution summarization metrics
        self.summarization_duration = Histogram(
            "contribution_summarization_duration_ms",
            "Contribution summarization latency in milliseconds",
            ["persona_name", "status"],
            buckets=[100, 250, 500, 1000, 2000, 5000, 10000],
        )

        self.summarization_batch_size = Histogram(
            "contribution_summarization_batch_size",
            "Number of contributions in a summarization batch",
            buckets=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        )

        self.summarization_batch_duration = Histogram(
            "contribution_summarization_batch_duration_ms",
            "Total batch summarization latency in milliseconds",
            buckets=[500, 1000, 2000, 5000, 10000, 20000, 30000],
        )

        # Database connection pool metrics
        self.db_pool_used_connections = Gauge(
            "db_pool_used_connections",
            "Number of database connections currently in use",
        )

        self.db_pool_free_connections = Gauge(
            "db_pool_free_connections",
            "Number of database connections available in pool",
        )

        self.db_pool_utilization_percent = Gauge(
            "db_pool_utilization_percent",
            "Percentage of database connection pool in use (0-100)",
        )

        # Event queue metrics (DLQ monitoring)
        self.event_dlq_depth = Gauge(
            "event_dlq_depth",
            "Number of events in the dead letter queue",
        )

        self.event_retry_queue_depth = Gauge(
            "event_retry_queue_depth",
            "Number of events in the retry queue",
        )

        # Redis reconnection metrics
        self.redis_reconnect_total = Counter(
            "bo1_redis_reconnect_attempts_total",
            "Total Redis reconnection attempts",
        )

        self.redis_buffer_depth = Gauge(
            "bo1_redis_buffer_depth",
            "Number of events buffered during Redis disconnection",
        )

        # Redis metadata fallback to PostgreSQL
        self.redis_metadata_fallback_total = Counter(
            "bo1_redis_metadata_fallback_total",
            "Redis metadata cache misses that fell back to PostgreSQL",
            ["result"],  # success, failure
        )

        # Redis metadata dual-write to PostgreSQL
        self.redis_metadata_dualwrite_total = Counter(
            "bo1_redis_metadata_dualwrite_total",
            "Redis metadata dual-writes to PostgreSQL after Redis save",
            ["result"],  # success, failure
        )

        # User context cache metrics
        self.user_context_cache_total = Counter(
            "bo1_user_context_cache_total",
            "User context cache lookups",
            ["result"],  # hit, miss
        )

        # Database pool degradation metrics
        self.db_pool_degraded = Gauge(
            "bo1_db_pool_degraded",
            "Whether database pool is in degradation mode (0/1)",
        )

        self.db_pool_queue_depth = Gauge(
            "bo1_db_pool_queue_depth",
            "Number of requests waiting in degradation queue",
        )

        self.db_requests_queued_total = Counter(
            "bo1_db_requests_queued_total",
            "Total requests queued due to pool exhaustion",
        )

        self.db_requests_shed_total = Counter(
            "bo1_db_requests_shed_total",
            "Total requests rejected due to pool exhaustion (load shedding)",
        )

        # API startup duration gauge (in milliseconds)
        self.api_startup_duration_ms = Gauge(
            "bo1_api_startup_duration_ms",
            "API startup duration in milliseconds",
            ["phase"],  # module_init, lifespan, total
        )

        # Graph node execution metrics
        self.graph_node_duration = Histogram(
            "bo1_graph_node_duration_seconds",
            "Graph node execution duration in seconds",
            ["node_name"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0, 120.0],
        )

        self.graph_node_total = Counter(
            "bo1_graph_node_total",
            "Total graph node executions by status",
            ["node_name", "status"],  # status: success, error
        )

        # Cache hit rate gauges (for unified cache monitoring)
        self.cache_hit_rate = Gauge(
            "bo1_cache_hit_rate",
            "Cache hit rate by cache type (0.0-1.0)",
            ["cache_type"],  # prompt, research, llm
        )

        self.cache_hits_total = Counter(
            "bo1_cache_hits_total",
            "Total cache hits by cache type",
            ["cache_type"],
        )

        self.cache_misses_total = Counter(
            "bo1_cache_misses_total",
            "Total cache misses by cache type",
            ["cache_type"],
        )

    def record_startup_time(self, phase: str, duration_ms: float) -> None:
        """Record startup time for a specific phase.

        Args:
            phase: Startup phase (module_init, lifespan, total)
            duration_ms: Duration in milliseconds
        """
        self.api_startup_duration_ms.labels(phase=phase).set(duration_ms)

    def _normalize_model(self, model: str | None) -> str:
        """Normalize model name to low-cardinality label.

        Examples:
            claude-sonnet-4-5-20250929 -> sonnet-4.5
            claude-haiku-4-5-20251001 -> haiku-4.5
            voyage-3 -> voyage-3
        """
        if not model:
            return "unknown"
        model_lower = model.lower()
        if "sonnet-4-5" in model_lower or "sonnet-4.5" in model_lower:
            return "sonnet-4.5"
        if "haiku-4-5" in model_lower or "haiku-4.5" in model_lower:
            return "haiku-4.5"
        if "opus-4" in model_lower:
            return "opus-4"
        if "3-5-haiku" in model_lower or "haiku-3-5" in model_lower:
            return "haiku-3.5"
        if "voyage" in model_lower:
            return model_lower
        return model[:20]  # Truncate long model names

    def observe_llm_request(
        self,
        provider: str,
        model: str | None,
        operation: str,
        duration_seconds: float,
        node: str | None = None,
    ) -> None:
        """Record LLM request duration.

        Args:
            provider: Provider name (anthropic, voyage, etc.)
            model: Model name
            operation: Operation type (completion, embedding, search)
            duration_seconds: Request duration in seconds
            node: Graph node name (optional, ignored - kept for API compat)
        """
        normalized_model = self._normalize_model(model)
        self.llm_request_duration.labels(
            provider=provider,
            model=normalized_model,
            operation=operation,
        ).observe(duration_seconds)

    def record_tokens(
        self,
        provider: str,
        model: str | None,
        input_tokens: int = 0,
        output_tokens: int = 0,
        cache_read_tokens: int = 0,
        cache_write_tokens: int = 0,
    ) -> None:
        """Record token usage.

        Args:
            provider: Provider name
            model: Model name
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cache_read_tokens: Tokens read from cache
            cache_write_tokens: Tokens written to cache
        """
        normalized_model = self._normalize_model(model)
        if input_tokens > 0:
            self.llm_tokens.labels(
                provider=provider,
                model=normalized_model,
                token_type="input",  # noqa: S106
            ).inc(input_tokens)
        if output_tokens > 0:
            self.llm_tokens.labels(
                provider=provider,
                model=normalized_model,
                token_type="output",  # noqa: S106
            ).inc(output_tokens)
        if cache_read_tokens > 0:
            self.llm_tokens.labels(
                provider=provider,
                model=normalized_model,
                token_type="cache_read",  # noqa: S106
            ).inc(cache_read_tokens)
        if cache_write_tokens > 0:
            self.llm_tokens.labels(
                provider=provider,
                model=normalized_model,
                token_type="cache_write",  # noqa: S106
            ).inc(cache_write_tokens)

    def record_cost(self, provider: str, model: str | None, cost_dollars: float) -> None:
        """Record cost in USD.

        Args:
            provider: Provider name
            model: Model name
            cost_dollars: Cost in USD
        """
        if cost_dollars > 0:
            normalized_model = self._normalize_model(model)
            self.llm_cost.labels(provider=provider, model=normalized_model).inc(cost_dollars)

    def record_event(self, event_type: str, status: str = "success") -> None:
        """Record SSE event emission.

        Args:
            event_type: Event type (contribution, synthesis, error, etc.)
            status: Status (success, error)
        """
        self.session_events.labels(event_type=event_type, status=status).inc()

    def record_cache_hit(self, hit: bool) -> None:
        """Record cache hit or miss.

        Args:
            hit: True for cache hit, False for miss
        """
        self.llm_cache.labels(result="hit" if hit else "miss").inc()

    def sse_connection_opened(self) -> None:
        """Increment active SSE connections."""
        self.active_sse_connections.inc()

    def sse_connection_closed(self) -> None:
        """Decrement active SSE connections."""
        self.active_sse_connections.dec()

    def record_budget_alert(self, alert_type: str, current_cost: float, budget: float) -> None:
        """Record budget alert (warning or exceeded).

        Args:
            alert_type: Alert type ('warning' or 'exceeded')
            current_cost: Current session cost
            budget: Budget threshold
        """
        self.budget_alerts.labels(alert_type=alert_type).inc()

    def record_summarization_duration(
        self, persona_name: str, status: str, duration_ms: float
    ) -> None:
        """Record contribution summarization latency.

        Args:
            persona_name: Name of the persona being summarized
            status: success, fallback, or error
            duration_ms: Duration in milliseconds
        """
        self.summarization_duration.labels(persona_name=persona_name, status=status).observe(
            duration_ms
        )

    def record_summarization_batch(self, batch_size: int, duration_ms: float) -> None:
        """Record batch summarization metrics.

        Args:
            batch_size: Number of contributions in the batch
            duration_ms: Total batch duration in milliseconds
        """
        self.summarization_batch_size.observe(batch_size)
        self.summarization_batch_duration.observe(duration_ms)

    def update_pool_metrics(
        self, used_connections: int, free_connections: int, utilization_pct: float
    ) -> None:
        """Update database connection pool metrics.

        Args:
            used_connections: Number of connections currently in use
            free_connections: Number of connections available
            utilization_pct: Pool utilization percentage (0-100)
        """
        self.db_pool_used_connections.set(used_connections)
        self.db_pool_free_connections.set(free_connections)
        self.db_pool_utilization_percent.set(utilization_pct)

    def update_queue_metrics(self, dlq_depth: int, retry_queue_depth: int) -> None:
        """Update event queue metrics (DLQ and retry queue).

        Args:
            dlq_depth: Number of events in the dead letter queue
            retry_queue_depth: Number of events in the retry queue
        """
        self.event_dlq_depth.set(dlq_depth)
        self.event_retry_queue_depth.set(retry_queue_depth)

    def update_degradation_metrics(
        self,
        is_degraded: bool,
        queue_depth: int,
    ) -> None:
        """Update database pool degradation metrics.

        Args:
            is_degraded: Whether pool is in degradation mode
            queue_depth: Number of requests in degradation queue
        """
        self.db_pool_degraded.set(1 if is_degraded else 0)
        self.db_pool_queue_depth.set(queue_depth)

    def record_request_queued(self) -> None:
        """Record a request queued due to pool exhaustion."""
        self.db_requests_queued_total.inc()

    def record_request_shed(self) -> None:
        """Record a request rejected due to load shedding."""
        self.db_requests_shed_total.inc()

    def record_graph_node_execution(
        self, node_name: str, duration_seconds: float, success: bool
    ) -> None:
        """Record graph node execution metrics.

        Args:
            node_name: Name of the graph node (e.g., "decompose", "select_personas")
            duration_seconds: Execution duration in seconds
            success: Whether execution succeeded
        """
        self.graph_node_duration.labels(node_name=node_name).observe(duration_seconds)
        self.graph_node_total.labels(
            node_name=node_name, status="success" if success else "error"
        ).inc()

    def update_cache_hit_rate(self, cache_type: str, hit_rate: float) -> None:
        """Update cache hit rate gauge.

        Args:
            cache_type: Cache type (prompt, research, llm)
            hit_rate: Hit rate as decimal (0.0-1.0)
        """
        self.cache_hit_rate.labels(cache_type=cache_type).set(hit_rate)

    def record_cache_operation(self, cache_type: str, hit: bool) -> None:
        """Record cache hit or miss for a specific cache type.

        Args:
            cache_type: Cache type (prompt, research, llm)
            hit: True for hit, False for miss
        """
        if hit:
            self.cache_hits_total.labels(cache_type=cache_type).inc()
        else:
            self.cache_misses_total.labels(cache_type=cache_type).inc()


# Global Prometheus metrics instance
prom_metrics = PrometheusMetrics()
