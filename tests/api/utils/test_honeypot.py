"""Unit tests for honeypot validation utility."""

import pytest
from fastapi import HTTPException

from backend.api.utils.honeypot import (
    HoneypotMixin,
    validate_honeypot_field,
    validate_honeypot_fields,
)


class TestValidateHoneypotField:
    """Test individual honeypot field validation."""

    def test_none_is_clean(self):
        """None value should be considered clean."""
        assert validate_honeypot_field(None) is True

    def test_empty_string_is_clean(self):
        """Empty string should be considered clean."""
        assert validate_honeypot_field("") is True

    def test_whitespace_only_is_clean(self):
        """Whitespace-only string should be considered clean."""
        assert validate_honeypot_field("   ") is True
        assert validate_honeypot_field("\t\n") is True

    def test_value_is_triggered(self):
        """Any actual value should trigger the honeypot."""
        assert validate_honeypot_field("test@example.com") is False
        assert validate_honeypot_field("http://spam.com") is False
        assert validate_honeypot_field("123-456-7890") is False
        assert validate_honeypot_field("a") is False


class TestHoneypotMixin:
    """Test HoneypotMixin pydantic model."""

    def test_mixin_accepts_empty_fields(self):
        """Mixin should accept None/empty values."""

        class TestModel(HoneypotMixin):
            name: str

        model = TestModel(name="test")
        assert model.hp_email is None
        assert model.hp_url is None
        assert model.hp_phone is None

    def test_mixin_accepts_values_via_alias(self):
        """Mixin should accept values via _hp_ alias."""

        class TestModel(HoneypotMixin):
            name: str

        model = TestModel(name="test", _hp_email="bot@spam.com")
        assert model.hp_email == "bot@spam.com"


class TestValidateHoneypotFields:
    """Test full honeypot validation on request bodies."""

    def test_clean_request_passes(self):
        """Request with no honeypot values should pass."""

        class TestRequest(HoneypotMixin):
            message: str

        body = TestRequest(message="Hello")
        # Should not raise
        validate_honeypot_fields(body, "test_endpoint")

    def test_email_honeypot_triggers_400(self):
        """Filled email honeypot should raise 400."""

        class TestRequest(HoneypotMixin):
            message: str

        body = TestRequest(message="Hello", _hp_email="spam@bot.com")

        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(body, "test_endpoint")

        assert exc_info.value.status_code == 400
        assert exc_info.value.detail == "Invalid request"

    def test_url_honeypot_triggers_400(self):
        """Filled URL honeypot should raise 400."""

        class TestRequest(HoneypotMixin):
            message: str

        body = TestRequest(message="Hello", _hp_url="http://spam.com")

        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(body, "test_endpoint")

        assert exc_info.value.status_code == 400

    def test_phone_honeypot_triggers_400(self):
        """Filled phone honeypot should raise 400."""

        class TestRequest(HoneypotMixin):
            message: str

        body = TestRequest(message="Hello", _hp_phone="555-1234")

        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(body, "test_endpoint")

        assert exc_info.value.status_code == 400

    def test_multiple_honeypots_triggers_400(self):
        """Multiple filled honeypots should still raise 400."""

        class TestRequest(HoneypotMixin):
            message: str

        body = TestRequest(
            message="Hello",
            _hp_email="spam@bot.com",
            _hp_url="http://spam.com",
        )

        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(body, "test_endpoint")

        assert exc_info.value.status_code == 400

    def test_generic_error_message(self):
        """Error message should be generic to not reveal detection method."""

        class TestRequest(HoneypotMixin):
            message: str

        body = TestRequest(message="Hello", _hp_email="spam@bot.com")

        with pytest.raises(HTTPException) as exc_info:
            validate_honeypot_fields(body, "test_endpoint")

        # Should not mention "honeypot" or specific field
        assert "honeypot" not in exc_info.value.detail.lower()
        assert "_hp_" not in exc_info.value.detail
