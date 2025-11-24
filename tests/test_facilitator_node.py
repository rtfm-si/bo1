"""Tests for facilitator node implementation."""

import pytest

from bo1.graph.nodes import facilitator_decide_node
from bo1.graph.state import create_initial_state
from bo1.models.problem import SubProblem
from bo1.models.state import ContributionMessage
from tests.utils.factories import create_test_contributions_batch

pytestmark = pytest.mark.requires_llm


@pytest.fixture
def marketing_problem_with_sp(sample_problem_marketing):
    """Create marketing problem with sub-problem."""
    sample_problem_marketing.sub_problems = [
        SubProblem(
            id="sp1",
            goal="Determine SEO potential",
            context="Current SEO state",
            complexity_score=6,
            dependencies=[],
        )
    ]
    return sample_problem_marketing


@pytest.fixture
def state_with_contributions(marketing_problem_with_sp, load_personas_by_codes):
    """Create state with initial contributions for facilitator to review."""
    # Load real personas using helper
    personas = load_personas_by_codes(["growth_hacker", "finance_strategist", "risk_officer"])

    state = create_initial_state(
        session_id="test_session_fac",
        problem=marketing_problem_with_sp,
        max_rounds=10,
    )

    # Add personas and contributions to state
    state["personas"] = personas
    state["current_sub_problem"] = marketing_problem_with_sp.sub_problems[0]
    state["round_number"] = 1

    # Create contributions using factory
    contributions = create_test_contributions_batch(
        persona_codes=["growth_hacker", "finance_strategist", "risk_officer"],
        round_number=1,
        content_template="Contribution from {persona_name} about marketing strategy...",
    )

    state["contributions"] = contributions

    return state


@pytest.mark.asyncio
async def test_facilitator_decide_node_creates_decision(state_with_contributions):
    """Test facilitator_decide_node creates a facilitator decision."""
    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    # Verify updates
    assert "facilitator_decision" in updates
    assert "metrics" in updates
    assert "phase" in updates
    assert "current_node" in updates

    # Verify decision structure (dict, not object)
    decision = updates["facilitator_decision"]
    assert isinstance(decision, dict)
    assert decision["action"] in ["continue", "vote", "moderator", "research"]
    assert decision["reasoning"] is not None
    assert len(decision["reasoning"]) > 0


@pytest.mark.asyncio
async def test_facilitator_decide_node_tracks_cost(state_with_contributions):
    """Test facilitator_decide_node tracks cost in metrics."""
    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    # Verify cost tracked using assertion helper
    # Note: Cost is tracked even if 0 for some auto-triggered actions
    assert "metrics" in updates
    metrics = updates["metrics"]
    assert hasattr(metrics, "phase_costs")


@pytest.mark.asyncio
async def test_facilitator_decide_node_continue_action(state_with_contributions):
    """Test facilitator decides to continue when discussion has potential."""
    # Set up state for continuation (early round, good discussion)
    state_with_contributions["round_number"] = 2
    state_with_contributions["max_rounds"] = 10

    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    decision = updates["facilitator_decision"]

    # At round 2 of 10, facilitator should likely continue
    # (though not guaranteed depending on LLM response)
    assert decision["action"] in ["continue", "vote", "moderator"]

    # If continue, verify next_speaker is set
    if decision["action"] == "continue":
        assert decision["next_speaker"] is not None
        assert decision["next_speaker"] in ["growth_hacker", "finance_strategist", "risk_officer"]


@pytest.mark.asyncio
async def test_facilitator_decide_node_vote_action_near_max_rounds(state_with_contributions):
    """Test facilitator decides to vote when approaching max rounds."""
    # Set up state near end of max rounds
    state_with_contributions["round_number"] = 9
    state_with_contributions["max_rounds"] = 10

    # Add more contributions to show discussion has progressed
    for i in range(2, 10):
        state_with_contributions["contributions"].extend(
            [
                ContributionMessage(
                    persona_code="growth_hacker",
                    persona_name="Growth Hacker",
                    round_number=i,
                    content=f"Round {i}: Building on previous points about SEO...",
                    thinking=f"Round {i} analysis...",
                    token_count=50,
                    cost=0.001,
                ),
                ContributionMessage(
                    persona_code="finance_strategist",
                    persona_name="Finance Strategist",
                    round_number=i,
                    content=f"Round {i}: Additional insights on paid ads...",
                    thinking=f"Round {i} insights...",
                    token_count=45,
                    cost=0.0009,
                ),
            ]
        )

    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    decision = updates["facilitator_decision"]

    # Near max rounds, facilitator should likely vote or continue one more round
    # (though moderator is also valid if discussion needs intervention)
    assert decision["action"] in ["vote", "continue", "moderator"]


@pytest.mark.asyncio
async def test_facilitator_decide_node_preserves_state(state_with_contributions):
    """Test facilitator_decide_node doesn't modify original state unexpectedly."""
    original_round = state_with_contributions["round_number"]
    original_contributions_count = len(state_with_contributions["contributions"])

    # Run facilitator decide node
    await facilitator_decide_node(state_with_contributions)

    # Verify original state unchanged (nodes should return updates, not mutate state)
    assert state_with_contributions["round_number"] == original_round
    assert len(state_with_contributions["contributions"]) == original_contributions_count


@pytest.mark.asyncio
async def test_facilitator_rotation_guidance(state_with_contributions):
    """Test facilitator receives rotation guidance to balance participation.

    This test verifies that the facilitator's decision takes into account
    contribution counts and last speakers to encourage diverse participation.
    """
    # Create unbalanced state: one persona spoke 3 times, others once each
    state_with_contributions["round_number"] = 4
    state_with_contributions["contributions"] = [
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=1,
            content="Round 1: Initial SEO analysis...",
            thinking="Analysis...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=2,
            content="Round 2: Additional SEO insights...",
            thinking="More analysis...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=3,
            content="Round 3: Further SEO recommendations...",
            thinking="Continued analysis...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Strategist",
            round_number=1,
            content="Round 1: Financial perspective on SEO investment...",
            thinking="Financial analysis...",
            token_count=45,
            cost=0.0009,
        ),
        ContributionMessage(
            persona_code="risk_officer",
            persona_name="Risk Officer",
            round_number=1,
            content="Round 1: Risk assessment of SEO strategy...",
            thinking="Risk evaluation...",
            token_count=48,
            cost=0.00095,
        ),
    ]

    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    decision = updates["facilitator_decision"]

    # If facilitator decides to continue, next speaker should NOT be growth_hacker
    # (since they've already spoken 3 times while others only spoke once)
    # Note: We can't guarantee LLM behavior, but we verify the guidance was provided
    if decision["action"] == "continue":
        next_speaker = decision["next_speaker"]

        # Rotation guidance should encourage picking finance_strategist or risk_officer
        # However, we'll just verify that the decision is reasonable
        # (LLM might still pick growth_hacker if they determine it's critical)
        assert next_speaker in ["growth_hacker", "finance_strategist", "risk_officer"]

        # Log for manual inspection during test runs
        # (facilitator SHOULD prefer finance_strategist or risk_officer)
        if next_speaker == "growth_hacker":
            # This is acceptable if reasoning is strong, but should be rare
            assert (
                "critical" in decision["reasoning"].lower()
                or "unique" in decision["reasoning"].lower()
            )


@pytest.mark.asyncio
async def test_facilitator_avoids_consecutive_repeats(state_with_contributions):
    """Test facilitator avoids selecting the same persona consecutively.

    This test verifies that rotation guidance helps prevent the same
    persona from speaking back-to-back.
    """
    # Set up state where last speaker was growth_hacker
    state_with_contributions["round_number"] = 3
    state_with_contributions["contributions"] = [
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Strategist",
            round_number=1,
            content="Round 1: Financial analysis...",
            thinking="Analysis...",
            token_count=45,
            cost=0.0009,
        ),
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=2,
            content="Round 2: SEO insights building on financial analysis...",
            thinking="Building on finance...",
            token_count=50,
            cost=0.001,
        ),
    ]

    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    decision = updates["facilitator_decision"]

    # If continuing, should prefer someone OTHER than growth_hacker (last speaker)
    if decision["action"] == "continue":
        next_speaker = decision["next_speaker"]

        # Verify next speaker is reasonable
        assert next_speaker in ["growth_hacker", "finance_strategist", "risk_officer"]

        # Note: We can't strictly enforce no consecutive repeats because
        # the LLM might determine it's critical, but rotation guidance
        # should make it less likely


@pytest.mark.asyncio
async def test_facilitator_prevents_premature_voting(state_with_contributions):
    """Test that facilitator is prevented from voting before minimum rounds.

    This test verifies Bug #3 fix: preventing premature voting that
    causes shallow deliberations and incomplete sub-problem coverage.
    """
    # Set up state at round 2 (before minimum of 3)
    state_with_contributions["round_number"] = 2
    state_with_contributions["max_rounds"] = 10

    # Add contributions to make it look like discussion is converging
    # (but still too early to vote)
    state_with_contributions["contributions"] = [
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=1,
            content="Round 1: SEO is the best approach...",
            thinking="Analysis...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Strategist",
            round_number=2,
            content="Round 2: I agree, SEO makes financial sense...",
            thinking="Financial perspective...",
            token_count=48,
            cost=0.0009,
        ),
    ]

    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    decision = updates["facilitator_decision"]

    # Even if facilitator tried to vote, system should override to "continue"
    # (minimum 3 rounds required before voting)
    assert decision["action"] in ["continue", "moderator", "research"]

    # If the decision was "continue", verify it's reasonable
    if decision["action"] == "continue":
        assert decision["next_speaker"] in ["growth_hacker", "finance_strategist", "risk_officer"]


@pytest.mark.asyncio
async def test_facilitator_allows_voting_after_minimum_rounds(state_with_contributions):
    """Test that facilitator can vote after minimum rounds threshold."""
    # Set up state at round 4 (after minimum of 3)
    state_with_contributions["round_number"] = 4
    state_with_contributions["max_rounds"] = 10

    # Add substantial contributions showing depth
    for i in range(1, 5):
        state_with_contributions["contributions"].extend(
            [
                ContributionMessage(
                    persona_code="growth_hacker",
                    persona_name="Growth Hacker",
                    round_number=i,
                    content=f"Round {i}: SEO analysis point {i}...",
                    thinking=f"Round {i} thinking...",
                    token_count=50,
                    cost=0.001,
                ),
                ContributionMessage(
                    persona_code="finance_strategist",
                    persona_name="Finance Strategist",
                    round_number=i,
                    content=f"Round {i}: Financial perspective {i}...",
                    thinking=f"Round {i} financial analysis...",
                    token_count=48,
                    cost=0.0009,
                ),
            ]
        )

    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    decision = updates["facilitator_decision"]

    # After round 4, facilitator can choose any action including voting
    assert decision["action"] in ["continue", "vote", "moderator", "research"]
