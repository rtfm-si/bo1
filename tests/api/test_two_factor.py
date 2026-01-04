"""Tests for two-factor authentication endpoints.

Validates:
- GET /v1/user/2fa/status returns 2FA status
- POST /v1/user/2fa/setup initiates 2FA setup
- POST /v1/user/2fa/verify-setup completes setup
- POST /v1/user/2fa/disable disables 2FA
- POST /v1/user/2fa/verify verifies TOTP/backup codes
- Rate limiting on verification attempts
- Backup code management
"""

from unittest.mock import MagicMock, patch

import pytest

from backend.api.two_factor import (
    BACKUP_CODE_COUNT,
    BACKUP_CODE_LENGTH,
    MAX_TOTP_ATTEMPTS,
    TOTP_LOCKOUT_MINUTES,
    _generate_backup_codes,
    _hash_backup_code,
    _verify_backup_code,
)


@pytest.mark.unit
class TestBackupCodeGeneration:
    """Test backup code generation utilities."""

    def test_generate_backup_codes_count(self) -> None:
        """Test that correct number of backup codes are generated."""
        codes = _generate_backup_codes()
        assert len(codes) == BACKUP_CODE_COUNT

    def test_generate_backup_codes_length(self) -> None:
        """Test that backup codes have correct length."""
        codes = _generate_backup_codes()
        for code in codes:
            assert len(code) == BACKUP_CODE_LENGTH

    def test_generate_backup_codes_unique(self) -> None:
        """Test that all generated backup codes are unique."""
        codes = _generate_backup_codes()
        assert len(set(codes)) == len(codes)

    def test_generate_backup_codes_alphanumeric(self) -> None:
        """Test that backup codes use only allowed characters."""
        # Allowed alphabet excludes ambiguous chars (0, O, l, I)
        allowed = set("ABCDEFGHJKLMNPQRSTUVWXYZ23456789")
        codes = _generate_backup_codes()
        for code in codes:
            for char in code:
                assert char in allowed


@pytest.mark.unit
class TestBackupCodeHashing:
    """Test backup code hashing and verification."""

    def test_hash_backup_code_deterministic(self) -> None:
        """Test that hashing is deterministic."""
        code = "ABCD1234"
        hash1 = _hash_backup_code(code)
        hash2 = _hash_backup_code(code)
        assert hash1 == hash2

    def test_hash_backup_code_case_insensitive(self) -> None:
        """Test that hashing is case-insensitive."""
        code_upper = "ABCD1234"
        code_lower = "abcd1234"
        assert _hash_backup_code(code_upper) == _hash_backup_code(code_lower)

    def test_hash_backup_code_different_codes(self) -> None:
        """Test that different codes produce different hashes."""
        code1 = "ABCD1234"
        code2 = "EFGH5678"
        assert _hash_backup_code(code1) != _hash_backup_code(code2)

    def test_verify_backup_code_valid(self) -> None:
        """Test that valid code verifies correctly."""
        code = "ABCD1234"
        hashed = _hash_backup_code(code)
        assert _verify_backup_code(code, hashed) is True

    def test_verify_backup_code_case_insensitive(self) -> None:
        """Test that verification is case-insensitive."""
        code = "ABCD1234"
        hashed = _hash_backup_code(code)
        assert _verify_backup_code(code.lower(), hashed) is True

    def test_verify_backup_code_invalid(self) -> None:
        """Test that invalid code fails verification."""
        code = "ABCD1234"
        wrong_code = "WRONG123"
        hashed = _hash_backup_code(code)
        assert _verify_backup_code(wrong_code, hashed) is False


@pytest.mark.unit
class TestRateLimitConstants:
    """Test rate limiting configuration."""

    def test_max_attempts_reasonable(self) -> None:
        """Test that max attempts is reasonable (not too low or high)."""
        assert 3 <= MAX_TOTP_ATTEMPTS <= 10

    def test_lockout_duration_reasonable(self) -> None:
        """Test that lockout duration is reasonable (5-60 minutes)."""
        assert 5 <= TOTP_LOCKOUT_MINUTES <= 60


@pytest.mark.unit
class TestTwoFactorRateLimiting:
    """Test 2FA rate limiting logic."""

    @patch("backend.api.two_factor.db_session")
    def test_check_rate_limit_not_locked(self, mock_db: MagicMock) -> None:
        """Test rate limit check when not locked out."""
        from backend.api.two_factor import _check_totp_rate_limit

        # Mock database to return no lockout
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {
            "totp_failed_attempts": 2,
            "totp_lockout_until": None,
        }
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        is_locked, remaining = _check_totp_rate_limit("test-user")
        assert is_locked is False
        assert remaining == 0

    @patch("backend.api.two_factor.db_session")
    def test_check_rate_limit_user_not_found(self, mock_db: MagicMock) -> None:
        """Test rate limit check when user not found."""
        from backend.api.two_factor import _check_totp_rate_limit

        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None
        mock_conn = MagicMock()
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_db.return_value.__enter__.return_value = mock_conn

        is_locked, remaining = _check_totp_rate_limit("nonexistent-user")
        assert is_locked is False
        assert remaining == 0


@pytest.mark.unit
class TestTwoFactorStatusResponse:
    """Test 2FA status response model."""

    def test_status_response_enabled(self) -> None:
        """Test status response when 2FA is enabled."""
        from backend.api.two_factor import TwoFactorStatusResponse

        response = TwoFactorStatusResponse(
            enabled=True,
            enabled_at="2024-01-01T00:00:00Z",
            backup_codes_remaining=10,
        )
        assert response.enabled is True
        assert response.backup_codes_remaining == 10

    def test_status_response_disabled(self) -> None:
        """Test status response when 2FA is disabled."""
        from backend.api.two_factor import TwoFactorStatusResponse

        response = TwoFactorStatusResponse(
            enabled=False,
            enabled_at=None,
            backup_codes_remaining=0,
        )
        assert response.enabled is False
        assert response.enabled_at is None


@pytest.mark.unit
class TestSetupResponse:
    """Test 2FA setup response model."""

    def test_setup_response_valid(self) -> None:
        """Test setup response with valid data."""
        from backend.api.two_factor import SetupTwoFactorResponse

        backup_codes = _generate_backup_codes()
        response = SetupTwoFactorResponse(
            secret="JBSWY3DPEHPK3PXP",  # noqa: S106 - test data, not real secret
            qr_uri="otpauth://totp/Test?secret=JBSWY3DPEHPK3PXP",
            backup_codes=backup_codes,
        )
        assert len(response.secret) > 0
        assert response.qr_uri.startswith("otpauth://")
        assert len(response.backup_codes) == BACKUP_CODE_COUNT


@pytest.mark.unit
class TestVerifyResponse:
    """Test 2FA verification response models."""

    def test_verify_setup_response(self) -> None:
        """Test verify setup response."""
        from backend.api.two_factor import VerifySetupResponse

        response = VerifySetupResponse(
            success=True,
            message="2FA enabled",
        )
        assert response.success is True

    def test_verify_totp_response_regular(self) -> None:
        """Test verify TOTP response for regular code."""
        from backend.api.two_factor import VerifyTwoFactorResponse

        response = VerifyTwoFactorResponse(
            success=True,
            used_backup_code=False,
            backup_codes_remaining=None,
        )
        assert response.used_backup_code is False

    def test_verify_totp_response_backup_code(self) -> None:
        """Test verify TOTP response for backup code."""
        from backend.api.two_factor import VerifyTwoFactorResponse

        response = VerifyTwoFactorResponse(
            success=True,
            used_backup_code=True,
            backup_codes_remaining=9,
        )
        assert response.used_backup_code is True
        assert response.backup_codes_remaining == 9


@pytest.mark.unit
class TestDisableResponse:
    """Test 2FA disable response model."""

    def test_disable_response_success(self) -> None:
        """Test disable response on success."""
        from backend.api.two_factor import DisableTwoFactorResponse

        response = DisableTwoFactorResponse(
            success=True,
            message="2FA disabled",
        )
        assert response.success is True

    def test_disable_response_failure(self) -> None:
        """Test disable response on failure."""
        from backend.api.two_factor import DisableTwoFactorResponse

        response = DisableTwoFactorResponse(
            success=False,
            message="Invalid password",
        )
        assert response.success is False


@pytest.mark.unit
class TestSetupTwoFactorUserSync:
    """Test 2FA setup user synchronization (ISS-003 fix).

    These tests verify the user existence check and UPDATE row count handling
    that were added to fix ISS-003 (500 error when user not in local DB).
    """

    def test_ensure_exists_import_and_call_pattern(self) -> None:
        """Test that ensure_exists is called with user_id and email."""
        # This is a simpler unit test that verifies the code path exists
        # Integration testing of the full flow happens in e2e tests

        # Read the source code to verify the pattern
        import inspect

        from backend.api import two_factor

        source = inspect.getsource(two_factor.setup_two_factor)

        # Verify the ensure_exists call is present with correct pattern
        assert "user_repository.ensure_exists(user_id, email)" in source
        assert "if not user_repository.ensure_exists" in source

    def test_update_returning_check_exists(self) -> None:
        """Test that UPDATE uses RETURNING and checks for None."""
        import inspect

        from backend.api import two_factor

        source = inspect.getsource(two_factor.setup_two_factor)

        # Verify RETURNING clause is used
        assert "RETURNING id" in source

        # Verify None check for 0 rows
        assert "if not row:" in source
        assert "UPDATE totp_backup_codes affected 0 rows" in source

    def test_error_messages_are_user_friendly(self) -> None:
        """Test that error messages provide clear guidance."""
        import inspect

        from backend.api import two_factor

        source = inspect.getsource(two_factor.setup_two_factor)

        # Verify user-friendly error messages
        assert "Failed to initialize account" in source
        assert "Account setup incomplete" in source
        assert "sign out and sign in again" in source
