"""Tests for metrics collection system."""

import pytest

from backend.api.metrics import MetricsCollector, track_api_call


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    def test_increment_counter(self):
        """Test counter increments correctly."""
        collector = MetricsCollector()
        collector.increment("test.counter", 5)
        collector.increment("test.counter", 3)

        stats = collector.get_stats()
        assert stats["counters"]["test.counter"] == 8

    def test_observe_histogram(self):
        """Test histogram records values."""
        collector = MetricsCollector()
        collector.observe("test.duration", 0.1)
        collector.observe("test.duration", 0.2)
        collector.observe("test.duration", 0.3)

        stats = collector.get_stats()
        hist = stats["histograms"]["test.duration"]

        assert hist["count"] == 3
        assert hist["avg"] == pytest.approx(0.2)
        assert hist["min"] == 0.1
        assert hist["max"] == 0.3
        assert hist["sum"] == pytest.approx(0.6)

    def test_histogram_percentiles(self):
        """Test histogram percentile calculations."""
        collector = MetricsCollector()

        # Add 100 values from 1 to 100
        for i in range(1, 101):
            collector.observe("test.values", float(i))

        stats = collector.get_stats()
        hist = stats["histograms"]["test.values"]

        assert hist["count"] == 100
        # Percentiles use int(count * percentile) as index, so p50 = index 50 = value 51
        assert hist["p50"] == 51.0  # Median (index 50 → value 51)
        assert hist["p95"] == 96.0  # 95th percentile (index 95 → value 96)
        assert hist["p99"] == 100.0  # 99th percentile (index 99 → value 100)

    def test_empty_histogram_stats(self):
        """Test histogram stats for empty histogram."""
        collector = MetricsCollector()
        stats = collector.get_stats()

        # Empty histograms should not appear in stats
        assert "empty.histogram" not in stats["histograms"]

        # But if we call _histogram_stats directly, it should return zeros
        empty_stats = collector._histogram_stats([])
        assert empty_stats["count"] == 0
        assert empty_stats["sum"] == 0.0
        assert empty_stats["avg"] == 0.0

    def test_reset_metrics(self):
        """Test resetting all metrics."""
        collector = MetricsCollector()
        collector.increment("test.counter", 10)
        collector.observe("test.duration", 1.5)

        # Verify metrics exist
        stats = collector.get_stats()
        assert stats["counters"]["test.counter"] == 10
        assert len(stats["histograms"]["test.duration"]) > 0

        # Reset
        collector.reset()

        # Verify metrics are gone
        stats = collector.get_stats()
        assert len(stats["counters"]) == 0
        assert len(stats["histograms"]) == 0

    def test_multiple_counters(self):
        """Test multiple independent counters."""
        collector = MetricsCollector()
        collector.increment("api.sessions.get.success")
        collector.increment("api.sessions.get.success")
        collector.increment("api.sessions.post.success")
        collector.increment("api.sessions.get.error")

        stats = collector.get_stats()
        assert stats["counters"]["api.sessions.get.success"] == 2
        assert stats["counters"]["api.sessions.post.success"] == 1
        assert stats["counters"]["api.sessions.get.error"] == 1

    def test_multiple_histograms(self):
        """Test multiple independent histograms."""
        collector = MetricsCollector()
        collector.observe("api.sessions.get.duration", 0.1)
        collector.observe("api.sessions.get.duration", 0.2)
        collector.observe("api.sessions.post.duration", 0.5)

        stats = collector.get_stats()
        assert stats["histograms"]["api.sessions.get.duration"]["count"] == 2
        assert stats["histograms"]["api.sessions.post.duration"]["count"] == 1


class TestTrackApiCall:
    """Test the track_api_call context manager."""

    def test_track_success(self):
        """Test tracking successful API call."""
        collector = MetricsCollector()

        # Manually inject collector for testing
        from backend.api import metrics as metrics_module

        original_metrics = metrics_module.metrics
        metrics_module.metrics = collector

        try:
            with track_api_call("test.endpoint", "GET"):
                pass  # Simulated successful call

            stats = collector.get_stats()
            assert stats["counters"]["api.test.endpoint.get.success"] == 1
            assert "api.test.endpoint.get.duration" in stats["histograms"]
            assert stats["histograms"]["api.test.endpoint.get.duration"]["count"] == 1
        finally:
            metrics_module.metrics = original_metrics

    def test_track_error(self):
        """Test tracking failed API call."""
        collector = MetricsCollector()

        from backend.api import metrics as metrics_module

        original_metrics = metrics_module.metrics
        metrics_module.metrics = collector

        try:
            with pytest.raises(ValueError):
                with track_api_call("test.endpoint", "POST"):
                    raise ValueError("Test error")

            stats = collector.get_stats()
            assert stats["counters"]["api.test.endpoint.post.error"] == 1
            assert "api.test.endpoint.post.duration" in stats["histograms"]
        finally:
            metrics_module.metrics = original_metrics

    def test_track_duration(self):
        """Test that duration is recorded in milliseconds."""
        import time

        collector = MetricsCollector()

        from backend.api import metrics as metrics_module

        original_metrics = metrics_module.metrics
        metrics_module.metrics = collector

        try:
            with track_api_call("test.endpoint", "GET"):
                time.sleep(0.01)  # Sleep for 10ms

            stats = collector.get_stats()
            hist = stats["histograms"]["api.test.endpoint.get.duration"]

            # Duration should be at least 0.01 seconds (but likely slightly more)
            assert hist["min"] >= 0.01
            assert hist["max"] >= 0.01
        finally:
            metrics_module.metrics = original_metrics

    def test_track_multiple_calls(self):
        """Test tracking multiple calls to same endpoint."""
        collector = MetricsCollector()

        from backend.api import metrics as metrics_module

        original_metrics = metrics_module.metrics
        metrics_module.metrics = collector

        try:
            # 3 successful calls
            for _ in range(3):
                with track_api_call("test.endpoint", "GET"):
                    pass

            # 2 failed calls
            for _ in range(2):
                try:
                    with track_api_call("test.endpoint", "GET"):
                        raise RuntimeError("Test error")
                except RuntimeError:
                    pass

            stats = collector.get_stats()
            assert stats["counters"]["api.test.endpoint.get.success"] == 3
            assert stats["counters"]["api.test.endpoint.get.error"] == 2
            assert stats["histograms"]["api.test.endpoint.get.duration"]["count"] == 5
        finally:
            metrics_module.metrics = original_metrics


class TestMetricsIntegration:
    """Integration tests for metrics system."""

    def test_metrics_format(self):
        """Test that metrics output format is correct."""
        collector = MetricsCollector()
        collector.increment("test.counter1", 10)
        collector.increment("test.counter2", 5)
        collector.observe("test.histogram1", 1.5)
        collector.observe("test.histogram1", 2.5)

        stats = collector.get_stats()

        # Verify structure
        assert "counters" in stats
        assert "histograms" in stats

        # Verify counter format
        assert isinstance(stats["counters"], dict)
        assert stats["counters"]["test.counter1"] == 10
        assert stats["counters"]["test.counter2"] == 5

        # Verify histogram format
        assert isinstance(stats["histograms"], dict)
        hist = stats["histograms"]["test.histogram1"]
        assert "count" in hist
        assert "sum" in hist
        assert "avg" in hist
        assert "min" in hist
        assert "max" in hist
        assert "p50" in hist
        assert "p95" in hist
        assert "p99" in hist

    def test_concurrent_updates(self):
        """Test that metrics handle concurrent updates (basic thread-safety check)."""
        import threading

        collector = MetricsCollector()

        def increment_counter():
            for _ in range(100):
                collector.increment("test.concurrent")

        # Start 10 threads, each incrementing 100 times
        threads = [threading.Thread(target=increment_counter) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        stats = collector.get_stats()
        # Should have 10 * 100 = 1000 increments
        assert stats["counters"]["test.concurrent"] == 1000


class TestCacheStats:
    """Test cache statistics calculation (P1: prompt cache monitoring)."""

    def test_get_cache_stats_calculates_hit_rate(self):
        """Test that cache hit rate is calculated correctly."""
        collector = MetricsCollector()

        # Simulate 3 cache hits and 2 misses
        collector.increment("llm.cache.hits", 3)
        collector.increment("llm.cache.misses", 2)

        stats = collector.get_stats()
        cache = stats["cache"]

        assert cache["hits"] == 3
        assert cache["misses"] == 2
        assert cache["total_calls"] == 5
        assert cache["hit_rate"] == pytest.approx(0.6)  # 3/5 = 0.6

    def test_get_cache_stats_zero_calls(self):
        """Test that cache stats handle zero calls gracefully."""
        collector = MetricsCollector()

        stats = collector.get_stats()
        cache = stats["cache"]

        assert cache["hits"] == 0
        assert cache["misses"] == 0
        assert cache["total_calls"] == 0
        assert cache["hit_rate"] == 0.0  # No division by zero

    def test_get_cache_stats_tokens_saved(self):
        """Test that tokens saved are aggregated correctly."""
        collector = MetricsCollector()

        collector.observe("llm.cache.tokens_saved", 1000.0)
        collector.observe("llm.cache.tokens_saved", 500.0)
        collector.observe("llm.cache.tokens_saved", 250.0)

        stats = collector.get_stats()
        cache = stats["cache"]

        assert cache["tokens_saved"] == 1750.0

    def test_get_cache_stats_cost_saved(self):
        """Test that cost saved is aggregated correctly."""
        collector = MetricsCollector()

        collector.observe("llm.cache.cost_saved", 0.05)
        collector.observe("llm.cache.cost_saved", 0.03)

        stats = collector.get_stats()
        cache = stats["cache"]

        assert cache["cost_saved"] == pytest.approx(0.08)

    def test_get_cache_stats_included_in_get_stats(self):
        """Test that cache stats are included in the main stats output."""
        collector = MetricsCollector()
        collector.increment("llm.cache.hits", 1)

        stats = collector.get_stats()

        assert "cache" in stats
        assert "counters" in stats
        assert "histograms" in stats


class TestPrometheusMetrics:
    """Tests for Prometheus metrics."""

    def test_normalize_model_sonnet(self) -> None:
        """Test model name normalization for Sonnet."""
        from backend.api.metrics import prom_metrics

        # Use global instance to avoid duplicate registration
        assert prom_metrics._normalize_model("claude-sonnet-4-5-20250929") == "sonnet-4.5"
        assert prom_metrics._normalize_model("claude-sonnet-4.5-latest") == "sonnet-4.5"

    def test_normalize_model_haiku(self) -> None:
        """Test model name normalization for Haiku."""
        from backend.api.metrics import prom_metrics

        assert prom_metrics._normalize_model("claude-haiku-4-5-20251001") == "haiku-4.5"
        assert prom_metrics._normalize_model("claude-3-5-haiku-20241022") == "haiku-3.5"

    def test_normalize_model_opus(self) -> None:
        """Test model name normalization for Opus."""
        from backend.api.metrics import prom_metrics

        assert prom_metrics._normalize_model("claude-opus-4-20250514") == "opus-4"

    def test_normalize_model_voyage(self) -> None:
        """Test model name normalization for Voyage."""
        from backend.api.metrics import prom_metrics

        assert prom_metrics._normalize_model("voyage-3") == "voyage-3"
        assert prom_metrics._normalize_model("voyage-3-large") == "voyage-3-large"

    def test_normalize_model_unknown(self) -> None:
        """Test model name normalization for unknown models."""
        from backend.api.metrics import prom_metrics

        assert prom_metrics._normalize_model(None) == "unknown"
        assert (
            prom_metrics._normalize_model("some-very-long-model-name-that-exceeds")
            == "some-very-long-model"
        )

    def test_record_cost_zero(self) -> None:
        """Test that zero cost is not recorded."""
        from backend.api.metrics import prom_metrics

        # This should not raise any errors
        prom_metrics.record_cost("anthropic", "sonnet-4.5", 0.0)

    def test_record_tokens(self) -> None:
        """Test token recording does not raise."""
        from backend.api.metrics import prom_metrics

        # This should not raise any errors
        prom_metrics.record_tokens(
            provider="anthropic",
            model="claude-sonnet-4-5-20250929",
            input_tokens=1000,
            output_tokens=200,
            cache_read_tokens=500,
            cache_write_tokens=100,
        )

    def test_record_event(self) -> None:
        """Test event recording does not raise."""
        from backend.api.metrics import prom_metrics

        prom_metrics.record_event("contribution", "success")
        prom_metrics.record_event("error", "error")

    def test_sse_connection_tracking(self) -> None:
        """Test SSE connection gauge operations."""
        from backend.api.metrics import prom_metrics

        # These should not raise any errors
        prom_metrics.sse_connection_opened()
        prom_metrics.sse_connection_closed()


class TestPrometheusEndpoint:
    """Tests for /metrics endpoint."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi.testclient import TestClient

        from backend.api.main import app

        return TestClient(app)

    def test_metrics_endpoint_exists(self, client) -> None:
        """Test that /metrics endpoint exists and returns prometheus format."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus format starts with # HELP or metric names
        content = response.text
        assert "http_request" in content or "# HELP" in content or "# TYPE" in content

    def test_metrics_endpoint_content_type(self, client) -> None:
        """Test that /metrics returns correct content type."""
        response = client.get("/metrics")
        assert response.status_code == 200
        # Prometheus metrics use text/plain or openmetrics format
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type or "text/openmetrics" in content_type
