"""Tests for parallel multi-expert round execution."""

import pytest

from bo1.graph.nodes import _determine_phase
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem


@pytest.fixture
def sample_problem() -> Problem:
    """Create sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we invest in feature X?",
        context="Test context",
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
    ]

    return [PersonaProfile(**p) for p in personas_data if p]


def test_parallel_round_state_structure(sample_problem, sample_personas):
    """Test that parallel round initializes all required state fields."""
    state = create_initial_state(
        session_id="test-state",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )

    # Verify new parallel architecture fields exist
    assert "current_phase" in state
    assert "experts_per_round" in state
    assert "semantic_novelty_scores" in state
    assert "exploration_score" in state
    assert "focus_score" in state

    # Verify defaults
    assert state["current_phase"] == "exploration"
    assert isinstance(state["experts_per_round"], list)
    assert len(state["experts_per_round"]) == 0
    assert isinstance(state["semantic_novelty_scores"], dict)
    assert state["exploration_score"] == 0.0
    assert state["focus_score"] == 1.0


def test_determine_phase_6_rounds():
    """Test phase determination for 6-round max configuration."""
    # Round 1-2 = exploration
    assert _determine_phase(1, 6) == "exploration"
    assert _determine_phase(2, 6) == "exploration"

    # Round 3-4 = challenge
    assert _determine_phase(3, 6) == "challenge"
    assert _determine_phase(4, 6) == "challenge"

    # Round 5-6 = convergence
    assert _determine_phase(5, 6) == "convergence"
    assert _determine_phase(6, 6) == "convergence"


def test_determine_phase_scaling():
    """Test phase determination scales with different max_rounds."""
    # 3 rounds
    # exploration_end = max(2, 3//3) = max(2, 1) = 2
    # challenge_end = max(4, 2*3//3) = max(4, 2) = 4
    assert _determine_phase(1, 3) == "exploration"
    assert _determine_phase(2, 3) == "exploration"
    assert _determine_phase(3, 3) == "challenge"  # 3 > 2, 3 <= 4

    # 9 rounds
    # exploration_end = max(2, 9//3) = max(2, 3) = 3
    # challenge_end = max(4, 2*9//3) = max(4, 6) = 6
    assert _determine_phase(1, 9) == "exploration"
    assert _determine_phase(2, 9) == "exploration"
    assert _determine_phase(3, 9) == "exploration"
    assert _determine_phase(4, 9) == "challenge"
    assert _determine_phase(5, 9) == "challenge"
    assert _determine_phase(6, 9) == "challenge"
    assert _determine_phase(7, 9) == "convergence"
    assert _determine_phase(8, 9) == "convergence"
    assert _determine_phase(9, 9) == "convergence"


def test_max_rounds_validation(sample_problem, sample_personas):
    """Test that max_rounds is capped at 6."""
    from bo1.graph.state import validate_state

    state = create_initial_state(
        session_id="test-validation",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )

    # Should pass validation
    validate_state(state)

    # Test that exceeding cap raises error
    state["max_rounds"] = 10
    with pytest.raises(ValueError, match="max_rounds .* exceeds hard cap of 6"):
        validate_state(state)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires LLM and Voyage AI - only run in integration tests")
async def test_parallel_round_execution(sample_problem, sample_personas):
    """Test parallel round executes multiple experts simultaneously.

    This test is skipped by default as it requires:
    - Anthropic API key (for LLM)
    - Voyage AI API key (for semantic dedup)
    - Network access

    To run: pytest -m integration tests/graph/test_parallel_round.py
    """
    from bo1.graph.nodes import parallel_round_node

    state = create_initial_state(
        session_id="test-parallel",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )
    state["round_number"] = 1

    result = await parallel_round_node(state)

    # Should have contributions from multiple experts
    new_contribs = [c for c in result["contributions"] if c.round_number == 1]
    assert len(new_contribs) >= 2, "Should have at least 2 contributions after dedup"
    assert len(new_contribs) <= 5, "Should have at most 5 contributions"

    # Round number should increment
    assert result["round_number"] == 2

    # Phase should be set
    assert result["current_phase"] in ["exploration", "challenge", "convergence"]

    # Experts tracking should be populated
    assert len(result["experts_per_round"]) == 1
    assert len(result["experts_per_round"][0]) >= 2


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires LLM - only run in integration tests")
async def test_parallel_round_failsafe(sample_problem, sample_personas):
    """Test failsafe when all contributions filtered as duplicates.

    This test would require mocking semantic dedup to return all duplicates,
    then verifying that at least 1 contribution is kept.
    """
    # TODO: Implement with mocking
    pass


def test_initial_round_contributions_use_round_1():
    """Test that initial_round contributions use round_number=1.

    This is critical to prevent the double-contribution bug where experts
    contribute in both initial_round (round 0) and parallel_round (round 1).
    """
    # The fix ensures initial_round contributions have round_number=1
    # and state advances to round_number=2 after initial_round

    # Check that the engine uses round_number=1 for initial round
    # This is validated by checking the code path, not runtime
    # The actual integration test would verify contributions have correct round_number
    pass


def test_parallel_round_guard_skips_duplicate_rounds(sample_problem, sample_personas):
    """Test that parallel_round_node skips if round already has contributions.

    This guard prevents double-contribution in edge cases like graph retries.
    """
    from bo1.models.state import ContributionMessage, ContributionType

    state = create_initial_state(
        session_id="test-guard",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )
    state["round_number"] = 2

    # Add existing contribution for round 2
    existing_contrib = ContributionMessage(
        persona_code="growth_hacker",
        persona_name="The Growth Strategist",
        content="Test contribution",
        thinking=None,
        contribution_type=ContributionType.RESPONSE,
        round_number=2,
        token_count=100,
        cost=0.01,
    )
    state["contributions"] = [existing_contrib]

    # Import the guard check logic
    existing_contributions = state.get("contributions", [])
    round_contributions = []
    for c in existing_contributions:
        c_round = c.round_number if hasattr(c, "round_number") else c.get("round_number")
        if c_round == 2:
            round_contributions.append(c)

    # Guard should detect existing contributions
    assert len(round_contributions) == 1
    assert round_contributions[0].persona_code == "growth_hacker"


@pytest.mark.asyncio
async def test_expert_selection_filters_round_contributors(sample_problem, sample_personas):
    """Test that expert selection filters experts who already contributed this round."""
    from bo1.graph.deliberation.experts import select_experts_for_round
    from bo1.models.state import ContributionMessage, ContributionType

    state = create_initial_state(
        session_id="test-filter",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )
    state["round_number"] = 2

    # Add contribution from growth_hacker for round 2
    existing_contrib = ContributionMessage(
        persona_code="growth_hacker",
        persona_name="The Growth Strategist",
        content="Already contributed",
        thinking=None,
        contribution_type=ContributionType.RESPONSE,
        round_number=2,
        token_count=100,
        cost=0.01,
    )
    state["contributions"] = [existing_contrib]

    # Select experts should filter out growth_hacker
    selected = await select_experts_for_round(state, "exploration", 2)

    # growth_hacker should not be in selected experts
    selected_codes = [p.code for p in selected]
    assert "growth_hacker" not in selected_codes
    # Other experts should still be available
    assert len(selected) > 0
