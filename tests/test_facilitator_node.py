"""Tests for facilitator node implementation."""

import pytest

from bo1.agents.facilitator import FacilitatorDecision
from bo1.graph.nodes import facilitator_decide_node
from bo1.graph.state import create_initial_state
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage

pytestmark = pytest.mark.requires_llm


@pytest.fixture
def sample_problem():
    """Create a sample problem for testing."""
    return Problem(
        title="Marketing Budget Decision",
        description="Should I invest $50K in SEO or paid ads for my SaaS product?",
        context="Solo founder, B2B SaaS, $100K ARR, 6-month timeline",
        sub_problems=[
            SubProblem(
                id="sp1",
                goal="Determine SEO potential",
                context="Current SEO state",
                complexity_score=6,
                dependencies=[],
            )
        ],
    )


@pytest.fixture
def sample_personas():
    """Create sample personas for testing."""
    from bo1.data import get_persona_by_code

    # Use real personas from personas.json
    personas = []
    for code in ["growth_hacker", "finance_strategist", "risk_officer"]:
        persona_dict = get_persona_by_code(code)
        if persona_dict:
            personas.append(PersonaProfile.model_validate(persona_dict))

    return personas


@pytest.fixture
def state_with_contributions(sample_problem, sample_personas):
    """Create state with initial contributions for facilitator to review."""
    state = create_initial_state(
        session_id="test_session_fac",
        problem=sample_problem,
        max_rounds=10,
    )

    # Add personas and contributions to state
    state["personas"] = sample_personas
    state["current_sub_problem"] = sample_problem.sub_problems[0]
    state["round_number"] = 1

    # Add sample contributions
    contributions = [
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=1,
            content="I think we should focus on SEO for long-term growth...",
            thinking="Considering long-term value...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Strategist",
            round_number=1,
            content="Paid ads can give us quick wins and immediate ROI...",
            thinking="Analyzing short-term gains...",
            token_count=45,
            cost=0.0009,
        ),
        ContributionMessage(
            persona_code="risk_officer",
            persona_name="Risk Officer",
            round_number=1,
            content="SEO requires 6-12 months to show results but is more sustainable...",
            thinking="Evaluating sustainability...",
            token_count=55,
            cost=0.0011,
        ),
    ]

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

    # Verify decision structure
    decision = updates["facilitator_decision"]
    assert isinstance(decision, FacilitatorDecision)
    assert decision.action in ["continue", "vote", "moderator", "research"]
    assert decision.reasoning is not None
    assert len(decision.reasoning) > 0


@pytest.mark.asyncio
async def test_facilitator_decide_node_tracks_cost(state_with_contributions):
    """Test facilitator_decide_node tracks cost in metrics."""
    # Run facilitator decide node
    updates = await facilitator_decide_node(state_with_contributions)

    # Verify cost tracked
    metrics = updates["metrics"]
    assert hasattr(metrics, "phase_costs")

    # Cost should be tracked if LLM was called
    # (If auto-triggered moderator/research, cost might be 0)
    if updates["facilitator_decision"].action in ["continue", "vote"]:
        assert "facilitator_decision" in metrics.phase_costs
        assert metrics.phase_costs["facilitator_decision"] >= 0


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
    assert decision.action in ["continue", "vote", "moderator"]

    # If continue, verify next_speaker is set
    if decision.action == "continue":
        assert decision.next_speaker is not None
        assert decision.next_speaker in ["growth_hacker", "finance_strategist", "risk_officer"]


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
    assert decision.action in ["vote", "continue", "moderator"]


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
