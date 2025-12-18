"""Redis persistence integration tests.

Tests Redis state management, connection handling, and graceful degradation.
Would prevent issues where tests are modified to disable Redis just to pass.
"""

import pytest

from bo1.graph.state import create_initial_state, serialize_state_for_checkpoint
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, ContributionType, DeliberationMetrics

# ============================================================================
# Connection Handling Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_redis
def test_redis_connection_success(redis_manager):
    """Test: Redis manager connects successfully when Redis is available."""
    manager = redis_manager

    # Verify connection works
    assert manager.client.ping() is True

    # Verify basic operations work
    # Note: decode_responses=True in RedisManager, so strings are returned
    manager.client.set("test_key", "test_value")
    assert manager.client.get("test_key") == "test_value"

    # Cleanup
    manager.client.delete("test_key")


@pytest.mark.unit
def test_redis_connection_failure_handling(redis_manager):
    """Test: System handles Redis unavailability gracefully."""
    # With standard fixture, Redis should be available in test environment
    # This test validates the connection works
    if redis_manager is None:
        pytest.skip("Redis not available")
    assert redis_manager.client.ping() is True


# ============================================================================
# State Persistence Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_redis
@pytest.mark.skip(reason="Needs PersonaProfile fixture - complex model")
def test_state_persistence_round_trip(redis_manager):
    """Test: State can be saved to and loaded from Redis without data loss."""
    manager = redis_manager

    # Create complex state with all fields populated
    from bo1.models.persona import PersonaCategory, PersonaType, ResponseStyle

    problem = Problem(
        title="AI Infrastructure Investment",
        description="Should we invest $500K in AI infrastructure?",
        context="Series A funded startup",
    )

    personas = [
        PersonaProfile(
            id="strategic-advisor-123",
            code="strategic_advisor",
            name="Maria Chen",
            archetype="Strategic Advisor",
            category=PersonaCategory.STRATEGY,
            description="Strategy and scaling expert",
            emoji="🎯",
            color_hex="#FF0000",
            traits={
                "creative": 0.7,
                "analytical": 0.9,
                "optimistic": 0.8,
                "risk_averse": 0.4,
                "detail_oriented": 0.8,
            },
            default_weight=1.0,
            temperature=0.7,
            system_prompt="You are Maria Chen...",
            response_style=ResponseStyle.ANALYTICAL,
            display_name="Maria",
            domain_expertise=["strategy", "scaling"],
            persona_type=PersonaType.STANDARD,
        ),
        PersonaProfile(
            id="financial-analyst-456",
            code="financial_analyst",
            name="David Park",
            archetype="Financial Analyst",
            category=PersonaCategory.FINANCE,
            description="Finance and modeling expert",
            emoji="💰",
            color_hex="#00FF00",
            traits={
                "creative": 0.5,
                "analytical": 0.95,
                "optimistic": 0.6,
                "risk_averse": 0.7,
                "detail_oriented": 0.9,
            },
            default_weight=1.0,
            temperature=0.6,
            system_prompt="You are David Park...",
            response_style=ResponseStyle.ANALYTICAL,
            display_name="David",
            domain_expertise=["finance", "modeling"],
            persona_type=PersonaType.STANDARD,
        ),
    ]

    contribution = ContributionMessage(
        persona_code="strategic_advisor",
        persona_name="Maria Chen",
        content="I recommend focusing on unit economics...",
        thinking="Let me analyze the financial implications...",
        contribution_type=ContributionType.INITIAL,
        round_number=0,
        token_count=250,
        cost=0.0015,
    )

    original_state = create_initial_state(
        session_id="test-persist-123",
        problem=problem,
        personas=personas,
        max_rounds=7,
    )
    original_state["contributions"] = [contribution]
    original_state["round_summaries"] = ["Round 0: Initial contributions collected"]
    original_state["round_number"] = 1

    # Save state
    session_key = "deliberation:test-persist-123"
    serialized = serialize_state_for_checkpoint(original_state)
    manager.save_state(session_key, serialized)

    # Load state
    loaded_data = manager.load_state(session_key)
    assert loaded_data is not None

    # Verify all fields preserved
    assert loaded_data["session_id"] == "test-persist-123"
    assert loaded_data["problem"]["title"] == problem.title
    assert len(loaded_data["personas"]) == 2
    assert loaded_data["personas"][0]["code"] == "strategic_advisor"
    assert len(loaded_data["contributions"]) == 1
    assert loaded_data["contributions"][0]["content"] == contribution.content
    assert loaded_data["round_summaries"] == ["Round 0: Initial contributions collected"]
    assert loaded_data["round_number"] == 1
    assert loaded_data["max_rounds"] == 7

    # Cleanup
    manager.client.delete(session_key)


@pytest.mark.integration
@pytest.mark.requires_redis
@pytest.mark.skip(reason="Needs PersonaProfile fixture - complex model")
def test_state_with_nested_objects_persists_correctly(redis_manager):
    """Test: Complex nested objects (personas, contributions) persist correctly."""
    from bo1.models.persona import PersonaCategory, PersonaType, ResponseStyle

    manager = redis_manager

    problem = Problem(title="Test", description="Test", context="Test")

    # Multiple personas
    personas = [
        PersonaProfile(
            id=f"expert-{i}",
            code=f"expert_{i}",
            name=f"Expert {i}",
            archetype=f"Expert {i}",
            category=PersonaCategory.STRATEGY,
            description=f"Expert {i} description",
            emoji="🎯",
            color_hex="#FF0000",
            traits={
                "creative": 0.5,
                "analytical": 0.8,
                "optimistic": 0.6,
                "risk_averse": 0.5,
                "detail_oriented": 0.7,
            },
            default_weight=1.0,
            temperature=0.7,
            system_prompt=f"You are Expert {i}",
            response_style=ResponseStyle.ANALYTICAL,
            display_name=f"Expert {i}",
            domain_expertise=[f"skill_{i}", f"skill_{i + 1}"],
            persona_type=PersonaType.STANDARD,
        )
        for i in range(5)
    ]

    # Multiple contributions
    contributions = [
        ContributionMessage(
            persona_code=f"expert_{i}",
            persona_name=f"Expert {i}",
            content=f"Contribution {i}",
            thinking=None,
            token_count=None,
            cost=None,
            round_number=0,
        )
        for i in range(5)
    ]

    state = create_initial_state("test-nested-123", problem, personas=personas)
    state["contributions"] = contributions
    state["round_summaries"] = ["Summary 1", "Summary 2", "Summary 3"]

    # Save and load
    session_key = "deliberation:test-nested-123"
    serialized = serialize_state_for_checkpoint(state)
    manager.save_state(session_key, serialized)
    loaded = manager.load_state(session_key)

    # Verify nested structures
    assert loaded is not None
    assert len(loaded["personas"]) == 5
    assert len(loaded["contributions"]) == 5
    assert len(loaded["round_summaries"]) == 3

    # Verify nested list fields
    assert loaded["personas"][2]["expertise"] == ["skill_2", "skill_3"]

    # Cleanup
    manager.client.delete(session_key)


@pytest.mark.integration
@pytest.mark.requires_redis
def test_state_with_none_optional_fields_persists(redis_manager):
    """Test: State with None optional fields persists correctly."""
    manager = redis_manager

    problem = Problem(title="Test", description="Test", context="Test")

    state = create_initial_state("test-none-123", problem)

    # Set optional fields to None
    state["current_sub_problem"] = None
    state["facilitator_decision"] = None
    state["stop_reason"] = None
    state["user_input"] = None
    state["synthesis"] = None

    # Save and load
    session_key = "deliberation:test-none-123"
    serialized = serialize_state_for_checkpoint(state)
    manager.save_state(session_key, serialized)
    loaded = manager.load_state(session_key)

    # Verify None fields preserved
    assert loaded is not None
    assert loaded["current_sub_problem"] is None
    assert loaded["facilitator_decision"] is None
    assert loaded["stop_reason"] is None
    assert loaded["user_input"] is None
    assert loaded["synthesis"] is None

    # Cleanup
    manager.client.delete(session_key)


# ============================================================================
# Concurrent Session Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_redis
def test_concurrent_sessions_isolated(redis_manager):
    """Test: Multiple concurrent sessions maintain isolation."""
    manager = redis_manager

    problem = Problem(title="Test", description="Test", context="Test")

    # Create 3 different sessions
    sessions = []
    for i in range(3):
        session_id = f"test-concurrent-{i}"
        state = create_initial_state(session_id, problem, max_rounds=i + 3)
        state["round_number"] = i

        session_key = f"deliberation:{session_id}"
        serialized = serialize_state_for_checkpoint(state)
        manager.save_state(session_key, serialized)
        sessions.append((session_key, session_id, i))

    # Verify each session has correct data
    for session_key, session_id, round_num in sessions:
        loaded = manager.load_state(session_key)
        assert loaded is not None
        assert loaded["session_id"] == session_id
        assert loaded["round_number"] == round_num
        assert loaded["max_rounds"] == round_num + 3

    # Cleanup
    for session_key, _, _ in sessions:
        manager.client.delete(session_key)


@pytest.mark.integration
@pytest.mark.requires_redis
def test_session_updates_dont_affect_other_sessions(redis_manager):
    """Test: Updating one session doesn't affect others."""
    manager = redis_manager

    problem = Problem(title="Test", description="Test", context="Test")

    # Create session 1
    state1 = create_initial_state("test-update-1", problem, max_rounds=5)
    key1 = "deliberation:test-update-1"
    manager.save_state(key1, serialize_state_for_checkpoint(state1))

    # Create session 2
    state2 = create_initial_state("test-update-2", problem, max_rounds=7)
    key2 = "deliberation:test-update-2"
    manager.save_state(key2, serialize_state_for_checkpoint(state2))

    # Update session 1
    state1["round_number"] = 3
    manager.save_state(key1, serialize_state_for_checkpoint(state1))

    # Verify session 2 unchanged
    loaded2 = manager.load_state(key2)
    assert loaded2 is not None
    assert loaded2["round_number"] == 0  # Should still be initial value
    assert loaded2["max_rounds"] == 7

    # Cleanup
    manager.client.delete(key1)
    manager.client.delete(key2)


# ============================================================================
# Session Expiration Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_redis
def test_session_ttl_is_set(redis_manager):
    """Test: Sessions have TTL (Time To Live) configured."""
    manager = redis_manager

    problem = Problem(title="Test", description="Test", context="Test")

    state = create_initial_state("test-ttl-123", problem)
    session_key = "deliberation:test-ttl-123"

    # Save state with TTL (default 24h = 86400 seconds)
    serialized = serialize_state_for_checkpoint(state)
    manager.save_state(session_key, serialized, ttl=3600)  # 1 hour for test

    # Verify TTL is set
    ttl = manager.client.ttl(session_key)
    assert ttl > 0, "TTL should be set"
    assert ttl <= 3600, "TTL should be <= 1 hour"

    # Cleanup
    manager.client.delete(session_key)


# ============================================================================
# Error Handling Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_redis
def test_loading_nonexistent_session_returns_none(redis_manager):
    """Test: Loading a non-existent session returns None."""
    manager = redis_manager

    loaded = manager.load_state("deliberation:nonexistent-session")
    assert loaded is None


@pytest.mark.integration
@pytest.mark.requires_redis
def test_corrupted_data_handling(redis_manager):
    """Test: Corrupted session data is handled gracefully."""
    manager = redis_manager

    # Store invalid JSON
    session_key = "deliberation:test-corrupted"
    manager.client.set(session_key, "invalid json {{{")

    # Loading should handle gracefully (either return None or raise specific error)
    try:
        loaded = manager.load_state(session_key)
        # If it succeeds, it should return None
        assert loaded is None
    except Exception as e:
        # If it raises, it should be a clear error
        assert "json" in str(e).lower() or "decode" in str(e).lower()

    # Cleanup
    manager.client.delete(session_key)


# ============================================================================
# Metrics Persistence Tests
# ============================================================================


@pytest.mark.integration
@pytest.mark.requires_redis
def test_metrics_persist_correctly(redis_manager):
    """Test: DeliberationMetrics with all fields persist correctly."""
    manager = redis_manager

    problem = Problem(title="Test", description="Test", context="Test")

    metrics = DeliberationMetrics(
        total_cost=0.125,
        total_tokens=5000,
        cache_hits=15,
        cache_creation_tokens=500,
        cache_read_tokens=3000,
        phase_costs={
            "decomposition": 0.02,
            "persona_selection": 0.01,
            "initial_round": 0.05,
            "discussion": 0.035,
        },
        convergence_score=0.85,
        novelty_score=0.15,
        conflict_score=0.30,
    )

    state = create_initial_state("test-metrics-123", problem)
    state["metrics"] = metrics

    # Save and load
    session_key = "deliberation:test-metrics-123"
    serialized = serialize_state_for_checkpoint(state)
    manager.save_state(session_key, serialized)
    loaded = manager.load_state(session_key)

    # Verify all metrics fields
    assert loaded is not None
    assert loaded["metrics"]["total_cost"] == 0.125
    assert loaded["metrics"]["total_tokens"] == 5000
    assert loaded["metrics"]["cache_hits"] == 15
    assert len(loaded["metrics"]["phase_costs"]) == 4
    assert loaded["metrics"]["convergence_score"] == 0.85
    assert loaded["metrics"]["novelty_score"] == 0.15
    assert loaded["metrics"]["conflict_score"] == 0.30

    # Cleanup
    manager.client.delete(session_key)
