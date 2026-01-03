"""Unit tests for router_utils module."""

import logging

from bo1.graph.router_utils import (
    get_problem_attr,
    get_subproblem_attr,
    log_routing_decision,
    validate_state_field,
)


class TestValidateStateField:
    """Tests for validate_state_field helper."""

    def test_returns_value_when_present(self):
        """Should return field value when field exists and has value."""
        state = {"my_field": "my_value"}
        result = validate_state_field(state, "my_field", "test_router")
        assert result == "my_value"

    def test_returns_none_when_missing(self, caplog):
        """Should return None and log error when field is missing."""
        state = {}
        with caplog.at_level(logging.ERROR):
            result = validate_state_field(state, "missing_field", "test_router")

        assert result is None
        assert "test_router: No missing_field in state" in caplog.text

    def test_returns_none_when_falsy(self, caplog):
        """Should return None for falsy values (empty list, None, etc)."""
        state = {"empty_list": [], "none_value": None, "empty_string": ""}

        with caplog.at_level(logging.ERROR):
            assert validate_state_field(state, "empty_list", "test_router") is None
            assert validate_state_field(state, "none_value", "test_router") is None
            assert validate_state_field(state, "empty_string", "test_router") is None


class TestGetProblemAttr:
    """Tests for get_problem_attr helper."""

    def test_returns_attr_from_object(self):
        """Should return attribute from object."""

        class MockProblem:
            sub_problems = ["sp1", "sp2"]

        result = get_problem_attr(MockProblem(), "sub_problems")
        assert result == ["sp1", "sp2"]

    def test_returns_key_from_dict(self):
        """Should return key value from dict (checkpoint restoration case)."""
        problem_dict = {"sub_problems": ["sp1", "sp2"], "id": "problem-123"}
        result = get_problem_attr(problem_dict, "sub_problems")
        assert result == ["sp1", "sp2"]

    def test_returns_default_when_none(self):
        """Should return default when problem is None."""
        result = get_problem_attr(None, "sub_problems", default=[])
        assert result == []

    def test_returns_default_when_missing(self):
        """Should return default when attribute is missing."""

        class MockProblem:
            pass

        result = get_problem_attr(MockProblem(), "nonexistent", default="fallback")
        assert result == "fallback"


class TestGetSubproblemAttr:
    """Tests for get_subproblem_attr helper."""

    def test_returns_attr_from_object(self):
        """Should return attribute from SubProblem object."""

        class MockSubProblem:
            id = "sp-123"
            goal = "Test goal"

        result = get_subproblem_attr(MockSubProblem(), "goal")
        assert result == "Test goal"

    def test_returns_key_from_dict(self):
        """Should return key value from dict (checkpoint restoration case)."""
        sp_dict = {"id": "sp-123", "goal": "Test goal"}
        result = get_subproblem_attr(sp_dict, "goal")
        assert result == "Test goal"

    def test_returns_default_when_none(self):
        """Should return default when sub-problem is None."""
        result = get_subproblem_attr(None, "goal", default="unknown")
        assert result == "unknown"

    def test_returns_default_when_missing(self):
        """Should return default when attribute is missing."""
        sp_dict = {"id": "sp-123"}
        result = get_subproblem_attr(sp_dict, "nonexistent", default="N/A")
        assert result == "N/A"


class TestLogRoutingDecision:
    """Tests for @log_routing_decision decorator."""

    def test_logs_entry_and_exit(self, caplog):
        """Should log entry context and exit decision."""

        @log_routing_decision("test_router")
        def my_router(state):
            return "next_node"

        state = {"phase": "discussion", "round_number": 3}

        with caplog.at_level(logging.INFO):
            result = my_router(state)

        assert result == "next_node"
        assert "test_router: Entry" in caplog.text
        assert "phase=discussion" in caplog.text
        assert "round=3" in caplog.text
        assert "test_router: Decision -> next_node" in caplog.text

    def test_preserves_function_metadata(self):
        """Should preserve function name and docstring via functools.wraps."""

        @log_routing_decision("test_router")
        def my_documented_router(state):
            """This is the docstring."""
            return "result"

        assert my_documented_router.__name__ == "my_documented_router"
        assert my_documented_router.__doc__ == """This is the docstring."""

    def test_logs_available_context_only(self, caplog):
        """Should only log context fields that are present."""

        @log_routing_decision("minimal_router")
        def minimal_router(state):
            return "result"

        # State with only phase set
        state = {"phase": "selection"}

        with caplog.at_level(logging.INFO):
            minimal_router(state)

        assert "phase=selection" in caplog.text
        # round and sp_idx not in state, should not appear
        assert "round=" not in caplog.text
        assert "sp_idx=" not in caplog.text

    def test_logs_no_context_when_empty(self, caplog):
        """Should log 'no context' when state has no relevant fields."""

        @log_routing_decision("empty_router")
        def empty_router(state):
            return "result"

        state = {"unrelated_field": "value"}

        with caplog.at_level(logging.INFO):
            empty_router(state)

        assert "empty_router: Entry (no context)" in caplog.text

    def test_handles_should_stop_field(self, caplog):
        """Should include should_stop in context when present."""

        @log_routing_decision("stop_router")
        def stop_router(state):
            return "vote"

        state = {"should_stop": True, "round_number": 5}

        with caplog.at_level(logging.INFO):
            stop_router(state)

        assert "should_stop=True" in caplog.text
        assert "round=5" in caplog.text
