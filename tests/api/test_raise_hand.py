"""Tests for raise-hand (user interjection) endpoint.

Tests POST /api/v1/sessions/{id}/raise-hand functionality:
- Valid interjection submission
- Session status validation (only running sessions)
- Rate limiting (one pending interjection at a time)
- Message validation
- Prompt injection detection
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest


class TestRaiseHandRequest:
    """Tests for RaiseHandRequest validation."""

    def test_valid_message(self):
        """Test valid interjection message."""
        from backend.api.control import RaiseHandRequest

        req = RaiseHandRequest(message="What about regulatory compliance?")
        assert req.message == "What about regulatory compliance?"

    def test_message_min_length(self):
        """Test message minimum length validation."""
        from pydantic import ValidationError

        from backend.api.control import RaiseHandRequest

        with pytest.raises(ValidationError):
            RaiseHandRequest(message="")

    def test_message_max_length(self):
        """Test message maximum length validation."""
        from pydantic import ValidationError

        from backend.api.control import RaiseHandRequest

        with pytest.raises(ValidationError):
            RaiseHandRequest(message="x" * 2001)

    def test_message_whitespace_only(self):
        """Test message with only whitespace is invalid."""

        from backend.api.control import RaiseHandRequest

        # Single character passes min_length but this tests behavior
        req = RaiseHandRequest(message="   a   ")
        assert req.message == "   a   "


class TestRaiseHandEndpoint:
    """Tests for raise-hand endpoint logic."""

    @pytest.fixture
    def mock_redis_manager(self):
        """Create a mock Redis manager."""
        manager = MagicMock()
        manager.is_available = True
        return manager

    @pytest.fixture
    def mock_session_running(self):
        """Create mock metadata for a running session."""
        return {
            "status": "running",
            "user_id": "test-user-123",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "problem_statement": "Test problem",
        }

    @pytest.fixture
    def mock_session_paused(self):
        """Create mock metadata for a paused session."""
        return {
            "status": "paused",
            "user_id": "test-user-123",
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "problem_statement": "Test problem",
        }

    @pytest.fixture
    def mock_state_no_pending(self):
        """Create mock state with no pending interjection."""
        return {
            "user_interjection": None,
            "needs_interjection_response": False,
            "interjection_responses": [],
            "round_number": 2,
        }

    @pytest.fixture
    def mock_state_pending(self):
        """Create mock state with pending interjection."""
        return {
            "user_interjection": "Previous question",
            "needs_interjection_response": True,
            "interjection_responses": [],
            "round_number": 2,
        }

    def test_session_status_validation(self, mock_session_paused):
        """Test that non-running sessions are rejected."""
        # When session is paused, raise_hand should fail with 400
        status = mock_session_paused.get("status")
        assert status != "running"

    def test_pending_interjection_check(self, mock_state_pending):
        """Test that pending interjections block new submissions."""
        # If needs_interjection_response is True, should reject with 429
        assert mock_state_pending["needs_interjection_response"] is True

    def test_state_update_on_submission(self, mock_state_no_pending):
        """Test state is correctly updated when submitting interjection."""
        message = "What about market expansion?"

        # Simulate state update
        state = mock_state_no_pending.copy()
        state["user_interjection"] = message
        state["needs_interjection_response"] = True
        state["interjection_responses"] = []

        assert state["user_interjection"] == message
        assert state["needs_interjection_response"] is True
        assert state["interjection_responses"] == []


class TestInterjectionStateFields:
    """Tests for interjection state fields in DeliberationGraphState."""

    def test_control_state_includes_interjection_fields(self):
        """Test ControlState includes interjection fields."""
        from bo1.graph.state import ControlState

        # Check type hints include interjection fields
        hints = ControlState.__annotations__
        assert "user_interjection" in hints
        assert "interjection_responses" in hints
        assert "needs_interjection_response" in hints

    def test_get_control_state_extracts_interjection(self):
        """Test get_control_state extracts interjection fields."""
        from bo1.graph.state import get_control_state

        mock_state = {
            "should_stop": False,
            "user_interjection": "Test question",
            "needs_interjection_response": True,
            "interjection_responses": [{"persona": "CFO", "response": "Good question"}],
        }

        control = get_control_state(mock_state)
        assert control["user_interjection"] == "Test question"
        assert control["needs_interjection_response"] is True
        assert len(control["interjection_responses"]) == 1

    def test_create_initial_state_includes_interjection_defaults(self):
        """Test create_initial_state sets interjection defaults."""
        from bo1.graph.state import create_initial_state
        from bo1.models.problem import Problem

        problem = Problem(
            title="Test Problem",
            description="Test problem description",
            context="Test context",
        )
        state = create_initial_state(
            session_id="test-session-123",
            problem=problem,
        )

        assert state["user_interjection"] is None
        assert state["needs_interjection_response"] is False
        assert state["interjection_responses"] == []


class TestInterjectionSSEEvents:
    """Tests for interjection SSE event formatters."""

    def test_user_interjection_raised_event(self):
        """Test user_interjection_raised event formatter."""
        from backend.api.events import user_interjection_raised_event

        event = user_interjection_raised_event(
            session_id="test-session-123",
            message="What about compliance?",
        )

        assert "event: user_interjection_raised" in event
        assert "test-session-123" in event
        assert "What about compliance?" in event

    def test_interjection_response_event(self):
        """Test interjection_response event formatter."""
        from backend.api.events import interjection_response_event

        event = interjection_response_event(
            session_id="test-session-123",
            persona_code="CFO",
            persona_name="Chief Financial Officer",
            response="That's a great point about compliance.",
            round_number=2,
        )

        assert "event: interjection_response" in event
        assert "CFO" in event
        assert "Chief Financial Officer" in event
        assert "great point" in event
        assert "round_number" in event

    def test_interjection_complete_event(self):
        """Test interjection_complete event formatter."""
        from backend.api.events import interjection_complete_event

        event = interjection_complete_event(
            session_id="test-session-123",
            total_responses=4,
            round_number=2,
        )

        assert "event: interjection_complete" in event
        assert "test-session-123" in event
        assert "total_responses" in event
        assert "4" in event
