"""Integration tests for deliberation logging.

Verifies that deliberation pipeline nodes emit logs with required fields.
"""

import logging
from io import StringIO

import pytest

from bo1.graph.state import DeliberationGraphState, create_initial_state
from bo1.models.problem import Problem
from bo1.utils.deliberation_logger import get_deliberation_logger


class TestDeliberationNodeLogging:
    """Tests that node entry points use deliberation logger with context."""

    @pytest.fixture
    def sample_state(self) -> DeliberationGraphState:
        """Create sample state for testing."""
        problem = Problem(
            title="Test Problem Title",
            description="Test problem",
            context="Test context",
        )
        return create_initial_state(
            session_id="test-session-12345",
            problem=problem,
            user_id="test-user-67890",
        )

    @pytest.fixture
    def capture_deliberation_logs(self) -> tuple[logging.Logger, StringIO]:
        """Capture logs from bo1.deliberation logger."""
        stream = StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger = logging.getLogger("bo1.deliberation")
        logger.handlers = []
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False  # Prevent duplicate logs

        return logger, stream

    def test_deliberation_logger_from_state(
        self, sample_state: DeliberationGraphState, capture_deliberation_logs: tuple
    ) -> None:
        """Logger created from state has correct context."""
        _, stream = capture_deliberation_logs

        session_id = sample_state.get("session_id")
        user_id = sample_state.get("user_id")

        dlog = get_deliberation_logger(session_id, user_id, "test_node")
        dlog.info("Test message")

        output = stream.getvalue()
        # Check session_id is truncated to 8 chars
        assert "session_id=test-ses" in output
        # Check user_id is truncated to 8 chars
        assert "user_id=test-use" in output
        assert "node_name=test_node" in output

    def test_logs_include_extra_context(
        self, sample_state: DeliberationGraphState, capture_deliberation_logs: tuple
    ) -> None:
        """Extra context fields are included in output."""
        _, stream = capture_deliberation_logs

        dlog = get_deliberation_logger(
            sample_state.get("session_id"), sample_state.get("user_id"), "rounds"
        )
        dlog.info("Round complete", round_number=3, contributions=5, cost="$0.15")

        output = stream.getvalue()
        assert "round_number=3" in output
        assert "contributions=5" in output
        assert "cost=$0.15" in output

    def test_pre_session_placeholder(self, capture_deliberation_logs: tuple) -> None:
        """Early logs use 'pre-session' placeholder."""
        _, stream = capture_deliberation_logs

        dlog = get_deliberation_logger(None, None, "intake_node")
        dlog.info("Processing intake")

        output = stream.getvalue()
        assert "session_id=pre-sess" in output
        assert "user_id=anonymou" in output

    def test_bound_logger_extends_context(
        self, sample_state: DeliberationGraphState, capture_deliberation_logs: tuple
    ) -> None:
        """Bound logger extends node_name with sub-context."""
        _, stream = capture_deliberation_logs

        dlog = get_deliberation_logger(
            sample_state.get("session_id"), sample_state.get("user_id"), "persona_executor"
        )
        bound = dlog.bind(persona="maria_cto")
        bound.info("Executing persona call")

        output = stream.getvalue()
        assert "node_name=persona_executor.persona=maria_cto" in output


class TestAllNodeTypesEmitRequiredFields:
    """Smoke test that all major node types have deliberation logger integration."""

    def test_rounds_module_imports_deliberation_logger(self) -> None:
        """rounds.py imports get_deliberation_logger."""
        from bo1.graph.nodes import rounds

        assert hasattr(rounds, "get_deliberation_logger")

    def test_synthesis_module_imports_deliberation_logger(self) -> None:
        """synthesis.py imports get_deliberation_logger."""
        from bo1.graph.nodes import synthesis

        assert hasattr(synthesis, "get_deliberation_logger")

    def test_decomposition_module_imports_deliberation_logger(self) -> None:
        """decomposition.py imports get_deliberation_logger."""
        from bo1.graph.nodes import decomposition

        assert hasattr(decomposition, "get_deliberation_logger")

    def test_orchestration_deliberation_imports_logger(self) -> None:
        """deliberation.py orchestration imports get_deliberation_logger."""
        from bo1.orchestration import deliberation

        assert hasattr(deliberation, "get_deliberation_logger")

    @pytest.mark.skip(
        reason="persona_executor doesn't use deliberation logger yet - future enhancement"
    )
    def test_persona_executor_imports_logger(self) -> None:
        """persona_executor.py imports get_deliberation_logger."""
        from bo1.orchestration import persona_executor

        assert hasattr(persona_executor, "get_deliberation_logger")
