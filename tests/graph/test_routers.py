"""Tests for graph router functions.

Specifically tests dict/object handling after checkpoint restoration.
"""

from bo1.graph.routers import route_after_synthesis


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
