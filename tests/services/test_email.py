"""Tests for email service."""

from backend.services.email import (
    generate_unsubscribe_token,
    get_unsubscribe_url,
    validate_unsubscribe_token,
)


class TestUnsubscribeTokens:
    """Tests for unsubscribe token generation and validation."""

    def test_generate_and_validate_token(self) -> None:
        """Test that generated tokens can be validated."""
        user_id = "test-user-123"
        email_type = "all"

        token = generate_unsubscribe_token(user_id, email_type)
        result = validate_unsubscribe_token(token)

        assert result is not None
        assert result == (user_id, email_type)

    def test_validate_token_different_types(self) -> None:
        """Test token validation with different email types."""
        user_id = "test-user-456"

        for email_type in ["all", "reminders", "digest", "meeting"]:
            token = generate_unsubscribe_token(user_id, email_type)
            result = validate_unsubscribe_token(token)

            assert result is not None
            assert result[0] == user_id
            assert result[1] == email_type

    def test_validate_invalid_token(self) -> None:
        """Test that invalid tokens are rejected."""
        result = validate_unsubscribe_token("invalid-token")
        assert result is None

    def test_validate_tampered_token(self) -> None:
        """Test that tampered tokens are rejected."""
        user_id = "test-user-789"
        token = generate_unsubscribe_token(user_id, "all")

        # Tamper with the token by changing user_id
        parts = token.rsplit(":", 1)
        tampered = f"hacked-user:all:{parts[1]}"

        result = validate_unsubscribe_token(tampered)
        assert result is None

    def test_validate_empty_token(self) -> None:
        """Test that empty token is rejected."""
        result = validate_unsubscribe_token("")
        assert result is None

    def test_unsubscribe_url_format(self) -> None:
        """Test unsubscribe URL generation."""
        user_id = "test-user-url"
        url = get_unsubscribe_url(user_id, "reminders")

        assert "/api/v1/email/unsubscribe?token=" in url
        assert "test-user-url" in url
        assert "reminders" in url


class TestEmailTemplates:
    """Tests for email template rendering."""

    def test_welcome_email_renders(self) -> None:
        """Test welcome email template renders without errors."""
        from backend.services.email_templates import render_welcome_email

        html, text = render_welcome_email(user_name="Test User", user_id="user-123")

        assert "Welcome" in html
        assert "Test User" in html
        assert "Board of One" in html
        assert "Dashboard" in html

        assert "Welcome" in text
        assert "Test User" in text

    def test_welcome_email_without_name(self) -> None:
        """Test welcome email works without user name."""
        from backend.services.email_templates import render_welcome_email

        html, text = render_welcome_email(user_name=None, user_id="user-123")

        assert "Welcome," in html
        assert "Board of One" in html

    def test_meeting_completed_email_renders(self) -> None:
        """Test meeting completed email template renders without errors."""
        from backend.services.email_templates import render_meeting_completed_email

        html, text = render_meeting_completed_email(
            user_id="user-123",
            problem_statement="How should we price our SaaS product?",
            summary="The meeting concluded with recommendations for tiered pricing.",
            recommendations=["Use tiered pricing", "Add annual discount", "Free trial"],
            actions=[
                {
                    "title": "Research competitor pricing",
                    "due_date": "2025-12-15",
                    "priority": "high",
                },
                {"title": "Draft pricing page", "due_date": "2025-12-20", "priority": "medium"},
            ],
            meeting_url="https://boardof.one/meeting/abc123",
        )

        assert "Meeting Complete" in html
        assert "pricing" in html.lower()
        assert "Research competitor pricing" in html
        assert "Unsubscribe" in html

        assert "Meeting Complete" in text
        assert "pricing" in text.lower()

    def test_action_reminder_email_renders(self) -> None:
        """Test action reminder email template renders without errors."""
        from datetime import date

        from backend.services.email_templates import render_action_reminder_email

        html, text = render_action_reminder_email(
            user_id="user-123",
            action_title="Review marketing strategy",
            action_description="Analyze Q4 performance and plan Q1 campaigns.",
            due_date=date(2025, 12, 15),
            action_url="https://boardof.one/actions/xyz789",
            is_overdue=False,
        )

        assert "Review marketing strategy" in html
        assert "2025-12-15" in html
        assert "Unsubscribe" in html

        assert "Review marketing strategy" in text

    def test_action_reminder_overdue(self) -> None:
        """Test overdue action reminder has correct styling."""
        from datetime import date

        from backend.services.email_templates import render_action_reminder_email

        html, text = render_action_reminder_email(
            user_id="user-123",
            action_title="Overdue task",
            action_description="This was due yesterday.",
            due_date=date(2025, 12, 10),
            action_url="https://boardof.one/actions/late",
            is_overdue=True,
        )

        assert "overdue" in html.lower()
        assert "[Overdue]" in text

    def test_weekly_digest_email_renders(self) -> None:
        """Test weekly digest email template renders without errors."""
        from backend.services.email_templates import render_weekly_digest_email

        html, text = render_weekly_digest_email(
            user_id="user-123",
            overdue_actions=[
                {"title": "Late task 1", "due_date": "2025-12-05"},
            ],
            upcoming_actions=[
                {"title": "Upcoming task 1", "due_date": "2025-12-15"},
                {"title": "Upcoming task 2", "due_date": "2025-12-16"},
            ],
            completed_count=5,
            meetings_count=2,
        )

        assert "Weekly Summary" in html
        assert "5" in html  # completed count
        assert "2" in html  # meetings count
        assert "Late task 1" in html
        assert "Upcoming task 1" in html
        assert "Unsubscribe" in html

        assert "Weekly Summary" in text
