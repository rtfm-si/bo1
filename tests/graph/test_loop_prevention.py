"""Tests for infinite loop prevention layers 1-3."""

import networkx as nx
import pytest

from bo1.graph.safety.loop_prevention import (
    DELIBERATION_RECURSION_LIMIT,
    check_convergence_node,
    route_convergence_check,
    validate_graph_acyclic,
    validate_round_counter_invariants,
)
from bo1.graph.state import DeliberationGraphState, create_initial_state
from bo1.models.problem import Problem
from bo1.models.state import DeliberationMetrics


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we invest in feature X?",
        context="SaaS startup with $500K budget",
    )


# ============================================================================
# Layer 1: Recursion Limit Tests
# ============================================================================


def test_recursion_limit_constant():
    """Test that recursion limit is set correctly."""
    # 15 rounds × 3 nodes/round + 10 overhead = 55
    assert DELIBERATION_RECURSION_LIMIT == 55


# ============================================================================
# Layer 2: Cycle Detection Tests
# ============================================================================


def test_validate_graph_acyclic_no_cycles():
    """Test graph validation with no cycles (fully acyclic)."""
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("start", "decompose"),
            ("decompose", "select"),
            ("select", "initial_round"),
            ("initial_round", "vote"),
            ("vote", "end"),
        ]
    )

    # Should not raise
    validate_graph_acyclic(graph)


def test_validate_graph_acyclic_with_controlled_cycle():
    """Test graph validation with a controlled cycle (has exit)."""
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("facilitator", "persona"),
            ("persona", "check_convergence"),
            (
                "check_convergence",
                "facilitator",
            ),  # Cycle: facilitator → persona → check → facilitator
            ("check_convergence", "vote"),  # Exit: check → vote (breaks the cycle)
        ]
    )

    # Should not raise (cycle has exit to "vote")
    validate_graph_acyclic(graph)


def test_validate_graph_acyclic_with_uncontrolled_cycle():
    """Test graph validation fails with uncontrolled cycle (no exit)."""
    graph = nx.DiGraph()
    graph.add_edges_from(
        [
            ("A", "B"),
            ("B", "C"),
            ("C", "A"),  # Cycle with no exit
        ]
    )

    with pytest.raises(ValueError, match="Uncontrolled cycle detected"):
        validate_graph_acyclic(graph)


# ============================================================================
# Layer 3: Round Counter Tests
# ============================================================================


def test_check_convergence_below_max_rounds(sample_problem: Problem):
    """Test convergence check when below max rounds."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=10,
    )
    state["round_number"] = 5

    result = check_convergence_node(state)

    assert result["should_stop"] is False
    assert result.get("stop_reason") is None


def test_check_convergence_at_max_rounds(sample_problem: Problem):
    """Test convergence check when at max rounds."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=10,
    )
    state["round_number"] = 10

    result = check_convergence_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "max_rounds"


def test_check_convergence_at_hard_cap(sample_problem: Problem):
    """Test convergence check at absolute hard cap (15 rounds)."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=15,
    )
    state["round_number"] = 15

    result = check_convergence_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "hard_cap_15_rounds"


def test_check_convergence_with_high_score(sample_problem: Problem):
    """Test convergence check when convergence score is high."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=10,
    )
    state["round_number"] = 3
    state["metrics"] = DeliberationMetrics(convergence_score=0.90)

    result = check_convergence_node(state)

    assert result["should_stop"] is True
    assert result["stop_reason"] == "consensus"


def test_check_convergence_with_low_score(sample_problem: Problem):
    """Test convergence check when convergence score is low."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=10,
    )
    state["round_number"] = 3
    state["metrics"] = DeliberationMetrics(convergence_score=0.50)

    result = check_convergence_node(state)

    assert result["should_stop"] is False


def test_route_convergence_check_stop(sample_problem: Problem):
    """Test routing when should_stop is True."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
    )
    state["should_stop"] = True
    state["stop_reason"] = "max_rounds"

    route = route_convergence_check(state)

    assert route == "vote"


def test_route_convergence_check_continue(sample_problem: Problem):
    """Test routing when should_stop is False."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
    )
    state["should_stop"] = False

    route = route_convergence_check(state)

    assert route == "facilitator_decide"


# ============================================================================
# Invariant Validation Tests
# ============================================================================


def test_validate_round_counter_valid(sample_problem: Problem):
    """Test round counter validation with valid state."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        max_rounds=10,
    )
    state["round_number"] = 5

    # Should not raise
    validate_round_counter_invariants(state)


def test_validate_round_counter_negative():
    """Test round counter validation fails with negative round."""
    state: DeliberationGraphState = {
        "session_id": "test",
        "problem": None,  # type: ignore
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": None,  # type: ignore
        "round_number": -1,  # Invalid
        "max_rounds": 10,
        "metrics": DeliberationMetrics(),
    }

    with pytest.raises(ValueError, match="Invalid round_number"):
        validate_round_counter_invariants(state)


def test_validate_round_counter_exceeds_hard_cap():
    """Test round counter validation fails when max_rounds exceeds hard cap."""
    state: DeliberationGraphState = {
        "session_id": "test",
        "problem": None,  # type: ignore
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": None,  # type: ignore
        "round_number": 5,
        "max_rounds": 20,  # Exceeds hard cap of 15
        "metrics": DeliberationMetrics(),
    }

    with pytest.raises(ValueError, match="hard cap is 15"):
        validate_round_counter_invariants(state)


def test_validate_round_counter_round_exceeds_max():
    """Test round counter validation fails when round exceeds max."""
    state: DeliberationGraphState = {
        "session_id": "test",
        "problem": None,  # type: ignore
        "personas": [],
        "contributions": [],
        "round_summaries": [],
        "phase": None,  # type: ignore
        "round_number": 11,
        "max_rounds": 10,
        "metrics": DeliberationMetrics(),
    }

    with pytest.raises(ValueError, match="exceeds max_rounds"):
        validate_round_counter_invariants(state)


# ============================================================================
# Integration Tests
# ============================================================================


def test_convergence_node_preserves_state(sample_problem: Problem):
    """Test that convergence node preserves all state fields."""
    state = create_initial_state(
        session_id="test-preserve",
        problem=sample_problem,
        max_rounds=10,
    )
    state["round_number"] = 3

    # Add some contributions
    from bo1.models.state import ContributionMessage

    state["contributions"] = [
        ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="Test contribution",
            round_number=1,
        )
    ]

    result = check_convergence_node(state)

    # Verify all fields preserved
    assert result["session_id"] == "test-preserve"
    assert result["problem"] == sample_problem
    assert len(result["contributions"]) == 1
    assert result["round_number"] == 3


def test_multiple_rounds_with_counter(sample_problem: Problem):
    """Test multiple rounds with round counter incrementing."""
    state = create_initial_state(
        session_id="test-multi",
        problem=sample_problem,
        max_rounds=5,
    )

    for round_num in range(1, 6):
        state["round_number"] = round_num
        result = check_convergence_node(state)

        if round_num < 5:
            assert result["should_stop"] is False
        else:
            # Round 5 should trigger max_rounds stop
            assert result["should_stop"] is True
            assert result["stop_reason"] == "max_rounds"
