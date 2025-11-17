"""Security tests for backend code review fixes.

Tests for:
- SQL injection prevention
- Session ID validation
- User ID validation
- API key logging
"""

import pytest
from fastapi import HTTPException

from backend.api.utils.validation import validate_cache_id, validate_session_id, validate_user_id
from bo1.state.postgres_manager import find_cached_research, get_stale_research_cache_entries


class TestSessionIDValidation:
    """Test session ID validation prevents injection."""

    def test_valid_session_id(self):
        """Valid UUID format should pass."""
        valid_id = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_session_id(valid_id) == valid_id.lower()

    def test_valid_session_id_with_prefix(self):
        """Valid UUID with bo1_ prefix should pass."""
        valid_id = "bo1_550e8400-e29b-41d4-a716-446655440000"
        assert validate_session_id(valid_id) == valid_id.lower()

    def test_invalid_session_id_sql_injection(self):
        """SQL injection attempt should be rejected."""
        malicious_id = "'; DROP TABLE sessions;--"

        with pytest.raises(HTTPException) as exc_info:
            validate_session_id(malicious_id)

        assert exc_info.value.status_code == 400
        assert "Invalid session ID format" in exc_info.value.detail

    def test_invalid_session_id_path_traversal(self):
        """Path traversal attempt should be rejected."""
        malicious_id = "../../etc/passwd"

        with pytest.raises(HTTPException) as exc_info:
            validate_session_id(malicious_id)

        assert exc_info.value.status_code == 400

    def test_invalid_session_id_script_injection(self):
        """Script injection attempt should be rejected."""
        malicious_id = "<script>alert('xss')</script>"

        with pytest.raises(HTTPException) as exc_info:
            validate_session_id(malicious_id)

        assert exc_info.value.status_code == 400


class TestUserIDValidation:
    """Test user ID validation prevents injection."""

    def test_valid_user_id_alphanumeric(self):
        """Valid alphanumeric user ID should pass."""
        valid_id = "test_user_1"
        assert validate_user_id(valid_id) == valid_id

    def test_valid_user_id_email(self):
        """Valid email-style user ID should pass."""
        valid_id = "user@example.com"
        assert validate_user_id(valid_id) == valid_id

    def test_invalid_user_id_sql_injection(self):
        """SQL injection attempt should be rejected."""
        malicious_id = "admin'; DROP TABLE users;--"

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id(malicious_id)

        assert exc_info.value.status_code == 400
        assert "Invalid user ID format" in exc_info.value.detail

    def test_invalid_user_id_special_chars(self):
        """Disallowed special characters should be rejected."""
        malicious_id = "user$%^&*()"

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id(malicious_id)

        assert exc_info.value.status_code == 400

    def test_invalid_user_id_too_long(self):
        """User ID exceeding 255 chars should be rejected."""
        malicious_id = "a" * 256

        with pytest.raises(HTTPException) as exc_info:
            validate_user_id(malicious_id)

        assert exc_info.value.status_code == 400


class TestCacheIDValidation:
    """Test cache ID validation prevents injection."""

    def test_valid_cache_id(self):
        """Valid UUID should pass."""
        valid_id = "550e8400-e29b-41d4-a716-446655440000"
        assert validate_cache_id(valid_id) == valid_id.lower()

    def test_invalid_cache_id_with_prefix(self):
        """UUID with prefix should be rejected (cache IDs don't have prefixes)."""
        invalid_id = "bo1_550e8400-e29b-41d4-a716-446655440000"

        with pytest.raises(HTTPException) as exc_info:
            validate_cache_id(invalid_id)

        assert exc_info.value.status_code == 400

    def test_invalid_cache_id_sql_injection(self):
        """SQL injection attempt should be rejected."""
        malicious_id = "'; DELETE FROM research_cache;--"

        with pytest.raises(HTTPException) as exc_info:
            validate_cache_id(malicious_id)

        assert exc_info.value.status_code == 400


class TestSQLInjectionPrevention:
    """Test SQL injection prevention in database queries."""

    def test_max_age_days_integer_validation(self):
        """max_age_days must be a positive integer."""
        # Test with string (potential injection)
        with pytest.raises(ValueError) as exc_info:
            find_cached_research(
                question_embedding=[0.1] * 1024,
                max_age_days="90; DROP TABLE research_cache;--",  # type: ignore[arg-type]
            )

        assert "must be a positive integer" in str(exc_info.value)

    def test_max_age_days_negative_validation(self):
        """Negative max_age_days should be rejected."""
        with pytest.raises(ValueError) as exc_info:
            find_cached_research(
                question_embedding=[0.1] * 1024,
                max_age_days=-1,
            )

        assert "must be a positive integer" in str(exc_info.value)

    def test_days_old_integer_validation(self):
        """days_old must be a positive integer."""
        # Test with string (potential injection)
        with pytest.raises(ValueError) as exc_info:
            get_stale_research_cache_entries(
                days_old="90; DROP TABLE research_cache;--",  # type: ignore[arg-type]
            )

        assert "must be a positive integer" in str(exc_info.value)

    def test_days_old_negative_validation(self):
        """Negative days_old should be rejected."""
        with pytest.raises(ValueError) as exc_info:
            get_stale_research_cache_entries(days_old=-1)

        assert "must be a positive integer" in str(exc_info.value)


class TestAPIKeySecurity:
    """Test API key logging is prevented."""

    def test_admin_key_not_logged(self, caplog, monkeypatch):
        """Admin API key should not appear in logs."""
        # Set a valid admin key in environment for this test
        monkeypatch.setenv("ADMIN_API_KEY", "valid_admin_key_12345")

        # Need to reload the module to pick up the new env var
        import importlib

        from backend.api.middleware import admin

        importlib.reload(admin)

        # Test invalid key - should not log the key itself
        with pytest.raises(HTTPException):
            admin.require_admin(x_admin_key="secret_key_12345")

        # Check logs don't contain the actual key
        assert "secret_key_12345" not in caplog.text
        assert "Invalid admin API key attempted" in caplog.text


# Mark tests that require database connection
pytestmark = pytest.mark.integration
