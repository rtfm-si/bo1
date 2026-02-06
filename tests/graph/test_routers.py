"""Tests for router functions."""

from unittest.mock import patch

from bo1.graph.router_utils import (
    get_problem_attr as _get_problem_attr,
)
from bo1.graph.router_utils import (
    get_subproblem_attr as _get_subproblem_attr,
)
from bo1.graph.router_utils import (
    validate_state_field as _validate_state_field,
)
from bo1.graph.routers import (
    route_clarification,
    route_convergence_check,
    route_facilitator_decision,
    route_subproblem_execution,
)


class TestRouteConvergenceCheck:
    """Tests for route_convergence_check router."""

    def test_should_stop_true_routes_to_vote(self):
        """Should route to vote when should_stop is True."""
        state = {"should_stop": True}

        result = route_convergence_check(state)

        assert result == "vote"

    def test_should_stop_false_routes_to_facilitator(self):
        """Should route to facilitator_decide when should_stop is False."""
        state = {"should_stop": False}

        result = route_convergence_check(state)

        assert result == "facilitator_decide"


class TestRouteSubproblemExecution:
    """Tests for route_subproblem_execution router."""

    def test_parallel_mode_true_routes_to_parallel(self):
        """Should route to parallel_subproblems when parallel_mode is True."""
        state = {"parallel_mode": True}

        result = route_subproblem_execution(state)

        assert result == "parallel_subproblems"

    def test_parallel_mode_false_routes_to_sequential(self):
        """Should route to select_personas when parallel_mode is False."""
        state = {"parallel_mode": False}

        result = route_subproblem_execution(state)

        assert result == "select_personas"


class TestRouteClarification:
    """Tests for route_clarification router."""

    def test_should_stop_true_routes_to_end(self):
        """Should route to END when should_stop is True (session paused)."""
        state = {"should_stop": True}

        result = route_clarification(state)

        assert result == "END"

    def test_should_stop_false_routes_to_persona(self):
        """Should route to persona_contribute when should_stop is False."""
        state = {"should_stop": False}

        result = route_clarification(state)

        assert result == "persona_contribute"


class TestValidationHelpers:
    """Tests for validation helper functions."""

    def test_validate_state_field_returns_value_when_present(self):
        """Should return field value when present."""
        state = {"facilitator_decision": {"action": "vote"}}

        result = _validate_state_field(state, "facilitator_decision", "test_router")

        assert result == {"action": "vote"}

    def test_validate_state_field_returns_none_when_missing(self):
        """Should return None when field is missing."""
        state = {}

        result = _validate_state_field(state, "facilitator_decision", "test_router")

        assert result is None

    def test_validate_state_field_logs_error_when_missing(self):
        """Should log GRAPH_STATE_ERROR with router context when field is missing."""
        state = {}

        with patch("bo1.graph.router_utils.log_error") as mock_log:
            _validate_state_field(state, "some_field", "my_router")

            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert call_args[0][1].name == "GRAPH_STATE_ERROR"
            assert "my_router" in call_args[0][2]
            assert "some_field" in call_args[0][2]


class TestRouteFacilitatorDecisionWithHelper:
    """Tests for route_facilitator_decision using validation helper."""

    def test_returns_end_when_no_decision(self):
        """Should return END when facilitator_decision is missing."""
        state = {}

        result = route_facilitator_decision(state)

        assert result == "END"

    def test_routes_to_vote_on_vote_action(self):
        """Should route to vote when action is vote."""
        state = {"facilitator_decision": {"action": "vote"}}

        result = route_facilitator_decision(state)

        assert result == "vote"

    def test_routes_to_persona_on_continue_action(self):
        """Should route to persona_contribute when action is continue."""
        state = {"facilitator_decision": {"action": "continue"}}

        result = route_facilitator_decision(state)

        assert result == "persona_contribute"

    def test_routes_to_persona_on_unknown_action(self):
        """Should fallback to persona_contribute on unknown action."""
        state = {"facilitator_decision": {"action": "unknown_action"}}

        result = route_facilitator_decision(state)

        assert result == "persona_contribute"


class TestGetProblemAttr:
    """Tests for _get_problem_attr helper."""

    def test_handles_dict_problem(self):
        """Should work with dict (checkpoint restored problem)."""
        problem = {"sub_problems": ["sp1", "sp2"]}

        result = _get_problem_attr(problem, "sub_problems", [])

        assert result == ["sp1", "sp2"]

    def test_handles_object_problem(self):
        """Should work with object problem."""

        class MockProblem:
            sub_problems = ["sp1"]

        result = _get_problem_attr(MockProblem(), "sub_problems", [])

        assert result == ["sp1"]

    def test_returns_default_when_none(self):
        """Should return default when problem is None."""
        result = _get_problem_attr(None, "sub_problems", [])

        assert result == []


class TestGetSubproblemAttr:
    """Tests for _get_subproblem_attr helper."""

    def test_handles_dict_subproblem(self):
        """Should work with dict (checkpoint restored sub-problem)."""
        sp = {"id": "sp-001", "goal": "Test goal"}

        result = _get_subproblem_attr(sp, "goal")

        assert result == "Test goal"

    def test_handles_object_subproblem(self):
        """Should work with object sub-problem."""

        class MockSubProblem:
            id = "sp-001"
            goal = "Object goal"

        result = _get_subproblem_attr(MockSubProblem(), "goal")

        assert result == "Object goal"

    def test_returns_default_when_none(self):
        """Should return default when sub-problem is None."""
        result = _get_subproblem_attr(None, "goal", "default")

        assert result == "default"
