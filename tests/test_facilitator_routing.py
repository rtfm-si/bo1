"""Tests for facilitator routing logic."""

from dataclasses import asdict

import pytest

from bo1.agents.facilitator import FacilitatorDecision
from bo1.graph.routers import route_facilitator_decision
from bo1.graph.state import create_initial_state
from tests.utils.factories import create_test_problem


@pytest.fixture
def sample_state():
    """Create a sample state for testing."""
    problem = create_test_problem()

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

    # Add decision to state as dict (to match real graph behavior)
    sample_state["facilitator_decision"] = asdict(decision)

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    assert next_node == "vote"


def test_route_facilitator_decision_continue(sample_state):
    """Test routing when facilitator decides to continue discussion."""
    # Create facilitator decision for continuation
    decision = FacilitatorDecision(
        action="continue",
        reasoning="Need more depth on paid ads ROI",
        next_speaker="maria",
        speaker_prompt="Analyze paid ads ROI potential",
    )

    # Add decision to state as dict (to match real graph behavior)
    sample_state["facilitator_decision"] = asdict(decision)

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    assert next_node == "persona_contribute"


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

    # Add decision to state as dict (to match real graph behavior)
    sample_state["facilitator_decision"] = asdict(decision)

    # Test routing
    next_node = route_facilitator_decision(sample_state)

    # Should fall back to persona_contribute for unknown actions (graceful degradation)
    assert next_node == "persona_contribute"
