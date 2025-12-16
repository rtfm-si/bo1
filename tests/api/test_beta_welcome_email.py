"""Tests for beta welcome email functionality."""

from unittest.mock import patch


class TestBetaWelcomeEmail:
    """Tests for send_beta_welcome_email function."""

    def test_sends_email_when_api_key_configured(self) -> None:
        """Test email is sent when Resend API key is configured."""
        with (
            patch("backend.api.email.get_settings") as mock_settings,
            patch("backend.api.email.resend") as mock_resend,
        ):
            mock_settings.return_value.resend_api_key = "re_test_key_12345"
            mock_resend.Emails.send.return_value = {"id": "email-123"}

            from backend.api.email import send_beta_welcome_email

            result = send_beta_welcome_email("test@example.com")

            assert result is not None
            assert result["id"] == "email-123"
            mock_resend.Emails.send.assert_called_once()
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert call_args["to"] == ["test@example.com"]
            assert "Welcome" in call_args["subject"]

    def test_returns_none_when_api_key_missing(self) -> None:
        """Test None returned when Resend API key not configured."""
        with patch("backend.api.email.get_settings") as mock_settings:
            mock_settings.return_value.resend_api_key = ""

            from backend.api.email import send_beta_welcome_email

            result = send_beta_welcome_email("test@example.com")

            assert result is None

    def test_returns_none_on_resend_error(self) -> None:
        """Test None returned when Resend API fails."""
        import resend.exceptions

        with (
            patch("backend.api.email.get_settings") as mock_settings,
            patch("backend.api.email.resend") as mock_resend,
        ):
            mock_settings.return_value.resend_api_key = "re_test_key_12345"
            # ResendError requires: code, error_type, message, suggested_action
            mock_resend.Emails.send.side_effect = resend.exceptions.ResendError(
                code=401,
                error_type="validation_error",
                message="Invalid API key",
                suggested_action="Check your API key",
            )
            mock_resend.exceptions.ResendError = resend.exceptions.ResendError

            from backend.api.email import send_beta_welcome_email

            result = send_beta_welcome_email("test@example.com")

            assert result is None

    def test_email_contains_correct_link(self) -> None:
        """Test email contains signup link."""
        with (
            patch("backend.api.email.get_settings") as mock_settings,
            patch("backend.api.email.resend") as mock_resend,
        ):
            mock_settings.return_value.resend_api_key = "re_test_key_12345"
            mock_resend.Emails.send.return_value = {"id": "email-456"}

            from backend.api.email import send_beta_welcome_email

            result = send_beta_welcome_email("user@test.com")

            assert result is not None
            call_args = mock_resend.Emails.send.call_args[0][0]
            assert "https://boardof.one/auth" in call_args["html"]
            assert "user@test.com" in call_args["html"]


class TestBetaWelcomeEmailTemplates:
    """Tests for beta welcome email HTML/text templates."""

    def test_html_template_renders(self) -> None:
        """Test HTML template renders correctly."""
        from backend.api.email import _get_beta_welcome_html

        html = _get_beta_welcome_html("test@example.com")

        assert "<!DOCTYPE html>" in html
        assert "test@example.com" in html
        assert "Board of One" in html
        assert "Get Started" in html
        assert "https://boardof.one/auth" in html

    def test_text_template_renders(self) -> None:
        """Test plain text template renders correctly."""
        from backend.api.email import _get_beta_welcome_text

        text = _get_beta_welcome_text("test@example.com")

        assert "test@example.com" in text
        assert "Board of One" in text
        assert "https://boardof.one/auth" in text
