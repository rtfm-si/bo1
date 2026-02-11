"""Comprehensive Pydantic model validation tests.

Tests serialization, deserialization, validation, and edge cases for all
Pydantic models. Would catch model structure changes and validation issues.
"""

from datetime import datetime

import pytest
from pydantic import ValidationError

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.recommendations import Recommendation
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationMetrics,
    DeliberationPhaseType,
)

# ============================================================================
# Round-Trip Serialization Tests
# ============================================================================


@pytest.mark.unit
def test_problem_model_round_trip():
    """Test: Problem model serializes and deserializes correctly."""
    original = Problem(
        title="AI Infrastructure Investment",
        description="Should we invest $500K in AI infrastructure?",
        context="Series A funded startup, 50 employees",
    )

    # Serialize to dict
    data = original.model_dump()
    assert isinstance(data, dict)
    assert data["title"] == original.title

    # Serialize to JSON
    json_str = original.model_dump_json()
    assert isinstance(json_str, str)
    assert "500K" in json_str

    # Deserialize from dict
    restored_from_dict = Problem.model_validate(data)
    assert restored_from_dict.title == original.title
    assert restored_from_dict.description == original.description
    assert restored_from_dict.context == original.context

    # Deserialize from JSON
    restored_from_json = Problem.model_validate_json(json_str)
    assert restored_from_json.title == original.title


@pytest.mark.unit
def test_sub_problem_model_round_trip():
    """Test: SubProblem model serializes and deserializes correctly."""
    original = SubProblem(
        id="sp-001",
        goal="What is the projected ROI?",
        context="Need to justify the investment",
        complexity_score=6,
    )

    # Round trip through dict
    data = original.model_dump()
    restored = SubProblem.model_validate(data)

    assert restored.id == original.id
    assert restored.goal == original.goal
    assert restored.context == original.context
    assert restored.complexity_score == original.complexity_score

    # Round trip through JSON
    json_str = original.model_dump_json()
    restored_json = SubProblem.model_validate_json(json_str)
    assert restored_json.goal == original.goal


@pytest.mark.unit
def test_persona_profile_model_round_trip(sample_persona):
    """Test: PersonaProfile model serializes and deserializes correctly."""
    original = sample_persona

    # Round trip through dict
    data = original.model_dump()
    restored = PersonaProfile.model_validate(data)

    assert restored.code == original.code
    assert restored.name == original.name
    assert restored.domain_expertise == original.domain_expertise
    assert restored.system_prompt == original.system_prompt

    # Verify list fields are preserved
    assert len(restored.domain_expertise) > 0


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
def test_vote_model_round_trip():
    """Test: Vote/Recommendation model serializes and deserializes correctly."""
    original = Recommendation(
        persona_code="strategic_advisor",
        persona_name="Maria Chen",
        recommendation="Approve investment in X",
        confidence=0.8,
        reasoning="Strong financial projections and market validation",
    )

    # Round trip through dict
    data = original.model_dump()
    restored = Recommendation.model_validate(data)

    assert restored.persona_code == original.persona_code
    assert restored.persona_name == original.persona_name
    assert restored.recommendation == original.recommendation
    assert restored.confidence == original.confidence
    assert restored.reasoning == original.reasoning


# ============================================================================
# Validation Error Tests
# ============================================================================


@pytest.mark.unit
def test_problem_model_requires_all_fields():
    """Test: Problem model raises ValidationError when required fields missing."""
    # Missing title
    with pytest.raises(ValidationError) as exc_info:
        Problem(
            description="Test",
            context="Test",
        )  # type: ignore[call-arg]
    assert "title" in str(exc_info.value)

    # Missing context
    with pytest.raises(ValidationError) as exc_info:
        Problem(
            title="Test",
            description="Test",
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
            thinking=None,
            token_count=None,
            cost=None,
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
        Recommendation(
            persona_code="test",
            persona_name="Test",
            recommendation="Approve investment",
            confidence=1.5,
            reasoning="Test",
        )
    assert "confidence" in str(exc_info.value)

    # confidence < 0.0 should fail
    with pytest.raises(ValidationError) as exc_info:
        Recommendation(
            persona_code="test",
            persona_name="Test",
            recommendation="Approve investment",
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
    # Empty fields should be allowed (validation happens at business logic level)
    problem = Problem(
        title="",
        description="",
        context="",
    )
    assert problem.title == ""


@pytest.mark.unit
def test_models_handle_empty_lists():
    """Test: Models handle empty lists correctly."""
    from bo1.models.persona import PersonaCategory, PersonaType, ResponseStyle

    persona = PersonaProfile(
        id="test-id",
        code="test",
        name="Test",
        archetype="Test",
        category=PersonaCategory.STRATEGY,
        description="Test",
        emoji="🧪",
        color_hex="#FF0000",
        traits={
            "creative": 0.5,
            "analytical": 0.8,
            "optimistic": 0.6,
            "risk_averse": 0.4,
            "detail_oriented": 0.7,
        },
        default_weight=1.0,
        temperature=0.7,
        system_prompt="Test",
        response_style=ResponseStyle.ANALYTICAL,
        display_name="Test",
        domain_expertise=[],  # Empty list should be allowed
        persona_type=PersonaType.STANDARD,
    )
    assert persona.domain_expertise == []


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


@pytest.mark.unit
def test_models_handle_very_long_strings():
    """Test: Models handle very long strings without issues."""
    long_text = "A" * 10000  # 10K character string

    problem = Problem(
        title=long_text,
        description=long_text,
        context=long_text,
    )

    # Should serialize without issues
    data = problem.model_dump()
    assert len(data["title"]) == 10000

    # Should deserialize without issues
    restored = Problem.model_validate(data)
    assert len(restored.title) == 10000


@pytest.mark.unit
def test_models_handle_special_characters():
    """Test: Models handle special characters and unicode."""
    special_text = "Test with émojis 🚀 and spëcial çhars: <>{}[]|\\\"'`~!@#$%^&*()"

    problem = Problem(
        title=special_text,
        description=special_text,
        context=special_text,
    )

    # JSON serialization should handle unicode
    json_str = problem.model_dump_json()
    assert "🚀" in json_str or "\\u" in json_str  # Either raw or escaped

    # Should round-trip correctly
    restored = Problem.model_validate_json(json_str)
    assert restored.title == special_text


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
        thinking=None,
        token_count=None,
        cost=None,
        round_number="5",  # type: ignore[arg-type]
    )
    assert contribution.round_number == 5
    assert isinstance(contribution.round_number, int)

    # String to float for cost
    contribution_with_cost = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test",
        thinking=None,
        token_count=None,
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
            thinking=None,
            token_count=None,
            cost=None,
            round_number=0,
        )


@pytest.mark.unit
def test_contribution_message_new_fields_optional():
    """Test: New DB-aligned fields are optional with None defaults."""
    # Create with only original required fields
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test Persona",
        content="Test content",
        round_number=1,
    )

    # New fields should default to None
    assert contribution.id is None
    assert contribution.session_id is None
    assert contribution.model is None
    assert contribution.phase is None
    assert contribution.embedding is None


@pytest.mark.unit
def test_contribution_message_new_fields_set():
    """Test: New DB-aligned fields can be set."""
    contribution = ContributionMessage(
        persona_code="ceo",
        persona_name="CEO",
        content="Strategic analysis...",
        round_number=2,
        id=42,
        session_id="bo1_test123",
        model="claude-sonnet-4-20250514",
        phase=DeliberationPhaseType.EXPLORATION,
        embedding=[0.1, 0.2, 0.3],
    )

    assert contribution.id == 42
    assert contribution.session_id == "bo1_test123"
    assert contribution.model == "claude-sonnet-4-20250514"
    assert contribution.phase == DeliberationPhaseType.EXPLORATION
    assert contribution.embedding == [0.1, 0.2, 0.3]


@pytest.mark.unit
def test_contribution_message_from_db_row():
    """Test: from_db_row() factory converts DB dict correctly."""
    from datetime import datetime

    db_row = {
        "id": 123,
        "session_id": "bo1_abc",
        "persona_code": "cfo",
        "content": "Financial analysis...",
        "round_number": 3,
        "phase": "challenge",
        "cost": 0.0025,
        "tokens": 150,
        "model": "claude-haiku-3-5-20241022",
        "created_at": datetime(2025, 1, 15, 10, 30),
    }

    msg = ContributionMessage.from_db_row(db_row)

    assert msg.id == 123
    assert msg.session_id == "bo1_abc"
    assert msg.persona_code == "cfo"
    assert msg.persona_name == "cfo"  # Falls back to persona_code
    assert msg.content == "Financial analysis..."
    assert msg.round_number == 3
    assert msg.phase == DeliberationPhaseType.CHALLENGE
    assert msg.cost == 0.0025
    assert msg.token_count == 150  # Maps from 'tokens' to 'token_count'
    assert msg.model == "claude-haiku-3-5-20241022"
    assert msg.timestamp == datetime(2025, 1, 15, 10, 30)


@pytest.mark.unit
def test_contribution_message_embedding_excluded_from_dump():
    """Test: embedding field excluded from model_dump() by default."""
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Content",
        round_number=1,
        embedding=[0.1] * 1024,  # Large vector
    )

    dumped = contribution.model_dump()
    assert "embedding" not in dumped


@pytest.mark.unit
def test_contribution_message_phase_enum_values():
    """Test: phase field accepts all DeliberationPhaseType enum values."""
    for phase in DeliberationPhaseType:
        contribution = ContributionMessage(
            persona_code="test",
            persona_name="Test",
            content="Content",
            round_number=1,
            phase=phase,
        )
        assert contribution.phase == phase


@pytest.mark.unit
def test_contribution_message_phase_string_still_works():
    """Test: phase field still accepts string for backward compatibility."""
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Content",
        round_number=1,
        phase="exploration",  # String value
    )
    assert contribution.phase == "exploration"


@pytest.mark.unit
def test_contribution_message_from_db_row_converts_phase_to_enum():
    """Test: from_db_row converts phase string to enum."""
    db_row = {
        "id": 1,
        "session_id": "bo1_test",
        "persona_code": "ceo",
        "content": "Test",
        "round_number": 1,
        "phase": "convergence",
        "cost": 0.001,
        "tokens": 100,
        "model": "test-model",
        "created_at": datetime.now(),
    }

    msg = ContributionMessage.from_db_row(db_row)
    assert msg.phase == DeliberationPhaseType.CONVERGENCE
    assert isinstance(msg.phase, DeliberationPhaseType)


@pytest.mark.unit
def test_contribution_message_from_db_row_handles_invalid_phase():
    """Test: from_db_row handles invalid phase gracefully."""
    db_row = {
        "id": 1,
        "session_id": "bo1_test",
        "persona_code": "ceo",
        "content": "Test",
        "round_number": 1,
        "phase": "invalid_phase",  # Not a valid enum value
        "cost": 0.001,
        "tokens": 100,
        "model": "test-model",
        "created_at": datetime.now(),
    }

    msg = ContributionMessage.from_db_row(db_row)
    assert msg.phase is None  # Falls back to None for invalid values
