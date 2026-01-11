"""Integration tests for honeypot validation on API endpoints.

Tests that honeypot validation is wired into request models and
called by endpoint handlers. Uses direct validation calls to avoid
CSRF/auth complexities in test setup.
"""

import pytest
from fastapi import HTTPException

from backend.api.advisor import MentorChatRequest
from backend.api.models import CreateSessionRequest, FeedbackCreate
from backend.api.utils.honeypot import validate_honeypot_fields


class TestSessionHoneypot:
    """Test honeypot validation on session creation request model."""

    @pytest.mark.unit
    def test_clean_request_passes_honeypot(self):
        """Session request with empty honeypot fields should pass validation."""
        request = CreateSessionRequest(
            problem_statement="Should we expand to Europe? This is a serious strategic question that requires deliberation."
        )
        # Should not raise
        validate_honeypot_fields(request, "sessions.create")

    @pytest.mark.unit
    def test_filled_email_honeypot_returns_400(self):
        """Session request with filled email honeypot should raise 400."""
        request = CreateSessionRequest(
            problem_statement="Should we expand? This is a strategic question that needs discussion.",
            _hp_email="bot@spam.com",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "sessions.create")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid request"

    @pytest.mark.unit
    def test_filled_url_honeypot_returns_400(self):
        """Session request with filled URL honeypot should raise 400."""
        request = CreateSessionRequest(
            problem_statement="Should we expand? This is a strategic question.",
            _hp_url="http://spam.com",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "sessions.create")

        assert exc_info.value.status_code == 400

    @pytest.mark.unit
    def test_filled_phone_honeypot_returns_400(self):
        """Session request with filled phone honeypot should raise 400."""
        request = CreateSessionRequest(
            problem_statement="Should we expand? This is a strategic question.",
            _hp_phone="555-1234",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "sessions.create")

        assert exc_info.value.status_code == 400


class TestFeedbackHoneypot:
    """Test honeypot validation on feedback submission request model."""

    @pytest.mark.unit
    def test_clean_request_passes_honeypot(self):
        """Feedback request with empty honeypot fields should pass validation."""
        request = FeedbackCreate(
            type="feature_request",
            title="Please add dark mode",
            description="It would be great to have dark mode support for late night work.",
        )
        # Should not raise
        validate_honeypot_fields(request, "feedback.submit")

    @pytest.mark.unit
    def test_filled_email_honeypot_returns_400(self):
        """Feedback request with filled email honeypot should raise 400."""
        request = FeedbackCreate(
            type="feature_request",
            title="Please add dark mode",
            description="It would be great to have dark mode support.",
            _hp_email="spam@bot.com",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "feedback.submit")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid request"

    @pytest.mark.unit
    def test_filled_url_honeypot_returns_400(self):
        """Feedback request with filled URL honeypot should raise 400."""
        request = FeedbackCreate(
            type="problem_report",
            title="Page not loading",
            description="The meeting page shows a spinner but never loads.",
            _hp_url="http://spam.com",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "feedback.submit")

        assert exc_info.value.status_code == 400


class TestMentorHoneypot:
    """Test honeypot validation on mentor chat request model."""

    @pytest.mark.unit
    def test_clean_request_passes_honeypot(self):
        """Mentor request with empty honeypot fields should pass validation."""
        request = MentorChatRequest(
            message="How should I prioritize my tasks?",
        )
        # Should not raise
        validate_honeypot_fields(request, "mentor.chat")

    @pytest.mark.unit
    def test_filled_email_honeypot_returns_400(self):
        """Mentor request with filled email honeypot should raise 400."""
        request = MentorChatRequest(
            message="How should I prioritize my tasks?",
            _hp_email="bot@spam.com",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "mentor.chat")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid request"

    @pytest.mark.unit
    def test_filled_phone_honeypot_returns_400(self):
        """Mentor request with filled phone honeypot should raise 400."""
        request = MentorChatRequest(
            message="How should I prioritize my tasks?",
            _hp_phone="555-1234",
        )
        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(request, "mentor.chat")

        assert exc_info.value.status_code == 400
