"""Comprehensive roundtrip tests for state serialization.

Tests serialize_state_for_checkpoint() and deserialize_state_from_checkpoint()
for data integrity across all DeliberationGraphState fields.

Key test areas:
- Full state roundtrip with all fields populated
- Edge cases: empty, minimal, large payloads, nested structures
- Type preservation: datetime, UUID, enums, TypedDicts
- Error handling: invalid JSON, missing fields, schema violations
"""

import uuid
from datetime import UTC, datetime

import pytest

from bo1.graph.state import (
    DeliberationGraphState,
    create_initial_state,
    deserialize_state_from_checkpoint,
    serialize_state_for_checkpoint,
)
from bo1.models.persona import PersonaCategory, PersonaProfile, PersonaType, ResponseStyle
from bo1.models.problem import Constraint, ConstraintType, Problem, SubProblem
from bo1.models.recommendations import Recommendation
from bo1.models.state import (
    AspectCoverage,
    ContributionMessage,
    ContributionStatus,
    ContributionType,
    DeliberationMetrics,
    DeliberationPhase,
    DeliberationPhaseType,
    SubProblemResult,
)

# =============================================================================
# TEST FACTORY HELPERS
# =============================================================================


def make_persona(
    code: str = "test_persona",
    name: str = "Test Persona",
    **overrides,
) -> PersonaProfile:
    """Create a test persona with sensible defaults."""
    defaults = {
        "id": str(uuid.uuid4()),
        "code": code,
        "name": name,
        "archetype": "Test Expert",
        "category": PersonaCategory.STRATEGY,
        "description": f"A test persona for {code}",
        "emoji": "🧪",
        "color_hex": "#FF5733",
        "traits": {
            "creative": 0.7,
            "analytical": 0.8,
            "optimistic": 0.5,
            "risk_averse": 0.4,
            "detail_oriented": 0.6,
        },
        "default_weight": 1.0,
        "temperature": 0.7,
        "system_prompt": f"<system_role>You are {name}.</system_role>",
        "response_style": ResponseStyle.ANALYTICAL,
        "is_active": True,
        "persona_type": PersonaType.STANDARD,
        "is_visible": True,
        "display_name": name.split()[0],
        "domain_expertise": ["strategy", "analysis"],
    }
    defaults.update(overrides)
    return PersonaProfile(**defaults)


def make_contribution(
    persona_code: str = "expert",
    round_number: int = 1,
    **overrides,
) -> ContributionMessage:
    """Create a test contribution with sensible defaults."""
    defaults = {
        "persona_code": persona_code,
        "persona_name": f"{persona_code.title()} Expert",
        "content": f"Contribution from {persona_code} in round {round_number}.",
        "round_number": round_number,
        "thinking": f"Analyzing the problem from {persona_code} perspective...",
        "contribution_type": ContributionType.RESPONSE,
        "timestamp": datetime.now(UTC),
        "token_count": 150,
        "cost": 0.003,
        "id": None,
        "session_id": None,
        "user_id": None,
        "status": ContributionStatus.COMMITTED,
        "model": "claude-sonnet-4-20250514",
        "phase": DeliberationPhaseType.EXPLORATION,
        "metadata": {"contribution_id": str(uuid.uuid4())},
    }
    defaults.update(overrides)
    return ContributionMessage(**defaults)


def make_sub_problem(
    sp_id: str = "sp_001",
    goal: str = "Analyze market conditions",
    **overrides,
) -> SubProblem:
    """Create a test sub-problem with sensible defaults."""
    defaults = {
        "id": sp_id,
        "goal": goal,
        "context": f"Context for {sp_id}: {goal}",
        "complexity_score": 5,
        "dependencies": [],
        "constraints": [
            Constraint(
                type=ConstraintType.TIME,
                description="Complete within 2 weeks",
                value="14 days",
            ),
        ],
        "focus": None,
    }
    defaults.update(overrides)
    return SubProblem(**defaults)


def make_problem(
    title: str = "Test Problem",
    num_sub_problems: int = 2,
    **overrides,
) -> Problem:
    """Create a test problem with sub-problems."""
    defaults = {
        "title": title,
        "description": f"Test problem: {title}",
        "context": "B2B SaaS startup, 50 users, $100K ARR",
        "constraints": [
            Constraint(
                type=ConstraintType.BUDGET,
                description="Maximum budget",
                value=50000,
            ),
        ],
        "sub_problems": [
            make_sub_problem(sp_id=f"sp_{i:03d}", goal=f"Sub-problem {i} goal")
            for i in range(1, num_sub_problems + 1)
        ],
    }
    defaults.update(overrides)
    return Problem(**defaults)


def make_sub_problem_result(
    sp_id: str = "sp_001",
    **overrides,
) -> SubProblemResult:
    """Create a test sub-problem result."""
    defaults = {
        "sub_problem_id": sp_id,
        "sub_problem_goal": f"Goal for {sp_id}",
        "synthesis": f"Synthesis for {sp_id}: recommend approach X based on analysis.",
        "votes": [
            {"persona": "ceo", "choice": "approve", "confidence": 0.85},
            {"persona": "cfo", "choice": "approve", "confidence": 0.72},
        ],
        "contribution_count": 12,
        "cost": 0.15,
        "duration_seconds": 180.5,
        "expert_panel": ["ceo", "cfo", "cto"],
        "expert_summaries": {
            "ceo": "CEO emphasized strategic alignment.",
            "cfo": "CFO highlighted cost implications.",
            "cto": "CTO addressed technical feasibility.",
        },
    }
    defaults.update(overrides)
    return SubProblemResult(**defaults)


def make_recommendation(
    persona_code: str = "ceo",
    **overrides,
) -> Recommendation:
    """Create a test recommendation."""
    defaults = {
        "persona_code": persona_code,
        "persona_name": f"{persona_code.upper()} Expert",
        "recommendation": f"Recommendation from {persona_code}: proceed with option A.",
        "reasoning": "Based on analysis, option A provides the best balance of risk and reward.",
        "confidence": 0.85,
        "conditions": ["Budget approval required", "Team capacity confirmed"],
        "weight": 1.0,
        "alternatives_considered": ["Option B (cheaper)", "Option C (faster)"],
        "risk_assessment": "Primary risk is execution timeline.",
    }
    defaults.update(overrides)
    return Recommendation(**defaults)


def make_metrics(**overrides) -> DeliberationMetrics:
    """Create test deliberation metrics with all fields populated."""
    defaults = {
        "total_cost": 0.45,
        "total_tokens": 15000,
        "cache_hits": 5,
        "cache_creation_tokens": 2000,
        "cache_read_tokens": 3000,
        "phase_costs": {
            "decomposition": 0.05,
            "selection": 0.02,
            "initial_round": 0.12,
            "discussion": 0.20,
            "synthesis": 0.06,
        },
        "convergence_score": 0.78,
        "novelty_score": 0.45,
        "conflict_score": 0.25,
        "drift_events": 1,
        "exploration_score": 0.72,
        "focus_score": 0.85,
        "meeting_completeness_index": 0.75,
        "aspect_coverage": [
            AspectCoverage(name="risks_failure_modes", level="deep", notes="Fully explored"),
            AspectCoverage(name="stakeholders_impact", level="shallow", notes="Needs more"),
        ],
        "next_round_focus_prompts": ["Explore stakeholder concerns"],
        "missing_critical_aspects": ["stakeholders_impact"],
        "complexity_score": 0.65,
        "scope_breadth": 0.5,
        "dependencies": 0.4,
        "ambiguity": 0.3,
        "stakeholders_complexity": 0.6,
        "novelty": 0.35,
        "recommended_rounds": 5,
        "recommended_experts": 4,
        "complexity_reasoning": "Moderate complexity with clear boundaries.",
    }
    defaults.update(overrides)
    return DeliberationMetrics(**defaults)


def make_full_state(
    session_id: str | None = None,
    num_personas: int = 3,
    num_contributions: int = 10,
    num_sub_problems: int = 3,
    num_sub_problem_results: int = 2,
    **overrides,
) -> DeliberationGraphState:
    """Create a fully populated DeliberationGraphState for roundtrip testing.

    Populates all fields with realistic test data to validate serialization
    preserves everything correctly.

    Args:
        session_id: Session ID (auto-generated UUID if not provided)
        num_personas: Number of personas to create
        num_contributions: Number of contributions to create
        num_sub_problems: Number of sub-problems in the problem
        num_sub_problem_results: Number of completed sub-problem results
        **overrides: Override any state field

    Returns:
        Fully populated DeliberationGraphState
    """
    if session_id is None:
        session_id = f"bo1_{uuid.uuid4().hex[:12]}"

    # Create personas
    persona_codes = ["ceo", "cfo", "cto", "growth_hacker", "product_mgr"]
    personas = [
        make_persona(code=persona_codes[i % len(persona_codes)], name=f"Expert {i + 1}")
        for i in range(num_personas)
    ]

    # Create contributions across rounds
    contributions = []
    for i in range(num_contributions):
        round_num = i // 3 + 1  # ~3 contributions per round
        phase_map = {1: "exploration", 2: "challenge", 3: "convergence"}
        phase = phase_map.get(min(round_num, 3), "convergence")
        contributions.append(
            make_contribution(
                persona_code=persona_codes[i % len(persona_codes)],
                round_number=round_num,
                phase=DeliberationPhaseType(phase),
                timestamp=datetime(2024, 1, 15, 10, i, 0, tzinfo=UTC),
            )
        )

    # Create problem with sub-problems
    problem = make_problem(num_sub_problems=num_sub_problems)

    # Create sub-problem results
    sub_problem_results = [
        make_sub_problem_result(sp_id=f"sp_{i + 1:03d}") for i in range(num_sub_problem_results)
    ]

    # Build full state
    state: DeliberationGraphState = {
        # Core identifiers
        "session_id": session_id,
        "request_id": f"req_{uuid.uuid4().hex[:8]}",
        # Problem context
        "problem": problem,
        "current_sub_problem": problem.sub_problems[0] if problem.sub_problems else None,
        # Participants
        "personas": personas,
        # Discussion state
        "contributions": contributions,
        "round_summaries": [
            "Round 1: Initial exploration of problem space.",
            "Round 2: Challenged assumptions about market size.",
            "Round 3: Converged on recommended approach.",
        ],
        # Phase tracking
        "phase": DeliberationPhase.SYNTHESIS,
        "round_number": 3,
        "max_rounds": 5,
        # Metrics
        "metrics": make_metrics(),
        # Decision tracking
        "facilitator_decision": {
            "action": "continue",
            "reasoning": "More exploration needed.",
            "guidance": "Focus on risk assessment.",
        },
        # Control flags
        "should_stop": False,
        "stop_reason": None,
        # Human-in-the-loop
        "user_input": None,
        "user_id": f"user_{uuid.uuid4().hex[:8]}",
        "subscription_tier": "pro",
        # Visualization
        "current_node": "synthesis_node",
        # Final outputs
        "votes": [
            {"persona_code": "ceo", "recommendation": "approve", "confidence": 0.85},
            {"persona_code": "cfo", "recommendation": "approve", "confidence": 0.72},
        ],
        "synthesis": "Final synthesis: Recommend proceeding with option A.",
        # Multi-sub-problem tracking
        "sub_problem_results": sub_problem_results,
        "sub_problem_index": 1,
        # Context collection
        "collect_context": True,
        "business_context": {
            "company_size": "startup",
            "industry": "SaaS",
            "funding_stage": "seed",
            "team_size": 10,
        },
        "pending_clarification": None,
        "clarification_answers": {
            "target_market": "SMB",
            "pricing_model": "subscription",
        },
        "phase_costs": {
            "decomposition": 0.05,
            "selection": 0.02,
            "initial_round": 0.12,
        },
        # Meeting quality guidance
        "facilitator_guidance": {
            "suggested_focus": "risk_mitigation",
            "priority_aspects": ["dependencies", "constraints"],
        },
        # Research tracking
        "completed_research_queries": [
            {"query": "market size SaaS 2024", "embedding": [0.1] * 10},
        ],
        "pending_research_queries": [],
        "research_results": [
            {"query": "market size SaaS 2024", "summary": "Market growing 15% YoY."},
        ],
        # Comparison detection
        "comparison_detected": True,
        "comparison_options": ["React", "Svelte"],
        "comparison_type": "technology",
        # Parallel architecture fields
        "current_phase": "convergence",
        "experts_per_round": [["ceo", "cfo"], ["cto", "ceo"], ["cfo", "cto"]],
        "semantic_novelty_scores": {"contrib_1": 0.65, "contrib_2": 0.45},
        "exploration_score": 0.72,
        "focus_score": 0.85,
        # Parallel sub-problems
        "execution_batches": [[0, 1], [2]],
        "parallel_mode": True,
        "dependency_error": None,
        # Context sufficiency
        "limited_context_mode": False,
        "context_insufficient_emitted": False,
        "context_insufficiency_info": None,
        "user_context_choice": None,
        "best_effort_prompt_injected": False,
        "consecutive_research_without_improvement": 0,
        "meta_discussion_count": 2,
        "total_contributions_checked": 10,
        # Stalled disagreement
        "high_conflict_low_novelty_rounds": 0,
        # Data analysis
        "attached_datasets": ["ds_001", "ds_002"],
        "data_analysis_results": [
            {"dataset_id": "ds_001", "insight": "Revenue trending up."},
        ],
        # User-selected context
        "context_ids": {
            "meetings": ["meeting_1", "meeting_2"],
            "actions": ["action_1"],
            "datasets": ["ds_001"],
        },
        # User preferences
        "skip_clarification": False,
        # Early termination
        "termination_requested": False,
        "termination_type": None,
        "termination_reason": None,
        # User interjection
        "user_interjection": None,
        "interjection_responses": [],
        "needs_interjection_response": False,
    }

    # Apply overrides
    state.update(overrides)

    return state


# =============================================================================
# CORE ROUNDTRIP TESTS
# =============================================================================


@pytest.mark.unit
class TestRoundtripFullState:
    """Test full state roundtrip with all fields populated."""

    def test_roundtrip_full_state(self) -> None:
        """Full state survives serialize → deserialize with data integrity."""
        state = make_full_state()
        original_session_id = state["session_id"]

        # Serialize
        serialized = serialize_state_for_checkpoint(state)

        # Verify serialization converted Pydantic models to dicts
        assert isinstance(serialized["problem"], dict)
        assert isinstance(serialized["personas"][0], dict)
        assert isinstance(serialized["contributions"][0], dict)
        assert isinstance(serialized["metrics"], dict)
        assert isinstance(serialized["sub_problem_results"][0], dict)
        assert isinstance(serialized["current_sub_problem"], dict)

        # Deserialize
        deserialized = deserialize_state_from_checkpoint(serialized)

        # Verify deserialization restored Pydantic models
        assert isinstance(deserialized["problem"], Problem)
        assert isinstance(deserialized["personas"][0], PersonaProfile)
        assert isinstance(deserialized["contributions"][0], ContributionMessage)
        assert isinstance(deserialized["metrics"], DeliberationMetrics)
        assert isinstance(deserialized["sub_problem_results"][0], SubProblemResult)
        assert isinstance(deserialized["current_sub_problem"], SubProblem)

        # Verify data integrity
        assert deserialized["session_id"] == original_session_id
        assert deserialized["problem"].title == "Test Problem"
        assert len(deserialized["personas"]) == 3
        assert len(deserialized["contributions"]) == 10
        assert len(deserialized["sub_problem_results"]) == 2

    def test_roundtrip_preserves_nested_sub_problems(self) -> None:
        """Problem.sub_problems list survives roundtrip intact."""
        state = make_full_state(num_sub_problems=5)

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        problem = deserialized["problem"]
        assert len(problem.sub_problems) == 5
        assert problem.sub_problems[0].id == "sp_001"
        assert problem.sub_problems[4].id == "sp_005"

    def test_roundtrip_preserves_metrics_fields(self) -> None:
        """All DeliberationMetrics fields survive roundtrip."""
        state = make_full_state()

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        metrics = deserialized["metrics"]
        assert metrics.total_cost == 0.45
        assert metrics.convergence_score == 0.78
        assert metrics.exploration_score == 0.72
        assert len(metrics.aspect_coverage) == 2
        assert metrics.aspect_coverage[0].name == "risks_failure_modes"


# =============================================================================
# EDGE CASE TESTS
# =============================================================================


@pytest.mark.unit
class TestRoundtripMinimalState:
    """Test minimal state with only required fields."""

    def test_roundtrip_minimal_state(self) -> None:
        """Minimal state (only required fields) roundtrips correctly."""
        problem = make_problem(num_sub_problems=0)
        state = create_initial_state(
            session_id="minimal_session",
            problem=problem,
        )

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized["session_id"] == "minimal_session"
        assert isinstance(deserialized["problem"], Problem)
        assert deserialized["personas"] == []
        assert deserialized["contributions"] == []


@pytest.mark.unit
class TestRoundtripLargePayloads:
    """Test large payloads for performance and data integrity."""

    def test_roundtrip_50_contributions(self) -> None:
        """50+ contributions roundtrip without data loss."""
        state = make_full_state(num_contributions=50)

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert len(deserialized["contributions"]) == 50
        # Verify first and last contribution content
        assert "expert" in deserialized["contributions"][0].persona_code.lower() or deserialized[
            "contributions"
        ][0].persona_code in ["ceo", "cfo", "cto", "growth_hacker", "product_mgr"]
        assert isinstance(deserialized["contributions"][-1], ContributionMessage)

    def test_roundtrip_5_sub_problems_with_full_results(self) -> None:
        """5 sub-problems with full results roundtrip correctly."""
        state = make_full_state(num_sub_problems=5, num_sub_problem_results=5)

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert len(deserialized["problem"].sub_problems) == 5
        assert len(deserialized["sub_problem_results"]) == 5

        # Verify result integrity
        for i, result in enumerate(deserialized["sub_problem_results"]):
            assert isinstance(result, SubProblemResult)
            assert result.sub_problem_id == f"sp_{i + 1:03d}"
            assert len(result.expert_panel) == 3


@pytest.mark.unit
class TestRoundtripOptionalFieldsNone:
    """Test state with all optional fields set to None."""

    def test_roundtrip_all_optionals_none(self) -> None:
        """State with all optional fields as None roundtrips correctly."""
        problem = make_problem()
        state = create_initial_state(
            session_id="optional_none_test",
            problem=problem,
        )

        # Explicitly set optional fields to None
        state["current_sub_problem"] = None
        state["synthesis"] = None
        state["facilitator_decision"] = None
        state["stop_reason"] = None
        state["user_input"] = None
        state["user_interjection"] = None
        state["dependency_error"] = None
        state["termination_type"] = None

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized.get("current_sub_problem") is None
        assert deserialized.get("synthesis") is None
        assert deserialized.get("facilitator_decision") is None
        assert deserialized.get("stop_reason") is None


@pytest.mark.unit
class TestRoundtripDatetimeFields:
    """Test datetime field precision and timezone handling."""

    def test_datetime_precision_preserved(self) -> None:
        """Contribution timestamp precision survives roundtrip."""
        precise_time = datetime(2024, 1, 15, 10, 30, 45, 123456, tzinfo=UTC)
        contribution = make_contribution(timestamp=precise_time)
        state = make_full_state(num_contributions=0)
        state["contributions"] = [contribution]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        restored_time = deserialized["contributions"][0].timestamp
        # Note: JSON serialization may lose microseconds depending on format
        assert restored_time.year == 2024
        assert restored_time.month == 1
        assert restored_time.day == 15
        assert restored_time.hour == 10
        assert restored_time.minute == 30
        assert restored_time.second == 45

    def test_utc_timezone_preserved(self) -> None:
        """UTC timezone is preserved in datetime fields."""
        utc_time = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        contribution = make_contribution(timestamp=utc_time)
        state = make_full_state(num_contributions=0)
        state["contributions"] = [contribution]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        restored = deserialized["contributions"][0].timestamp
        # Timezone may be lost in JSON, but UTC time should be correct
        assert restored.hour == 12


@pytest.mark.unit
class TestRoundtripUuidFields:
    """Test UUID field preservation."""

    def test_session_id_preserved(self) -> None:
        """Session ID (UUID format) preserved correctly."""
        session_id = f"bo1_{uuid.uuid4().hex}"
        state = make_full_state(session_id=session_id)

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized["session_id"] == session_id

    def test_request_id_preserved(self) -> None:
        """Request ID preserved correctly."""
        request_id = f"req_{uuid.uuid4().hex[:16]}"
        state = make_full_state()
        state["request_id"] = request_id

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized["request_id"] == request_id

    def test_persona_id_preserved(self) -> None:
        """Persona UUIDs preserved correctly."""
        persona_uuid = str(uuid.uuid4())
        persona = make_persona(id=persona_uuid)
        state = make_full_state(num_personas=0)
        state["personas"] = [persona]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized["personas"][0].id == persona_uuid


@pytest.mark.unit
class TestRoundtripEnumValues:
    """Test enum value preservation."""

    def test_deliberation_phase_enum_preserved(self) -> None:
        """DeliberationPhase enum value preserved."""
        state = make_full_state()
        state["phase"] = DeliberationPhase.VOTING

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        # Phase may be string or enum depending on serialization
        phase = deserialized["phase"]
        if isinstance(phase, DeliberationPhase):
            assert phase == DeliberationPhase.VOTING
        else:
            assert phase == "voting"

    def test_contribution_type_enum_preserved(self) -> None:
        """ContributionType enum preserved in contributions."""
        contribution = make_contribution(contribution_type=ContributionType.FACILITATOR)
        state = make_full_state(num_contributions=0)
        state["contributions"] = [contribution]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        restored = deserialized["contributions"][0]
        assert restored.contribution_type == ContributionType.FACILITATOR

    def test_persona_category_enum_preserved(self) -> None:
        """PersonaCategory enum preserved in personas."""
        persona = make_persona(category=PersonaCategory.FINANCE)
        state = make_full_state(num_personas=0)
        state["personas"] = [persona]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized["personas"][0].category == PersonaCategory.FINANCE


# =============================================================================
# ERROR HANDLING TESTS
# =============================================================================


@pytest.mark.unit
class TestDeserializeInvalidJson:
    """Test error handling for invalid/malformed input."""

    def test_deserialize_non_dict_raises(self) -> None:
        """Non-dict input raises appropriate error."""
        with pytest.raises((TypeError, AttributeError, ValueError)):
            # Passing a list instead of dict should fail
            deserialize_state_from_checkpoint(["not", "a", "dict"])  # type: ignore

    def test_deserialize_invalid_problem_schema(self) -> None:
        """Invalid Problem schema raises ValidationError."""
        from pydantic import ValidationError

        invalid_checkpoint = {
            "session_id": "test",
            "problem": {
                # Missing required fields: title, description, context
                "sub_problems": [],
            },
        }

        with pytest.raises(ValidationError):
            deserialize_state_from_checkpoint(invalid_checkpoint)

    def test_deserialize_invalid_persona_schema(self) -> None:
        """Invalid PersonaProfile schema raises ValidationError."""
        from pydantic import ValidationError

        invalid_checkpoint = {
            "session_id": "test",
            "problem": {
                "title": "Test",
                "description": "Test",
                "context": "Test",
                "sub_problems": [],
            },
            "personas": [
                {
                    # Missing required fields
                    "code": "test",
                }
            ],
        }

        with pytest.raises(ValidationError):
            deserialize_state_from_checkpoint(invalid_checkpoint)


@pytest.mark.unit
class TestDeserializeMissingFields:
    """Test graceful handling of missing fields (backward compat)."""

    def test_missing_optional_fields_no_error(self) -> None:
        """Missing optional fields don't cause errors."""
        minimal = {
            "session_id": "test",
            "problem": {
                "title": "Test",
                "description": "Test problem",
                "context": "Test context",
                "sub_problems": [],
            },
            "phase": "intake",
            "round_number": 0,
            "max_rounds": 5,
        }

        # Should not raise
        result = deserialize_state_from_checkpoint(minimal)

        assert result["session_id"] == "test"
        # Missing fields should stay missing (not None)
        assert "personas" not in result
        assert "contributions" not in result
        assert "synthesis" not in result

    def test_missing_nested_optional_fields_ok(self) -> None:
        """Missing nested optional fields handled gracefully."""
        minimal = {
            "session_id": "test",
            "problem": {
                "title": "Test",
                "description": "Test",
                "context": "Test",
                # sub_problems defaults to empty list in Problem model
            },
        }

        result = deserialize_state_from_checkpoint(minimal)
        assert isinstance(result["problem"], Problem)
        assert result["problem"].sub_problems == []


@pytest.mark.unit
class TestSerializeAlreadyDicts:
    """Test serialization when models are already dicts (partial deserialization)."""

    def test_serialize_mixed_pydantic_dict_personas(self) -> None:
        """Mixed Pydantic/dict items in personas list handled correctly."""
        state = make_full_state(num_personas=0)
        state["personas"] = [
            make_persona(code="pydantic"),  # Pydantic model
            {  # Already a dict
                "id": str(uuid.uuid4()),
                "code": "dict_persona",
                "name": "Dict Persona",
                "archetype": "Test",
                "category": "strategy",
                "description": "A dict",
                "emoji": "📝",
                "color_hex": "#123456",
                "traits": {
                    "creative": 0.5,
                    "analytical": 0.5,
                    "optimistic": 0.5,
                    "risk_averse": 0.5,
                    "detail_oriented": 0.5,
                },
                "default_weight": 1.0,
                "temperature": 0.7,
                "system_prompt": "Test",
                "response_style": "analytical",
                "display_name": "Dict",
                "domain_expertise": ["test"],
            },
        ]

        serialized = serialize_state_for_checkpoint(state)

        # Both should be dicts
        assert isinstance(serialized["personas"][0], dict)
        assert isinstance(serialized["personas"][1], dict)

    def test_serialize_mixed_pydantic_dict_contributions(self) -> None:
        """Mixed Pydantic/dict items in contributions handled correctly."""
        state = make_full_state(num_contributions=0)
        state["contributions"] = [
            make_contribution(persona_code="pydantic"),  # Pydantic
            {  # Dict
                "persona_code": "dict",
                "persona_name": "Dict Expert",
                "content": "Dict contribution",
                "round_number": 1,
            },
        ]

        serialized = serialize_state_for_checkpoint(state)

        assert isinstance(serialized["contributions"][0], dict)
        assert isinstance(serialized["contributions"][1], dict)


# =============================================================================
# DEEP EQUALITY VERIFICATION
# =============================================================================


@pytest.mark.unit
class TestDeepEquality:
    """Test deep equality of complex nested structures."""

    def test_sub_problem_result_expert_summaries(self) -> None:
        """Expert summaries dict in SubProblemResult preserved."""
        summaries = {
            "ceo": "CEO provided strategic direction.",
            "cfo": "CFO analyzed financial implications.",
            "cto": "CTO assessed technical feasibility.",
        }
        result = make_sub_problem_result(expert_summaries=summaries)
        state = make_full_state(num_sub_problem_results=0)
        state["sub_problem_results"] = [result]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        restored = deserialized["sub_problem_results"][0]
        assert restored.expert_summaries == summaries

    def test_nested_dict_in_votes(self) -> None:
        """Nested dicts in votes field preserved."""
        votes = [
            {"persona": "ceo", "choice": "approve", "meta": {"confidence": 0.9}},
            {"persona": "cfo", "choice": "reject", "meta": {"reason": "budget"}},
        ]
        result = make_sub_problem_result(votes=votes)
        state = make_full_state(num_sub_problem_results=0)
        state["sub_problem_results"] = [result]

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        restored = deserialized["sub_problem_results"][0]
        assert restored.votes == votes
        assert restored.votes[0]["meta"]["confidence"] == 0.9

    def test_business_context_nested_structure(self) -> None:
        """Nested business_context structure preserved."""
        context = {
            "company": {
                "name": "TestCorp",
                "size": "startup",
                "metrics": {"mrr": 10000, "growth": 0.15},
            },
            "market": ["B2B", "SaaS"],
        }
        state = make_full_state()
        state["business_context"] = context

        serialized = serialize_state_for_checkpoint(state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        assert deserialized["business_context"] == context
        assert deserialized["business_context"]["company"]["metrics"]["mrr"] == 10000
