"""Tests for DeliberationGraphState nested TypedDicts and accessor helpers.

Validates:
1. Nested TypedDict definitions are correct
2. Accessor helpers extract fields properly
3. Serialization/deserialization round-trip preserves all 55+ fields
4. Backward compatibility with flat structure
"""

import pytest

from bo1.graph.state import (
    ComparisonState,
    ContextState,
    ControlState,
    DataState,
    DiscussionState,
    MetricsState,
    ParallelState,
    ParticipantState,
    PhaseState,
    ProblemState,
    ResearchState,
    create_initial_state,
    deserialize_state_from_checkpoint,
    get_comparison_state,
    get_context_state,
    get_control_state,
    get_data_state,
    get_discussion_state,
    get_metrics_state,
    get_parallel_state,
    get_participant_state,
    get_phase_state,
    get_problem_state,
    get_research_state,
    serialize_state_for_checkpoint,
    state_to_dict,
)
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import ContributionMessage, DeliberationMetrics, DeliberationPhase


@pytest.fixture
def sample_problem():
    """Create a sample problem for testing."""
    return Problem(
        title="Test Problem",
        description="Test problem description",
        context="Test business context",
        sub_problems=[
            SubProblem(
                id="sp1",
                goal="First sub-problem goal",
                context="Context for sub-problem 1",
                complexity_score=3,
                dependencies=[],
            ),
            SubProblem(
                id="sp2",
                goal="Second sub-problem goal",
                context="Context for sub-problem 2",
                complexity_score=5,
                dependencies=["sp1"],
            ),
        ],
    )


@pytest.fixture
def sample_persona():
    """Create a sample persona for testing."""
    return PersonaProfile(
        id="test-persona-123",
        code="test_expert",
        name="Test Expert",
        archetype="Quality Specialist",
        category="ops",
        description="An expert in testing and quality assurance",
        emoji="🔍",
        color_hex="#3B82F6",
        traits={"analytical": 0.9, "critical": 0.8},
        default_weight=1.0,
        temperature=0.7,
        system_prompt="You are a test expert.",
        response_style="analytical",
        display_name="Test Expert",
        domain_expertise=["Testing", "Quality"],
    )


@pytest.fixture
def sample_contribution():
    """Create a sample contribution for testing."""
    return ContributionMessage(
        persona_name="Test Expert",
        persona_code="test_expert",
        round_number=1,
        content="Test contribution content",
        timestamp="2025-01-01T00:00:00Z",
    )


@pytest.fixture
def full_state(sample_problem, sample_persona, sample_contribution):
    """Create a fully populated state for testing."""
    state = create_initial_state(
        session_id="test-session-123",
        problem=sample_problem,
        personas=[sample_persona],
        max_rounds=5,
        user_id="user-456",
        collect_context=True,
        skip_clarification=False,
        context_ids={"meetings": ["m1"], "actions": ["a1"], "datasets": []},
        subscription_tier="pro",
    )
    # Add additional fields that aren't set by create_initial_state
    state["contributions"] = [sample_contribution]
    state["round_summaries"] = ["Round 1 summary"]
    state["votes"] = [{"persona": "Expert1", "recommendation": "A"}]
    state["synthesis"] = "Final synthesis text"
    state["business_context"] = {"industry": "tech"}
    state["comparison_detected"] = True
    state["comparison_options"] = ["Option A", "Option B"]
    state["comparison_type"] = "technology"
    state["attached_datasets"] = ["ds-1", "ds-2"]
    state["data_analysis_results"] = [{"query": "test", "result": "data"}]
    return state


class TestNestedTypedDictDefinitions:
    """Test that nested TypedDict classes are properly defined."""

    def test_problem_state_fields(self):
        """ProblemState has correct field types."""
        ps = ProblemState(
            problem=None,  # type: ignore
            current_sub_problem=None,
            sub_problem_results=[],
            sub_problem_index=0,
        )
        assert "problem" in ps
        assert "sub_problem_index" in ps

    def test_phase_state_fields(self):
        """PhaseState has correct field types."""
        ps = PhaseState(
            phase=DeliberationPhase.INTAKE,
            current_phase="exploration",
            round_number=1,
            max_rounds=6,
            current_node="decompose",
        )
        assert ps["round_number"] == 1
        assert ps["max_rounds"] == 6

    def test_participant_state_fields(self):
        """ParticipantState has correct field types."""
        ps = ParticipantState(
            personas=[],
            experts_per_round=[["Expert1"], ["Expert2"]],
        )
        assert ps["experts_per_round"] == [["Expert1"], ["Expert2"]]

    def test_discussion_state_fields(self):
        """DiscussionState has correct field types."""
        ds = DiscussionState(
            contributions=[],
            round_summaries=["Summary 1"],
            votes=[{"persona": "Test", "vote": "A"}],
            synthesis="Final answer",
        )
        assert ds["synthesis"] == "Final answer"

    def test_research_state_fields(self):
        """ResearchState has correct field types."""
        rs = ResearchState(
            completed_research_queries=[{"query": "test", "embedding": [0.1, 0.2]}],
            pending_research_queries=[],
            research_results=[{"source": "web", "content": "data"}],
        )
        assert len(rs["completed_research_queries"]) == 1

    def test_comparison_state_fields(self):
        """ComparisonState has correct field types."""
        cs = ComparisonState(
            comparison_detected=True,
            comparison_options=["React", "Svelte"],
            comparison_type="technology",
        )
        assert cs["comparison_detected"] is True
        assert cs["comparison_options"] == ["React", "Svelte"]

    def test_context_state_fields(self):
        """ContextState has correct field types."""
        ctx = ContextState(
            collect_context=True,
            business_context={"industry": "tech"},
            pending_clarification=None,
            clarification_answers={"q1": "a1"},
            context_ids={"meetings": ["m1"]},
            context_insufficient_emitted=False,
            context_insufficiency_info=None,
            user_context_choice="continue",
            limited_context_mode=False,
            best_effort_prompt_injected=False,
        )
        assert ctx["user_context_choice"] == "continue"

    def test_control_state_fields(self):
        """ControlState has correct field types."""
        ctrl = ControlState(
            should_stop=False,
            stop_reason=None,
            termination_requested=True,
            termination_type="user_cancelled",
            termination_reason="User ended meeting",
            skip_clarification=True,
        )
        assert ctrl["termination_requested"] is True

    def test_metrics_state_fields(self):
        """MetricsState has correct field types."""
        ms = MetricsState(
            metrics=DeliberationMetrics(),
            phase_costs={"exploration": 0.5},
            semantic_novelty_scores={"c1": 0.8},
            exploration_score=0.7,
            focus_score=0.9,
            consecutive_research_without_improvement=2,
            meta_discussion_count=1,
            total_contributions_checked=10,
            high_conflict_low_novelty_rounds=0,
        )
        assert ms["exploration_score"] == 0.7

    def test_parallel_state_fields(self):
        """ParallelState has correct field types."""
        ps = ParallelState(
            execution_batches=[[0], [1, 2]],
            parallel_mode=True,
            dependency_error=None,
        )
        assert ps["parallel_mode"] is True

    def test_data_state_fields(self):
        """DataState has correct field types."""
        ds = DataState(
            attached_datasets=["ds-1", "ds-2"],
            data_analysis_results=[{"query": "q1", "result": "r1"}],
        )
        assert len(ds["attached_datasets"]) == 2


class TestAccessorHelpers:
    """Test accessor helper functions extract fields correctly."""

    def test_get_problem_state(self, full_state):
        """get_problem_state extracts problem fields."""
        ps = get_problem_state(full_state)
        assert ps["problem"] is not None
        assert ps["sub_problem_index"] == 0
        assert ps["sub_problem_results"] == []

    def test_get_phase_state(self, full_state):
        """get_phase_state extracts phase fields."""
        ps = get_phase_state(full_state)
        assert ps["phase"] == DeliberationPhase.INTAKE
        assert ps["round_number"] == 0
        assert ps["max_rounds"] == 5
        assert ps["current_node"] == "start"

    def test_get_participant_state(self, full_state):
        """get_participant_state extracts participant fields."""
        ps = get_participant_state(full_state)
        assert len(ps["personas"]) == 1
        assert ps["experts_per_round"] == []

    def test_get_discussion_state(self, full_state):
        """get_discussion_state extracts discussion fields."""
        ds = get_discussion_state(full_state)
        assert len(ds["contributions"]) == 1
        assert ds["round_summaries"] == ["Round 1 summary"]
        assert ds["synthesis"] == "Final synthesis text"

    def test_get_research_state(self, full_state):
        """get_research_state extracts research fields."""
        rs = get_research_state(full_state)
        assert rs["completed_research_queries"] == []
        assert rs["pending_research_queries"] == []

    def test_get_comparison_state(self, full_state):
        """get_comparison_state extracts comparison fields."""
        cs = get_comparison_state(full_state)
        assert cs["comparison_detected"] is True
        assert cs["comparison_options"] == ["Option A", "Option B"]
        assert cs["comparison_type"] == "technology"

    def test_get_context_state(self, full_state):
        """get_context_state extracts context fields."""
        ctx = get_context_state(full_state)
        assert ctx["collect_context"] is True
        assert ctx["business_context"] == {"industry": "tech"}
        assert ctx["context_ids"] == {"meetings": ["m1"], "actions": ["a1"], "datasets": []}

    def test_get_control_state(self, full_state):
        """get_control_state extracts control fields."""
        ctrl = get_control_state(full_state)
        assert ctrl["should_stop"] is False
        assert ctrl["termination_requested"] is False
        assert ctrl["skip_clarification"] is False

    def test_get_metrics_state(self, full_state):
        """get_metrics_state extracts metrics fields."""
        ms = get_metrics_state(full_state)
        assert ms["metrics"] is not None
        assert ms["phase_costs"] == {}
        assert ms["exploration_score"] == 0.0

    def test_get_parallel_state(self, full_state):
        """get_parallel_state extracts parallel fields."""
        ps = get_parallel_state(full_state)
        assert ps["execution_batches"] == []
        assert ps["parallel_mode"] is False

    def test_get_data_state(self, full_state):
        """get_data_state extracts data fields."""
        ds = get_data_state(full_state)
        assert ds["attached_datasets"] == ["ds-1", "ds-2"]
        assert len(ds["data_analysis_results"]) == 1


class TestSerializationRoundTrip:
    """Test serialization/deserialization preserves all fields."""

    def test_serialize_deserialize_roundtrip(self, full_state):
        """All fields preserved through serialize/deserialize cycle."""
        serialized = serialize_state_for_checkpoint(full_state)
        deserialized = deserialize_state_from_checkpoint(serialized)

        # Core fields
        assert deserialized["session_id"] == full_state["session_id"]
        assert deserialized["user_id"] == full_state["user_id"]
        assert deserialized["subscription_tier"] == full_state["subscription_tier"]

        # Problem fields
        assert deserialized["problem"].title == full_state["problem"].title
        assert len(deserialized["problem"].sub_problems) == 2

        # Phase fields
        assert deserialized["phase"] == full_state["phase"]
        assert deserialized["round_number"] == full_state["round_number"]
        assert deserialized["max_rounds"] == full_state["max_rounds"]

        # Participant fields
        assert len(deserialized["personas"]) == 1
        assert deserialized["personas"][0].name == "Test Expert"

        # Discussion fields
        assert len(deserialized["contributions"]) == 1
        assert deserialized["contributions"][0].content == "Test contribution content"
        assert deserialized["synthesis"] == "Final synthesis text"

        # Context fields
        assert deserialized["business_context"] == {"industry": "tech"}
        assert deserialized["context_ids"] == {
            "meetings": ["m1"],
            "actions": ["a1"],
            "datasets": [],
        }

        # Data fields
        assert deserialized["attached_datasets"] == ["ds-1", "ds-2"]

    def test_state_to_dict_matches_serialize(self, full_state):
        """state_to_dict produces same structure as serialize_state_for_checkpoint."""
        dict_result = state_to_dict(full_state)
        serialized = serialize_state_for_checkpoint(full_state)

        # Both should have problem as dict
        assert isinstance(dict_result["problem"], dict)
        assert isinstance(serialized["problem"], dict)

        # Both should have same keys
        assert set(dict_result.keys()) == set(serialized.keys())

    def test_serialize_empty_lists_preserved(self, sample_problem):
        """Empty lists are preserved, not converted to None."""
        state = create_initial_state(
            session_id="test",
            problem=sample_problem,
        )
        serialized = serialize_state_for_checkpoint(state)

        assert serialized["contributions"] == []
        assert serialized["round_summaries"] == []
        assert serialized["completed_research_queries"] == []

    def test_serialize_none_values_preserved(self, sample_problem):
        """None values are preserved, not omitted."""
        state = create_initial_state(
            session_id="test",
            problem=sample_problem,
        )
        serialized = serialize_state_for_checkpoint(state)

        assert serialized["current_sub_problem"] is None
        assert serialized["synthesis"] is None
        assert serialized["stop_reason"] is None


class TestFieldCount:
    """Test that all 55+ fields are accounted for."""

    def test_all_fields_in_nested_typeddicts(self, full_state):
        """All state fields are covered by nested TypedDicts."""
        # Get all fields from accessor helpers
        all_accessor_fields = set()

        ps = get_problem_state(full_state)
        all_accessor_fields.update(ps.keys())

        phs = get_phase_state(full_state)
        all_accessor_fields.update(phs.keys())

        parts = get_participant_state(full_state)
        all_accessor_fields.update(parts.keys())

        ds = get_discussion_state(full_state)
        all_accessor_fields.update(ds.keys())

        rs = get_research_state(full_state)
        all_accessor_fields.update(rs.keys())

        cs = get_comparison_state(full_state)
        all_accessor_fields.update(cs.keys())

        ctx = get_context_state(full_state)
        all_accessor_fields.update(ctx.keys())

        ctrl = get_control_state(full_state)
        all_accessor_fields.update(ctrl.keys())

        ms = get_metrics_state(full_state)
        all_accessor_fields.update(ms.keys())

        pars = get_parallel_state(full_state)
        all_accessor_fields.update(pars.keys())

        data = get_data_state(full_state)
        all_accessor_fields.update(data.keys())

        # Core fields not in nested dicts
        core_fields = {
            "session_id",
            "user_id",
            "subscription_tier",
            "user_input",
            "facilitator_decision",
            "facilitator_guidance",
        }

        # Combine all fields
        all_covered_fields = all_accessor_fields | core_fields

        # Get actual state fields
        state_fields = set(full_state.keys())

        # Check coverage
        missing_fields = state_fields - all_covered_fields
        assert not missing_fields, f"Fields not covered by accessors: {missing_fields}"

    def test_field_count_minimum(self, sample_problem):
        """State has at least 50 fields."""
        state = create_initial_state(
            session_id="test",
            problem=sample_problem,
        )
        assert len(state) >= 50, f"Expected 50+ fields, got {len(state)}"


class TestBackwardCompatibility:
    """Test backward compatibility with flat structure."""

    def test_direct_field_access_still_works(self, full_state):
        """Direct field access (flat structure) still works."""
        # These should all work without using accessor helpers
        assert full_state["session_id"] == "test-session-123"
        assert full_state["round_number"] == 0
        assert full_state["should_stop"] is False
        assert full_state["business_context"] == {"industry": "tech"}

    def test_state_get_with_defaults(self, full_state):
        """state.get() with defaults works for optional fields."""
        assert full_state.get("nonexistent_field", "default") == "default"
        assert full_state.get("synthesis") == "Final synthesis text"
        assert full_state.get("stop_reason") is None

    def test_old_checkpoint_format_loads(self, sample_problem, sample_persona):
        """Old checkpoint format (flat dict) still loads correctly."""
        # Simulate old checkpoint format
        old_checkpoint = {
            "session_id": "old-session",
            "problem": sample_problem.model_dump(),
            "personas": [sample_persona.model_dump()],
            "contributions": [],
            "round_summaries": [],
            "phase": "intake",
            "round_number": 0,
            "max_rounds": 6,
            "metrics": DeliberationMetrics().model_dump(),
            "should_stop": False,
        }

        # Should deserialize without error
        result = deserialize_state_from_checkpoint(old_checkpoint)
        assert result["session_id"] == "old-session"
        assert isinstance(result["problem"], Problem)
