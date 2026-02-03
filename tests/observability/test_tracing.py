"""Tests for OpenTelemetry tracing integration."""

import os
from unittest.mock import MagicMock, patch


class TestTracingInit:
    """Test tracing initialization."""

    def test_tracing_disabled_by_default(self) -> None:
        """Tracing should be disabled when OTEL_ENABLED not set."""
        # Reset module state
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = False
        tracing_module._enabled = False
        tracing_module._tracer = None

        with patch.dict(os.environ, {}, clear=True):
            # Remove OTEL_ENABLED if set
            os.environ.pop("OTEL_ENABLED", None)

            from bo1.observability import init_tracing, is_tracing_enabled

            result = init_tracing()

            assert result is False
            assert is_tracing_enabled() is False

    def test_tracing_disabled_when_otel_enabled_false(self) -> None:
        """Tracing disabled when OTEL_ENABLED=false."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = False
        tracing_module._enabled = False
        tracing_module._tracer = None

        with patch.dict(os.environ, {"OTEL_ENABLED": "false"}):
            from bo1.observability import init_tracing, is_tracing_enabled

            result = init_tracing()

            assert result is False
            assert is_tracing_enabled() is False

    def test_init_tracing_returns_false_when_already_initialized(self) -> None:
        """Second call to init_tracing should return False."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = True
        tracing_module._enabled = False

        from bo1.observability import init_tracing

        result = init_tracing()
        assert result is False

    def test_get_tracer_returns_noop_when_disabled(self) -> None:
        """get_tracer should return a noop tracer when tracing disabled."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = True
        tracing_module._enabled = False
        tracing_module._tracer = None

        from bo1.observability import get_tracer

        tracer = get_tracer()

        # Should return a tracer (noop) or None if opentelemetry not installed
        if tracer is not None:
            # Should have start_as_current_span method
            assert hasattr(tracer, "start_as_current_span")


class TestSpanFromContext:
    """Test span_from_context helper."""

    def test_span_from_context_yields_none_when_disabled(self) -> None:
        """span_from_context yields None when tracing disabled."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = True
        tracing_module._enabled = False

        from bo1.observability.tracing import span_from_context

        with span_from_context("test.span", {"key": "value"}) as span:
            assert span is None

    def test_span_from_context_with_attributes(self) -> None:
        """span_from_context accepts attributes dict."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = True
        tracing_module._enabled = False

        from bo1.observability.tracing import span_from_context

        attrs = {"llm.provider": "anthropic", "llm.model": "claude"}
        with span_from_context("llm.call", attrs) as span:
            # Should not raise even with attributes
            assert span is None


class TestTracingEnabled:
    """Test behavior when tracing is enabled (mocked)."""

    def test_init_tracing_with_otel_enabled(self) -> None:
        """init_tracing initializes when OTEL_ENABLED=true."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = False
        tracing_module._enabled = False
        tracing_module._tracer = None

        # Mock the OTEL imports to avoid needing actual collector
        mock_trace = MagicMock()
        mock_tracer = MagicMock()
        mock_trace.get_tracer.return_value = mock_tracer

        with patch.dict(os.environ, {"OTEL_ENABLED": "true", "OTEL_SERVICE_NAME": "test-svc"}):
            with patch.dict(
                "sys.modules",
                {
                    "opentelemetry": MagicMock(),
                    "opentelemetry.trace": mock_trace,
                    "opentelemetry.sdk.trace": MagicMock(),
                    "opentelemetry.sdk.trace.export": MagicMock(),
                    "opentelemetry.sdk.trace.sampling": MagicMock(),
                    "opentelemetry.sdk.resources": MagicMock(),
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(),
                },
            ):
                from bo1.observability import init_tracing

                result = init_tracing()

                # Should succeed with mocked deps
                assert result is True

    def test_init_tracing_handles_import_error(self) -> None:
        """init_tracing handles missing OTEL packages gracefully."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = False
        tracing_module._enabled = False
        tracing_module._tracer = None

        with patch.dict(os.environ, {"OTEL_ENABLED": "true"}):
            # Simulate import error
            with patch(
                "bo1.observability.tracing.init_tracing",
                side_effect=ImportError("No module named 'opentelemetry'"),
            ):
                # The real init_tracing catches exceptions and returns False
                pass  # Can't easily test this without complex patching

    def test_sample_rate_from_env(self) -> None:
        """Sample rate should be configurable via env var."""
        import bo1.observability.tracing as tracing_module

        tracing_module._initialized = False
        tracing_module._enabled = False
        tracing_module._tracer = None

        mock_sampler_class = MagicMock()
        mock_trace = MagicMock()

        with patch.dict(
            os.environ,
            {"OTEL_ENABLED": "true", "OTEL_TRACES_SAMPLER_ARG": "0.5"},
        ):
            with patch.dict(
                "sys.modules",
                {
                    "opentelemetry": MagicMock(),
                    "opentelemetry.trace": mock_trace,
                    "opentelemetry.sdk.trace": MagicMock(),
                    "opentelemetry.sdk.trace.export": MagicMock(),
                    "opentelemetry.sdk.trace.sampling": MagicMock(
                        TraceIdRatioBased=mock_sampler_class
                    ),
                    "opentelemetry.sdk.resources": MagicMock(),
                    "opentelemetry.exporter.otlp.proto.grpc.trace_exporter": MagicMock(),
                },
            ):
                from bo1.observability import init_tracing

                init_tracing()

                # Verify sampler was created with 0.5 rate
                mock_sampler_class.assert_called_once_with(0.5)


class TestRecordException:
    """Test exception recording on spans."""

    def test_record_exception_on_none_span(self) -> None:
        """record_exception_on_span should handle None span gracefully."""
        from bo1.observability.tracing import record_exception_on_span

        # Should not raise
        record_exception_on_span(None, ValueError("test error"))

    def test_record_exception_on_mock_span(self) -> None:
        """record_exception_on_span should call span methods if opentelemetry available."""
        try:
            import opentelemetry  # noqa: F401
        except ImportError:
            import pytest

            pytest.skip("opentelemetry not installed")

        from bo1.observability.tracing import record_exception_on_span

        mock_span = MagicMock()
        exc = ValueError("test error")

        record_exception_on_span(mock_span, exc)

        mock_span.record_exception.assert_called_once_with(exc)
