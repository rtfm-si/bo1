"""Unit tests for password validation.

Tests the validate_password_strength function used by SuperTokens
for enforcing password requirements during sign-up.
"""

import pytest

from backend.api.supertokens_config import (
    MIN_PASSWORD_LENGTH,
    PASSWORD_REQUIREMENTS_MSG,
    validate_password_strength,
)


class TestPasswordValidation:
    """Tests for validate_password_strength function."""

    @pytest.mark.asyncio
    async def test_short_password_rejected(self):
        """Passwords shorter than MIN_PASSWORD_LENGTH are rejected."""
        result = await validate_password_strength("short1", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_exactly_min_length_minus_one_rejected(self):
        """Password with exactly MIN_PASSWORD_LENGTH-1 chars is rejected."""
        # 11 characters: letters + number
        password = "a" * 10 + "1"
        assert len(password) == MIN_PASSWORD_LENGTH - 1
        result = await validate_password_strength(password, "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_letters_only_rejected(self):
        """Passwords with only letters (no numbers) are rejected."""
        # 12+ letters, no digits
        result = await validate_password_strength("abcdefghijkl", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_numbers_only_rejected(self):
        """Passwords with only numbers (no letters) are rejected."""
        # 12+ digits, no letters
        result = await validate_password_strength("123456789012", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_valid_password_accepted(self):
        """Valid password with letters, numbers, and sufficient length passes."""
        result = await validate_password_strength("Password1234", "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_exactly_min_length_accepted(self):
        """Password with exactly MIN_PASSWORD_LENGTH chars passes if it has letters+numbers."""
        # 12 characters: 11 letters + 1 digit
        password = "a" * 11 + "1"
        assert len(password) == MIN_PASSWORD_LENGTH
        result = await validate_password_strength(password, "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_long_valid_password_accepted(self):
        """Long passwords meeting requirements pass."""
        result = await validate_password_strength("ThisIsAVeryLongPassword123", "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_special_chars_allowed(self):
        """Passwords with special characters are accepted if they also have letters+numbers."""
        result = await validate_password_strength("P@ssw0rd!2345", "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_unicode_letters_accepted(self):
        """Unicode letters count as letters."""
        # 12 chars: unicode letters + digit
        result = await validate_password_strength("Пароль123456", "public")  # Russian "Password"
        assert result is None

    @pytest.mark.asyncio
    async def test_spaces_allowed(self):
        """Passwords with spaces are accepted if meeting requirements."""
        result = await validate_password_strength("Pass word 1234", "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_mixed_case_accepted(self):
        """Mixed case passwords meeting requirements pass."""
        result = await validate_password_strength("AbCdEfGhIj12", "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_leading_numbers_accepted(self):
        """Passwords starting with numbers are accepted if meeting requirements."""
        result = await validate_password_strength("123Password45", "public")
        assert result is None

    @pytest.mark.asyncio
    async def test_only_special_chars_rejected(self):
        """Passwords with only special characters (no letters/numbers) are rejected."""
        result = await validate_password_strength("!@#$%^&*()_+", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_special_chars_and_numbers_rejected(self):
        """Passwords with special chars and numbers but no letters are rejected."""
        result = await validate_password_strength("!@#$1234567!", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_special_chars_and_letters_rejected(self):
        """Passwords with special chars and letters but no numbers are rejected."""
        result = await validate_password_strength("!@#$abcdefg!", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_empty_password_rejected(self):
        """Empty password is rejected."""
        result = await validate_password_strength("", "public")
        assert result == PASSWORD_REQUIREMENTS_MSG

    @pytest.mark.asyncio
    async def test_tenant_id_ignored(self):
        """Different tenant_id values don't affect validation."""
        # Same password should give same result regardless of tenant
        result1 = await validate_password_strength("Password1234", "tenant1")
        result2 = await validate_password_strength("Password1234", "tenant2")
        assert result1 is None
        assert result2 is None

        result3 = await validate_password_strength("short", "tenant1")
        result4 = await validate_password_strength("short", "tenant2")
        assert result3 == PASSWORD_REQUIREMENTS_MSG
        assert result4 == PASSWORD_REQUIREMENTS_MSG
