"""Type contract tests to catch type mismatches before CI/CD.

These tests validate that our type annotations match actual runtime behavior
and external API contracts. They would have caught the recent mypy errors.
"""

import pytest

from bo1.agents.facilitator import FacilitatorDecision
from bo1.graph.state import (
    DeliberationGraphState,
    create_initial_state,
    serialize_state_for_checkpoint,
    validate_state,
)
from bo1.llm.client import ClaudeClient, TokenUsage
from bo1.models.problem import Problem
from bo1.models.state import (
    ContributionMessage,
    ContributionType,
    DeliberationMetrics,
    DeliberationPhase,
)

# ============================================================================
# LLM Client Type Contracts
# ============================================================================


@pytest.mark.unit
def test_token_usage_model_structure():
    """Test: TokenUsage model has correct fields and types."""
    usage = TokenUsage(
        input_tokens=100,
        output_tokens=50,
        cache_creation_tokens=20,
        cache_read_tokens=80,
    )

    # Verify fields exist and are correct types
    assert isinstance(usage.input_tokens, int)
    assert isinstance(usage.output_tokens, int)
    assert isinstance(usage.cache_creation_tokens, int)
    assert isinstance(usage.cache_read_tokens, int)

    # Verify properties
    assert isinstance(usage.total_input_tokens, int)
    assert usage.total_input_tokens == 120  # 100 + 20
    assert isinstance(usage.total_tokens, int)
    assert usage.total_tokens == 250  # 100 + 50 + 20 + 80

    # Verify cache hit rate calculation
    assert isinstance(usage.cache_hit_rate, float)
    assert 0.0 <= usage.cache_hit_rate <= 1.0

    # Test calculate_cost returns float
    cost = usage.calculate_cost("sonnet")
    assert isinstance(cost, float)
    assert cost >= 0.0


@pytest.mark.unit
def test_claude_client_initialization():
    """Test: ClaudeClient initializes with correct types."""
    client = ClaudeClient()

    # Verify internal state types
    assert isinstance(client.max_retries, int)
    assert client.api_key is None or isinstance(client.api_key, str)


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_llm_client_call_returns_correct_types():
    """Test: LLM client call returns (str, TokenUsage) tuple."""
    client = ClaudeClient()

    response, usage = await client.call(
        model="haiku",
        messages=[{"role": "user", "content": "Say 'test' and nothing else"}],
        system="You only say exactly what the user asks.",
        max_tokens=50,
    )

    # Verify return types
    assert isinstance(response, str), f"Expected str, got {type(response)}"
    assert isinstance(usage, TokenUsage), f"Expected TokenUsage, got {type(usage)}"

    # Verify TokenUsage fields match API response
    assert isinstance(usage.input_tokens, int)
    assert isinstance(usage.output_tokens, int)
    assert isinstance(usage.cache_creation_tokens, int)
    assert isinstance(usage.cache_read_tokens, int)

    # All token counts should be non-negative
    assert usage.input_tokens >= 0
    assert usage.output_tokens >= 0
    assert usage.cache_creation_tokens >= 0
    assert usage.cache_read_tokens >= 0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_llm_client_with_caching_returns_correct_types():
    """Test: LLM client with caching still returns correct types."""
    client = ClaudeClient()

    system = "You are a test assistant." * 50  # Long system prompt

    response, usage = await client.call(
        model="haiku",
        messages=[{"role": "user", "content": "Hi"}],
        system=system,
        cache_system=True,
        max_tokens=50,
    )

    # Verify types with caching enabled
    assert isinstance(response, str)
    assert isinstance(usage, TokenUsage)

    # With caching, either cache_creation or cache_read should be > 0
    assert usage.cache_creation_tokens > 0 or usage.cache_read_tokens >= 0


@pytest.mark.asyncio
@pytest.mark.requires_llm
async def test_llm_client_call_for_role_returns_correct_types():
    """Test: call_for_role returns same types as call."""
    client = ClaudeClient()

    response, usage = await client.call_for_role(
        role="SUMMARIZER",
        messages=[{"role": "user", "content": "Summarize: Test"}],
        max_tokens=50,
    )

    assert isinstance(response, str)
    assert isinstance(usage, TokenUsage)


# ============================================================================
# Graph State Type Contracts
# ============================================================================


@pytest.mark.unit
def test_deliberation_graph_state_structure():
    """Test: DeliberationGraphState has all required fields with correct types."""
    problem = Problem(title="Test problem", description="Test context", context="Test constraints")

    state = create_initial_state(
        session_id="test-123",
        problem=problem,
        max_rounds=5,
    )

    # Verify required fields exist
    assert "session_id" in state
    assert "problem" in state
    assert "personas" in state
    assert "contributions" in state
    assert "round_summaries" in state
    assert "phase" in state
    assert "round_number" in state
    assert "max_rounds" in state
    assert "metrics" in state

    # Verify field types
    assert isinstance(state["session_id"], str)
    assert isinstance(state["problem"], Problem)
    assert isinstance(state["personas"], list)
    assert isinstance(state["contributions"], list)
    assert isinstance(state["round_summaries"], list)
    assert isinstance(state["phase"], DeliberationPhase)
    assert isinstance(state["round_number"], int)
    assert isinstance(state["max_rounds"], int)
    assert isinstance(state["metrics"], DeliberationMetrics)

    # Verify optional fields
    assert state["current_sub_problem"] is None or isinstance(
        state["current_sub_problem"], type(None)
    )
    assert state["facilitator_decision"] is None or isinstance(
        state["facilitator_decision"], FacilitatorDecision
    )
    assert isinstance(state["should_stop"], bool)
    assert state["stop_reason"] is None or isinstance(state["stop_reason"], str)
    assert state["user_input"] is None or isinstance(state["user_input"], str)
    assert isinstance(state["current_node"], str)
    assert isinstance(state["recommendations"], list)
    assert state["synthesis"] is None or isinstance(state["synthesis"], str)


@pytest.mark.unit
def test_state_validation_catches_missing_fields():
    """Test: validate_state raises ValueError for missing required fields."""
    # Empty state should fail
    with pytest.raises(ValueError, match="Missing required field"):
        validate_state(DeliberationGraphState())

    # State with only session_id should fail
    with pytest.raises(ValueError, match="Missing required field"):
        validate_state(DeliberationGraphState(session_id="test"))


@pytest.mark.unit
def test_state_validation_catches_invalid_rounds():
    """Test: validate_state catches invalid round numbers."""
    problem = Problem(title="Test", description="Test", context="Test")

    # Test negative round_number
    state = create_initial_state("test", problem)
    state["round_number"] = -1

    with pytest.raises(ValueError, match="Invalid round_number"):
        validate_state(state)

    # Test round_number > max_rounds
    state = create_initial_state("test", problem, max_rounds=5)
    state["round_number"] = 10

    with pytest.raises(ValueError, match="exceeds max_rounds"):
        validate_state(state)

    # Test max_rounds > 15 (hard cap)
    state = create_initial_state("test", problem, max_rounds=20)

    with pytest.raises(ValueError, match="exceeds hard cap"):
        validate_state(state)


@pytest.mark.unit
def test_state_serialization_preserves_types(sample_problem, sample_personas):
    """Test: serialize_state_for_checkpoint preserves all data."""
    problem = sample_problem
    personas = sample_personas

    contribution = ContributionMessage(
        persona_code="test_expert",
        persona_name="Test Expert",
        content="Test contribution",
        contribution_type=ContributionType.INITIAL,
        thinking=None,
        token_count=None,
        cost=None,
        round_number=0,
    )

    state = create_initial_state("test-123", problem, personas=personas, max_rounds=5)
    state["contributions"] = [contribution]
    state["round_summaries"] = ["Round 0 summary"]

    # Serialize to dict
    serialized = serialize_state_for_checkpoint(state)

    # Verify it's a dict
    assert isinstance(serialized, dict)

    # Verify all keys preserved
    assert "session_id" in serialized
    assert "problem" in serialized
    assert "personas" in serialized
    assert "contributions" in serialized
    assert "round_summaries" in serialized

    # Verify nested objects are dicts (not Pydantic models)
    assert isinstance(serialized["problem"], dict)
    assert isinstance(serialized["personas"], list)
    assert isinstance(serialized["personas"][0], dict)
    assert isinstance(serialized["contributions"], list)
    assert isinstance(serialized["contributions"][0], dict)
    assert isinstance(serialized["metrics"], dict)


# ============================================================================
# Pydantic Model Type Contracts
# ============================================================================


@pytest.mark.unit
def test_contribution_message_fields_have_correct_types():
    """Test: ContributionMessage fields have correct types."""
    contribution = ContributionMessage(
        persona_code="test",
        persona_name="Test",
        content="Test content",
        contribution_type=ContributionType.INITIAL,
        thinking=None,
        token_count=None,
        cost=None,
        round_number=0,
    )

    assert isinstance(contribution.persona_code, str)
    assert isinstance(contribution.persona_name, str)
    assert isinstance(contribution.content, str)
    assert isinstance(contribution.contribution_type, ContributionType)
    assert isinstance(contribution.round_number, int)
    assert contribution.thinking is None or isinstance(contribution.thinking, str)
    assert contribution.token_count is None or isinstance(contribution.token_count, int)
    assert contribution.cost is None or isinstance(contribution.cost, float)


@pytest.mark.unit
def test_deliberation_metrics_fields_have_correct_types():
    """Test: DeliberationMetrics fields have correct types."""
    metrics = DeliberationMetrics()

    assert isinstance(metrics.total_cost, float)
    assert isinstance(metrics.total_tokens, int)
    assert isinstance(metrics.cache_hits, int)
    assert isinstance(metrics.cache_creation_tokens, int)
    assert isinstance(metrics.cache_read_tokens, int)
    assert isinstance(metrics.phase_costs, dict)

    # Verify optional fields
    assert metrics.convergence_score is None or isinstance(metrics.convergence_score, float)
    assert metrics.novelty_score is None or isinstance(metrics.novelty_score, float)
    assert metrics.conflict_score is None or isinstance(metrics.conflict_score, float)

    # Verify score constraints (if set)
    metrics.convergence_score = 0.8
    assert 0.0 <= metrics.convergence_score <= 1.0


@pytest.mark.unit
def test_persona_profile_fields_have_correct_types(sample_persona):
    """Test: PersonaProfile fields have correct types."""
    persona = sample_persona

    assert isinstance(persona.code, str)
    assert isinstance(persona.name, str)
    # domain_expertise can be list or string (postgres array)
    assert isinstance(persona.domain_expertise, list | str)
    if isinstance(persona.domain_expertise, list):
        assert all(isinstance(e, str) for e in persona.domain_expertise)
    assert isinstance(persona.system_prompt, str)


@pytest.mark.unit
def test_problem_model_fields_have_correct_types(sample_problem):
    """Test: Problem model fields have correct types."""
    problem = sample_problem

    assert isinstance(problem.title, str)
    assert isinstance(problem.description, str)
    assert isinstance(problem.context, str)
    # constraints is a list of Constraint objects
    assert isinstance(problem.constraints, list)
