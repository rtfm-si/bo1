"""Prometheus metrics middleware for FastAPI.

Provides automatic HTTP metrics instrumentation and custom business metrics.
"""

import logging
import re

from prometheus_client import Counter, Gauge, Histogram
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from prometheus_fastapi_instrumentator.instrumentation import (
    PrometheusFastApiInstrumentator,
)

logger = logging.getLogger(__name__)

# Path patterns to normalize (replace dynamic segments with placeholders)
PATH_NORMALIZERS = [
    (re.compile(r"/sessions/[a-f0-9-]{36}"), "/sessions/:id"),
    (re.compile(r"/datasets/[a-f0-9-]{36}"), "/datasets/:id"),
    (re.compile(r"/actions/[a-f0-9-]{36}"), "/actions/:id"),
    (re.compile(r"/projects/[a-f0-9-]{36}"), "/projects/:id"),
    (re.compile(r"/meeting/[a-f0-9-]{36}"), "/meeting/:id"),
    (re.compile(r"/users/[a-f0-9-]{36}"), "/users/:id"),
]

# Paths to exclude from metrics
EXCLUDED_PATHS = {"/health", "/ready", "/metrics", "/api/health", "/api/ready"}


def normalize_path(path: str) -> str:
    """Normalize dynamic path segments to reduce cardinality."""
    for pattern, replacement in PATH_NORMALIZERS:
        path = pattern.sub(replacement, path)
    return path


# Custom business metrics
bo1_sessions_total = Counter(
    "bo1_sessions_total",
    "Total sessions created",
    ["status"],
)

# Note: session_id label must be truncated via truncate_label() to limit cardinality
bo1_deliberation_rounds_total = Counter(
    "bo1_deliberation_rounds_total",
    "Total deliberation rounds completed",
    ["session_id"],
)

bo1_llm_cost_cents_total = Counter(
    "bo1_llm_cost_cents_total",
    "Total LLM costs in cents",
    ["model", "provider"],
)

bo1_llm_requests_total = Counter(
    "bo1_llm_requests_total",
    "Total LLM API requests",
    ["model", "provider", "status"],
)

bo1_active_sessions = Gauge(
    "bo1_active_sessions",
    "Number of currently active sessions",
)

bo1_sse_connections = Gauge(
    "bo1_sse_connections",
    "Number of active SSE connections",
)

bo1_request_duration_seconds = Histogram(
    "bo1_request_duration_seconds",
    "Request duration in seconds",
    ["method", "path", "status"],
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

# Rate limiter health metrics
bo1_rate_limiter_degraded = Gauge(
    "bo1_rate_limiter_degraded",
    "Rate limiter operating in degraded mode (1=degraded, 0=healthy)",
)

bo1_rate_limiter_redis_failures_total = Counter(
    "bo1_rate_limiter_redis_failures_total",
    "Total Redis failures in rate limiter",
)

# Global IP rate limit metrics
bo1_global_rate_limit_hits_total = Counter(
    "bo1_global_rate_limit_hits_total",
    "Total requests checked by global IP rate limiter",
)

bo1_global_rate_limit_blocked_total = Counter(
    "bo1_global_rate_limit_blocked_total",
    "Total requests blocked by global IP rate limiter",
    ["ip_hash"],  # Low-cardinality hash of IP for grouping
)

# Event batching metrics (P2-PERF)
bo1_events_batched_total = Counter(
    "bo1_events_batched_total",
    "Total events processed through batcher (includes both batched and critical)",
    ["priority"],
)

bo1_event_batch_size = Histogram(
    "bo1_event_batch_size",
    "Size of event batches persisted to PostgreSQL",
    buckets=(1, 5, 10, 25, 50, 100),
)

bo1_event_batch_latency_ms = Histogram(
    "bo1_event_batch_latency_ms",
    "Latency of event batch persistence in milliseconds",
    buckets=(10, 25, 50, 100, 250, 500, 1000),
)

bo1_pending_events = Gauge(
    "bo1_pending_events",
    "Current number of events pending in batch buffer",
)

# Expert event buffer metrics (P2-PERF stream optimization)
bo1_event_buffer_size = Gauge(
    "bo1_event_buffer_size",
    "Number of events buffered in expert event buffer before flush",
    ["expert_id"],
)

bo1_event_merge_ratio = Gauge(
    "bo1_event_merge_ratio",
    "Ratio of merged events to total events (0.0-1.0)",
)

# Note: session_id label must be truncated via truncate_label() to limit cardinality
bo1_sse_frame_count = Counter(
    "bo1_sse_frame_count",
    "Total SSE frames sent to clients",
    ["session_id"],
)

# Citation compliance metrics (LLM quality tracking)
bo1_citation_compliance_total = Counter(
    "bo1_citation_compliance_total",
    "Citation compliance checks for masked personas",
    ["persona_type", "compliant"],
)

bo1_citation_count = Histogram(
    "bo1_citation_count",
    "Number of citations per masked persona response",
    ["persona_type"],
    buckets=(0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10),
)

# Early exit metrics (cost savings tracking)
bo1_early_exit_total = Counter(
    "bo1_early_exit_total",
    "Total early exits triggered when convergence high and novelty low",
    ["reason"],
)

# Circuit breaker metrics
bo1_circuit_breaker_state = Gauge(
    "bo1_circuit_breaker_state",
    "Circuit breaker state (0=closed, 1=half_open, 2=open)",
    ["service"],
)

bo1_circuit_breaker_trips_total = Counter(
    "bo1_circuit_breaker_trips_total",
    "Total circuit breaker trips (transitions to open state)",
    ["service"],
)

bo1_circuit_breaker_fault_total = Counter(
    "bo1_circuit_breaker_fault_total",
    "Total faults recorded by circuit breaker by type",
    ["service", "fault_type"],
)

# Event queue depth gauge (updated by health checks)
bo1_event_queue_depth = Gauge(
    "bo1_event_queue_depth",
    "Current event queue depth for health monitoring",
)

# XML validation metrics (LLM output format validation)
bo1_llm_xml_validation_failures_total = Counter(
    "bo1_llm_xml_validation_failures_total",
    "Total XML validation failures in LLM responses",
    ["agent_type", "tag"],
)

bo1_llm_xml_retry_success_total = Counter(
    "bo1_llm_xml_retry_success_total",
    "Total successful retries after XML validation failure",
    ["agent_type"],
)


def create_instrumentator() -> PrometheusFastApiInstrumentator:
    """Create and configure the Prometheus instrumentator."""
    instrumentator = Instrumentator(
        should_group_status_codes=True,
        should_ignore_untemplated=True,
        should_respect_env_var=False,
        should_instrument_requests_inprogress=True,
        excluded_handlers=["/health", "/ready", "/metrics", "/api/health", "/api/ready"],
        inprogress_name="http_requests_inprogress",
        inprogress_labels=True,
    )

    # Add default metrics
    instrumentator.add(
        metrics.request_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    instrumentator.add(
        metrics.response_size(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )
    instrumentator.add(
        metrics.latency(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
        )
    )
    instrumentator.add(
        metrics.requests(
            should_include_handler=True,
            should_include_method=True,
            should_include_status=True,
        )
    )

    return instrumentator


# Business metric recording functions


def record_session_created(status: str = "created") -> None:
    """Record a session creation event."""
    bo1_sessions_total.labels(status=status).inc()


def record_session_completed() -> None:
    """Record a session completion event."""
    bo1_sessions_total.labels(status="completed").inc()


def record_session_failed() -> None:
    """Record a session failure event."""
    bo1_sessions_total.labels(status="failed").inc()


def record_round_completed(session_id: str) -> None:
    """Record a deliberation round completion."""
    # Use truncated session ID to limit cardinality (see bo1/utils/metrics.py)
    from bo1.utils.metrics import truncate_label

    bo1_deliberation_rounds_total.labels(session_id=truncate_label(session_id)).inc()


def record_llm_cost(model: str, provider: str, cost_cents: float) -> None:
    """Record LLM cost."""
    bo1_llm_cost_cents_total.labels(model=model, provider=provider).inc(cost_cents)


def record_llm_request(model: str, provider: str, success: bool = True) -> None:
    """Record an LLM API request."""
    status = "success" if success else "error"
    bo1_llm_requests_total.labels(model=model, provider=provider, status=status).inc()


def set_active_sessions(count: int) -> None:
    """Set the current number of active sessions."""
    bo1_active_sessions.set(count)


def increment_sse_connections() -> None:
    """Increment active SSE connections count."""
    bo1_sse_connections.inc()


def decrement_sse_connections() -> None:
    """Decrement active SSE connections count."""
    bo1_sse_connections.dec()


def set_rate_limiter_degraded(degraded: bool) -> None:
    """Set rate limiter degraded status."""
    bo1_rate_limiter_degraded.set(1 if degraded else 0)


def record_rate_limiter_redis_failure() -> None:
    """Record a Redis failure in rate limiter."""
    bo1_rate_limiter_redis_failures_total.inc()


def record_global_rate_limit_hit() -> None:
    """Record a request checked by global rate limiter."""
    bo1_global_rate_limit_hits_total.inc()


def record_global_rate_limit_blocked(ip: str) -> None:
    """Record a request blocked by global IP rate limiter.

    Args:
        ip: Client IP address (hashed for low cardinality)
    """
    # Hash IP for low cardinality (first 8 chars of hash)
    import hashlib

    ip_hash = hashlib.sha256(ip.encode()).hexdigest()[:8]
    bo1_global_rate_limit_blocked_total.labels(ip_hash=ip_hash).inc()


def record_citation_compliance(persona_type: str, citation_count: int, is_compliant: bool) -> None:
    """Record citation compliance for masked persona responses.

    Args:
        persona_type: Type of persona ("researcher" or "moderator")
        citation_count: Number of citations found in response
        is_compliant: Whether response met minimum citation requirements
    """
    compliant_str = "true" if is_compliant else "false"
    bo1_citation_compliance_total.labels(persona_type=persona_type, compliant=compliant_str).inc()
    bo1_citation_count.labels(persona_type=persona_type).observe(citation_count)


def record_early_exit(reason: str = "convergence_high") -> None:
    """Record an early exit event for cost savings tracking.

    Args:
        reason: Reason for early exit (default: "convergence_high")
    """
    bo1_early_exit_total.labels(reason=reason).inc()


def record_circuit_breaker_state(service: str, state: str) -> None:
    """Record circuit breaker state for a service.

    Args:
        service: Service name (e.g., "anthropic", "voyage", "brave")
        state: State string ("closed", "half_open", "open")
    """
    state_map = {"closed": 0, "half_open": 1, "open": 2}
    bo1_circuit_breaker_state.labels(service=service).set(state_map.get(state, -1))


def record_circuit_breaker_trip(service: str) -> None:
    """Record a circuit breaker trip (transition to open state).

    Args:
        service: Service name that tripped
    """
    bo1_circuit_breaker_trips_total.labels(service=service).inc()


def record_circuit_breaker_fault(service: str, fault_type: str) -> None:
    """Record a fault classification in circuit breaker.

    Args:
        service: Service name (e.g., "anthropic", "voyage", "brave")
        fault_type: Fault type ("transient", "permanent", "unknown")
    """
    bo1_circuit_breaker_fault_total.labels(service=service, fault_type=fault_type).inc()


def record_event_queue_depth(depth: int) -> None:
    """Record current event queue depth.

    Args:
        depth: Number of pending events in queue
    """
    bo1_event_queue_depth.set(depth)


def record_xml_validation_failure(agent_type: str, tag: str) -> None:
    """Record XML validation failure in LLM response.

    Args:
        agent_type: Type of agent that produced the response
        tag: Missing or malformed XML tag
    """
    bo1_llm_xml_validation_failures_total.labels(agent_type=agent_type, tag=tag).inc()


def record_xml_retry_success(agent_type: str) -> None:
    """Record successful retry after XML validation failure.

    Args:
        agent_type: Type of agent that succeeded on retry
    """
    bo1_llm_xml_retry_success_total.labels(agent_type=agent_type).inc()
