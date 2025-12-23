"""Tests for LLM health probe module.

Tests cover:
- Probe result caching and TTL
- Probe success updates cache and metrics
- Probe failure increments failure counter
- Concurrent access to cached results
- Probe timeout handling
- Circuit breaker integration
- Background refresh task
"""

import asyncio
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from backend.api.llm_health_probe import (
    LLMHealthProbe,
    ProbeResult,
    get_llm_health_probe,
)


class TestProbeResult:
    """Tests for ProbeResult dataclass."""

    def test_to_dict_healthy(self):
        """Test converting healthy result to dict."""
        result = ProbeResult(
            healthy=True,
            latency_ms=234.567,
            error=None,
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
        )
        d = result.to_dict()
        assert d["healthy"] is True
        assert d["latency_ms"] == 234.6  # Rounded to 1 decimal
        assert d["error"] is None
        assert d["timestamp"] == "2025-01-15T12:00:00+00:00"

    def test_to_dict_unhealthy(self):
        """Test converting unhealthy result to dict."""
        result = ProbeResult(
            healthy=False,
            latency_ms=0.0,
            error="circuit_breaker_open",
            timestamp=datetime(2025, 1, 15, 12, 0, 0, tzinfo=UTC),
        )
        d = result.to_dict()
        assert d["healthy"] is False
        assert d["latency_ms"] == 0.0
        assert d["error"] == "circuit_breaker_open"


class TestLLMHealthProbe:
    """Tests for LLMHealthProbe class."""

    @pytest.fixture
    def probe(self):
        """Create a fresh probe instance for each test."""
        return LLMHealthProbe(ttl_seconds=30)

    def test_get_cached_status_empty(self, probe):
        """Test getting cached status when cache is empty."""
        result = probe.get_cached_status("anthropic")
        assert result is None

    def test_get_all_cached_statuses_empty(self, probe):
        """Test getting all cached statuses when cache is empty."""
        result = probe.get_all_cached_statuses()
        assert result == {}

    def test_is_cache_stale_missing(self, probe):
        """Test cache staleness check for missing entry."""
        assert probe.is_cache_stale("anthropic") is True

    def test_is_cache_stale_fresh(self, probe):
        """Test cache staleness check for fresh entry."""
        # Manually add a fresh entry
        probe._cache["anthropic"] = ProbeResult(
            healthy=True,
            latency_ms=100.0,
            error=None,
            timestamp=datetime.now(UTC),
        )
        assert probe.is_cache_stale("anthropic") is False

    def test_is_cache_stale_expired(self, probe):
        """Test cache staleness check for expired entry."""
        # Manually add an old entry (older than TTL)
        old_timestamp = datetime.now(UTC) - timedelta(seconds=60)
        probe._cache["anthropic"] = ProbeResult(
            healthy=True,
            latency_ms=100.0,
            error=None,
            timestamp=old_timestamp,
        )
        assert probe.is_cache_stale("anthropic") is True


class TestProbeProvider:
    """Tests for probe_provider method."""

    @pytest.fixture
    def probe(self):
        """Create a fresh probe instance for each test."""
        return LLMHealthProbe(ttl_seconds=30)

    @pytest.mark.asyncio
    async def test_probe_anthropic_success(self, probe):
        """Test successful Anthropic probe updates cache and metrics."""
        mock_response = MagicMock()

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("anthropic.AsyncAnthropic") as mock_client_class,
            patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb,
        ):
            # Setup mocks
            mock_cb = MagicMock()
            mock_cb.is_open = False
            mock_get_cb.return_value = mock_cb

            mock_client = MagicMock()
            mock_client.messages.count_tokens = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await probe.probe_provider("anthropic")

            assert result.healthy is True
            assert result.error is None
            assert result.latency_ms > 0
            assert probe.get_cached_status("anthropic") is not None

    @pytest.mark.asyncio
    async def test_probe_anthropic_circuit_open(self, probe):
        """Test Anthropic probe when circuit breaker is open."""
        with patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb:
            mock_cb = MagicMock()
            mock_cb.is_open = True
            mock_get_cb.return_value = mock_cb

            result = await probe.probe_provider("anthropic")

            assert result.healthy is False
            assert result.error == "circuit_breaker_open"
            assert result.latency_ms == 0.0

    @pytest.mark.asyncio
    async def test_probe_anthropic_no_api_key(self, probe):
        """Test Anthropic probe when API key is not configured."""
        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": ""}, clear=False),
            patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb,
        ):
            mock_cb = MagicMock()
            mock_cb.is_open = False
            mock_get_cb.return_value = mock_cb

            # Remove the key entirely
            with patch.dict("os.environ", {}, clear=False):
                import os

                os.environ.pop("ANTHROPIC_API_KEY", None)

                result = await probe.probe_provider("anthropic")

                assert result.healthy is False
                assert result.error == "api_key_not_configured"

    @pytest.mark.asyncio
    async def test_probe_openai_success(self, probe):
        """Test successful OpenAI probe updates cache."""
        mock_response = MagicMock()
        mock_response.data = []

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch("openai.AsyncOpenAI") as mock_client_class,
            patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb,
        ):
            mock_cb = MagicMock()
            mock_cb.is_open = False
            mock_get_cb.return_value = mock_cb

            mock_client = MagicMock()
            mock_client.models.list = AsyncMock(return_value=mock_response)
            mock_client_class.return_value = mock_client

            result = await probe.probe_provider("openai")

            assert result.healthy is True
            assert result.error is None
            assert probe.get_cached_status("openai") is not None

    @pytest.mark.asyncio
    async def test_probe_timeout_handling(self, probe):
        """Test probe timeout is handled correctly."""

        async def slow_call(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("anthropic.AsyncAnthropic") as mock_client_class,
            patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb,
        ):
            mock_cb = MagicMock()
            mock_cb.is_open = False
            mock_get_cb.return_value = mock_cb

            mock_client = MagicMock()
            mock_client.messages.count_tokens = slow_call
            mock_client_class.return_value = mock_client

            # Use a short timeout for the test
            with patch(
                "backend.api.llm_health_probe.LLM_HEALTH_PROBE_TIMEOUT_SECONDS",
                0.1,
            ):
                result = await probe.probe_provider("anthropic")

                assert result.healthy is False
                assert "timeout" in result.error.lower() or "TimeoutError" in result.error


class TestConcurrentAccess:
    """Tests for thread-safe cache access."""

    @pytest.mark.asyncio
    async def test_concurrent_cache_reads(self):
        """Test that multiple concurrent reads don't cause issues."""
        probe = LLMHealthProbe(ttl_seconds=30)

        # Pre-populate cache
        probe._cache["anthropic"] = ProbeResult(
            healthy=True,
            latency_ms=100.0,
            error=None,
            timestamp=datetime.now(UTC),
        )
        probe._cache["openai"] = ProbeResult(
            healthy=True,
            latency_ms=150.0,
            error=None,
            timestamp=datetime.now(UTC),
        )

        async def read_cache():
            for _ in range(100):
                probe.get_cached_status("anthropic")
                probe.get_cached_status("openai")
                probe.get_all_cached_statuses()
                probe.is_cache_stale("anthropic")
                await asyncio.sleep(0)

        # Run multiple concurrent readers
        await asyncio.gather(*[read_cache() for _ in range(10)])

        # Should complete without errors
        assert probe.get_cached_status("anthropic") is not None


class TestBackgroundRefresh:
    """Tests for background refresh task."""

    @pytest.mark.asyncio
    async def test_start_stop_lifecycle(self):
        """Test probe can be started and stopped cleanly."""
        probe = LLMHealthProbe(ttl_seconds=1)

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test", "OPENAI_API_KEY": "test"}),
            patch.object(probe, "probe_provider", new_callable=AsyncMock) as mock_probe,
        ):
            mock_probe.return_value = ProbeResult(
                healthy=True,
                latency_ms=100.0,
                error=None,
                timestamp=datetime.now(UTC),
            )

            await probe.start()
            assert probe._refresh_task is not None

            # Let it run briefly
            await asyncio.sleep(0.1)

            await probe.stop()
            assert probe._shutdown_event.is_set()

    @pytest.mark.asyncio
    async def test_disabled_via_env(self):
        """Test probe does not start when disabled via env var."""
        probe = LLMHealthProbe(ttl_seconds=1)

        with patch(
            "backend.api.llm_health_probe.LLM_HEALTH_PROBE_ENABLED",
            False,
        ):
            await probe.start()
            assert probe._refresh_task is None


class TestSingleton:
    """Tests for singleton accessor."""

    def test_get_llm_health_probe_returns_same_instance(self):
        """Test that get_llm_health_probe returns singleton."""
        # Reset singleton for test
        import backend.api.llm_health_probe as module

        module._probe_instance = None

        probe1 = get_llm_health_probe()
        probe2 = get_llm_health_probe()

        assert probe1 is probe2


class TestMetricsIntegration:
    """Tests for Prometheus metrics integration."""

    @pytest.mark.asyncio
    async def test_probe_records_latency_metric(self):
        """Test that successful probe records latency metric."""
        probe = LLMHealthProbe(ttl_seconds=30)

        with (
            patch.dict("os.environ", {"OPENAI_API_KEY": "test-key"}),
            patch("openai.AsyncOpenAI") as mock_client_class,
            patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb,
            patch("backend.api.middleware.metrics.bo1_llm_probe_latency_seconds") as mock_histogram,
            patch("backend.api.middleware.metrics.bo1_llm_provider_healthy") as mock_gauge,
        ):
            mock_cb = MagicMock()
            mock_cb.is_open = False
            mock_get_cb.return_value = mock_cb

            mock_client = MagicMock()
            mock_client.models.list = AsyncMock(return_value=MagicMock(data=[]))
            mock_client_class.return_value = mock_client

            await probe.probe_provider("openai")

            # Verify metrics were recorded
            mock_histogram.labels.assert_called_with(provider="openai")
            mock_histogram.labels().observe.assert_called()
            mock_gauge.labels.assert_called_with(provider="openai")
            mock_gauge.labels().set.assert_called_with(1)  # healthy=True

    @pytest.mark.asyncio
    async def test_probe_failure_records_result(self):
        """Test that probe failure returns correct result with error type."""
        probe = LLMHealthProbe(ttl_seconds=30)

        with (
            patch.dict("os.environ", {"ANTHROPIC_API_KEY": "test-key"}),
            patch("anthropic.AsyncAnthropic") as mock_client_class,
            patch("bo1.llm.circuit_breaker.get_circuit_breaker") as mock_get_cb,
        ):
            mock_cb = MagicMock()
            mock_cb.is_open = False
            mock_get_cb.return_value = mock_cb

            mock_client = MagicMock()
            mock_client.messages.count_tokens = AsyncMock(side_effect=ValueError("API error"))
            mock_client_class.return_value = mock_client

            result = await probe.probe_provider("anthropic")

            # Verify result indicates failure with error type
            assert result.healthy is False
            assert "ValueError" in result.error
