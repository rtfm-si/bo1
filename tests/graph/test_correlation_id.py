"""Tests for correlation ID (request_id) propagation through graph nodes.

Verifies that request_id flows from initial state through deliberation pipeline.
"""

import logging
import uuid

from bo1.graph.state import DeliberationGraphState, create_initial_state
from bo1.models.problem import Problem


class TestCorrelationIdPropagation:
    """Test request_id flows through the deliberation pipeline."""

    def test_request_id_in_initial_state(self):
        """Verify request_id can be set in initial state."""
        request_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        problem = Problem(
            title="Test Problem",
            description="Test problem description",
            context="Test context",
        )
        state = create_initial_state(session_id=session_id, problem=problem, request_id=request_id)
        assert state.get("request_id") == request_id

    def test_request_id_none_by_default(self):
        """Verify request_id is None when not explicitly provided."""
        session_id = str(uuid.uuid4())
        problem = Problem(
            title="Test Problem",
            description="Test problem description",
            context="Test context",
        )
        state = create_initial_state(session_id=session_id, problem=problem)
        assert state.get("request_id") is None

    def test_log_with_session_includes_request_id(self, caplog):
        """Verify log_with_session properly formats request_id in logs."""
        # Import directly to avoid networkx dependency chain
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("utils", "bo1/graph/nodes/utils.py")
        utils_module = importlib.util.module_from_spec(spec)
        sys.modules["bo1.graph.nodes.utils_direct"] = utils_module
        spec.loader.exec_module(utils_module)
        log_with_session = utils_module.log_with_session

        request_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())

        with caplog.at_level(logging.INFO):
            log_with_session(
                logging.getLogger(__name__),
                logging.INFO,
                session_id,
                "Test log message",
                request_id=request_id,
            )

        # Check that request_id appears in logs (truncated to 8 chars)
        log_with_request = [r for r in caplog.records if request_id[:8] in r.getMessage()]
        assert len(log_with_request) > 0, f"Expected request_id {request_id[:8]} in logs"
        assert "request=" in log_with_request[0].getMessage()

    def test_log_with_session_handles_none_request_id(self, caplog):
        """Verify log_with_session works when request_id is None."""
        # Import directly to avoid networkx dependency chain
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("utils", "bo1/graph/nodes/utils.py")
        utils_module = importlib.util.module_from_spec(spec)
        sys.modules["bo1.graph.nodes.utils_direct"] = utils_module
        spec.loader.exec_module(utils_module)
        log_with_session = utils_module.log_with_session

        session_id = str(uuid.uuid4())

        with caplog.at_level(logging.INFO):
            log_with_session(
                logging.getLogger(__name__),
                logging.INFO,
                session_id,
                "Test log message",
                request_id=None,
            )

        # Check that log exists without request_id
        assert len(caplog.records) > 0
        assert "request=" not in caplog.records[0].getMessage()
        assert "session=" in caplog.records[0].getMessage()


class TestPromptRequestCorrelationId:
    """Test that PromptRequest propagates request_id."""

    def test_prompt_request_default_uuid(self):
        """Verify PromptRequest generates UUID by default."""
        from bo1.llm.broker import PromptRequest

        request = PromptRequest(
            system="test system",
            user_message="test message",
        )
        assert request.request_id is not None
        # Should be a valid UUID
        uuid.UUID(request.request_id)

    def test_prompt_request_custom_request_id(self):
        """Verify PromptRequest accepts custom request_id."""
        from bo1.llm.broker import PromptRequest

        custom_id = str(uuid.uuid4())
        request = PromptRequest(
            system="test system",
            user_message="test message",
            request_id=custom_id,
        )
        assert request.request_id == custom_id


class TestPersonaExecutorCorrelationId:
    """Test that PersonaExecutor propagates request_id from state."""

    def test_persona_executor_extracts_request_id(self):
        """Verify PersonaExecutor can access request_id from state."""
        from bo1.orchestration.persona_executor import PersonaExecutor

        request_id = str(uuid.uuid4())
        state: DeliberationGraphState = {
            "session_id": str(uuid.uuid4()),
            "request_id": request_id,
            "problem": None,
            "sub_problems": [],
            "current_sub_problem_index": 0,
            "personas": [],
            "contributions": [],
            "round_number": 0,
            "max_rounds": 4,
            "phase": None,
            "synthesis": None,
            "votes": [],
            "metrics": {},
        }

        executor = PersonaExecutor(state=state)
        assert executor.state is not None
        assert executor.state.get("request_id") == request_id
