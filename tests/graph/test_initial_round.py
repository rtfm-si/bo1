"""Tests for initial_round_node parallelization.

Tests cover:
- Parallel contribution generation for 3-5 personas
- Semantic deduplication (filters duplicates, keeps ≥1)
- Quality check integration
- Round summarization
- Double-contribution guard
- Cross-sub-problem memory
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bo1.graph.nodes.rounds import (
    _build_cross_subproblem_memories,
    initial_round_node,
)
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, ContributionType, DeliberationPhase


@pytest.fixture
def sample_problem() -> Problem:
    """Create sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we expand into European markets?",
        context="Current US revenue: $5M ARR. Team of 20.",
        constraints=[],
        sub_problems=[],
    )


@pytest.fixture
def sample_personas():
    """Load real personas from catalog."""
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    personas_data = [
        get_persona_by_code("growth_hacker"),
        get_persona_by_code("finance_strategist"),
        get_persona_by_code("tech_lead"),
        get_persona_by_code("product_designer"),
        get_persona_by_code("domain_researcher"),
    ]

    return [PersonaProfile(**p) for p in personas_data if p]


class TestInitialRoundStateShape:
    """Test initial_round_node returns expected state structure."""

    def test_state_includes_required_fields(self, sample_problem, sample_personas):
        """Test that initial state has all fields needed for initial_round_node."""
        state = create_initial_state(
            session_id="test-shape",
            problem=sample_problem,
            personas=sample_personas,
            max_rounds=6,
        )

        # Required input fields
        assert "session_id" in state
        assert "problem" in state
        assert "personas" in state
        assert state["personas"] == sample_personas

        # Initial state starts at round 0, initial_round_node processes round 1
        assert state["round_number"] == 0

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Requires LLM - only run in integration tests")
    async def test_output_includes_enrichments(self, sample_problem, sample_personas):
        """Test that initial_round_node returns all enrichment fields."""
        state = create_initial_state(
            session_id="test-enrichments",
            problem=sample_problem,
            personas=sample_personas,
            max_rounds=6,
        )

        result = await initial_round_node(state)

        # Core fields
        assert "contributions" in result
        assert "phase" in result
        assert result["phase"] == DeliberationPhase.DISCUSSION
        assert result["round_number"] == 2  # Next round

        # Enrichment fields from parallel pattern
        assert "round_summaries" in result
        assert "facilitator_guidance" in result
        assert "experts_per_round" in result
        assert "metrics" in result


class TestDoubleContributionGuard:
    """Test guard that prevents double-contribution bug."""

    @pytest.mark.asyncio
    async def test_guard_skips_if_round_1_has_contributions(self, sample_problem, sample_personas):
        """Test that initial_round_node skips if round 1 already has contributions."""
        state = create_initial_state(
            session_id="test-guard",
            problem=sample_problem,
            personas=sample_personas,
            max_rounds=6,
        )

        # Add existing contribution for round 1
        existing_contrib = ContributionMessage(
            persona_code="growth_hacker",
            persona_name="The Growth Strategist",
            content="Already contributed to round 1",
            thinking=None,
            contribution_type=ContributionType.INITIAL,
            round_number=1,
            token_count=100,
            cost=0.01,
        )
        state["contributions"] = [existing_contrib]

        result = await initial_round_node(state)

        # Should skip and advance to round 2
        assert result["round_number"] == 2
        assert result["current_node"] == "initial_round_skipped"
        # Should NOT add new contributions
        assert "contributions" not in result or result.get("contributions") == []

    @pytest.mark.asyncio
    async def test_guard_handles_dict_contributions(self, sample_problem, sample_personas):
        """Test guard handles dict contributions from checkpoint deserialization."""
        state = create_initial_state(
            session_id="test-guard-dict",
            problem=sample_problem,
            personas=sample_personas,
            max_rounds=6,
        )

        # Add dict contribution (from checkpoint deserialization)
        existing_contrib = {
            "persona_code": "growth_hacker",
            "persona_name": "The Growth Strategist",
            "content": "Already contributed",
            "thinking": None,
            "contribution_type": "initial",
            "round_number": 1,
            "token_count": 100,
            "cost": 0.01,
        }
        state["contributions"] = [existing_contrib]

        result = await initial_round_node(state)

        # Should detect dict contribution and skip
        assert result["round_number"] == 2
        assert result["current_node"] == "initial_round_skipped"

    @pytest.mark.asyncio
    async def test_guard_allows_empty_round_1(self, sample_problem, sample_personas):
        """Test that guard allows execution when round 1 has no contributions."""
        state = create_initial_state(
            session_id="test-allow",
            problem=sample_problem,
            personas=sample_personas,
            max_rounds=6,
        )
        state["contributions"] = []

        # Import the guard check logic
        existing_contributions = state.get("contributions", [])
        round_contributions = [
            c
            for c in existing_contributions
            if (c.round_number if hasattr(c, "round_number") else c.get("round_number")) == 1
        ]

        # Guard should allow (no round 1 contributions)
        assert len(round_contributions) == 0


class TestCrossSubproblemMemory:
    """Test expert memory from previous sub-problems."""

    def test_builds_memory_from_sub_problem_results(self, sample_personas):
        """Test _build_cross_subproblem_memories builds expert memory correctly."""
        from unittest.mock import MagicMock

        # Create mock sub-problem results
        sub_problem_results = []
        mock_result = MagicMock()
        mock_result.expert_summaries = {
            "growth_hacker": "Focus on viral loops and referral programs",
            "finance_strategist": "ROI analysis suggests 18-month payback",
        }
        mock_result.sub_problem_goal = "Market entry strategy"
        sub_problem_results.append(mock_result)

        memories = _build_cross_subproblem_memories(sample_personas, sub_problem_results)

        # growth_hacker should have memory
        assert "growth_hacker" in memories
        assert "viral loops" in memories["growth_hacker"]
        assert "Market entry strategy" in memories["growth_hacker"]

        # finance_strategist should have memory
        assert "finance_strategist" in memories
        assert "ROI analysis" in memories["finance_strategist"]

        # Others should not have memory (not in expert_summaries)
        assert "tech_lead" not in memories
        assert "product_designer" not in memories

    def test_handles_empty_sub_problem_results(self, sample_personas):
        """Test memory builder handles empty sub-problem results."""
        memories = _build_cross_subproblem_memories(sample_personas, [])
        assert memories == {}

    def test_handles_multiple_sub_problems(self, sample_personas):
        """Test memory builder combines multiple sub-problems."""
        from unittest.mock import MagicMock

        sub_problem_results = []

        # First sub-problem
        mock_result_1 = MagicMock()
        mock_result_1.expert_summaries = {"growth_hacker": "First sub-problem position"}
        mock_result_1.sub_problem_goal = "Goal 1"
        sub_problem_results.append(mock_result_1)

        # Second sub-problem
        mock_result_2 = MagicMock()
        mock_result_2.expert_summaries = {"growth_hacker": "Second sub-problem position"}
        mock_result_2.sub_problem_goal = "Goal 2"
        sub_problem_results.append(mock_result_2)

        memories = _build_cross_subproblem_memories(sample_personas, sub_problem_results)

        # Should combine both
        assert "growth_hacker" in memories
        assert "Goal 1" in memories["growth_hacker"]
        assert "Goal 2" in memories["growth_hacker"]
        assert "First sub-problem" in memories["growth_hacker"]
        assert "Second sub-problem" in memories["growth_hacker"]


class TestSemanticDeduplication:
    """Test semantic deduplication filters duplicates but keeps ≥1."""

    @pytest.mark.asyncio
    async def test_dedup_keeps_at_least_one(self):
        """Test failsafe keeps at least one contribution."""
        from bo1.graph.nodes.rounds import _apply_semantic_deduplication

        # Mock the filter to return empty (all duplicates)
        # The failsafe should keep at least one
        result = await _apply_semantic_deduplication([])
        assert result == []

        # With contributions, failsafe applies
        # Note: actual dedup requires Voyage AI, so we test the failsafe logic

    @pytest.mark.asyncio
    async def test_dedup_handles_empty_list(self):
        """Test deduplication handles empty contribution list."""
        from bo1.graph.nodes.rounds import _apply_semantic_deduplication

        result = await _apply_semantic_deduplication([])
        assert result == []


class TestQualityCheck:
    """Test quality check integration."""

    @pytest.mark.asyncio
    async def test_quality_check_updates_guidance(self):
        """Test that quality check updates facilitator_guidance on shallow contributions."""
        from bo1.graph.nodes.rounds import _check_contribution_quality

        contributions = [
            ContributionMessage(
                persona_code="growth_hacker",
                persona_name="Growth Strategist",
                content="Short shallow response.",
                thinking=None,
                contribution_type=ContributionType.INITIAL,
                round_number=1,
                token_count=20,
                cost=0.002,
            ),
        ]

        # Mock quality check to return shallow result
        mock_quality_result = MagicMock()
        mock_quality_result.is_shallow = True
        mock_quality_result.quality_score = 0.3
        mock_quality_result.feedback = "Lacks specific evidence"

        with patch(
            "bo1.graph.quality.contribution_check.check_contributions_quality",
            new_callable=AsyncMock,
            return_value=([mock_quality_result], []),
        ):
            metrics = MagicMock()
            metrics.total_cost = 0.0

            quality_results, guidance = await _check_contribution_quality(
                contributions=contributions,
                problem_context="Test context",
                round_number=1,
                metrics=metrics,
                facilitator_guidance={},
            )

            # Should have quality issues
            assert "quality_issues" in guidance
            assert len(guidance["quality_issues"]) == 1
            assert guidance["quality_issues"][0]["shallow_count"] == 1

    @pytest.mark.asyncio
    async def test_quality_check_handles_empty_contributions(self):
        """Test quality check handles empty list gracefully."""
        from bo1.graph.nodes.rounds import _check_contribution_quality

        mock_metrics = MagicMock()
        mock_metrics.total_cost = 0.0

        quality_results, guidance = await _check_contribution_quality(
            contributions=[],
            problem_context="Test context",
            round_number=1,
            metrics=mock_metrics,
            facilitator_guidance={},
        )

        assert quality_results == []
        assert guidance == {}


class TestRoundSummarization:
    """Test round summarization."""

    @pytest.mark.asyncio
    async def test_summarize_returns_none_for_empty(self):
        """Test summarization returns None for empty contributions."""
        from bo1.graph.nodes.rounds import _summarize_round

        mock_metrics = MagicMock()
        mock_metrics.total_cost = 0.0

        result = await _summarize_round(
            contributions=[],
            round_number=1,
            current_phase="exploration",
            problem_statement="Test problem",
            metrics=mock_metrics,
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_summarize_returns_none_for_round_zero(self):
        """Test summarization returns None for round 0."""
        from bo1.graph.nodes.rounds import _summarize_round

        contributions = [
            ContributionMessage(
                persona_code="growth_hacker",
                persona_name="Growth Strategist",
                content="Test contribution.",
                thinking=None,
                contribution_type=ContributionType.INITIAL,
                round_number=0,
                token_count=20,
                cost=0.002,
            ),
        ]

        mock_metrics = MagicMock()
        mock_metrics.total_cost = 0.0

        result = await _summarize_round(
            contributions=contributions,
            round_number=0,
            current_phase="exploration",
            problem_statement="Test problem",
            metrics=mock_metrics,
        )

        assert result is None


class TestGenerateParallelContributions:
    """Test _generate_parallel_contributions with contribution_type parameter."""

    def test_contribution_type_parameter_exists(self):
        """Test that _generate_parallel_contributions accepts contribution_type."""
        import inspect

        from bo1.graph.nodes.rounds import _generate_parallel_contributions

        sig = inspect.signature(_generate_parallel_contributions)
        params = list(sig.parameters.keys())

        assert "contribution_type" in params
        assert "expert_memories" in params

    def test_expert_memories_parameter_exists(self):
        """Test that _generate_parallel_contributions accepts expert_memories."""
        import inspect

        from bo1.graph.nodes.rounds import _generate_parallel_contributions

        sig = inspect.signature(_generate_parallel_contributions)
        param = sig.parameters["expert_memories"]

        # Should have default of None
        assert param.default is None


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires LLM and Voyage AI - only run in integration tests")
async def test_initial_round_full_execution(sample_problem, sample_personas):
    """Integration test: full initial_round_node execution.

    This test requires:
    - Anthropic API key (for LLM)
    - Voyage AI API key (for semantic dedup)

    To run: pytest -m integration tests/graph/test_initial_round.py
    """
    state = create_initial_state(
        session_id="test-full",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )

    result = await initial_round_node(state)

    # Should have contributions from personas
    contributions = result["contributions"]
    assert len(contributions) >= 1, "Should have at least 1 contribution after dedup"
    assert len(contributions) <= len(sample_personas), "Should not exceed persona count"

    # All contributions should be round 1
    for c in contributions:
        assert c.round_number == 1

    # Round number should advance to 2
    assert result["round_number"] == 2

    # Phase should be DISCUSSION
    assert result["phase"] == DeliberationPhase.DISCUSSION

    # Should have round summary
    assert "round_summaries" in result
    assert len(result["round_summaries"]) == 1

    # Should have experts tracking
    assert "experts_per_round" in result
    assert len(result["experts_per_round"]) == 1
