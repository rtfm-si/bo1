"""Tests for vote and synthesis nodes implementation."""

import pytest

from bo1.graph.nodes import synthesize_node, vote_node
from bo1.graph.state import create_initial_state
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationPhase

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
    """Create state with contributions ready for voting."""
    state = create_initial_state(
        session_id="test_session_vote",
        problem=sample_problem,
        max_rounds=10,
    )

    # Add personas and contributions to state
    state["personas"] = sample_personas
    state["current_sub_problem"] = sample_problem.sub_problems[0]
    state["round_number"] = 3
    state["phase"] = DeliberationPhase.DISCUSSION

    # Add sample contributions from 3 rounds
    contributions = [
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=1,
            content="I think we should focus on SEO for long-term growth and sustainable CAC reduction.",
            thinking="Considering long-term value...",
            token_count=50,
            cost=0.001,
        ),
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Strategist",
            round_number=1,
            content="Paid ads can give us quick wins and immediate ROI. We need to consider cash flow.",
            thinking="Analyzing short-term gains...",
            token_count=45,
            cost=0.0009,
        ),
        ContributionMessage(
            persona_code="risk_officer",
            persona_name="Risk Officer",
            round_number=1,
            content="SEO requires 6-12 months to show results but is more sustainable long-term.",
            thinking="Evaluating sustainability...",
            token_count=55,
            cost=0.0011,
        ),
        # Round 2
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Growth Hacker",
            round_number=2,
            content="Building on that, a 70/30 split (SEO/Paid) could balance both needs.",
            thinking="Considering hybrid approach...",
            token_count=40,
            cost=0.0008,
        ),
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Finance Strategist",
            round_number=2,
            content="I can support 60/40 if we have clear milestones and exit criteria.",
            thinking="Evaluating risk mitigation...",
            token_count=38,
            cost=0.0007,
        ),
    ]

    state["contributions"] = contributions

    return state


@pytest.mark.asyncio
async def test_vote_node_collects_votes(state_with_contributions):
    """Test vote_node collects votes from all personas."""
    # Run vote node
    updates = await vote_node(state_with_contributions)

    # Verify updates
    assert "votes" in updates
    assert "metrics" in updates
    assert "phase" in updates
    assert "current_node" in updates

    # Verify votes structure
    votes = updates["votes"]
    assert isinstance(votes, list)
    assert len(votes) == 3  # One vote per persona

    # Verify each vote has required fields (using recommendation system)
    for vote in votes:
        assert "persona_code" in vote
        assert "persona_name" in vote
        assert "recommendation" in vote  # Changed from "decision"
        assert "reasoning" in vote
        assert "confidence" in vote
        assert "conditions" in vote
        assert "weight" in vote

        # Verify recommendation is a non-empty string (not binary decision)
        assert isinstance(vote["recommendation"], str)
        assert len(vote["recommendation"]) > 0

        # Verify confidence is 0-1
        assert 0 <= vote["confidence"] <= 1

    # Verify phase updated to VOTING
    assert updates["phase"] == DeliberationPhase.VOTING

    # Verify cost tracked
    metrics = updates["metrics"]
    assert "voting" in metrics.phase_costs
    assert metrics.phase_costs["voting"] > 0


@pytest.mark.asyncio
async def test_synthesize_node_generates_synthesis(state_with_contributions):
    """Test synthesize_node generates synthesis report."""
    # First collect votes
    vote_updates = await vote_node(state_with_contributions)

    # Update state with votes
    state_with_contributions["votes"] = vote_updates["votes"]
    state_with_contributions["metrics"] = vote_updates["metrics"]

    # Run synthesis node
    synthesis_updates = await synthesize_node(state_with_contributions)

    # Verify updates
    assert "synthesis" in synthesis_updates
    assert "metrics" in synthesis_updates
    assert "phase" in synthesis_updates
    assert "current_node" in synthesis_updates

    # Verify synthesis content
    synthesis = synthesis_updates["synthesis"]
    assert isinstance(synthesis, str)
    assert len(synthesis) > 0

    # Verify disclaimer is present
    assert "AI-generated" in synthesis
    assert "professional advisory" in synthesis

    # Verify phase updated to COMPLETE
    assert synthesis_updates["phase"] == DeliberationPhase.COMPLETE

    # Verify cost tracked
    metrics = synthesis_updates["metrics"]
    assert "synthesis" in metrics.phase_costs
    assert metrics.phase_costs["synthesis"] > 0


@pytest.mark.asyncio
async def test_vote_and_synthesis_end_to_end(state_with_contributions):
    """Test complete vote + synthesis flow."""
    # Run vote node
    vote_updates = await vote_node(state_with_contributions)

    # Apply vote updates to state
    state_with_contributions["votes"] = vote_updates["votes"]
    state_with_contributions["metrics"] = vote_updates["metrics"]
    state_with_contributions["phase"] = vote_updates["phase"]

    # Verify voting completed
    assert len(state_with_contributions["votes"]) == 3
    assert state_with_contributions["phase"] == DeliberationPhase.VOTING

    # Run synthesis node
    synthesis_updates = await synthesize_node(state_with_contributions)

    # Apply synthesis updates
    state_with_contributions["synthesis"] = synthesis_updates["synthesis"]
    state_with_contributions["metrics"] = synthesis_updates["metrics"]
    state_with_contributions["phase"] = synthesis_updates["phase"]

    # Verify synthesis completed
    assert state_with_contributions["synthesis"] is not None
    assert state_with_contributions["phase"] == DeliberationPhase.COMPLETE

    # Verify total cost accumulated across both phases
    metrics = state_with_contributions["metrics"]
    assert "voting" in metrics.phase_costs
    assert "synthesis" in metrics.phase_costs
    assert metrics.total_cost > 0
