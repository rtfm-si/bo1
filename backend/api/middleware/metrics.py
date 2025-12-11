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
    # Use truncated session ID to limit cardinality
    short_id = session_id[:8] if len(session_id) > 8 else session_id
    bo1_deliberation_rounds_total.labels(session_id=short_id).inc()


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
