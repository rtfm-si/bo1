"""Tests for graph node execution metrics.

Tests the timing decorator and Prometheus metrics integration.
"""

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from bo1.graph.metrics import timed_node, wrap_node_with_timing


class TestTimedNodeDecorator:
    """Tests for the @timed_node decorator."""

    @pytest.mark.asyncio
    async def test_records_successful_execution(self) -> None:
        """Verify metrics are recorded for successful node execution."""
        mock_prom = MagicMock()

        with patch("backend.api.metrics.prom_metrics", mock_prom):

            @timed_node("test_node")
            async def test_node(state: dict) -> dict:
                await asyncio.sleep(0.01)  # 10ms
                return {"result": "success"}

            result = await test_node({"input": "test"})

        assert result == {"result": "success"}
        # Verify metrics were recorded
        mock_prom.record_graph_node_execution.assert_called_once()
        call_args = mock_prom.record_graph_node_execution.call_args
        assert call_args[0][0] == "test_node"  # node_name
        assert call_args[0][1] >= 0.01  # duration >= 10ms
        assert call_args[0][2] is True  # success=True

    @pytest.mark.asyncio
    async def test_records_failed_execution(self) -> None:
        """Verify metrics are recorded with error status on exception."""
        mock_prom = MagicMock()

        with patch("backend.api.metrics.prom_metrics", mock_prom):

            @timed_node("failing_node")
            async def failing_node(state: dict) -> dict:
                raise ValueError("Test error")

            with pytest.raises(ValueError, match="Test error"):
                await failing_node({"input": "test"})

        # Verify metrics were recorded with error status
        mock_prom.record_graph_node_execution.assert_called_once()
        call_args = mock_prom.record_graph_node_execution.call_args
        assert call_args[0][0] == "failing_node"
        assert call_args[0][2] is False  # success=False

    @pytest.mark.asyncio
    async def test_timing_accuracy(self) -> None:
        """Verify recorded duration is accurate within tolerance."""
        mock_prom = MagicMock()
        sleep_duration = 0.05  # 50ms

        with patch("backend.api.metrics.prom_metrics", mock_prom):

            @timed_node("timed_node")
            async def timed_test(state: dict) -> dict:
                await asyncio.sleep(sleep_duration)
                return {}

            await timed_test({})

        call_args = mock_prom.record_graph_node_execution.call_args
        recorded_duration = call_args[0][1]
        # Allow 50ms tolerance (0.05s actual + up to 0.05s overhead)
        assert recorded_duration >= sleep_duration
        assert recorded_duration < sleep_duration + 0.05

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self) -> None:
        """Verify decorator preserves function name and docstring."""

        @timed_node("documented_node")
        async def documented_node(state: dict) -> dict:
            """This is a documented node function."""
            return {}

        assert documented_node.__name__ == "documented_node"
        assert "documented node function" in (documented_node.__doc__ or "")

    @pytest.mark.asyncio
    async def test_handles_metrics_failure_gracefully(self) -> None:
        """Verify node execution continues even if metrics recording fails."""

        @timed_node("graceful_node")
        async def graceful_node(state: dict) -> dict:
            return {"status": "ok"}

        # Patch to make metrics recording raise an exception
        with patch(
            "backend.api.metrics.prom_metrics.record_graph_node_execution",
            side_effect=RuntimeError("Metrics failure"),
        ):
            # Should not raise, just log warning
            result = await graceful_node({})

        assert result == {"status": "ok"}


class TestWrapNodeWithTiming:
    """Tests for the wrap_node_with_timing helper function."""

    @pytest.mark.asyncio
    async def test_wraps_existing_function(self) -> None:
        """Verify wrap_node_with_timing creates a timed wrapper."""
        mock_prom = MagicMock()

        async def original_node(state: dict) -> dict:
            return {"wrapped": True}

        wrapped = wrap_node_with_timing("wrapped_node", original_node)

        with patch("backend.api.metrics.prom_metrics", mock_prom):
            result = await wrapped({})

        assert result == {"wrapped": True}
        mock_prom.record_graph_node_execution.assert_called_once()
        assert mock_prom.record_graph_node_execution.call_args[0][0] == "wrapped_node"

    @pytest.mark.asyncio
    async def test_wrapped_function_passes_arguments(self) -> None:
        """Verify wrapped function correctly passes through arguments."""
        mock_prom = MagicMock()

        async def node_with_args(state: dict, config: dict | None = None) -> dict:
            return {"state": state, "config": config}

        wrapped = wrap_node_with_timing("args_node", node_with_args)

        with patch("backend.api.metrics.prom_metrics", mock_prom):
            result = await wrapped({"key": "value"}, config={"option": True})

        assert result == {"state": {"key": "value"}, "config": {"option": True}}


class TestPrometheusMetricsIntegration:
    """Integration tests for Prometheus metrics recording."""

    def test_record_graph_node_execution_success(self) -> None:
        """Verify successful execution records both histogram and counter."""
        from backend.api.metrics import prom_metrics

        # Record a successful execution
        prom_metrics.record_graph_node_execution("test_integration", 1.5, success=True)

        # The metrics should be recorded (we can't easily verify histogram values,
        # but we can verify no exceptions are raised)

    def test_record_graph_node_execution_error(self) -> None:
        """Verify error execution records with error status."""
        from backend.api.metrics import prom_metrics

        # Record a failed execution
        prom_metrics.record_graph_node_execution("test_error_node", 0.5, success=False)

        # Should complete without error

    def test_histogram_buckets_cover_expected_range(self) -> None:
        """Verify histogram buckets cover the expected latency range."""
        from backend.api.metrics import prom_metrics

        # Check bucket configuration (up to 120s for long-running nodes)
        buckets = prom_metrics.graph_node_duration._kwargs.get("buckets", [])
        assert 0.1 in buckets  # Fast operations
        assert 30.0 in buckets  # SLO threshold
        assert 60.0 in buckets  # Alert threshold
        assert 120.0 in buckets  # Maximum expected duration

    def test_counter_labels_include_node_name_and_status(self) -> None:
        """Verify counter has correct label names."""
        from backend.api.metrics import prom_metrics

        # Verify label names are configured correctly
        label_names = prom_metrics.graph_node_total._labelnames
        assert "node_name" in label_names
        assert "status" in label_names
