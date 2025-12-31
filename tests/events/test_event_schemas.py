"""Tests for event schema validation."""

import pytest
from pydantic import ValidationError

from bo1.events import (
    BaseEvent,
    ContributionEvent,
    ContributionSummary,
    ErrorEvent,
    SubProblemStartedEvent,
    VotingCompleteEvent,
)
from bo1.events.schemas import (
    EVENT_SCHEMA_REGISTRY,
    get_event_json_schemas,
    get_schema_for_event,
)


class TestBaseEvent:
    """Test base event schema."""

    def test_base_event_requires_event_type(self):
        """Test that event_type is required."""
        with pytest.raises(ValidationError):
            BaseEvent(session_id="test")

    def test_base_event_auto_timestamp(self):
        """Test that timestamp is auto-generated."""
        event = BaseEvent(event_type="test", session_id="test-session")
        assert event.timestamp is not None
        assert "T" in event.timestamp  # ISO format


class TestSubProblemStartedEvent:
    """Test SubProblemStartedEvent schema."""

    def test_valid_event(self):
        """Test creating valid event."""
        event = SubProblemStartedEvent(
            session_id="bo1_abc123",
            sub_problem_index=0,
            sub_problem_id="sp1",
            goal="Analyze market opportunity",
            total_sub_problems=3,
        )
        assert event.event_type == "subproblem_started"
        assert event.sub_problem_index == 0
        assert event.total_sub_problems == 3

    def test_invalid_negative_index(self):
        """Test that negative index is rejected."""
        with pytest.raises(ValidationError):
            SubProblemStartedEvent(
                session_id="bo1_abc123",
                sub_problem_index=-1,
                sub_problem_id="sp1",
                goal="Test",
                total_sub_problems=3,
            )

    def test_model_dump(self):
        """Test serialization to dict."""
        event = SubProblemStartedEvent(
            session_id="bo1_abc123",
            sub_problem_index=0,
            sub_problem_id="sp1",
            goal="Test goal",
            total_sub_problems=2,
        )
        data = event.model_dump()
        assert data["event_type"] == "subproblem_started"
        assert data["sub_problem_index"] == 0
        assert "timestamp" in data


class TestContributionEvent:
    """Test ContributionEvent schema."""

    def test_valid_contribution(self):
        """Test creating valid contribution event."""
        event = ContributionEvent(
            session_id="bo1_abc123",
            persona_code="CFO",
            persona_name="Zara Kim",
            content="From a financial perspective...",
            round=1,
            contribution_type="initial",
        )
        assert event.event_type == "contribution"
        assert event.persona_code == "CFO"

    def test_contribution_with_summary(self):
        """Test contribution with structured summary."""
        summary = ContributionSummary(
            concise="Key financial metrics suggest caution",
            looking_for="Revenue projections and burn rate",
            value_added="Financial risk assessment",
            concerns=["Cash flow uncertainty", "High CAC"],
            questions=["What's the projected runway?"],
        )
        event = ContributionEvent(
            session_id="bo1_abc123",
            persona_code="CFO",
            persona_name="Zara Kim",
            content="Full content here...",
            round=2,
            contribution_type="followup",
            summary=summary,
        )
        assert event.summary is not None
        assert len(event.summary.concerns) == 2

    def test_invalid_round_zero(self):
        """Test that round 0 is rejected."""
        with pytest.raises(ValidationError):
            ContributionEvent(
                session_id="bo1_abc123",
                persona_code="CFO",
                persona_name="Test",
                content="Test",
                round=0,
                contribution_type="initial",
            )


class TestErrorEvent:
    """Test ErrorEvent schema."""

    def test_error_event_with_sub_problem(self):
        """Test error event with sub-problem context."""
        event = ErrorEvent(
            session_id="bo1_abc123",
            error="Sub-problem 0 failed: Connection timeout",
            error_type="TimeoutError",
            node="parallel_subproblems",
            recoverable=False,
            sub_problem_index=0,
            sub_problem_goal="Analyze market opportunity",
        )
        assert event.event_type == "error"
        assert event.recoverable is False
        assert event.sub_problem_index == 0

    def test_error_event_minimal(self):
        """Test error event with minimal fields."""
        event = ErrorEvent(
            session_id="bo1_abc123",
            error="Something went wrong",
        )
        assert event.error_type == "UnknownError"
        assert event.recoverable is False


class TestVotingCompleteEvent:
    """Test VotingCompleteEvent schema."""

    def test_valid_consensus_levels(self):
        """Test all valid consensus levels."""
        for level in ["strong", "moderate", "weak"]:
            event = VotingCompleteEvent(
                session_id="test",
                votes_count=5,
                consensus_level=level,
            )
            assert event.consensus_level == level

    def test_invalid_consensus_level(self):
        """Test invalid consensus level is rejected."""
        with pytest.raises(ValidationError):
            VotingCompleteEvent(
                session_id="test",
                votes_count=5,
                consensus_level="invalid",
            )


class TestEventTypeValidation:
    """Test that event_type is validated correctly."""

    def test_event_type_literal_enforced(self):
        """Test that event_type must match the Literal."""
        # SubProblemStartedEvent should only accept "subproblem_started"
        event = SubProblemStartedEvent(
            session_id="test",
            sub_problem_index=0,
            sub_problem_id="sp1",
            goal="Test",
            total_sub_problems=1,
        )
        assert event.event_type == "subproblem_started"

        # Cannot override event_type
        event2 = SubProblemStartedEvent(
            session_id="test",
            event_type="subproblem_started",  # Must match
            sub_problem_index=0,
            sub_problem_id="sp1",
            goal="Test",
            total_sub_problems=1,
        )
        assert event2.event_type == "subproblem_started"


class TestEventSchemaRegistry:
    """Test event schema registry and JSON schema export."""

    def test_registry_contains_all_events(self):
        """Test that registry contains all expected event types."""
        expected_events = {
            "session_started",
            "decomposition_complete",
            "persona_selected",
            "persona_selection_complete",
            "subproblem_started",
            "subproblem_complete",
            "round_started",
            "contribution",
            "convergence",
            "voting_started",
            "voting_complete",
            "synthesis_complete",
            "meta_synthesis_complete",
            "truncation_warning",
            "error",
        }
        assert set(EVENT_SCHEMA_REGISTRY.keys()) == expected_events

    def test_get_event_json_schemas_returns_valid_schemas(self):
        """Test that get_event_json_schemas returns valid JSON Schema dicts."""
        schemas = get_event_json_schemas()

        # Should have same keys as registry
        assert set(schemas.keys()) == set(EVENT_SCHEMA_REGISTRY.keys())

        # Each schema should be a valid JSON Schema dict
        for _event_type, schema in schemas.items():
            assert isinstance(schema, dict)
            # Should have standard JSON Schema fields
            assert "properties" in schema or "$defs" in schema
            assert "type" in schema
            assert schema["type"] == "object"

    def test_json_schema_has_required_fields(self):
        """Test that JSON schemas include required event fields."""
        schemas = get_event_json_schemas()

        # All events should have event_type and session_id
        for event_type, schema in schemas.items():
            props = schema.get("properties", {})
            assert "event_type" in props, f"{event_type} missing event_type"
            assert "session_id" in props, f"{event_type} missing session_id"
            assert "timestamp" in props, f"{event_type} missing timestamp"

    def test_json_schema_contribution_has_expected_fields(self):
        """Test that contribution schema has all expected fields."""
        schemas = get_event_json_schemas()
        contrib = schemas["contribution"]

        props = contrib.get("properties", {})
        expected_fields = {
            "event_type",
            "session_id",
            "timestamp",
            "sub_problem_index",
            "persona_code",
            "persona_name",
            "content",
            "round",
            "contribution_type",
            "archetype",
            "domain_expertise",
            "summary",
        }
        assert expected_fields.issubset(set(props.keys()))

    def test_get_schema_for_event_returns_correct_class(self):
        """Test get_schema_for_event returns the correct Pydantic class."""
        from bo1.events import ContributionEvent, ErrorEvent, SessionStartedEvent

        assert get_schema_for_event("contribution") is ContributionEvent
        assert get_schema_for_event("error") is ErrorEvent
        assert get_schema_for_event("session_started") is SessionStartedEvent
        assert get_schema_for_event("unknown") is None

    def test_schema_count_matches_registry(self):
        """Test that schema count matches registry size."""
        schemas = get_event_json_schemas()
        assert len(schemas) == len(EVENT_SCHEMA_REGISTRY)
        assert len(schemas) == 15  # Current known count
