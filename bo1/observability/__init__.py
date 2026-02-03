"""Observability utilities for Bo1.

Provides:
- OpenTelemetry tracing integration (OTEL_ENABLED=true)
- Sentry error tracking integration (SENTRY_DSN required)

Both are disabled by default and gracefully noop when not configured.
"""

from bo1.observability.sentry import init_sentry, is_sentry_enabled
from bo1.observability.tracing import get_tracer, init_tracing, is_tracing_enabled

__all__ = [
    "init_tracing",
    "get_tracer",
    "is_tracing_enabled",
    "init_sentry",
    "is_sentry_enabled",
]
