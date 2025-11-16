"""Unit tests for multi-sub-problem iteration (Day 36.5)."""

from bo1.graph.routers import route_after_synthesis
from bo1.graph.state import DeliberationGraphState
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import DeliberationMetrics, DeliberationPhase


class TestRouteAfterSynthesis:
    """Test the route_after_synthesis router function."""

    def test_route_to_next_subproblem_when_more_exist(self):
        """Should route to next_subproblem when more sub-problems exist."""
        # Create problem with 3 sub-problems
        problem = Problem(
            title="Test Problem",
            description="Should we invest?",
            context="Testing multi-sub-problem",
            sub_problems=[
                SubProblem(
                    id="sp_001",
                    goal="Analyze CAC",
                    context="",
                    complexity_score=5,
                    dependencies=[],
                ),
                SubProblem(
                    id="sp_002",
                    goal="Choose channel",
                    context="",
                    complexity_score=6,
                    dependencies=["sp_001"],
                ),
                SubProblem(
                    id="sp_003",
                    goal="Allocate budget",
                    context="",
                    complexity_score=7,
                    dependencies=["sp_001", "sp_002"],
                ),
            ],
        )

        # State after completing first sub-problem (index=0)
        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=problem.sub_problems[0],
            personas=[],
            contributions=[],
            round_summaries=[],
            phase=DeliberationPhase.SYNTHESIS,
            round_number=1,
            max_rounds=10,
            metrics=DeliberationMetrics(),
            facilitator_decision=None,
            should_stop=False,
            stop_reason=None,
            user_input=None,
            current_node="synthesize",
            votes=[],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=0,  # Just finished first sub-problem
        )

        result = route_after_synthesis(state)

        assert result == "next_subproblem"

    def test_route_to_meta_synthesis_when_all_complete(self):
        """Should route to meta_synthesis when all sub-problems complete."""
        # Create problem with 2 sub-problems
        problem = Problem(
            title="Test Problem",
            description="Should we invest?",
            context="Testing multi-sub-problem",
            sub_problems=[
                SubProblem(
                    id="sp_001", goal="SP1", context="", complexity_score=5, dependencies=[]
                ),
                SubProblem(
                    id="sp_002", goal="SP2", context="", complexity_score=6, dependencies=[]
                ),
            ],
        )

        # State after completing second (last) sub-problem (index=1)
        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=problem.sub_problems[1],
            personas=[],
            contributions=[],
            round_summaries=[],
            phase=DeliberationPhase.SYNTHESIS,
            round_number=1,
            max_rounds=10,
            metrics=DeliberationMetrics(),
            facilitator_decision=None,
            should_stop=False,
            stop_reason=None,
            user_input=None,
            current_node="synthesize",
            votes=[],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=1,  # Just finished second (last) sub-problem
        )

        result = route_after_synthesis(state)

        assert result == "meta_synthesis"

    def test_route_to_end_for_atomic_problem(self):
        """Should route directly to END for atomic problems (1 sub-problem)."""
        # Create problem with only 1 sub-problem
        problem = Problem(
            title="Atomic Problem",
            description="Simple problem",
            context="Testing atomic",
            sub_problems=[
                SubProblem(
                    id="sp_001", goal="Only SP", context="", complexity_score=5, dependencies=[]
                )
            ],
        )

        # State after completing the only sub-problem
        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=problem.sub_problems[0],
            personas=[],
            contributions=[],
            round_summaries=[],
            phase=DeliberationPhase.SYNTHESIS,
            round_number=1,
            max_rounds=10,
            metrics=DeliberationMetrics(),
            facilitator_decision=None,
            should_stop=False,
            stop_reason=None,
            user_input=None,
            current_node="synthesize",
            votes=[],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=0,
        )

        result = route_after_synthesis(state)

        # Atomic optimization: skip meta-synthesis
        assert result == "END"
