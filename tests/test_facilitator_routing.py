"""Tests for facilitator routing logic."""

import pytest

from bo1.agents.facilitator import FacilitatorDecision
from bo1.graph.routers import route_facilitator_decision
from bo1.graph.state import create_initial_state
from bo1.models.problem import Problem


@pytest.fixture
def sample_state():
    """Create a sample state for testing."""
    problem = Problem(
        title="Test Problem",
        description="Test description",
        context="Test context",
        sub_problems=[],
    )

    return create_initial_state(
        session_id="test_route_session",
        problem=problem,
        max_rounds=10,
    )


def test_route_facilitator_decision_vote(sample_state):
    """Test routing when facilitator decides to vote."""
    # Create facilitator decision for voting
    decision = FacilitatorDecision(
        action="vote",
        reasoning="Discussion has reached consensus",
        phase_summary="Group converged on SEO strategy",
    )

    # Add decision to state
    sample_state["facilitator_decision"] = decision

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    assert next_node == "vote"


def test_route_facilitator_decision_moderator(sample_state):
    """Test routing when facilitator decides moderator intervention needed."""
    # Create facilitator decision for moderator
    decision = FacilitatorDecision(
        action="moderator",
        reasoning="Group converging too early",
        moderator_type="contrarian",
        moderator_focus="Challenge SEO assumptions",
    )

    # Add decision to state
    sample_state["facilitator_decision"] = decision

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    assert next_node == "moderator_intervene"


def test_route_facilitator_decision_continue(sample_state):
    """Test routing when facilitator decides to continue discussion."""
    # Create facilitator decision for continuation
    decision = FacilitatorDecision(
        action="continue",
        reasoning="Need more depth on paid ads ROI",
        next_speaker="maria",
        speaker_prompt="Analyze paid ads ROI potential",
    )

    # Add decision to state
    sample_state["facilitator_decision"] = decision

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    assert next_node == "persona_contribute"


def test_route_facilitator_decision_research(sample_state):
    """Test routing when facilitator requests research (ends for Week 5)."""
    # Create facilitator decision for research
    decision = FacilitatorDecision(
        action="research",
        reasoning="Need SEO cost data",
        research_query="Average SEO costs for B2B SaaS",
    )

    # Add decision to state
    sample_state["facilitator_decision"] = decision

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    # Research not implemented in Week 5, should route to END
    assert next_node == "END"


def test_route_facilitator_decision_missing_decision(sample_state):
    """Test routing when no facilitator decision in state."""
    # Don't add decision to state
    # Test routing
    next_node = route_facilitator_decision(sample_state)

    # Should default to END when no decision
    assert next_node == "END"


def test_route_facilitator_decision_unknown_action(sample_state):
    """Test routing with unknown action type."""
    # Create decision with invalid action (bypass type checking for test)
    decision = FacilitatorDecision(
        action="continue",  # Valid action
        reasoning="Test",
    )
    # Manually override action to test error handling
    decision.action = "invalid_action"  # type: ignore[assignment]

    # Add decision to state
    sample_state["facilitator_decision"] = decision

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    # Should default to END for unknown actions
    assert next_node == "END"
