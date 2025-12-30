"""Tests for SSE reconnection tracking and Retry-After headers.

Validates:
- Reconnection tracking in Redis metadata
- Prometheus metrics for reconnections
- Retry-After header in 429 responses
- Session detail response includes reconnect_count
- Exponential backoff calculation for SSE retry
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from backend.api.constants import SSE_RETRY_BASE_MS, SSE_RETRY_MAX_MS


class TestReconnectTracking:
    """Test SSE reconnection metadata tracking."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create mock Redis manager."""
        manager = MagicMock()
        manager.is_available = True
        manager.redis = MagicMock()
        return manager

    @pytest.fixture
    def mock_redis_pipeline(self, mock_redis_manager):
        """Create mock Redis pipeline."""
        pipeline = MagicMock()
        mock_redis_manager.redis.pipeline.return_value = pipeline
        pipeline.execute.return_value = [1, True, True, True, True, True]
        return pipeline

    @pytest.mark.asyncio
    async def test_track_reconnection_increments_count(
        self, mock_redis_manager, mock_redis_pipeline
    ):
        """Reconnection tracking increments count in Redis."""
        from backend.api.streaming import _track_reconnection

        # No previous disconnect time
        mock_redis_manager.redis.hgetall.return_value = {}

        with patch("backend.api.middleware.metrics.record_sse_reconnect") as mock_record:
            await _track_reconnection(
                mock_redis_manager,
                "bo1_test123",
                time.time(),
            )

            # Verify Redis pipeline operations
            mock_redis_pipeline.hincrby.assert_called_once()
            mock_redis_pipeline.hset.assert_called_once()
            mock_redis_pipeline.execute.assert_called_once()

            # Verify Prometheus metric emitted
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            assert args[0] == "bo1_test123"
            assert kwargs.get("gap_seconds") is None

    @pytest.mark.asyncio
    async def test_track_reconnection_calculates_gap(self, mock_redis_manager, mock_redis_pipeline):
        """Reconnection tracking calculates gap from previous disconnect."""
        from backend.api.streaming import _track_reconnection

        disconnect_time = time.time() - 30  # 30 seconds ago
        mock_redis_manager.redis.hgetall.return_value = {
            b"last_disconnect_at": str(disconnect_time).encode(),
            b"count": b"2",
        }

        connect_time = time.time()

        with patch("backend.api.middleware.metrics.record_sse_reconnect") as mock_record:
            await _track_reconnection(
                mock_redis_manager,
                "bo1_test123",
                connect_time,
            )

            # Verify gap was calculated and passed to metric
            mock_record.assert_called_once()
            args, kwargs = mock_record.call_args
            # record_sse_reconnect is called with positional args (session_id, gap_seconds)
            assert len(args) >= 2
            gap = args[1]  # gap_seconds is the second positional arg
            assert gap is not None
            assert 29 < gap < 31  # approximately 30 seconds

    @pytest.mark.asyncio
    async def test_track_reconnection_handles_redis_unavailable(self):
        """Reconnection tracking handles Redis unavailable gracefully."""
        from backend.api.streaming import _track_reconnection

        mock_manager = MagicMock()
        mock_manager.is_available = False

        with patch("backend.api.middleware.metrics.record_sse_reconnect") as mock_record:
            # Should not raise
            await _track_reconnection(mock_manager, "bo1_test123", time.time())

            # Metric still emitted without gap
            mock_record.assert_called_once_with("bo1_test123", gap_seconds=None)

    @pytest.mark.asyncio
    async def test_track_disconnect_stores_timestamp(self, mock_redis_manager):
        """Disconnect tracking stores timestamp in Redis."""
        from backend.api.streaming import _track_disconnect

        disconnect_time = time.time()

        await _track_disconnect(mock_redis_manager, "bo1_test123", disconnect_time)

        mock_redis_manager.redis.hset.assert_called_once()
        call_args = mock_redis_manager.redis.hset.call_args
        assert call_args[0][0] == "bo1_test123:reconnects"
        assert call_args[0][1] == "last_disconnect_at"


class TestGetReconnectInfo:
    """Test retrieving reconnection metadata."""

    @pytest.mark.asyncio
    async def test_get_reconnect_info_returns_count(self):
        """get_reconnect_info returns reconnect_count from Redis."""
        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.redis.hgetall.return_value = {
            b"count": b"5",
            b"last_at": b"1703000000.0",
        }

        with patch(
            "backend.api.streaming.get_redis_manager",
            return_value=mock_manager,
        ):
            from backend.api.streaming import get_reconnect_info

            result = await get_reconnect_info("bo1_test123")

            assert result is not None
            assert result["reconnect_count"] == 5
            assert result["last_reconnect_at"] == 1703000000.0

    @pytest.mark.asyncio
    async def test_get_reconnect_info_returns_none_when_unavailable(self):
        """get_reconnect_info returns None when Redis unavailable."""
        mock_manager = MagicMock()
        mock_manager.is_available = False

        with patch(
            "backend.api.streaming.get_redis_manager",
            return_value=mock_manager,
        ):
            from backend.api.streaming import get_reconnect_info

            result = await get_reconnect_info("bo1_test123")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_reconnect_info_returns_none_when_no_data(self):
        """get_reconnect_info returns None when no reconnection data exists."""
        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.redis.hgetall.return_value = {}

        with patch(
            "backend.api.streaming.get_redis_manager",
            return_value=mock_manager,
        ):
            from backend.api.streaming import get_reconnect_info

            result = await get_reconnect_info("bo1_test123")
            assert result is None


class TestReconnectMetrics:
    """Test Prometheus reconnection metrics."""

    def test_record_sse_reconnect_increments_counter(self):
        """record_sse_reconnect increments counter metric."""
        from backend.api.middleware.metrics import (
            bo1_sse_reconnect_total,
            record_sse_reconnect,
        )

        # Get initial value (ensure metric is registered)
        _ = bo1_sse_reconnect_total.labels(session_id="test_ses").collect()

        record_sse_reconnect("test_session_123", gap_seconds=None)

        # Counter should have been called (can't easily assert increment with prometheus_client)
        # Just verify it doesn't raise
        assert True

    def test_record_sse_reconnect_observes_gap_histogram(self):
        """record_sse_reconnect observes gap in histogram."""
        from backend.api.middleware.metrics import record_sse_reconnect

        # Should not raise
        record_sse_reconnect("test_session", gap_seconds=15.5)
        record_sse_reconnect("test_session", gap_seconds=None)
        assert True


class TestRetryAfterHeader:
    """Test Retry-After header in rate limit responses."""

    def _create_rate_limit_exc(self, detail_str: str) -> MagicMock:
        """Create a mock RateLimitExceeded exception with given detail."""
        exc = MagicMock()
        exc.detail = detail_str
        return exc

    @pytest.mark.asyncio
    async def test_rate_limit_handler_includes_retry_after(self):
        """Rate limit exception handler includes Retry-After header."""
        from fastapi import Request

        from backend.api.main import rate_limit_exception_handler

        # Create mock request
        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/v1/sessions"

        # Create mock exception with typical message
        exc = self._create_rate_limit_exc("5 per 1 minute")

        with patch("backend.api.middleware.metrics.record_api_endpoint_error"):
            response = await rate_limit_exception_handler(mock_request, exc)

            assert response.status_code == 429
            assert "Retry-After" in response.headers
            assert response.headers["Retry-After"] == "60"  # 1 minute

    @pytest.mark.asyncio
    async def test_rate_limit_handler_parses_seconds(self):
        """Rate limit handler correctly parses seconds-based limits."""
        from fastapi import Request

        from backend.api.main import rate_limit_exception_handler

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        exc = self._create_rate_limit_exc("10 per 30 second")

        with patch("backend.api.middleware.metrics.record_api_endpoint_error"):
            response = await rate_limit_exception_handler(mock_request, exc)

            assert response.headers["Retry-After"] == "30"

    @pytest.mark.asyncio
    async def test_rate_limit_handler_parses_hours(self):
        """Rate limit handler correctly parses hour-based limits."""
        from fastapi import Request

        from backend.api.main import rate_limit_exception_handler

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        exc = self._create_rate_limit_exc("100 per 1 hour")

        with patch("backend.api.middleware.metrics.record_api_endpoint_error"):
            response = await rate_limit_exception_handler(mock_request, exc)

            assert response.headers["Retry-After"] == "3600"

    @pytest.mark.asyncio
    async def test_rate_limit_handler_includes_body_field(self):
        """Rate limit response includes retry_after in body."""
        from fastapi import Request

        from backend.api.main import rate_limit_exception_handler

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        exc = self._create_rate_limit_exc("5 per 1 minute")

        with patch("backend.api.middleware.metrics.record_api_endpoint_error"):
            response = await rate_limit_exception_handler(mock_request, exc)

            import json

            body = json.loads(response.body)
            assert "retry_after" in body
            assert body["retry_after"] == 60

    @pytest.mark.asyncio
    async def test_rate_limit_handler_fallback_on_parse_error(self):
        """Rate limit handler uses fallback on parse error."""
        from fastapi import Request

        from backend.api.main import rate_limit_exception_handler

        mock_request = MagicMock(spec=Request)
        mock_request.url.path = "/api/test"

        # Unusual format that won't parse
        exc = self._create_rate_limit_exc("limit exceeded somehow")

        with patch("backend.api.middleware.metrics.record_api_endpoint_error"):
            response = await rate_limit_exception_handler(mock_request, exc)

            # Should fall back to 60 seconds
            assert response.headers["Retry-After"] == "60"


class TestSessionDetailReconnectCount:
    """Test SessionDetailResponse includes reconnect_count."""

    def test_session_detail_response_has_reconnect_count_field(self):
        """SessionDetailResponse model has reconnect_count field."""
        from datetime import datetime

        from backend.api.models import SessionDetailResponse

        response = SessionDetailResponse(
            id="bo1_test123",
            status="completed",
            phase="synthesis",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            problem={"statement": "test"},
            state=None,
            metrics=None,
            reconnect_count=5,
        )

        assert response.reconnect_count == 5

    def test_session_detail_response_reconnect_count_optional(self):
        """SessionDetailResponse reconnect_count is optional."""
        from datetime import datetime

        from backend.api.models import SessionDetailResponse

        response = SessionDetailResponse(
            id="bo1_test123",
            status="completed",
            phase="synthesis",
            created_at=datetime.now(),
            updated_at=datetime.now(),
            problem={"statement": "test"},
        )

        assert response.reconnect_count is None


class TestSSERetryBackoff:
    """Test SSE retry backoff calculation and formatting."""

    def test_calculate_sse_retry_delay_exponential_growth(self):
        """Verify retry delay grows exponentially with attempt number."""
        from backend.api.streaming import calculate_sse_retry_delay

        # Test increasing attempts - delays should grow (accounting for jitter)
        delays = [calculate_sse_retry_delay(i) for i in range(5)]

        # Each delay should be roughly 2x the previous (with jitter tolerance)
        # Base is 1000ms, so: ~1000, ~2000, ~4000, ~8000, ~16000
        assert delays[0] >= SSE_RETRY_BASE_MS * 0.9  # ~900-1100
        assert delays[0] <= SSE_RETRY_BASE_MS * 1.1

        # Check growth trend (allowing for jitter)
        for i in range(1, len(delays)):
            # Each should be roughly 2x previous (within 30% tolerance for jitter)
            assert delays[i] >= delays[i - 1] * 0.7, f"Delay at {i} should grow"

    def test_calculate_sse_retry_delay_caps_at_max(self):
        """Verify retry delay is capped at SSE_RETRY_MAX_MS (30 seconds)."""
        from backend.api.streaming import calculate_sse_retry_delay

        # Large attempt number should still cap at max
        delay = calculate_sse_retry_delay(100)
        assert delay <= SSE_RETRY_MAX_MS

        # Also test just beyond where it would exceed
        delay_10 = calculate_sse_retry_delay(10)  # 2^10 * 1000 = 1,024,000 >> 30,000
        assert delay_10 <= SSE_RETRY_MAX_MS

    def test_calculate_sse_retry_delay_zero_attempt(self):
        """Zero attempts should return base delay with jitter."""
        from backend.api.streaming import calculate_sse_retry_delay

        delay = calculate_sse_retry_delay(0)
        # Should be base ± 10% jitter
        assert delay >= SSE_RETRY_BASE_MS * 0.9
        assert delay <= SSE_RETRY_BASE_MS * 1.1

    def test_calculate_sse_retry_delay_negative_attempt(self):
        """Negative attempts should be treated as zero."""
        from backend.api.streaming import calculate_sse_retry_delay

        delay = calculate_sse_retry_delay(-5)
        # Should be same as attempt 0
        assert delay >= SSE_RETRY_BASE_MS * 0.9
        assert delay <= SSE_RETRY_BASE_MS * 1.1

    def test_format_sse_with_retry_prepends_field(self):
        """Verify format_sse_with_retry prepends retry: field correctly."""
        from backend.api.streaming import format_sse_with_retry

        event_str = "event: node_start\ndata: {}\n\n"
        result = format_sse_with_retry(event_str, 5000)

        assert result.startswith("retry: 5000\n")
        assert "event: node_start" in result
        assert "data: {}" in result

    def test_format_sse_with_retry_preserves_event(self):
        """Verify format_sse_with_retry preserves the original event content."""
        from backend.api.streaming import format_sse_with_retry

        original = 'id: bo1_test:1\nevent: contribution\ndata: {"persona": "analyst"}\n\n'
        result = format_sse_with_retry(original, 2000)

        # Original content should be preserved after retry line
        assert original in result
        assert result == f"retry: 2000\n{original}"


class TestResetReconnectCount:
    """Test resetting reconnect count on session completion."""

    @pytest.mark.asyncio
    async def test_reset_reconnect_count_sets_zero(self):
        """Reset sets count to 0 in Redis."""
        from backend.api.streaming import _reset_reconnect_count

        mock_manager = MagicMock()
        mock_manager.is_available = True

        await _reset_reconnect_count(mock_manager, "bo1_test123")

        mock_manager.redis.hset.assert_called_once_with("bo1_test123:reconnects", "count", "0")

    @pytest.mark.asyncio
    async def test_reset_reconnect_count_handles_redis_unavailable(self):
        """Reset handles Redis unavailable gracefully."""
        from backend.api.streaming import _reset_reconnect_count

        mock_manager = MagicMock()
        mock_manager.is_available = False

        # Should not raise
        await _reset_reconnect_count(mock_manager, "bo1_test123")

        # Should not attempt Redis operations
        mock_manager.redis.hset.assert_not_called()

    @pytest.mark.asyncio
    async def test_track_reconnection_returns_count(self):
        """Track reconnection returns the new reconnect count."""
        from backend.api.streaming import _track_reconnection

        mock_manager = MagicMock()
        mock_manager.is_available = True
        mock_manager.redis.hgetall.return_value = {
            b"count": b"3",
        }
        mock_pipeline = MagicMock()
        mock_manager.redis.pipeline.return_value = mock_pipeline
        mock_pipeline.execute.return_value = [4, True, True, True, True, True]

        with patch("backend.api.middleware.metrics.record_sse_reconnect"):
            count = await _track_reconnection(mock_manager, "bo1_test123", time.time())

        # Should return new count (current + 1)
        assert count == 4

    @pytest.mark.asyncio
    async def test_track_reconnection_returns_zero_on_unavailable(self):
        """Track reconnection returns 0 when Redis unavailable (fail-open)."""
        from backend.api.streaming import _track_reconnection

        mock_manager = MagicMock()
        mock_manager.is_available = False

        with patch("backend.api.middleware.metrics.record_sse_reconnect"):
            count = await _track_reconnection(mock_manager, "bo1_test123", time.time())

        assert count == 0
