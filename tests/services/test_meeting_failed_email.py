"""Tests for meeting failed email functionality.

Tests:
- Email template rendering
- send_meeting_failed_email preference checks
- Email triggered on session failure
"""

from unittest.mock import MagicMock, patch


class TestMeetingFailedEmailTemplate:
    """Test email template rendering for failed meetings."""

    def test_render_meeting_failed_email_basic(self):
        """Test basic template rendering."""
        from backend.services.email_templates import render_meeting_failed_email

        html, text = render_meeting_failed_email(
            user_id="user-123",
            problem_statement="Should I launch my product in Q1 or Q2?",
            error_type="LLMError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        # Check HTML content
        assert "Your meeting didn't complete" in html
        assert "Should I launch my product" in html
        assert "LLMError" in html
        assert "2025-12-17 10:30 UTC" in html
        assert "https://boardof.one/dashboard" in html
        assert "doesn't count toward your usage" in html

        # Check plain text content
        assert "Your meeting didn't complete" in text
        assert "Should I launch my product" in text

    def test_render_meeting_failed_email_truncates_long_problem(self):
        """Test that long problem statements are truncated."""
        from backend.services.email_templates import render_meeting_failed_email

        long_problem = "A" * 200  # More than 150 chars
        html, text = render_meeting_failed_email(
            user_id="user-123",
            problem_statement=long_problem,
            error_type="TimeoutError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        # Should be truncated with ellipsis
        assert "A" * 150 + "..." in html
        assert long_problem not in html

    def test_render_meeting_failed_email_llm_error_message(self):
        """Test user-friendly message for LLMError."""
        from backend.services.email_templates import render_meeting_failed_email

        html, _ = render_meeting_failed_email(
            user_id="user-123",
            problem_statement="Test problem",
            error_type="LLMError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        assert "AI service encountered a temporary issue" in html

    def test_render_meeting_failed_email_rate_limit_message(self):
        """Test user-friendly message for RateLimitError."""
        from backend.services.email_templates import render_meeting_failed_email

        html, _ = render_meeting_failed_email(
            user_id="user-123",
            problem_statement="Test problem",
            error_type="RateLimitError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        assert "high demand" in html

    def test_render_meeting_failed_email_timeout_message(self):
        """Test user-friendly message for TimeoutError."""
        from backend.services.email_templates import render_meeting_failed_email

        html, _ = render_meeting_failed_email(
            user_id="user-123",
            problem_statement="Test problem",
            error_type="TimeoutError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        assert "longer than expected" in html

    def test_render_meeting_failed_email_unknown_error(self):
        """Test generic message for unknown error types."""
        from backend.services.email_templates import render_meeting_failed_email

        html, _ = render_meeting_failed_email(
            user_id="user-123",
            problem_statement="Test problem",
            error_type="SomeRandomError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        assert "Something unexpected happened" in html

    def test_render_meeting_failed_email_has_unsubscribe(self):
        """Test that email includes unsubscribe link."""
        from backend.services.email_templates import render_meeting_failed_email

        html, _ = render_meeting_failed_email(
            user_id="user-123",
            problem_statement="Test problem",
            error_type="LLMError",
            timestamp="2025-12-17 10:30 UTC",
            dashboard_url="https://boardof.one/dashboard",
        )

        assert "Unsubscribe" in html


class TestSendMeetingFailedEmail:
    """Test send_meeting_failed_email function."""

    @patch("bo1.state.database.db_session")
    @patch("backend.services.email.send_email_async")
    @patch("bo1.config.get_settings")
    def test_sends_email_when_enabled(self, mock_settings, mock_send, mock_db):
        """Test email sent when user has meeting_emails enabled."""
        from backend.services.email import send_meeting_failed_email

        # Mock settings
        mock_settings.return_value.supertokens_website_domain = "https://boardof.one"

        # Mock database
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "email": "test@example.com",
            "email_preferences": {"meeting_emails": True},
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = send_meeting_failed_email(
            user_id="user-123",
            session_id="session-456",
            problem_statement="Test problem",
            error_type="LLMError",
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.kwargs["to"] == "test@example.com"
        assert "didn't complete" in call_args.kwargs["subject"]

    @patch("bo1.state.database.db_session")
    def test_skips_when_meeting_emails_disabled(self, mock_db):
        """Test email not sent when meeting_emails preference is False."""
        from backend.services.email import send_meeting_failed_email

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "email": "test@example.com",
            "email_preferences": {"meeting_emails": False},
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = send_meeting_failed_email(
            user_id="user-123",
            session_id="session-456",
            problem_statement="Test problem",
            error_type="LLMError",
        )

        assert result is False

    @patch("bo1.state.database.db_session")
    def test_skips_placeholder_email(self, mock_db):
        """Test email not sent to placeholder emails."""
        from backend.services.email import send_meeting_failed_email

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "email": "user-123@placeholder.local",
            "email_preferences": None,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = send_meeting_failed_email(
            user_id="user-123",
            session_id="session-456",
            problem_statement="Test problem",
            error_type="LLMError",
        )

        assert result is False

    @patch("bo1.state.database.db_session")
    def test_skips_user_not_found(self, mock_db):
        """Test handles user not found gracefully."""
        from backend.services.email import send_meeting_failed_email

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = send_meeting_failed_email(
            user_id="unknown-user",
            session_id="session-456",
            problem_statement="Test problem",
            error_type="LLMError",
        )

        assert result is False

    @patch("bo1.state.database.db_session")
    @patch("backend.services.email.send_email_async")
    @patch("bo1.config.get_settings")
    def test_sends_with_default_preferences(self, mock_settings, mock_send, mock_db):
        """Test email sent when email_preferences is None (defaults enabled)."""
        from backend.services.email import send_meeting_failed_email

        mock_settings.return_value.supertokens_website_domain = "https://boardof.one"

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "email": "test@example.com",
            "email_preferences": None,  # Default should allow sending
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
        mock_db.return_value.__exit__ = MagicMock(return_value=False)

        result = send_meeting_failed_email(
            user_id="user-123",
            session_id="session-456",
            problem_statement="Test problem",
            error_type="LLMError",
        )

        assert result is True
        mock_send.assert_called_once()

    @patch("bo1.state.database.db_session")
    def test_handles_db_error_gracefully(self, mock_db):
        """Test handles database errors without raising."""
        from backend.services.email import send_meeting_failed_email

        mock_db.side_effect = Exception("Database connection failed")

        result = send_meeting_failed_email(
            user_id="user-123",
            session_id="session-456",
            problem_statement="Test problem",
            error_type="LLMError",
        )

        assert result is False


class TestEventCollectorFailedEmailIntegration:
    """Test email triggered from EventCollector._mark_session_failed."""

    @patch("backend.services.email.send_meeting_failed_email")
    def test_mark_session_failed_sends_email(self, mock_send_email):
        """Test that _mark_session_failed triggers email notification."""
        from backend.api.event_collector import EventCollector

        # Create mock dependencies
        mock_publisher = MagicMock()
        mock_summarizer = MagicMock()
        mock_session_repo = MagicMock()

        # Mock session data
        mock_session_repo.get.return_value = {
            "user_id": "user-123",
            "problem_statement": "Should I expand to Europe?",
        }

        collector = EventCollector(mock_publisher, mock_summarizer, mock_session_repo)

        # Trigger failure
        test_error = ValueError("Test error")
        collector._mark_session_failed("session-456", test_error)

        # Verify email was called
        mock_send_email.assert_called_once_with(
            user_id="user-123",
            session_id="session-456",
            problem_statement="Should I expand to Europe?",
            error_type="ValueError",
        )

    @patch("backend.services.email.send_meeting_failed_email")
    def test_mark_session_failed_continues_on_email_error(self, mock_send_email):
        """Test that email errors don't block session failure marking."""
        from backend.api.event_collector import EventCollector

        mock_publisher = MagicMock()
        mock_summarizer = MagicMock()
        mock_session_repo = MagicMock()
        mock_session_repo.get.return_value = {
            "user_id": "user-123",
            "problem_statement": "Test problem",
        }

        # Make email send raise an error
        mock_send_email.side_effect = Exception("Email service unavailable")

        collector = EventCollector(mock_publisher, mock_summarizer, mock_session_repo)

        # Should not raise despite email error
        collector._mark_session_failed("session-456", ValueError("Test"))

        # Session status should still be updated
        mock_session_repo.update_status.assert_called_once()

    @patch("backend.services.email.send_meeting_failed_email")
    def test_mark_session_failed_skips_email_on_missing_session(self, mock_send_email):
        """Test email not attempted when session data not found."""
        from backend.api.event_collector import EventCollector

        mock_publisher = MagicMock()
        mock_summarizer = MagicMock()
        mock_session_repo = MagicMock()
        mock_session_repo.get.return_value = None  # Session not found

        collector = EventCollector(mock_publisher, mock_summarizer, mock_session_repo)

        collector._mark_session_failed("session-456", ValueError("Test"))

        # Email should not be called when session not found
        mock_send_email.assert_not_called()
