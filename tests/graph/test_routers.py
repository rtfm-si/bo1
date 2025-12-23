"""Tests for graph router functions.

Specifically tests dict/object handling after checkpoint restoration.
"""

from unittest.mock import patch

from bo1.graph.routers import (
    _validate_state_field,
    route_after_synthesis,
    route_facilitator_decision,
)


class TestRouteAfterSynthesis:
    """Tests for route_after_synthesis with dict-based problem."""

    def test_handles_dict_problem_single_subproblem(self):
        """Should handle problem as dict (after checkpoint restore) with single sub-problem."""
        state = {
            "problem": {
                "statement": "Test problem",
                "sub_problems": [{"id": "sp1", "goal": "Goal 1"}],
            },
            "sub_problem_index": 0,
            "sub_problem_results": [],
        }

        result = route_after_synthesis(state)
        # Single sub-problem -> END (atomic optimization)
        assert result == "END"

    def test_handles_dict_problem_multiple_subproblems_incomplete(self):
        """Should route to next_subproblem when more sub-problems exist."""
        state = {
            "problem": {
                "statement": "Test problem",
                "sub_problems": [
                    {"id": "sp1", "goal": "Goal 1"},
                    {"id": "sp2", "goal": "Goal 2"},
                ],
            },
            "sub_problem_index": 0,
            "sub_problem_results": [],
        }

        result = route_after_synthesis(state)
        assert result == "next_subproblem"

    def test_handles_dict_problem_all_complete(self):
        """Should route to meta_synthesis when all sub-problems complete."""
        from bo1.models.state import SubProblemResult

        state = {
            "problem": {
                "statement": "Test problem",
                "sub_problems": [
                    {"id": "sp1", "goal": "Goal 1"},
                    {"id": "sp2", "goal": "Goal 2"},
                ],
            },
            "sub_problem_index": 1,  # Last sub-problem
            "sub_problem_results": [
                SubProblemResult(
                    sub_problem_id="sp1",
                    sub_problem_goal="Goal 1",
                    synthesis="Result 1",
                    contribution_count=1,
                    cost=0.0,
                    duration_seconds=1.0,
                ),
                SubProblemResult(
                    sub_problem_id="sp2",
                    sub_problem_goal="Goal 2",
                    synthesis="Result 2",
                    contribution_count=1,
                    cost=0.0,
                    duration_seconds=1.0,
                ),
            ],
        }

        result = route_after_synthesis(state)
        assert result == "meta_synthesis"

    def test_handles_missing_problem(self):
        """Should return END when problem is None."""
        state = {
            "problem": None,
            "sub_problem_index": 0,
            "sub_problem_results": [],
        }

        result = route_after_synthesis(state)
        assert result == "END"


class TestValidationHelpers:
    """Tests for _validate_state_field helper."""

    def test_validate_state_field_returns_value_when_present(self):
        """Should return field value when present in state."""
        state = {"facilitator_decision": {"action": "vote"}}

        result = _validate_state_field(state, "facilitator_decision", "test_router")

        assert result == {"action": "vote"}

    def test_validate_state_field_returns_none_when_missing(self):
        """Should return None when field is missing from state."""
        state = {}

        result = _validate_state_field(state, "facilitator_decision", "test_router")

        assert result is None

    def test_validate_state_field_returns_none_when_none(self):
        """Should return None when field value is None."""
        state = {"facilitator_decision": None}

        result = _validate_state_field(state, "facilitator_decision", "test_router")

        assert result is None

    def test_validate_state_field_returns_none_when_empty(self):
        """Should return None when field value is empty (falsy)."""
        state = {"facilitator_decision": {}}

        result = _validate_state_field(state, "facilitator_decision", "test_router")

        assert result is None

    def test_validate_state_field_logs_error_when_missing(self):
        """Should log GRAPH_STATE_ERROR with router context when field is missing."""
        state = {}

        with patch("bo1.graph.routers.log_error") as mock_log:
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

    def test_routes_to_persona_contribute_on_continue_action(self):
        """Should route to persona_contribute when action is continue."""
        state = {"facilitator_decision": {"action": "continue"}}

        result = route_facilitator_decision(state)

        assert result == "persona_contribute"
