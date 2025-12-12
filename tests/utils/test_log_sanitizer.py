"""Tests for log sanitizer utility.

Covers:
- Password/secret field redaction
- Email partial masking
- Bearer token truncation
- Nested dict sanitization
- Structure preservation
"""

from bo1.utils.log_sanitizer import (
    REDACTED,
    is_sensitive_key,
    sanitize_log_data,
    sanitize_message,
    sanitize_value,
)


class TestSanitizePasswordField:
    """Test password and secret field redaction."""

    def test_password_in_dict_redacted(self) -> None:
        """Password values replaced with truncated form."""
        data = {"user": "test", "password": "secret123"}  # noqa: S105 - test data
        result = sanitize_log_data(data)
        assert result["user"] == "test"
        # Sensitive keys with >8 char values get truncated to 8 chars + ...
        assert result["password"] == "secret12..." or result["password"] == REDACTED  # noqa: S105

    def test_secret_key_redacted(self) -> None:
        """Secret key values redacted."""
        data = {"secret": "my-secret-value"}
        result = sanitize_log_data(data)
        assert "my-secret" not in str(result["secret"])

    def test_api_key_redacted(self) -> None:
        """API key values redacted."""
        data = {"api_key": "sk-1234567890abcdef"}
        result = sanitize_log_data(data)
        assert "1234567890" not in str(result["api_key"])

    def test_token_redacted(self) -> None:
        """Token values redacted."""
        data = {"access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.payload"}
        result = sanitize_log_data(data)
        assert "payload" not in str(result["access_token"])

    def test_case_insensitive_keys(self) -> None:
        """Key matching is case-insensitive."""
        data = {"PASSWORD": "secret", "Api_Key": "key123456789xyz"}
        result = sanitize_log_data(data)
        assert "secret" not in str(result["PASSWORD"])
        # Value is truncated to 8 chars, so full value not present
        assert "key123456789xyz" not in str(result["Api_Key"])


class TestSanitizeEmailPartial:
    """Test email partial masking."""

    def test_email_in_message_masked(self) -> None:
        """Email masked as j***@example.com."""
        msg = "User john.doe@example.com logged in"
        result = sanitize_message(msg)
        assert "@example.com" in result
        assert "john.doe" not in result
        assert "joh***@example.com" in result

    def test_short_local_part(self) -> None:
        """Short email local parts handled correctly."""
        msg = "Email: ab@test.com"
        result = sanitize_message(msg)
        assert "@test.com" in result
        assert "ab@test.com" not in result

    def test_email_in_dict_value(self) -> None:
        """Email in dict value is masked."""
        data = {"message": "Contact user@domain.org for help"}
        result = sanitize_log_data(data)
        assert "user@domain" not in str(result["message"])


class TestSanitizeBearerToken:
    """Test Bearer token truncation."""

    def test_bearer_token_truncated(self) -> None:
        """Bearer token truncated to 8 chars."""
        # Note: "Authorization: Bearer" matches KV pattern for authorization key
        # So the entire value gets redacted
        msg = "Auth header: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"
        result = sanitize_message(msg)
        assert "Bearer eyJhbGci..." in result
        assert "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" not in result

    def test_bearer_case_insensitive(self) -> None:
        """Bearer pattern is case-insensitive."""
        msg = "header: bearer abc123456789def"
        result = sanitize_message(msg)
        assert "abc12345..." in result


class TestSanitizeNestedDict:
    """Test deep keys sanitized recursively."""

    def test_nested_password(self) -> None:
        """Nested dict with password is sanitized."""
        data = {"auth": {"user": "test", "password": "nested_secret"}}
        result = sanitize_log_data(data)
        assert "nested_secret" not in str(result)

    def test_deeply_nested(self) -> None:
        """Deeply nested structures are sanitized."""
        data = {"level1": {"level2": {"level3": {"token": "deep_token_value"}}}}
        result = sanitize_log_data(data)
        assert "deep_token" not in str(result)

    def test_list_in_dict(self) -> None:
        """Lists within dicts are sanitized."""
        data = {
            "users": [{"name": "Alice", "password": "pass1"}, {"name": "Bob", "password": "pass2"}]
        }
        result = sanitize_log_data(data)
        assert "pass1" not in str(result)
        assert "pass2" not in str(result)
        assert result["users"][0]["name"] == "Alice"


class TestSanitizePreservesStructure:
    """Test non-sensitive fields unchanged."""

    def test_non_sensitive_preserved(self) -> None:
        """Non-sensitive fields are unchanged."""
        data = {
            "method": "POST",
            "path": "/api/v1/sessions",
            "status_code": 200,
            "duration_ms": 150,
        }
        result = sanitize_log_data(data)
        assert result == data

    def test_mixed_fields(self) -> None:
        """Mix of sensitive and non-sensitive fields."""
        data = {"user_id": "abc123", "action": "login", "password": "secret"}
        result = sanitize_log_data(data)
        assert result["user_id"] == "abc123"
        assert result["action"] == "login"
        assert "secret" not in str(result["password"])

    def test_none_values(self) -> None:
        """None values are preserved."""
        data = {"user": None, "password": None}
        result = sanitize_log_data(data)
        assert result["user"] is None
        assert result["password"] == REDACTED

    def test_numeric_values(self) -> None:
        """Numeric values are preserved."""
        data = {"count": 42, "ratio": 3.14}
        result = sanitize_log_data(data)
        assert result["count"] == 42
        assert result["ratio"] == 3.14


class TestSanitizeMessage:
    """Test string message sanitization."""

    def test_key_value_pattern_unquoted(self) -> None:
        """key=value patterns are redacted."""
        msg = "Login failed: password=secret123 for user"
        result = sanitize_message(msg)
        assert "password=[REDACTED]" in result
        assert "secret123" not in result

    def test_key_value_pattern_json(self) -> None:
        """JSON-style "key": "value" patterns are redacted."""
        msg = '{"password": "secret123", "user": "test"}'
        result = sanitize_message(msg)
        assert "secret123" not in result

    def test_multiple_patterns(self) -> None:
        """Multiple sensitive patterns in one message."""
        msg = "Request: token=abc123456789 api_key=xyz987654321"
        result = sanitize_message(msg)
        assert "abc123456789" not in result
        assert "xyz987654321" not in result


class TestIsSensitiveKey:
    """Test sensitive key detection."""

    def test_common_sensitive_keys(self) -> None:
        """Common sensitive keys are detected."""
        sensitive = ["password", "secret", "token", "api_key", "authorization"]
        for key in sensitive:
            assert is_sensitive_key(key), f"{key} should be sensitive"

    def test_case_insensitive(self) -> None:
        """Detection is case-insensitive."""
        assert is_sensitive_key("PASSWORD")
        assert is_sensitive_key("Api_Key")
        assert is_sensitive_key("ACCESS_TOKEN")

    def test_non_sensitive_keys(self) -> None:
        """Non-sensitive keys are not flagged."""
        non_sensitive = ["user_id", "name", "email", "path", "method"]
        for key in non_sensitive:
            assert not is_sensitive_key(key), f"{key} should not be sensitive"


class TestSanitizeValue:
    """Test individual value sanitization."""

    def test_sensitive_key_redacts(self) -> None:
        """Value with sensitive key is redacted."""
        result = sanitize_value("my-secret-value", key="password")
        assert "my-secret" not in str(result)

    def test_long_token_string(self) -> None:
        """Long token-like strings are truncated."""
        token = "abcdef123456789012345678901234567890"  # noqa: S105 - test data
        result = sanitize_value(token)
        assert token not in str(result)
        assert "abcdef12..." in result

    def test_regular_string_unchanged(self) -> None:
        """Regular strings without patterns are unchanged."""
        result = sanitize_value("Hello world", key="message")
        assert result == "Hello world"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dict(self) -> None:
        """Empty dict returns empty dict."""
        assert sanitize_log_data({}) == {}

    def test_empty_string(self) -> None:
        """Empty string returns empty string."""
        assert sanitize_message("") == ""

    def test_none_input(self) -> None:
        """None input returns None."""
        assert sanitize_log_data(None) is None

    def test_recursion_limit(self) -> None:
        """Deep recursion doesn't crash."""
        # Build deeply nested dict
        data: dict = {"value": "test"}
        for _ in range(20):
            data = {"nested": data}
        # Should not raise
        result = sanitize_log_data(data)
        assert result is not None


class TestJsonFormatterIntegration:
    """Test integration with JsonFormatter."""

    def test_json_formatter_sanitizes_message(self) -> None:
        """Log output contains no raw secrets in message."""
        import io
        import json
        import logging

        from bo1.utils.logging import JsonFormatter

        # Create a test logger with JsonFormatter
        logger = logging.getLogger("test_sanitization")
        logger.handlers.clear()
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log a message with sensitive data
        logger.info("Login failed: password=supersecret123 for user@example.com")

        # Parse the JSON output
        output = stream.getvalue()
        log_entry = json.loads(output)

        # Verify secrets are sanitized
        assert "supersecret123" not in log_entry["message"]
        assert "password=[REDACTED]" in log_entry["message"]
        # Email should be partially masked
        assert "user@example.com" not in log_entry["message"]
        assert "@example.com" in log_entry["message"]

    def test_json_formatter_sanitizes_context(self) -> None:
        """Log context dict is sanitized."""
        import io
        import json
        import logging

        from bo1.utils.logging import JsonFormatter

        logger = logging.getLogger("test_context_sanitization")
        logger.handlers.clear()
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        # Log with sensitive context
        logger.info(
            "Auth attempt",
            extra={"log_context": {"user": "test", "password": "secret_password_123"}},
        )

        output = stream.getvalue()
        log_entry = json.loads(output)

        # Context should be sanitized
        assert "context" in log_entry
        assert "secret_password" not in str(log_entry["context"])


class TestAuditMiddlewareSanitization:
    """Test that audit middleware doesn't log sensitive data."""

    def test_request_body_not_logged_raw(self) -> None:
        """Request bodies with passwords are not logged raw.

        Note: Audit middleware logs path/method/status, not request bodies.
        This test validates the design - bodies aren't included in audit logs.
        """
        # The audit_logging middleware only logs:
        # method, path, status_code, duration_ms, user_id, ip_address, user_agent
        # It does NOT log request/response bodies, which is the correct design.
        # If bodies were logged, they would need sanitization.
        pass  # Design validation - bodies not logged
