"""OpenTelemetry tracing integration for Bo1.

Provides distributed tracing with spans for LLM calls, graph nodes, and HTTP requests.
Disabled by default - enable via OTEL_ENABLED=true environment variable.

Usage:
    from bo1.observability import get_tracer

    tracer = get_tracer()
    with tracer.start_as_current_span("operation_name") as span:
        span.set_attribute("key", "value")
        # ... do work ...

Environment variables:
    OTEL_ENABLED: Enable tracing (default: false)
    OTEL_SERVICE_NAME: Service name for spans (default: bo1-api)
    OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector endpoint (default: http://localhost:4317)
    OTEL_TRACES_SAMPLER_ARG: Sampling rate 0.0-1.0 (default: 1.0 = all traces)
"""

from __future__ import annotations

import logging
import os
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Generator

    from opentelemetry.trace import Span, Tracer

logger = logging.getLogger(__name__)

# Module-level state
_tracer: Tracer | None = None
_initialized: bool = False
_enabled: bool = False


def is_tracing_enabled() -> bool:
    """Check if OpenTelemetry tracing is enabled.

    Returns:
        True if OTEL_ENABLED=true and tracing was successfully initialized
    """
    return _enabled and _initialized


def init_tracing(
    service_name: str | None = None,
    otlp_endpoint: str | None = None,
    sample_rate: float | None = None,
) -> bool:
    """Initialize OpenTelemetry tracing.

    Safe to call multiple times - subsequent calls are no-ops.
    Does nothing if OTEL_ENABLED is not set to 'true'.

    Args:
        service_name: Override OTEL_SERVICE_NAME env var
        otlp_endpoint: Override OTEL_EXPORTER_OTLP_ENDPOINT env var
        sample_rate: Override OTEL_TRACES_SAMPLER_ARG env var (0.0-1.0)

    Returns:
        True if tracing was initialized, False if disabled or already initialized
    """
    global _tracer, _initialized, _enabled

    # Check if already initialized
    if _initialized:
        return False

    # Check if enabled via env var
    otel_enabled = os.getenv("OTEL_ENABLED", "false").lower() in ("true", "1", "yes")
    if not otel_enabled:
        _initialized = True
        _enabled = False
        logger.debug("OpenTelemetry tracing disabled (OTEL_ENABLED not set)")
        return False

    try:
        # Lazy import to avoid overhead when disabled
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.trace.sampling import TraceIdRatioBased

        # Resolve configuration
        resolved_service_name = service_name or os.getenv("OTEL_SERVICE_NAME") or "bo1-api"
        resolved_endpoint = otlp_endpoint or os.getenv(
            "OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4317"
        )
        resolved_sample_rate = sample_rate
        if resolved_sample_rate is None:
            env_rate = os.getenv("OTEL_TRACES_SAMPLER_ARG")
            resolved_sample_rate = float(env_rate) if env_rate else 1.0

        # Create resource with service info
        app_version = os.getenv("APP_VERSION") or "unknown"
        resource = Resource.create(
            {
                "service.name": resolved_service_name,
                "service.version": app_version,
            }
        )

        # Create sampler
        sampler = TraceIdRatioBased(resolved_sample_rate)

        # Create tracer provider
        provider = TracerProvider(resource=resource, sampler=sampler)

        # Create OTLP exporter with batch processor
        exporter = OTLPSpanExporter(endpoint=resolved_endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)

        # Set as global provider
        trace.set_tracer_provider(provider)

        # Get tracer for this module
        _tracer = trace.get_tracer("bo1", "1.0.0")

        _initialized = True
        _enabled = True

        logger.info(
            f"OpenTelemetry tracing initialized: service={resolved_service_name}, "
            f"endpoint={resolved_endpoint}, sample_rate={resolved_sample_rate}"
        )
        return True

    except Exception as e:
        logger.warning(f"Failed to initialize OpenTelemetry tracing: {e}")
        _initialized = True
        _enabled = False
        return False


def get_tracer() -> Tracer | None:
    """Get the OpenTelemetry tracer.

    Returns a no-op tracer if tracing is disabled, or None if opentelemetry
    is not installed.

    Returns:
        Configured tracer, no-op tracer, or None
    """
    global _tracer

    if _tracer is not None:
        return _tracer

    # Return no-op tracer if not initialized or disabled
    try:
        from opentelemetry import trace

        return trace.get_tracer("bo1-noop")
    except ImportError:
        # OpenTelemetry not installed - return a minimal stub
        return None


@contextmanager
def span_from_context(
    name: str,
    attributes: dict[str, Any] | None = None,
) -> Generator[Span | None, None, None]:
    """Create a span if tracing is enabled, otherwise yield None.

    This is a convenience wrapper that avoids the need to check is_tracing_enabled()
    at every call site. The span is only created if tracing is enabled.

    Args:
        name: Span name (e.g., "llm.anthropic.completion")
        attributes: Optional initial span attributes

    Yields:
        Span object if tracing enabled, None otherwise

    Example:
        with span_from_context("llm.call", {"model": "claude"}) as span:
            if span:
                span.set_attribute("tokens", 100)
            result = do_work()
    """
    if not is_tracing_enabled():
        yield None
        return

    tracer = get_tracer()
    if tracer is None:
        yield None
        return

    with tracer.start_as_current_span(name, attributes=attributes) as span:
        yield span


def record_exception_on_span(span: Span | None, exception: Exception) -> None:
    """Record an exception on a span if it exists.

    Args:
        span: Span to record on (may be None if tracing disabled)
        exception: Exception to record
    """
    if span is not None:
        try:
            from opentelemetry.trace import StatusCode

            span.record_exception(exception)
            span.set_status(StatusCode.ERROR, str(exception))
        except ImportError:
            # OpenTelemetry not installed - skip recording
            pass
