"""Tests for subgraph state transformation helpers."""

import pytest

from bo1.graph.deliberation.subgraph.state import (
    SubProblemGraphState,
    build_expert_memory,
    create_subproblem_initial_state,
    result_from_subgraph_state,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationMetrics, SubProblemResult


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        title="Market Expansion Strategy",
        description="How should we approach market expansion?",
        context="We are a SaaS company looking to expand internationally.",
        sub_problems=[
            SubProblem(
                id="sp_1",
                goal="Identify target markets",
                context="Need to evaluate potential markets",
                complexity_score=5,
                dependencies=[],
            ),
            SubProblem(
                id="sp_2",
                goal="Develop pricing strategy",
                context="Pricing for international markets",
                complexity_score=6,
                dependencies=["sp_1"],
            ),
        ],
    )


# Note: Uses sample_personas fixture from conftest.py which loads real personas from catalog


class TestCreateSubproblemInitialState:
    """Tests for create_subproblem_initial_state()."""

    def test_creates_state_with_required_fields(
        self, sample_problem: Problem, sample_personas: list[PersonaProfile]
    ):
        """State should contain all required fields."""
        state = create_subproblem_initial_state(
            session_id="test_session",
            sub_problem=sample_problem.sub_problems[0],
            sub_problem_index=0,
            parent_problem=sample_problem,
            all_available_personas=sample_personas,
            expert_memory={},
        )

        assert state["session_id"] == "test_session"
        assert state["sub_problem_index"] == 0
        assert state["sub_problem"].id == "sp_1"
        assert state["parent_problem"].title == "Market Expansion Strategy"
        assert len(state["all_available_personas"]) == 2
        assert state["personas"] == []  # Empty until selected
        assert state["contributions"] == []
        assert state["round_number"] == 0
        assert state["should_stop"] is False

    def test_adaptive_max_rounds_based_on_complexity(
        self, sample_problem: Problem, sample_personas: list[PersonaProfile]
    ):
        """Max rounds should be set based on sub-problem complexity."""
        # Low complexity (3 rounds)
        low_complexity_sp = SubProblem(
            id="sp_low",
            goal="Simple task",
            context="Easy",
            complexity_score=2,
            dependencies=[],
        )
        state = create_subproblem_initial_state(
            session_id="test",
            sub_problem=low_complexity_sp,
            sub_problem_index=0,
            parent_problem=sample_problem,
            all_available_personas=sample_personas,
            expert_memory={},
        )
        assert state["max_rounds"] == 3

        # Medium complexity (4-5 rounds)
        state = create_subproblem_initial_state(
            session_id="test",
            sub_problem=sample_problem.sub_problems[0],  # complexity 5
            sub_problem_index=0,
            parent_problem=sample_problem,
            all_available_personas=sample_personas,
            expert_memory={},
        )
        assert state["max_rounds"] in [4, 5]

    def test_expert_memory_passed_through(
        self, sample_problem: Problem, sample_personas: list[PersonaProfile]
    ):
        """Expert memory should be included in state."""
        memory = {
            "strategist": "Previously recommended focusing on EU markets",
            "finance_expert": "Suggested premium pricing tier",
        }
        state = create_subproblem_initial_state(
            session_id="test",
            sub_problem=sample_problem.sub_problems[1],
            sub_problem_index=1,
            parent_problem=sample_problem,
            all_available_personas=sample_personas,
            expert_memory=memory,
        )

        assert state["expert_memory"] == memory


class TestResultFromSubgraphState:
    """Tests for result_from_subgraph_state()."""

    def test_extracts_result_from_completed_state(self, sample_personas: list[PersonaProfile]):
        """Should extract SubProblemResult from final state."""
        # Get persona codes from fixture
        persona_codes = [p.code for p in sample_personas]
        first_persona = sample_personas[0]

        final_state: SubProblemGraphState = {
            "session_id": "test",
            "sub_problem_index": 0,
            "sub_problem": SubProblem(
                id="sp_1",
                goal="Test goal",
                context="Test context",
                complexity_score=5,
                dependencies=[],
            ),
            "parent_problem": Problem(
                title="Test Problem",
                description="Test description",
                context="Test",
                sub_problems=[],
            ),
            "personas": sample_personas,
            "all_available_personas": sample_personas,
            "contributions": [
                ContributionMessage(
                    persona_code=first_persona.code,
                    persona_name=first_persona.name,
                    content="My analysis...",
                    round_number=1,
                )
            ],
            "round_summaries": ["Round 1 summary"],
            "round_number": 2,
            "max_rounds": 4,
            "should_stop": True,
            "stop_reason": "convergence",
            "facilitator_decision": None,
            "metrics": DeliberationMetrics(total_cost=0.05),
            "current_phase": "convergence",
            "experts_per_round": [persona_codes],
            "expert_memory": {},
            "recommendations": [{"persona_code": first_persona.code, "recommendation": "Proceed"}],
            "synthesis": "Final synthesis report...",
            "expert_summaries": {first_persona.code: "Expert recommended proceeding"},
            "user_id": None,
        }

        result = result_from_subgraph_state(final_state)

        assert isinstance(result, SubProblemResult)
        assert result.sub_problem_id == "sp_1"
        assert result.sub_problem_goal == "Test goal"
        assert result.synthesis == "Final synthesis report..."
        assert len(result.recommendations) == 1
        assert result.contribution_count == 1
        assert result.cost == 0.05
        assert result.expert_panel == persona_codes
        assert result.expert_summaries == {first_persona.code: "Expert recommended proceeding"}


class TestBuildExpertMemory:
    """Tests for build_expert_memory()."""

    def test_empty_results_returns_empty_dict(self):
        """No previous results should return empty memory."""
        memory = build_expert_memory([])
        assert memory == {}

    def test_aggregates_summaries_from_multiple_results(self):
        """Should aggregate summaries across sub-problems."""
        results = [
            SubProblemResult(
                sub_problem_id="sp_1",
                sub_problem_goal="Goal 1",
                synthesis="Synthesis 1",
                recommendations=[],
                contribution_count=5,
                cost=0.03,
                duration_seconds=60,
                expert_panel=["strategist"],
                expert_summaries={"strategist": "First position on goal 1"},
            ),
            SubProblemResult(
                sub_problem_id="sp_2",
                sub_problem_goal="Goal 2",
                synthesis="Synthesis 2",
                recommendations=[],
                contribution_count=4,
                cost=0.02,
                duration_seconds=45,
                expert_panel=["strategist", "finance_expert"],
                expert_summaries={
                    "strategist": "Second position on goal 2",
                    "finance_expert": "Finance perspective",
                },
            ),
        ]

        memory = build_expert_memory(results)

        # Strategist should have both summaries
        assert "strategist" in memory
        assert "Goal 1" in memory["strategist"]
        assert "Goal 2" in memory["strategist"]
        assert "First position" in memory["strategist"]
        assert "Second position" in memory["strategist"]

        # Finance expert only in second result
        assert "finance_expert" in memory
        assert "Finance perspective" in memory["finance_expert"]

    def test_preserves_sub_problem_context(self):
        """Memory should include sub-problem goal for context."""
        results = [
            SubProblemResult(
                sub_problem_id="sp_1",
                sub_problem_goal="Identify target markets",
                synthesis="Synthesis",
                recommendations=[],
                contribution_count=3,
                cost=0.01,
                duration_seconds=30,
                expert_panel=["strategist"],
                expert_summaries={"strategist": "Focus on EU"},
            ),
        ]

        memory = build_expert_memory(results)

        assert "Identify target markets" in memory["strategist"]
        assert "Focus on EU" in memory["strategist"]
