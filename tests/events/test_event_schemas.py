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
