"""Tests for email deliverability CLI script."""

from unittest.mock import patch

import pytest

from backend.scripts.test_email_deliverability import (
    TEMPLATES,
    get_action_reminder_data,
    get_meeting_completed_data,
    get_weekly_digest_data,
    get_welcome_data,
    get_workspace_invitation_data,
    main,
    parse_args,
    send_all_test_emails,
    send_test_email,
)


class TestArgumentParsing:
    """Tests for CLI argument parsing."""

    def test_requires_recipient(self):
        """Should fail without recipient."""
        with pytest.raises(SystemExit):
            parse_args([])

    def test_accepts_recipient(self):
        """Should accept recipient argument."""
        args = parse_args(["--recipient", "test@example.com"])
        assert args.recipient == "test@example.com"

    def test_accepts_short_recipient(self):
        """Should accept short -r flag."""
        args = parse_args(["-r", "test@example.com"])
        assert args.recipient == "test@example.com"

    def test_default_template_is_all(self):
        """Default template should be 'all'."""
        args = parse_args(["-r", "test@example.com"])
        assert args.template == "all"

    def test_accepts_specific_template(self):
        """Should accept specific template."""
        args = parse_args(["-r", "test@example.com", "-t", "welcome"])
        assert args.template == "welcome"

    def test_rejects_invalid_template(self):
        """Should reject invalid template name."""
        with pytest.raises(SystemExit):
            parse_args(["-r", "test@example.com", "-t", "invalid"])

    def test_accepts_list_templates(self):
        """Should accept --list-templates flag."""
        args = parse_args(["-r", "dummy@example.com", "--list-templates"])
        assert args.list_templates is True


class TestTestDataFixtures:
    """Tests for test data fixture functions."""

    def test_welcome_data_has_required_fields(self):
        """Welcome data should have user_name and user_id."""
        data = get_welcome_data()
        assert "user_name" in data
        assert "user_id" in data
        assert data["user_name"] is not None

    def test_meeting_completed_data_has_required_fields(self):
        """Meeting completed data should have all required fields."""
        data = get_meeting_completed_data()
        required = [
            "user_id",
            "problem_statement",
            "summary",
            "recommendations",
            "actions",
            "meeting_url",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"
        assert len(data["recommendations"]) > 0
        assert len(data["actions"]) > 0

    def test_action_reminder_data_due_tomorrow(self):
        """Action reminder (not overdue) should have future due date."""
        data = get_action_reminder_data(is_overdue=False)
        assert "user_id" in data
        assert "action_title" in data
        assert "due_date" in data
        assert data["is_overdue"] is False

    def test_action_reminder_data_overdue(self):
        """Action reminder (overdue) should have past due date."""
        data = get_action_reminder_data(is_overdue=True)
        assert data["is_overdue"] is True

    def test_weekly_digest_data_has_required_fields(self):
        """Weekly digest data should have all required fields."""
        data = get_weekly_digest_data()
        required = [
            "user_id",
            "overdue_actions",
            "upcoming_actions",
            "completed_count",
            "meetings_count",
        ]
        for field in required:
            assert field in data, f"Missing field: {field}"

    def test_workspace_invitation_data_has_required_fields(self):
        """Workspace invitation data should have all required fields."""
        data = get_workspace_invitation_data()
        required = ["workspace_name", "inviter_name", "role", "accept_url", "expires_at"]
        for field in required:
            assert field in data, f"Missing field: {field}"


class TestTemplateRegistry:
    """Tests for template registry."""

    def test_all_templates_registered(self):
        """Should have all expected templates registered."""
        expected = {
            "welcome",
            "meeting_completed",
            "action_reminder",
            "action_reminder_overdue",
            "weekly_digest",
            "workspace_invitation",
        }
        assert set(TEMPLATES.keys()) == expected

    def test_templates_have_valid_structure(self):
        """Each template should be a tuple of (name, render_fn, data_fn)."""
        for key, value in TEMPLATES.items():
            assert len(value) == 3, f"Template {key} should be 3-tuple"
            name, render_fn, data_fn = value
            assert isinstance(name, str), f"Template {key} name should be string"
            assert callable(render_fn), f"Template {key} render_fn should be callable"
            assert callable(data_fn), f"Template {key} data_fn should be callable"


class TestSendTestEmail:
    """Tests for send_test_email function."""

    @patch("backend.scripts.test_email_deliverability.send_email")
    def test_sends_welcome_email(self, mock_send):
        """Should send welcome email successfully."""
        mock_send.return_value = {"id": "test-123"}

        result = send_test_email("test@example.com", "welcome")

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args.kwargs["to"] == "test@example.com"
        assert "[TEST]" in call_args.kwargs["subject"]
        assert "Welcome" in call_args.kwargs["subject"]

    @patch("backend.scripts.test_email_deliverability.send_email")
    def test_returns_false_for_unknown_template(self, mock_send):
        """Should return False for unknown template."""
        result = send_test_email("test@example.com", "unknown_template")

        assert result is False
        mock_send.assert_not_called()

    @patch("backend.scripts.test_email_deliverability.send_email")
    def test_returns_false_when_no_api_key(self, mock_send):
        """Should return False when send_email returns None (no API key)."""
        mock_send.return_value = None

        result = send_test_email("test@example.com", "welcome")

        assert result is False

    @patch("backend.scripts.test_email_deliverability.send_email")
    def test_returns_false_on_email_error(self, mock_send):
        """Should return False and handle EmailError gracefully."""
        from backend.services.email import EmailError

        mock_send.side_effect = EmailError("Test error")

        result = send_test_email("test@example.com", "welcome")

        assert result is False


class TestSendAllTestEmails:
    """Tests for send_all_test_emails function."""

    @patch("backend.scripts.test_email_deliverability.send_test_email")
    def test_sends_all_templates(self, mock_send):
        """Should attempt to send all templates."""
        mock_send.return_value = True

        results = send_all_test_emails("test@example.com")

        assert mock_send.call_count == len(TEMPLATES)
        assert results["sent"] == len(TEMPLATES)
        assert results["failed"] == 0

    @patch("backend.scripts.test_email_deliverability.send_test_email")
    def test_counts_failures(self, mock_send):
        """Should count failures correctly."""
        # Alternate success/failure
        mock_send.side_effect = [True, False, True, False, True, False]

        results = send_all_test_emails("test@example.com")

        assert results["sent"] == 3
        assert results["failed"] == 3

    @patch("backend.scripts.test_email_deliverability.send_test_email")
    def test_returns_template_results(self, mock_send):
        """Should return individual template results."""
        mock_send.return_value = True

        results = send_all_test_emails("test@example.com")

        assert "templates" in results
        assert len(results["templates"]) == len(TEMPLATES)
        for template in results["templates"]:
            assert "name" in template
            assert "success" in template


class TestMain:
    """Tests for main entry point."""

    @patch("backend.scripts.test_email_deliverability.send_all_test_emails")
    def test_main_sends_all_by_default(self, mock_send_all):
        """Should send all templates when template=all."""
        mock_send_all.return_value = {"sent": 6, "failed": 0, "templates": []}

        exit_code = main(["--recipient", "test@example.com"])

        mock_send_all.assert_called_once_with("test@example.com")
        assert exit_code == 0

    @patch("backend.scripts.test_email_deliverability.send_test_email")
    def test_main_sends_single_template(self, mock_send):
        """Should send single template when specified."""
        mock_send.return_value = True

        exit_code = main(["--recipient", "test@example.com", "--template", "welcome"])

        mock_send.assert_called_once_with("test@example.com", "welcome")
        assert exit_code == 0

    @patch("backend.scripts.test_email_deliverability.send_test_email")
    def test_main_returns_1_on_failure(self, mock_send):
        """Should return exit code 1 when email fails."""
        mock_send.return_value = False

        exit_code = main(["--recipient", "test@example.com", "--template", "welcome"])

        assert exit_code == 1

    def test_main_list_templates(self, capsys):
        """Should list templates and exit 0."""
        exit_code = main(["--recipient", "dummy@example.com", "--list-templates"])

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "welcome" in captured.out
        assert "meeting_completed" in captured.out
