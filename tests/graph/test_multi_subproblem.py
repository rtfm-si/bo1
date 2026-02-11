"""Unit tests for multi-sub-problem iteration (Day 36.5)."""

import pytest

from bo1.graph.nodes import next_subproblem_node
from bo1.graph.routers import route_after_synthesis
from bo1.graph.state import DeliberationGraphState
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationMetrics, DeliberationPhase


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
            recommendations=[],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=0,  # Just finished first sub-problem
        )

        result = route_after_synthesis(state)

        assert result == "next_subproblem"

    def test_route_to_next_subproblem_for_last_sp(self):
        """Should route to next_subproblem even for last SP (to save result first).

        RACE CONDITION FIX: Previously routed directly to meta_synthesis,
        but that happened before the result was saved. Now we always go
        through next_subproblem first, then route_after_next_subproblem
        decides whether to continue or go to meta_synthesis.
        """
        from bo1.models.state import SubProblemResult

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

        # Create mock result for first sub-problem only
        # Note: sp2 result not yet in list - that's the fix!
        # The old code expected it here, but it's added by next_subproblem_node
        sub_problem_results = [
            SubProblemResult(
                sub_problem_id="sp_001",
                sub_problem_goal="SP1",
                synthesis="Synthesis for SP1",
                recommendations=[],
                contribution_count=5,
                cost=0.50,
                duration_seconds=30.0,
                expert_panel=["expert1", "expert2"],
            ),
        ]

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
            recommendations=[],
            synthesis="Test synthesis",
            sub_problem_results=sub_problem_results,
            sub_problem_index=1,  # Just finished second (last) sub-problem
        )

        result = route_after_synthesis(state)

        # Always routes to next_subproblem to save result first
        assert result == "next_subproblem"

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
            recommendations=[],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=0,
        )

        result = route_after_synthesis(state)

        # Atomic optimization: skip meta-synthesis
        assert result == "END"


def create_test_persona(code: str = "test_persona") -> PersonaProfile:
    """Helper to create a minimal PersonaProfile for testing."""
    from bo1.models.persona import PersonaCategory, ResponseStyle

    return PersonaProfile(
        id="test-id",
        code=code,
        name="Test Persona",
        archetype="Test",
        category=PersonaCategory.FINANCE,
        description="Test persona",
        emoji="🧪",
        color_hex="#000000",
        traits={"analytical": 0.8, "creative": 0.5, "collaborative": 0.7},
        default_weight=1.0,
        temperature=0.7,
        system_prompt="Test system prompt",
        response_style=ResponseStyle.ANALYTICAL,
        display_name="Test",
        domain_expertise=["testing"],
    )


@pytest.mark.unit
@pytest.mark.asyncio
class TestNextSubproblemNode:
    """Test the next_subproblem_node function."""

    async def test_increments_index_correctly(self):
        """Should increment sub_problem_index when moving to next."""
        problem = Problem(
            title="Test",
            description="Test problem",
            context="",
            sub_problems=[
                SubProblem(
                    id="sp_001", goal="SP1", context="", complexity_score=5, dependencies=[]
                ),
                SubProblem(
                    id="sp_002", goal="SP2", context="", complexity_score=6, dependencies=[]
                ),
            ],
        )

        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=problem.sub_problems[0],
            personas=[create_test_persona()],
            contributions=[],
            round_summaries=[],
            phase=DeliberationPhase.SYNTHESIS,
            round_number=3,
            max_rounds=10,
            metrics=DeliberationMetrics(total_cost=0.05),
            facilitator_decision=None,
            should_stop=False,
            stop_reason=None,
            user_input=None,
            current_node="synthesize",
            recommendations=[],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=0,
        )

        result = await next_subproblem_node(state)

        assert result["sub_problem_index"] == 1
        assert result["current_sub_problem"] == problem.sub_problems[1]

    async def test_resets_deliberation_state(self):
        """Should reset contributions, votes, and round_number for new sub-problem."""
        problem = Problem(
            title="Test",
            description="Test problem",
            context="",
            sub_problems=[
                SubProblem(
                    id="sp_001", goal="SP1", context="", complexity_score=5, dependencies=[]
                ),
                SubProblem(
                    id="sp_002", goal="SP2", context="", complexity_score=6, dependencies=[]
                ),
            ],
        )

        # State with some contributions and votes from first sub-problem
        from bo1.models.state import ContributionType

        contribution = ContributionMessage(
            persona_code="test_persona",
            persona_name="Test",
            content="Some contribution",
            thinking=None,
            contribution_type=ContributionType.INITIAL,
            round_number=2,
            token_count=None,
            cost=None,
        )

        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=problem.sub_problems[0],
            personas=[create_test_persona()],
            contributions=[contribution],
            round_summaries=["Round 1 summary"],
            phase=DeliberationPhase.SYNTHESIS,
            round_number=3,
            max_rounds=10,
            metrics=DeliberationMetrics(total_cost=0.05),
            facilitator_decision=None,
            should_stop=False,
            stop_reason=None,
            user_input=None,
            current_node="synthesize",
            votes=[{"persona_code": "test_persona", "recommendation": "Yes"}],
            synthesis="Test synthesis",
            sub_problem_results=[],
            sub_problem_index=0,
        )

        result = await next_subproblem_node(state)

        # Should reset deliberation state
        assert result["contributions"] == []
        assert result["recommendations"] == []
        assert result["round_number"] == 0  # Will be set to 1 by initial_round_node
        assert result["round_summaries"] == []
        assert result["synthesis"] is None
        assert result["facilitator_decision"] is None
        assert result["should_stop"] is False
        assert result["stop_reason"] is None

    async def test_saves_sub_problem_result(self):
        """Should save current sub-problem result before moving to next."""
        problem = Problem(
            title="Test",
            description="Test problem",
            context="",
            sub_problems=[
                SubProblem(
                    id="sp_001", goal="SP1", context="", complexity_score=5, dependencies=[]
                ),
                SubProblem(
                    id="sp_002", goal="SP2", context="", complexity_score=6, dependencies=[]
                ),
            ],
        )

        from bo1.models.state import ContributionType

        contribution = ContributionMessage(
            persona_code="test_persona",
            persona_name="Test",
            content="Test contribution",
            thinking=None,
            contribution_type=ContributionType.INITIAL,
            round_number=1,
            token_count=None,
            cost=None,
        )

        state = DeliberationGraphState(
            session_id="test-session",
            problem=problem,
            current_sub_problem=problem.sub_problems[0],
            personas=[create_test_persona()],
            contributions=[contribution],
            round_summaries=[],
            phase=DeliberationPhase.SYNTHESIS,
            round_number=2,
            max_rounds=10,
            metrics=DeliberationMetrics(total_cost=0.05, phase_costs={"test": 0.05}),
            facilitator_decision=None,
            should_stop=False,
            stop_reason=None,
            user_input=None,
            current_node="synthesize",
            recommendations=[],
            synthesis="SP1 synthesis",
            sub_problem_results=[],
            sub_problem_index=0,
        )

        result = await next_subproblem_node(state)

        # Should have saved result
        assert len(result["sub_problem_results"]) == 1

        saved_result = result["sub_problem_results"][0]
        assert saved_result.sub_problem_id == "sp_001"
        assert saved_result.sub_problem_goal == "SP1"
        assert saved_result.synthesis == "SP1 synthesis"
        assert saved_result.contribution_count == 1
        assert saved_result.expert_panel == ["test_persona"]
        assert saved_result.cost == 0.05
