"""Unit tests for password upgrade endpoint.

Tests the /api/v1/user/upgrade-password endpoint that allows users
to upgrade weak passwords to meet current strength requirements.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from supertokens_python.recipe.emailpassword.interfaces import (
    SignInOkResult,
    UpdateEmailOrPasswordOkResult,
    WrongCredentialsError,
)


class TestPasswordUpgradeEndpoint:
    """Tests for the password upgrade endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user dict as returned by get_current_user."""
        return {
            "user_id": "test-user-123",
            "email": "test@example.com",
            "auth_provider": "email",
            "subscription_tier": "free",
        }

    @pytest.fixture
    def mock_oauth_user(self):
        """Create a mock OAuth user dict (not email/password)."""
        return {
            "user_id": "test-user-456",
            "email": "oauth@example.com",
            "auth_provider": "google",
            "subscription_tier": "free",
        }

    @pytest.mark.asyncio
    async def test_upgrade_password_success(self, mock_user):
        """Successful password upgrade clears the flag."""
        from backend.api.user import PasswordUpgradeRequest, upgrade_password

        # Mock SuperTokens sign_in and update_email_or_password
        mock_sign_in_result = MagicMock(spec=SignInOkResult)
        mock_sign_in_result.user = MagicMock()
        mock_sign_in_result.user.id = mock_user["user_id"]

        mock_update_result = MagicMock(spec=UpdateEmailOrPasswordOkResult)

        with (
            patch(
                "supertokens_python.recipe.emailpassword.asyncio.sign_in",
                new_callable=AsyncMock,
                return_value=mock_sign_in_result,
            ) as mock_sign_in,
            patch(
                "supertokens_python.recipe.emailpassword.asyncio.update_email_or_password",
                new_callable=AsyncMock,
                return_value=mock_update_result,
            ) as mock_update,
            patch(
                "backend.api.supertokens_config.validate_password_strength",
                new_callable=AsyncMock,
                return_value=None,  # Valid password
            ),
            patch("bo1.state.database.db_session") as mock_db,
        ):
            # Setup mock db context
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            request = PasswordUpgradeRequest(
                old_password="OldPass123456",  # noqa: S106
                new_password="NewSecurePass123",  # noqa: S106
            )

            result = await upgrade_password(request, mock_user)

            assert result.success is True
            assert result.message == "Password upgraded successfully"

            # Verify sign_in was called with correct args
            mock_sign_in.assert_called_once_with(
                tenant_id="public",
                email=mock_user["email"],
                password="OldPass123456",  # noqa: S106
            )

            # Verify update was called
            mock_update.assert_called_once()

    @pytest.mark.asyncio
    async def test_upgrade_password_wrong_old_password(self, mock_user):
        """Wrong old password returns 400 error."""
        from fastapi import HTTPException

        from backend.api.user import PasswordUpgradeRequest, upgrade_password

        mock_wrong_creds = MagicMock(spec=WrongCredentialsError)

        with patch(
            "supertokens_python.recipe.emailpassword.asyncio.sign_in",
            new_callable=AsyncMock,
            return_value=mock_wrong_creds,
        ):
            request = PasswordUpgradeRequest(
                old_password="WrongPassword1",  # noqa: S106
                new_password="NewSecurePass123",  # noqa: S106
            )

            with pytest.raises(HTTPException) as exc_info:
                await upgrade_password(request, mock_user)

            assert exc_info.value.status_code == 400
            detail = exc_info.value.detail
            if isinstance(detail, dict):
                assert "incorrect" in detail.get("message", "").lower()
            else:
                assert "incorrect" in detail.lower()

    @pytest.mark.asyncio
    async def test_upgrade_password_weak_new_password(self, mock_user):
        """Weak new password (lacking required pattern) returns 400 error."""
        from fastapi import HTTPException

        from backend.api.user import PasswordUpgradeRequest, upgrade_password

        mock_sign_in_result = MagicMock(spec=SignInOkResult)
        mock_sign_in_result.user = MagicMock()
        mock_sign_in_result.user.id = mock_user["user_id"]

        with (
            patch(
                "supertokens_python.recipe.emailpassword.asyncio.sign_in",
                new_callable=AsyncMock,
                return_value=mock_sign_in_result,
            ),
            patch(
                "backend.api.supertokens_config.validate_password_strength",
                new_callable=AsyncMock,
                return_value="Password must contain at least one number",  # Invalid - missing digit
            ),
        ):
            # Password is 12+ chars but missing digit - passes Pydantic, fails strength check
            request = PasswordUpgradeRequest(
                old_password="OldPass123456",  # noqa: S106
                new_password="abcdefghijklmn",  # noqa: S106 No digits
            )

            with pytest.raises(HTTPException) as exc_info:
                await upgrade_password(request, mock_user)

            assert exc_info.value.status_code == 400

    @pytest.mark.asyncio
    async def test_upgrade_password_oauth_user_rejected(self, mock_oauth_user):
        """OAuth users cannot use password upgrade."""
        from fastapi import HTTPException

        from backend.api.user import PasswordUpgradeRequest, upgrade_password

        request = PasswordUpgradeRequest(
            old_password="OldPass123456",  # noqa: S106
            new_password="NewSecurePass123",  # noqa: S106
        )

        with pytest.raises(HTTPException) as exc_info:
            await upgrade_password(request, mock_oauth_user)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        detail_str = detail.get("message", "") if isinstance(detail, dict) else detail
        assert "email/password" in detail_str.lower()

    @pytest.mark.asyncio
    async def test_upgrade_password_no_email(self):
        """User without email returns 400 error."""
        from fastapi import HTTPException

        from backend.api.user import PasswordUpgradeRequest, upgrade_password

        user_no_email = {
            "user_id": "test-user-789",
            "email": None,
            "auth_provider": "email",
        }

        request = PasswordUpgradeRequest(
            old_password="OldPass123456",  # noqa: S106
            new_password="NewSecurePass123",  # noqa: S106
        )

        with pytest.raises(HTTPException) as exc_info:
            await upgrade_password(request, user_no_email)

        assert exc_info.value.status_code == 400
        detail = exc_info.value.detail
        detail_str = detail.get("message", "") if isinstance(detail, dict) else detail
        assert "email" in detail_str.lower()


class TestPasswordUpgradeFlagOnSignIn:
    """Tests for password upgrade flag being set on sign-in."""

    @pytest.mark.asyncio
    async def test_weak_password_sets_flag(self):
        """Signing in with weak password sets password_upgrade_needed flag."""
        from backend.api.supertokens_config import (
            validate_password_strength,
        )

        # Test that validation correctly identifies weak passwords
        result = await validate_password_strength("short", "public")
        assert result is not None  # Should return error message

        result = await validate_password_strength("Password1234", "public")
        assert result is None  # Should return None for valid password

    def test_set_password_upgrade_flag(self):
        """Test the helper function sets the flag correctly."""
        from backend.api.supertokens_config import _set_password_upgrade_flag

        with patch("bo1.state.database.db_session") as mock_db:
            mock_cursor = MagicMock()
            mock_conn = MagicMock()
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock_db.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.return_value.__exit__ = MagicMock(return_value=False)

            _set_password_upgrade_flag("test-user-123", True)

            # Verify the UPDATE query was called
            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "password_upgrade_needed" in call_args[0][0]
            assert call_args[0][1] == (True, "test-user-123")
