"""Comprehensive Pydantic model validation tests.

Tests serialization, deserialization, validation, and edge cases for all
Pydantic models. Would catch model structure changes and validation issues.
"""

import json
from datetime import datetime

import pytest
from pydantic import ValidationError

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationMetrics,
    DeliberationPhase,
    DeliberationState,
)
from bo1.models.votes import Vote, VoteDecision


# ============================================================================
# Round-Trip Serialization Tests
# ============================================================================


@pytest.mark.unit
def test_problem_model_round_trip():
    """Test: Problem model serializes and deserializes correctly."""
    original = Problem(
        statement="Should we invest $500K in AI infrastructure?",
        context="Series A funded startup, 50 employees",
        constraints="Must decide within 30 days, limited engineering bandwidth",
        success_criteria="Clear ROI projection, team buy-in >80%",
    )

    # Serialize to dict
    data = original.model_dump()
    assert isinstance(data, dict)
    assert data["statement"] == original.statement

    # Serialize to JSON
    json_str = original.model_dump_json()
    assert isinstance(json_str, str)
    assert "500K" in json_str

    # Deserialize from dict
    restored_from_dict = Problem.model_validate(data)
    assert restored_from_dict.statement == original.statement
    assert restored_from_dict.context == original.context
    assert restored_from_dict.constraints == original.constraints
    assert restored_from_dict.success_criteria == original.success_criteria

    # Deserialize from JSON
    restored_from_json = Problem.model_validate_json(json_str)
    assert restored_from_json.statement == original.statement


@pytest.mark.unit
def test_sub_problem_model_round_trip():
    """Test: SubProblem model serializes and deserializes correctly."""
    original = SubProblem(
        id="sp-001",
        statement="What is the projected ROI?",
        context="Need to justify the investment",
        assigned_personas=["financial_analyst", "growth_hacker"],
    )

    # Round trip through dict
    data = original.model_dump()
    restored = SubProblem.model_validate(data)

    assert restored.id == original.id
    assert restored.statement == original.statement
    assert restored.context == original.context
    assert restored.assigned_personas == original.assigned_personas

    # Round trip through JSON
    json_str = original.model_dump_json()
    restored_json = SubProblem.model_validate_json(json_str)
    assert restored_json.statement == original.statement


@pytest.mark.unit
def test_persona_profile_model_round_trip():
    """Test: PersonaProfile model serializes and deserializes correctly."""
    original = PersonaProfile(
        code="strategic_advisor",
        name="Maria Chen",
        expertise=["strategy", "scaling", "fundraising"],
        system_prompt="You are Maria Chen, a strategic advisor with 15 years...",
    )

    # Round trip through dict
    data = original.model_dump()
    restored = PersonaProfile.model_validate(data)

    assert restored.code == original.code
    assert restored.name == original.name
    assert restored.expertise == original.expertise
    assert restored.system_prompt == original.system_prompt

    # Verify list fields are preserved
    assert len(restored.expertise) == 3
    assert "strategy" in restored.expertise


@pytest.mark.unit
def test_contribution_message_model_round_trip():
    """Test: ContributionMessage model serializes and deserializes correctly."""
    original = ContributionMessage(
        persona_code="strategic_advisor",
        persona_name="Maria Chen",
        content="I recommend focusing on unit economics first...",
        thinking="Let me analyze the financial implications...",
        contribution_type=ContributionType.INITIAL,
        round_number=0,
        token_count=250,
        cost=0.0015,
    )

    # Round trip through dict
    data = original.model_dump()
    restored = ContributionMessage.model_validate(data)

    assert restored.persona_code == original.persona_code
    assert restored.persona_name == original.persona_name
    assert restored.content == original.content
    assert restored.thinking == original.thinking
    assert restored.contribution_type == original.contribution_type
    assert restored.round_number == original.round_number
    assert restored.token_count == original.token_count
    assert restored.cost == original.cost

    # Verify timestamp preserved
    assert isinstance(restored.timestamp, datetime)


@pytest.mark.unit
def test_deliberation_metrics_model_round_trip():
    """Test: DeliberationMetrics model serializes and deserializes correctly."""
    original = DeliberationMetrics(
        total_cost=0.125,
        total_tokens=5000,
        cache_hits=15,
        cache_creation_tokens=500,
        cache_read_tokens=3000,
        phase_costs={
            "decomposition": 0.02,
            "persona_selection": 0.01,
            "initial_round": 0.05,
        },
        convergence_score=0.85,
        novelty_score=0.15,
        conflict_score=0.30,
    )

    # Round trip through dict
    data = original.model_dump()
    restored = DeliberationMetrics.model_validate(data)

    assert restored.total_cost == original.total_cost
    assert restored.total_tokens == original.total_tokens
    assert restored.cache_hits == original.cache_hits
    assert restored.phase_costs == original.phase_costs
    assert restored.convergence_score == original.convergence_score
    assert restored.novelty_score == original.novelty_score
    assert restored.conflict_score == original.conflict_score

    # Round trip through JSON
    json_str = original.model_dump_json()
    restored_json = DeliberationMetrics.model_validate_json(json_str)
    assert restored_json.total_cost == original.total_cost


@pytest.mark.unit
def test_deliberation_state_model_round_trip():
    """Test: DeliberationState model serializes and deserializes correctly."""
    problem = Problem(
        statement="Test problem",
        context="Test context",
        constraints="Test constraints",
        success_criteria="Test success",
    )

    personas = [
        PersonaProfile(
            code="test_expert",
            name="Test Expert",
            expertise=["testing"],
            system_prompt="You are a test expert.",
        )
    ]

    contribution = ContributionMessage(
        persona_code="test_expert",
        persona_name="Test Expert",
        content="Test contribution",
        contribution_type=ContributionType.INITIAL,
        round_number=0,
    )

    original = DeliberationState(
        session_id="test-session-123",
        problem=problem,
        selected_personas=personas,
        contributions=[contribution],
        round_summaries=["Round 0: Initial contributions collected"],
        phase=DeliberationPhase.DISCUSSION,
        current_round=1,
        max_rounds=5,
        metrics=DeliberationMetrics(total_cost=0.05, total_tokens=1000),
    )

    # Round trip through dict
    data = original.model_dump()
    restored = DeliberationState.model_validate(data)

    assert restored.session_id == original.session_id
    assert restored.problem.statement == original.problem.statement
    assert len(restored.selected_personas) == 1
    assert restored.selected_personas[0].code == "test_expert"
    assert len(restored.contributions) == 1
    assert restored.contributions[0].content == "Test contribution"
    assert len(restored.round_summaries) == 1
    assert restored.phase == original.phase
    assert restored.current_round == original.current_round
    assert restored.max_rounds == original.max_rounds
    assert restored.metrics.total_cost == original.metrics.total_cost


@pytest.mark.unit
def test_vote_model_round_trip():
    """Test: Vote model serializes and deserializes correctly."""
    original = Vote(
        persona_code="strategic_advisor",
        persona_name="Maria Chen",
        decision=VoteDecision.YES,
        confidence=0.8,
        reasoning="Strong financial projections and market validation",
    )

    # Round trip through dict
    data = original.model_dump()
    restored = Vote.model_validate(data)

    assert restored.persona_code == original.persona_code
    assert restored.persona_name == original.persona_name
    assert restored.decision == original.decision
    assert restored.confidence == original.confidence
    assert restored.reasoning == original.reasoning


# ============================================================================
# Validation Error Tests
# ============================================================================


@pytest.mark.unit
def test_problem_model_requires_all_fields():
    """Test: Problem model raises ValidationError when required fields missing."""
    # Missing statement
    with pytest.raises(ValidationError) as exc_info:
        Problem(
            context="Test",
            constraints="Test",
            success_criteria="Test",
        )  # type: ignore[call-arg]
    assert "statement" in str(exc_info.value)

    # Missing context
    with pytest.raises(ValidationError) as exc_info:
        Problem(
            statement="Test",
            constraints="Test",
            success_criteria="Test",
        )  # type: ignore[call-arg]
    assert "context" in str(exc_info.value)


@pytest.mark.unit
def test_contribution_message_requires_fields():
    """Test: ContributionMessage raises ValidationError for missing fields."""
    # Missing required fields
    with pytest.raises(ValidationError) as exc_info:
        ContributionMessage(
            persona_code="test",
            content="Test",
        )  # type: ignore[call-arg]

    errors = str(exc_info.value)
    assert "persona_name" in errors or "round_number" in errors


@pytest.mark.unit
def test_contribution_message_validates_round_number():
    """Test: ContributionMessage validates round_number >= 0."""
    # Negative round_number should fail
    with pytest.raises(ValidationError) as exc_info:
        ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="Test",
            round_number=-1,
        )
    assert "round_number" in str(exc_info.value) or "greater" in str(exc_info.value)


@pytest.mark.unit
def test_deliberation_metrics_validates_score_ranges():
    """Test: DeliberationMetrics validates scores are in [0, 1] range."""
    # convergence_score > 1.0 should fail
    with pytest.raises(ValidationError) as exc_info:
        DeliberationMetrics(convergence_score=1.5)
    assert "convergence_score" in str(exc_info.value) or "less than" in str(exc_info.value)

    # convergence_score < 0.0 should fail
    with pytest.raises(ValidationError) as exc_info:
        DeliberationMetrics(convergence_score=-0.1)
    assert "convergence_score" in str(exc_info.value) or "greater" in str(exc_info.value)

    # Valid scores should work
    metrics = DeliberationMetrics(
        convergence_score=0.0,
        novelty_score=0.5,
        conflict_score=1.0,
    )
    assert metrics.convergence_score == 0.0
    assert metrics.novelty_score == 0.5
    assert metrics.conflict_score == 1.0


@pytest.mark.unit
def test_vote_validates_confidence_range():
    """Test: Vote validates confidence is in [0, 1] range."""
    # confidence > 1.0 should fail
    with pytest.raises(ValidationError) as exc_info:
        Vote(
            persona_code="test",
            persona_name="Test",
            decision=VoteDecision.YES,
            confidence=1.5,
            reasoning="Test",
        )
    assert "confidence" in str(exc_info.value)

    # confidence < 0.0 should fail
    with pytest.raises(ValidationError) as exc_info:
        Vote(
            persona_code="test",
            persona_name="Test",
            decision=VoteDecision.YES,
            confidence=-0.1,
            reasoning="Test",
        )
    assert "confidence" in str(exc_info.value)


# ============================================================================
# Edge Case Tests
# ============================================================================


@pytest.mark.unit
def test_models_handle_empty_strings():
    """Test: Models handle empty strings appropriately."""
    # Empty statement should be allowed (validation happens at business logic level)
    problem = Problem(
        statement="",
        context="",
        constraints="",
        success_criteria="",
    )
    assert problem.statement == ""


@pytest.mark.unit
def test_models_handle_empty_lists():
    """Test: Models handle empty lists correctly."""
    persona = PersonaProfile(
        code="test",
        name="Test",
        expertise=[],  # Empty list should be allowed
        system_prompt="Test",
    )
    assert persona.expertise == []

    state = DeliberationState(
        session_id="test",
        problem=Problem(
        title="Test",
        description="",
        context="",
    ),
        selected_personas=[],  # Empty list
        contributions=[],  # Empty list
        round_summaries=[],  # Empty list
        phase=DeliberationPhase.INTAKE,
        current_round=0,
        max_rounds=5,
        metrics=DeliberationMetrics(),
    )
    assert state.selected_personas == []
    assert state.contributions == []
    assert state.round_summaries == []


@pytest.mark.unit
def test_models_handle_none_optional_fields():
    """Test: Models handle None for optional fields."""
    # ContributionMessage with no thinking
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test",
        thinking=None,
        round_number=0,
        token_count=None,
        cost=None,
    )
    assert contribution.thinking is None
    assert contribution.token_count is None
    assert contribution.cost is None

    # DeliberationMetrics with no scores
    metrics = DeliberationMetrics()
    assert metrics.convergence_score is None
    assert metrics.novelty_score is None
    assert metrics.conflict_score is None

    # DeliberationState with no sub-problem
    state = DeliberationState(
        session_id="test",
        problem=Problem(
        title="Test",
        description="",
        context="",
    ),
        current_sub_problem=None,
        selected_personas=[],
        contributions=[],
        round_summaries=[],
        phase=DeliberationPhase.INTAKE,
        current_round=0,
        max_rounds=5,
        metrics=DeliberationMetrics(),
    )
    assert state.current_sub_problem is None


@pytest.mark.unit
def test_models_handle_very_long_strings():
    """Test: Models handle very long strings without issues."""
    long_text = "A" * 10000  # 10K character string

    problem = Problem(
        statement=long_text,
        context=long_text,
        constraints=long_text,
        success_criteria=long_text,
    )

    # Should serialize without issues
    data = problem.model_dump()
    assert len(data["statement"]) == 10000

    # Should deserialize without issues
    restored = Problem.model_validate(data)
    assert len(restored.statement) == 10000


@pytest.mark.unit
def test_models_handle_special_characters():
    """Test: Models handle special characters and unicode."""
    special_text = "Test with émojis 🚀 and spëcial çhars: <>{}[]|\\\"'`~!@#$%^&*()"

    problem = Problem(
        statement=special_text,
        context=special_text,
        constraints=special_text,
        success_criteria=special_text,
    )

    # JSON serialization should handle unicode
    json_str = problem.model_dump_json()
    assert "🚀" in json_str or "\\u" in json_str  # Either raw or escaped

    # Should round-trip correctly
    restored = Problem.model_validate_json(json_str)
    assert restored.statement == special_text


@pytest.mark.unit
def test_contribution_message_tokens_used_property():
    """Test: ContributionMessage.tokens_used property works correctly."""
    # With token_count set
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test",
        round_number=0,
        token_count=500,
    )
    assert contribution.tokens_used == 500

    # With token_count None
    contribution_no_tokens = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test",
        round_number=0,
        token_count=None,
    )
    assert contribution_no_tokens.tokens_used == 0


# ============================================================================
# Type Coercion Tests
# ============================================================================


@pytest.mark.unit
def test_models_coerce_compatible_types():
    """Test: Pydantic coerces compatible types when possible."""
    # String to int for round_number
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test",
        round_number="5",  # type: ignore[arg-type]
    )
    assert contribution.round_number == 5
    assert isinstance(contribution.round_number, int)

    # String to float for cost
    contribution_with_cost = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test",
        round_number=0,
        cost="0.123",  # type: ignore[arg-type]
    )
    assert contribution_with_cost.cost == 0.123
    assert isinstance(contribution_with_cost.cost, float)


@pytest.mark.unit
def test_models_reject_incompatible_types():
    """Test: Models reject incompatible type coercions."""
    # Invalid enum value
    with pytest.raises(ValidationError):
        ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="Test",
            contribution_type="invalid_type",  # type: ignore[arg-type]
            round_number=0,
        )

    # Invalid phase enum
    with pytest.raises(ValidationError):
        DeliberationState(
            session_id="test",
            problem=Problem(
        title="Test",
        description="",
        context="",
    ),
            selected_personas=[],
            contributions=[],
            round_summaries=[],
            phase="invalid_phase",  # type: ignore[arg-type]
            current_round=0,
            max_rounds=5,
            metrics=DeliberationMetrics(),
        )
