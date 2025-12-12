"""Tests for action replanning suggestion feature.

Tests:
- Extract replan context from cancelled action
- Analytics event logging
"""

from uuid import uuid4

from backend.services.action_context import extract_replan_context
from backend.services.analytics import log_replan_suggestion_accepted, log_replan_suggestion_shown


def test_extract_replan_context_with_missing_action():
    """Test extract_replan_context with non-existent action."""
    context = extract_replan_context(str(uuid4()))
    assert context == {}


def test_log_replan_suggestion_shown_no_exception():
    """Test that logging replan suggestion doesn't raise exception."""
    action_id = str(uuid4())
    user_id = str(uuid4())
    # Should not raise
    log_replan_suggestion_shown(action_id, user_id)


def test_log_replan_suggestion_accepted_no_exception():
    """Test that logging replan acceptance doesn't raise exception."""
    action_id = str(uuid4())
    user_id = str(uuid4())
    session_id = str(uuid4())
    # Should not raise
    log_replan_suggestion_accepted(action_id, user_id, session_id)
