"""Tests for OAuth error sanitization utilities."""

from backend.api.utils.oauth_errors import (
    SAFE_ERROR_CODES,
    get_user_friendly_message,
    sanitize_oauth_error,
    sanitize_supertokens_message,
)


class TestSanitizeOAuthError:
    """Tests for sanitize_oauth_error function."""

    def test_empty_error_returns_auth_failed(self) -> None:
        """Empty error string should default to auth_failed."""
        assert sanitize_oauth_error("", log_correlation=False) == "auth_failed"
        assert sanitize_oauth_error(None, log_correlation=False) == "auth_failed"  # type: ignore

    def test_access_denied_preserved(self) -> None:
        """Google's access_denied error should be preserved."""
        assert sanitize_oauth_error("access_denied", log_correlation=False) == "access_denied"
        assert sanitize_oauth_error("ACCESS_DENIED", log_correlation=False) == "access_denied"

    def test_internal_errors_mapped_to_auth_failed(self) -> None:
        """Internal flow errors should map to generic auth_failed."""
        internal_errors = [
            "missing_params",
            "token_exchange_failed",
            "no_access_token",
            "request_failed",
            "invalid_grant",
            "invalid_request",
            "invalid_scope",
            "server_error",
        ]
        for error in internal_errors:
            result = sanitize_oauth_error(error, log_correlation=False)
            assert result == "auth_failed", f"'{error}' should map to 'auth_failed'"

    def test_invalid_state_maps_to_session_expired(self) -> None:
        """Invalid state should map to session_expired."""
        assert sanitize_oauth_error("invalid_state", log_correlation=False) == "session_expired"
        assert sanitize_oauth_error("INVALID_STATE", log_correlation=False) == "session_expired"

    def test_config_errors_mapped(self) -> None:
        """Configuration errors should map to config_error."""
        assert sanitize_oauth_error("unauthorized_client", log_correlation=False) == "config_error"
        assert (
            sanitize_oauth_error("unsupported_response_type", log_correlation=False)
            == "config_error"
        )

    def test_rate_limiting_errors_mapped(self) -> None:
        """Rate limiting errors should map to rate_limited."""
        assert sanitize_oauth_error("too many attempts", log_correlation=False) == "rate_limited"
        assert sanitize_oauth_error("account locked", log_correlation=False) == "rate_limited"
        assert sanitize_oauth_error("lockout", log_correlation=False) == "rate_limited"

    def test_whitelist_errors_hidden(self) -> None:
        """Whitelist-related errors should map to access_denied (hiding internal details)."""
        assert sanitize_oauth_error("not on whitelist", log_correlation=False) == "access_denied"
        assert sanitize_oauth_error("whitelist rejection", log_correlation=False) == "access_denied"
        assert sanitize_oauth_error("not authorized", log_correlation=False) == "access_denied"
        assert sanitize_oauth_error("not allowed", log_correlation=False) == "access_denied"

    def test_unknown_errors_default_to_auth_failed(self) -> None:
        """Unknown errors should default to auth_failed."""
        assert (
            sanitize_oauth_error("some_random_error_code", log_correlation=False) == "auth_failed"
        )
        assert sanitize_oauth_error("xyz123", log_correlation=False) == "auth_failed"

    def test_case_insensitive_matching(self) -> None:
        """Error matching should be case-insensitive."""
        assert sanitize_oauth_error("ACCESS_DENIED", log_correlation=False) == "access_denied"
        assert sanitize_oauth_error("Invalid_State", log_correlation=False) == "session_expired"
        assert sanitize_oauth_error("WHITELIST", log_correlation=False) == "access_denied"


class TestGetUserFriendlyMessage:
    """Tests for get_user_friendly_message function."""

    def test_all_safe_codes_have_messages(self) -> None:
        """All safe error codes should have user-friendly messages."""
        for code in SAFE_ERROR_CODES:
            message = get_user_friendly_message(code)
            assert message is not None
            assert len(message) > 0

    def test_auth_failed_message(self) -> None:
        """auth_failed should have appropriate message."""
        message = get_user_friendly_message("auth_failed")
        assert "failed" in message.lower() or "try again" in message.lower()

    def test_access_denied_message(self) -> None:
        """access_denied should mention support."""
        message = get_user_friendly_message("access_denied")
        assert "denied" in message.lower() or "support" in message.lower()

    def test_rate_limited_message(self) -> None:
        """rate_limited should mention waiting."""
        message = get_user_friendly_message("rate_limited")
        assert "later" in message.lower() or "wait" in message.lower() or "try" in message.lower()

    def test_unknown_code_defaults(self) -> None:
        """Unknown codes should default to auth_failed message."""
        message = get_user_friendly_message("unknown_code_xyz")
        assert message == SAFE_ERROR_CODES["auth_failed"]


class TestSanitizeSupertokensMessage:
    """Tests for sanitize_supertokens_message function."""

    def test_whitelist_rejection_sanitized(self) -> None:
        """Whitelist rejection messages should be sanitized."""
        original = "Email test@example.com is not whitelisted for closed beta access"
        result = sanitize_supertokens_message(original)
        assert "whitelist" not in result.lower()
        assert "email" not in result.lower()
        assert "contact support" in result.lower()

    def test_closed_beta_message_sanitized(self) -> None:
        """Closed beta messages should be sanitized."""
        result = sanitize_supertokens_message("Not allowed in closed beta")
        assert "beta" not in result.lower()
        assert "contact support" in result.lower()

    def test_account_locked_sanitized(self) -> None:
        """Account locked messages should be sanitized."""
        result = sanitize_supertokens_message("Your account has been locked")
        assert "locked" not in result.lower()
        assert "unavailable" in result.lower() or "support" in result.lower()

    def test_account_deleted_sanitized(self) -> None:
        """Account deleted messages should be sanitized."""
        result = sanitize_supertokens_message("Account deleted")
        assert "deleted" not in result.lower()
        assert "unavailable" in result.lower() or "support" in result.lower()

    def test_rate_limiting_sanitized(self) -> None:
        """Rate limiting messages should be sanitized."""
        result = sanitize_supertokens_message(
            "Too many failed login attempts. Try again in 30 seconds."
        )
        # Should not reveal specific timing
        assert "30 seconds" not in result
        assert "later" in result.lower()

    def test_generic_error_sanitized(self) -> None:
        """Generic errors should get generic message."""
        result = sanitize_supertokens_message("Some internal error occurred")
        assert "internal" not in result.lower()
        assert "authentication failed" in result.lower() or "try again" in result.lower()


class TestIntegration:
    """Integration tests for error sanitization flow."""

    def test_sanitize_then_friendly_message(self) -> None:
        """Full flow: internal error -> safe code -> user message."""
        internal_error = "token_exchange_failed: OAuth token exchange returned 401"

        # Sanitize to safe code
        safe_code = sanitize_oauth_error(internal_error, log_correlation=False)
        assert safe_code == "auth_failed"

        # Get user-friendly message
        message = get_user_friendly_message(safe_code)
        assert "401" not in message
        assert "token" not in message.lower()
        assert "try again" in message.lower()

    def test_no_internal_details_leak(self) -> None:
        """Verify no internal details can leak through any error path."""
        sensitive_patterns = [
            "user_id=abc123",
            "email@example.com",
            "token=secret123",
            "API key",
            "client_secret",
            "database",
            "postgresql",
            "redis",
        ]

        for pattern in sensitive_patterns:
            error = f"Error with {pattern} involved"
            safe_code = sanitize_oauth_error(error, log_correlation=False)
            message = get_user_friendly_message(safe_code)

            # Verify no sensitive info in output
            assert pattern.lower() not in safe_code.lower()
            assert pattern.lower() not in message.lower()
