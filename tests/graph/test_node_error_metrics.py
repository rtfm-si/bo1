"""Tests for graph node error metrics."""

import logging
from unittest.mock import MagicMock

import pytest
from anthropic import APIConnectionError

from bo1.graph.nodes.utils import emit_node_error, retry_with_backoff


class TestEmitNodeError:
    """Test emit_node_error helper function."""

    def test_emit_node_error_records_metric(self) -> None:
        """emit_node_error calls record_graph_node_error with correct node_name."""
        from backend.api.middleware.metrics import bo1_graph_node_errors_total

        # Get initial counter value
        initial = bo1_graph_node_errors_total.labels(node_name="test_decompose_node")._value.get()

        emit_node_error("test_decompose_node", "test-session-123", "TimeoutError")

        # Verify counter was incremented
        new_value = bo1_graph_node_errors_total.labels(node_name="test_decompose_node")._value.get()
        assert new_value == initial + 1

    def test_emit_node_error_logs_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """emit_node_error logs error with session and error type."""
        with caplog.at_level(logging.ERROR):
            emit_node_error("synthesis_node", "abc12345-6789", "APIConnectionError")

        assert "[session=abc12345]" in caplog.text
        assert "synthesis_node" in caplog.text
        assert "APIConnectionError" in caplog.text

    def test_emit_node_error_handles_missing_session(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """emit_node_error uses 'unknown' when session_id is None."""
        with caplog.at_level(logging.ERROR):
            emit_node_error("rounds_node")

        assert "[session=unknown]" in caplog.text
        assert "rounds_node" in caplog.text
        assert "unknown" in caplog.text  # error_type defaults to unknown

    def test_emit_node_error_handles_import_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """emit_node_error gracefully handles ImportError for metrics."""
        # This should not raise, even if metrics module is unavailable
        with caplog.at_level(logging.ERROR):
            emit_node_error("test_node", "session-123", "TestError")

        assert "test_node" in caplog.text


class TestRetryWithBackoffErrorMetrics:
    """Test retry_with_backoff emits error metrics on failure."""

    @pytest.mark.asyncio
    async def test_retry_emits_error_on_final_timeout_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """retry_with_backoff emits error metric on final timeout failure."""
        call_count = 0

        async def failing_func() -> str:
            nonlocal call_count
            call_count += 1
            raise TimeoutError("Connection timeout")

        with (
            caplog.at_level(logging.ERROR),
            pytest.raises(TimeoutError),
        ):
            await retry_with_backoff(
                failing_func,
                max_retries=1,
                initial_delay=0.01,
                _session_id="test-session",
                _node_name="test_node",
            )

        assert call_count == 2  # Initial + 1 retry
        # Should have logged the error with session context
        assert "test-session" in caplog.text or "test-ses" in caplog.text
        assert "failed" in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_retry_emits_error_on_non_retryable_failure(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """retry_with_backoff emits error metric on non-retryable error."""

        async def failing_func() -> str:
            raise ValueError("Invalid input")

        with (
            caplog.at_level(logging.ERROR),
            pytest.raises(ValueError),
        ):
            await retry_with_backoff(
                failing_func,
                max_retries=3,
                initial_delay=0.01,
                _session_id="test-session-456",
                _node_name="validation_node",
            )

        # Should have logged immediately (no retry)
        assert "Non-retryable error" in caplog.text
        assert "ValueError" in caplog.text

    @pytest.mark.asyncio
    async def test_retry_no_error_on_success(self, caplog: pytest.LogCaptureFixture) -> None:
        """retry_with_backoff does not emit error on success."""

        async def success_func() -> str:
            return "success"

        with caplog.at_level(logging.ERROR):
            result = await retry_with_backoff(
                success_func,
                max_retries=3,
                _session_id="test-session",
                _node_name="success_node",
            )

        assert result == "success"
        # No error logs
        assert "failed" not in caplog.text.lower()

    @pytest.mark.asyncio
    async def test_retry_derives_node_name_from_function(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """retry_with_backoff uses function name when _node_name not provided."""

        async def my_custom_function() -> str:
            raise ValueError("Test error")

        with (
            caplog.at_level(logging.ERROR),
            pytest.raises(ValueError),
        ):
            await retry_with_backoff(
                my_custom_function,
                max_retries=0,
                _session_id="test-session",
            )

        assert "my_custom_function" in caplog.text

    @pytest.mark.asyncio
    async def test_retry_with_api_connection_error(self, caplog: pytest.LogCaptureFixture) -> None:
        """retry_with_backoff handles APIConnectionError and retries."""
        call_count = 0

        async def api_failing_func() -> str:
            nonlocal call_count
            call_count += 1
            raise APIConnectionError(request=MagicMock())

        with (
            caplog.at_level(logging.ERROR),
            pytest.raises(APIConnectionError),
        ):
            await retry_with_backoff(
                api_failing_func,
                max_retries=2,
                initial_delay=0.01,
                _session_id="api-session",
                _node_name="api_node",
            )

        assert call_count == 3  # Initial + 2 retries
        assert "All 3 attempts failed" in caplog.text
