"""Tests for graph state models and conversion functions."""

import pytest

from bo1.graph.state import (
    create_initial_state,
    deliberation_state_to_graph_state,
    graph_state_to_deliberation_state,
    state_to_dict,
    validate_state,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Constraint, ConstraintType, Problem
from bo1.models.state import (
    ContributionMessage,
    DeliberationPhase,
    DeliberationState,
)


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we invest in feature X?",
        context="SaaS startup with $500K budget",
        constraints=[
            Constraint(type=ConstraintType.BUDGET, description="Budget: $500K", value=500000),
            Constraint(
                type=ConstraintType.TIME, description="Timeline: 6 months", value="6 months"
            ),
        ],
        sub_problems=[],
    )


@pytest.fixture
def sample_personas() -> list[PersonaProfile]:
    """Create sample personas for testing using real persona data."""
    from bo1.data import get_persona_by_code

    # Load real personas from catalog
    growth_hacker_data = get_persona_by_code("growth_hacker")
    finance_strategist_data = get_persona_by_code("finance_strategist")

    if not growth_hacker_data or not finance_strategist_data:
        pytest.skip("Required personas not found in catalog")

    return [
        PersonaProfile(**growth_hacker_data),
        PersonaProfile(**finance_strategist_data),
    ]


def test_create_initial_state(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test creating initial graph state."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=10,
    )

    assert state["session_id"] == "test-123"
    assert state["problem"] == sample_problem
    assert state["personas"] == sample_personas
    assert state["phase"] == DeliberationPhase.INTAKE
    assert state["round_number"] == 0
    assert state["max_rounds"] == 10
    assert state["should_stop"] is False
    assert state["stop_reason"] is None
    assert state["contributions"] == []
    assert state["round_summaries"] == []
    assert state["current_node"] == "start"


def test_create_initial_state_without_personas(sample_problem: Problem) -> None:
    """Test creating initial state without personas (will be selected later)."""
    state = create_initial_state(
        session_id="test-456",
        problem=sample_problem,
    )

    assert state["session_id"] == "test-456"
    assert state["personas"] == []
    assert state["phase"] == DeliberationPhase.INTAKE


def test_validate_state_success(sample_problem: Problem) -> None:
    """Test state validation with valid state."""
    state = create_initial_state(
        session_id="test-789",
        problem=sample_problem,
    )

    # Should not raise
    validate_state(state)


def test_validate_state_missing_field(sample_problem: Problem) -> None:
    """Test state validation fails with missing required field."""
    state = create_initial_state(
        session_id="test-789",
        problem=sample_problem,
    )

    # Remove required field
    del state["session_id"]

    with pytest.raises(ValueError, match="Missing required field: session_id"):
        validate_state(state)


def test_validate_state_invalid_round_number(sample_problem: Problem) -> None:
    """Test state validation fails with negative round number."""
    state = create_initial_state(
        session_id="test-789",
        problem=sample_problem,
    )

    state["round_number"] = -1

    with pytest.raises(ValueError, match="Invalid round_number"):
        validate_state(state)


def test_validate_state_round_exceeds_max(sample_problem: Problem) -> None:
    """Test state validation fails when round exceeds max."""
    state = create_initial_state(
        session_id="test-789",
        problem=sample_problem,
        max_rounds=10,
    )

    state["round_number"] = 11

    with pytest.raises(ValueError, match="round_number.*exceeds max_rounds"):
        validate_state(state)


def test_validate_state_max_rounds_exceeds_cap(sample_problem: Problem) -> None:
    """Test state validation fails when max_rounds exceeds hard cap."""
    state = create_initial_state(
        session_id="test-789",
        problem=sample_problem,
        max_rounds=20,  # Exceeds hard cap of 15
    )

    with pytest.raises(ValueError, match="max_rounds.*exceeds hard cap"):
        validate_state(state)


def test_state_to_dict(sample_problem: Problem, sample_personas: list[PersonaProfile]) -> None:
    """Test converting state to dictionary for checkpointing."""
    state = create_initial_state(
        session_id="test-dict",
        problem=sample_problem,
        personas=sample_personas,
    )

    result = state_to_dict(state)

    assert isinstance(result, dict)
    assert result["session_id"] == "test-dict"
    assert isinstance(result["problem"], dict)
    assert isinstance(result["personas"], list)
    assert isinstance(result["personas"][0], dict)
    assert isinstance(result["metrics"], dict)


def test_v1_to_v2_conversion(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test converting v1 DeliberationState to v2 DeliberationGraphState."""
    v1_state = DeliberationState(
        session_id="v1-test",
        problem=sample_problem,
        selected_personas=sample_personas,
        current_round=2,
        max_rounds=10,
        phase=DeliberationPhase.DISCUSSION,
    )

    v2_state = deliberation_state_to_graph_state(v1_state)

    assert v2_state["session_id"] == "v1-test"
    assert v2_state["problem"] == sample_problem
    assert v2_state["personas"] == sample_personas
    assert v2_state["round_number"] == 2
    assert v2_state["max_rounds"] == 10
    assert v2_state["phase"] == DeliberationPhase.DISCUSSION
    # New v2 fields
    assert v2_state["should_stop"] is False
    assert v2_state["facilitator_decision"] is None


def test_v2_to_v1_conversion(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test converting v2 DeliberationGraphState to v1 DeliberationState."""
    v2_state = create_initial_state(
        session_id="v2-test",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=12,
    )
    v2_state["round_number"] = 3
    v2_state["phase"] = DeliberationPhase.VOTING

    v1_state = graph_state_to_deliberation_state(v2_state)

    assert v1_state.session_id == "v2-test"
    assert v1_state.problem == sample_problem
    assert v1_state.selected_personas == sample_personas
    assert v1_state.current_round == 3
    assert v1_state.max_rounds == 12
    assert v1_state.phase == DeliberationPhase.VOTING


def test_round_trip_conversion_no_data_loss(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test v1 → v2 → v1 round-trip conversion preserves data."""
    # Create v1 state with contributions
    v1_original = DeliberationState(
        session_id="round-trip",
        problem=sample_problem,
        selected_personas=sample_personas,
        current_round=5,
        max_rounds=10,
        phase=DeliberationPhase.DISCUSSION,
    )

    # Add a contribution
    contribution = ContributionMessage(
        persona_code="growth_hacker",
        persona_name="Zara",
        content="I think we should focus on growth...",
        round_number=1,
    )
    v1_original.add_contribution(contribution)

    # Convert v1 → v2
    v2_state = deliberation_state_to_graph_state(v1_original)

    # Convert v2 → v1
    v1_final = graph_state_to_deliberation_state(v2_state)

    # Verify no data loss
    assert v1_final.session_id == v1_original.session_id
    assert v1_final.problem == v1_original.problem
    assert v1_final.selected_personas == v1_original.selected_personas
    assert v1_final.current_round == v1_original.current_round
    assert v1_final.max_rounds == v1_original.max_rounds
    assert v1_final.phase == v1_original.phase
    assert len(v1_final.contributions) == len(v1_original.contributions)
    assert v1_final.contributions[0].persona_code == contribution.persona_code
    assert v1_final.contributions[0].content == contribution.content


def test_graph_state_with_contributions(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test graph state with contributions."""
    state = create_initial_state(
        session_id="test-contrib",
        problem=sample_problem,
        personas=sample_personas,
    )

    # Add contributions
    contrib1 = ContributionMessage(
        persona_code="growth_hacker",
        persona_name="Zara",
        content="Growth perspective...",
        round_number=1,
    )
    contrib2 = ContributionMessage(
        persona_code="tech_lead",
        persona_name="Alex",
        content="Technical perspective...",
        round_number=1,
    )

    state["contributions"] = [contrib1, contrib2]
    state["round_number"] = 1

    # Validate state still valid
    validate_state(state)

    # Convert to v1 and back
    v1_state = graph_state_to_deliberation_state(state)
    assert len(v1_state.contributions) == 2

    v2_state = deliberation_state_to_graph_state(v1_state)
    assert len(v2_state["contributions"]) == 2


def test_graph_state_with_stop_flags(sample_problem: Problem) -> None:
    """Test graph state with stop flags set."""
    state = create_initial_state(
        session_id="test-stop",
        problem=sample_problem,
    )

    state["should_stop"] = True
    state["stop_reason"] = "max_rounds"
    state["round_number"] = 10
    state["max_rounds"] = 10

    # Should still be valid
    validate_state(state)


def test_graph_state_with_metrics(sample_problem: Problem) -> None:
    """Test graph state with updated metrics."""
    state = create_initial_state(
        session_id="test-metrics",
        problem=sample_problem,
    )

    # Update metrics
    state["metrics"].total_cost = 0.15
    state["metrics"].total_tokens = 1500
    state["metrics"].cache_hits = 3

    # Convert to dict and verify metrics preserved
    result = state_to_dict(state)
    assert result["metrics"]["total_cost"] == 0.15
    assert result["metrics"]["total_tokens"] == 1500
    assert result["metrics"]["cache_hits"] == 3
