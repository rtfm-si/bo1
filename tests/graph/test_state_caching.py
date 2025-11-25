"""Tests for state conversion caching."""

import pytest

from bo1.graph.state import (
    clear_state_conversion_cache,
    create_initial_state,
    get_cache_stats,
    graph_state_to_deliberation_state,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, DeliberationPhase


@pytest.fixture
def sample_problem() -> Problem:
    """Create a sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Should we invest in feature X?",
        context="SaaS startup with $500K budget",
        sub_problems=[],
    )


@pytest.fixture
def sample_personas() -> list[PersonaProfile]:
    """Create sample personas for testing."""
    from bo1.data import get_persona_by_code

    growth_hacker_data = get_persona_by_code("growth_hacker")
    finance_strategist_data = get_persona_by_code("finance_strategist")

    if not growth_hacker_data or not finance_strategist_data:
        pytest.skip("Required personas not found in catalog")

    return [
        PersonaProfile(**growth_hacker_data),
        PersonaProfile(**finance_strategist_data),
    ]


@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    clear_state_conversion_cache()
    yield
    clear_state_conversion_cache()


def test_state_conversion_caching_same_state(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test that state conversion caches correctly for same state object."""
    state = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )

    # First call should be a cache miss
    result1 = graph_state_to_deliberation_state(state)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    # Second call with same state should return cached version
    result2 = graph_state_to_deliberation_state(state)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 1
    assert stats["hit_rate"] == 0.5

    # Should be identical object (cached)
    assert result1 is result2

    # Third call - verify cache still works
    result3 = graph_state_to_deliberation_state(state)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 2
    assert stats["hit_rate"] == 2 / 3

    assert result1 is result3


def test_state_conversion_cache_invalidation(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test that cache invalidates when state changes."""
    state1 = create_initial_state(
        session_id="test-123",
        problem=sample_problem,
        personas=sample_personas,
        max_rounds=6,
    )

    # First conversion
    result1 = graph_state_to_deliberation_state(state1)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0

    # Modify state (simulate LangGraph node update - creates new dict)
    state2 = {**state1, "round_number": state1["round_number"] + 1}

    # Second conversion should be cache miss (different object identity)
    result2 = graph_state_to_deliberation_state(state2)
    stats = get_cache_stats()
    assert stats["misses"] == 2
    assert stats["hits"] == 0

    # Should NOT be same object (cache invalidated)
    assert result1 is not result2
    assert result2.current_round == result1.current_round + 1


def test_state_conversion_with_contributions(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test caching with contributions in state."""
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
    state["contributions"] = [contrib1]
    state["round_number"] = 1

    # First call
    result1 = graph_state_to_deliberation_state(state)
    assert len(result1.contributions) == 1

    # Second call (cached)
    result2 = graph_state_to_deliberation_state(state)
    assert result1 is result2


def test_clear_cache() -> None:
    """Test cache clearing functionality."""
    from bo1.models.problem import Problem

    problem = Problem(
        title="Test",
        description="Test problem",
        context="",
        sub_problems=[],
    )

    state = create_initial_state(session_id="test", problem=problem)

    # Populate cache
    graph_state_to_deliberation_state(state)
    stats = get_cache_stats()
    assert stats["misses"] == 1

    # Second call (cache hit)
    graph_state_to_deliberation_state(state)
    stats = get_cache_stats()
    assert stats["hits"] == 1

    # Clear cache
    clear_state_conversion_cache()
    stats = get_cache_stats()
    assert stats["hits"] == 0
    assert stats["misses"] == 0
    assert stats["total"] == 0

    # Next call should be cache miss
    graph_state_to_deliberation_state(state)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0


def test_cache_stats_calculation() -> None:
    """Test cache statistics calculation."""
    from bo1.models.problem import Problem

    problem = Problem(
        title="Test",
        description="Test problem",
        context="",
        sub_problems=[],
    )

    state1 = create_initial_state(session_id="test1", problem=problem)
    state2 = create_initial_state(session_id="test2", problem=problem)

    # Initial stats
    stats = get_cache_stats()
    assert stats["hit_rate"] == 0.0

    # 1 miss
    graph_state_to_deliberation_state(state1)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 0
    assert stats["total"] == 1
    assert stats["hit_rate"] == 0.0

    # 1 hit
    graph_state_to_deliberation_state(state1)
    stats = get_cache_stats()
    assert stats["misses"] == 1
    assert stats["hits"] == 1
    assert stats["total"] == 2
    assert stats["hit_rate"] == 0.5

    # 1 miss (different state)
    graph_state_to_deliberation_state(state2)
    stats = get_cache_stats()
    assert stats["misses"] == 2
    assert stats["hits"] == 1
    assert stats["total"] == 3
    assert stats["hit_rate"] == 1 / 3

    # 1 hit (state2)
    graph_state_to_deliberation_state(state2)
    stats = get_cache_stats()
    assert stats["misses"] == 2
    assert stats["hits"] == 2
    assert stats["total"] == 4
    assert stats["hit_rate"] == 0.5


def test_cache_with_phase_changes(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test caching across different deliberation phases."""
    state = create_initial_state(
        session_id="test-phases",
        problem=sample_problem,
        personas=sample_personas,
    )

    # Phase 1: INTAKE
    result1 = graph_state_to_deliberation_state(state)
    assert result1.phase == DeliberationPhase.INTAKE
    stats = get_cache_stats()
    assert stats["misses"] == 1

    # Cache hit
    result2 = graph_state_to_deliberation_state(state)
    assert result1 is result2
    stats = get_cache_stats()
    assert stats["hits"] == 1

    # Phase 2: DISCUSSION (new state object)
    state2 = {**state, "phase": DeliberationPhase.DISCUSSION}
    result3 = graph_state_to_deliberation_state(state2)
    assert result3.phase == DeliberationPhase.DISCUSSION
    stats = get_cache_stats()
    assert stats["misses"] == 2  # Cache invalidated

    # Cache hit for state2
    result4 = graph_state_to_deliberation_state(state2)
    assert result3 is result4
    stats = get_cache_stats()
    assert stats["hits"] == 2


def test_cache_correctness_after_state_mutation(
    sample_problem: Problem, sample_personas: list[PersonaProfile]
) -> None:
    """Test that cache doesn't return stale data after state mutation."""
    state = create_initial_state(
        session_id="test-mutation",
        problem=sample_problem,
        personas=sample_personas,
    )

    # Initial conversion
    result1 = graph_state_to_deliberation_state(state)
    assert result1.current_round == 0

    # Simulate LangGraph state update (creates new dict)
    state_updated = {**state, "round_number": 5}

    # Should get new conversion (cache miss)
    result2 = graph_state_to_deliberation_state(state_updated)
    assert result2.current_round == 5
    assert result1 is not result2

    # Verify cache stats
    stats = get_cache_stats()
    assert stats["misses"] == 2
    assert stats["hits"] == 0
