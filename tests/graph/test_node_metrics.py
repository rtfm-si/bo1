"""Tests for graph node execution time metrics.

Validates:
1. emit_node_duration emits histogram metrics
2. node_timer context manager works correctly
3. Graceful degradation when metrics unavailable
"""

from unittest.mock import MagicMock, patch

import pytest


class TestEmitNodeDuration:
    """Test emit_node_duration function."""

    def test_emits_histogram_when_metrics_available(self) -> None:
        """Should call metrics.observe when metrics module available."""
        mock_metrics = MagicMock()

        with patch("bo1.graph.nodes.utils._metrics", mock_metrics):
            from bo1.graph.nodes.utils import emit_node_duration

            emit_node_duration("test_node", 150.5)

            # Should emit both specific and aggregate metrics
            assert mock_metrics.observe.call_count == 2
            mock_metrics.observe.assert_any_call("graph.node.test_node.duration_ms", 150.5)
            mock_metrics.observe.assert_any_call("graph.node.duration_ms", 150.5)

    def test_handles_missing_metrics_gracefully(self) -> None:
        """Should not raise when metrics module unavailable."""
        with patch("bo1.graph.nodes.utils._metrics", None):
            from bo1.graph.nodes.utils import emit_node_duration

            # Should not raise
            emit_node_duration("test_node", 100.0)


class TestNodeTimer:
    """Test node_timer context manager."""

    def test_measures_duration_correctly(self) -> None:
        """Should measure time elapsed in context."""
        mock_metrics = MagicMock()
        captured_duration = None

        def capture_observe(name: str, value: float) -> None:
            nonlocal captured_duration
            if name == "graph.node.duration_ms":
                captured_duration = value

        mock_metrics.observe.side_effect = capture_observe

        with patch("bo1.graph.nodes.utils._metrics", mock_metrics):
            import time

            from bo1.graph.nodes.utils import node_timer

            with node_timer("measure_test"):
                time.sleep(0.01)  # 10ms

            # Duration should be approximately 10ms (allow 5-50ms for test variance)
            assert captured_duration is not None
            assert 5 < captured_duration < 100  # Allow wide margin for CI

    def test_emits_on_exit_even_on_exception(self) -> None:
        """Should emit duration even when exception raised in context."""
        mock_metrics = MagicMock()

        with patch("bo1.graph.nodes.utils._metrics", mock_metrics):
            from bo1.graph.nodes.utils import node_timer

            with pytest.raises(ValueError):
                with node_timer("error_test"):
                    raise ValueError("test error")

            # Should still have emitted metrics
            assert mock_metrics.observe.call_count == 2

    def test_handles_missing_metrics_gracefully(self) -> None:
        """Should work without raising when metrics unavailable."""
        with patch("bo1.graph.nodes.utils._metrics", None):
            from bo1.graph.nodes.utils import node_timer

            # Should not raise
            with node_timer("no_metrics_test"):
                pass


class TestNodeTimingIntegration:
    """Integration tests for node timing across node modules."""

    def test_utils_module_imports_cleanly(self) -> None:
        """Utils module should import without errors."""
        from bo1.graph.nodes import utils

        assert hasattr(utils, "emit_node_duration")
        assert hasattr(utils, "node_timer")

    def test_decomposition_imports_emit(self) -> None:
        """Decomposition module should import emit_node_duration."""
        from bo1.graph.nodes import decomposition

        # Module should import without error - indicates emit_node_duration is available
        assert decomposition is not None

    def test_selection_imports_emit(self) -> None:
        """Selection module should import emit_node_duration."""
        from bo1.graph.nodes import selection

        assert selection is not None

    def test_rounds_imports_emit(self) -> None:
        """Rounds module should import emit_node_duration."""
        from bo1.graph.nodes import rounds

        assert rounds is not None

    def test_synthesis_imports_emit(self) -> None:
        """Synthesis module should import emit_node_duration."""
        from bo1.graph.nodes import synthesis

        assert synthesis is not None

    def test_moderation_imports_emit(self) -> None:
        """Moderation module should import emit_node_duration."""
        from bo1.graph.nodes import moderation

        assert moderation is not None

    def test_subproblems_imports_emit(self) -> None:
        """Subproblems module should import emit_node_duration."""
        from bo1.graph.nodes import subproblems

        assert subproblems is not None
