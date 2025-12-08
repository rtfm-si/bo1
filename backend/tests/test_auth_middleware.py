"""Tests for auth middleware (backend/api/middleware/auth.py)."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException


class TestRequireAuth:
    """Tests for require_auth() function."""

    def test_passes_valid_user(self):
        """require_auth returns user when user_id present."""
        from backend.api.middleware.auth import require_auth

        user = {"user_id": "test_123", "email": "test@example.com"}
        result = require_auth(user)
        assert result == user

    def test_raises_on_missing_user_id(self):
        """require_auth raises 401 when user_id missing."""
        from backend.api.middleware.auth import require_auth

        with pytest.raises(HTTPException) as exc_info:
            require_auth({"email": "test@example.com"})
        assert exc_info.value.status_code == 401
        assert "Authentication required" in exc_info.value.detail

    def test_raises_on_none_user(self):
        """require_auth raises 401 when user is None."""
        from backend.api.middleware.auth import require_auth

        with pytest.raises(HTTPException) as exc_info:
            require_auth(None)
        assert exc_info.value.status_code == 401

    def test_raises_on_empty_dict(self):
        """require_auth raises 401 when user is empty dict."""
        from backend.api.middleware.auth import require_auth

        with pytest.raises(HTTPException) as exc_info:
            require_auth({})
        assert exc_info.value.status_code == 401


class TestMvpMode:
    """Tests for MVP mode authentication."""

    @pytest.mark.asyncio
    async def test_mvp_returns_hardcoded_user_in_debug(self):
        """MVP mode returns hardcoded user when DEBUG=true."""
        with patch.dict("os.environ", {"DEBUG": "true"}):
            # Need to reload module to pick up env change
            import backend.api.middleware.auth as auth_module

            # Patch DEBUG_MODE directly since module already loaded
            with patch.object(auth_module, "DEBUG_MODE", True):
                result = await auth_module._get_current_user_mvp()

                assert result["user_id"] == "test_user_1"
                assert result["email"] == "test_user_1@test.com"
                assert result["role"] == "authenticated"
                assert result["subscription_tier"] == "free"
                assert result["is_admin"] is False

    @pytest.mark.asyncio
    async def test_mvp_rejects_non_debug(self):
        """MVP mode raises 500 when DEBUG=false (security guard)."""
        import backend.api.middleware.auth as auth_module

        with patch.object(auth_module, "DEBUG_MODE", False):
            with pytest.raises(HTTPException) as exc_info:
                await auth_module._get_current_user_mvp()

            assert exc_info.value.status_code == 500
            assert "misconfigured" in exc_info.value.detail.lower()


class TestSessionAuth:
    """Tests for SuperTokens session authentication."""

    @pytest.mark.asyncio
    async def test_session_auth_returns_user_data(self):
        """Session auth returns user data from valid session."""
        import backend.api.middleware.auth as auth_module

        mock_session = MagicMock()
        mock_session.get_user_id.return_value = "supertokens_user_123"
        mock_session.get_handle.return_value = "session_handle_abc"

        mock_user_data = {
            "email": "user@example.com",
            "subscription_tier": "pro",
            "is_admin": True,
        }

        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_user_data

        with patch("bo1.state.repositories.user_repository", mock_repo):
            # Call the function directly, passing session explicitly
            result = await auth_module._get_current_user_with_session(session=mock_session)

            assert result["user_id"] == "supertokens_user_123"
            assert result["email"] == "user@example.com"
            assert result["subscription_tier"] == "pro"
            assert result["is_admin"] is True
            assert result["session_handle"] == "session_handle_abc"

    @pytest.mark.asyncio
    async def test_session_auth_raises_on_exception(self):
        """Session auth raises 401 when session fails."""
        import backend.api.middleware.auth as auth_module

        mock_session = MagicMock()
        mock_session.get_user_id.side_effect = Exception("Session expired")

        with pytest.raises(HTTPException) as exc_info:
            await auth_module._get_current_user_with_session(session=mock_session)

        assert exc_info.value.status_code == 401
        assert "Authentication failed" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_session_auth_handles_missing_user_data(self):
        """Session auth handles case when user not in database."""
        import backend.api.middleware.auth as auth_module

        mock_session = MagicMock()
        mock_session.get_user_id.return_value = "new_user_123"
        mock_session.get_handle.return_value = "session_handle"

        mock_repo = MagicMock()
        mock_repo.get.return_value = None  # User not in DB

        with patch("bo1.state.repositories.user_repository", mock_repo):
            result = await auth_module._get_current_user_with_session(session=mock_session)

            assert result["user_id"] == "new_user_123"
            assert result["email"] is None
            assert result["subscription_tier"] == "free"
            assert result["is_admin"] is False


class TestProductionAuth:
    """Tests for production auth validation."""

    def test_production_auth_raises_when_misconfigured(self):
        """require_production_auth raises RuntimeError in production without auth."""
        import backend.api.middleware.auth as auth_module

        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch.object(auth_module, "get_settings", return_value=mock_settings):
            with patch.object(auth_module, "ENABLE_SUPERTOKENS_AUTH", False):
                with pytest.raises(RuntimeError) as exc_info:
                    auth_module.require_production_auth()

                assert "SECURITY VIOLATION" in str(exc_info.value)

    def test_production_auth_passes_when_auth_enabled(self):
        """require_production_auth passes when SuperTokens enabled."""
        import backend.api.middleware.auth as auth_module

        mock_settings = MagicMock()
        mock_settings.debug = False

        with patch.object(auth_module, "get_settings", return_value=mock_settings):
            with patch.object(auth_module, "ENABLE_SUPERTOKENS_AUTH", True):
                # Should not raise
                auth_module.require_production_auth()

    def test_production_auth_passes_in_debug_mode(self):
        """require_production_auth passes in debug mode."""
        import backend.api.middleware.auth as auth_module

        mock_settings = MagicMock()
        mock_settings.debug = True

        with patch.object(auth_module, "get_settings", return_value=mock_settings):
            with patch.object(auth_module, "ENABLE_SUPERTOKENS_AUTH", False):
                # Should not raise even without auth
                auth_module.require_production_auth()


class TestAdminAuth:
    """Tests for admin authentication."""

    @pytest.mark.asyncio
    async def test_admin_mvp_returns_user(self):
        """Admin MVP mode returns user with admin access."""
        import backend.api.middleware.auth as auth_module

        with patch.object(auth_module, "DEBUG_MODE", True):
            result = await auth_module._require_admin_mvp()

            assert result["user_id"] == "test_user_1"
            assert result["role"] == "authenticated"

    @pytest.mark.asyncio
    async def test_admin_session_rejects_non_admin(self):
        """Admin session auth raises 403 for non-admin user."""
        import backend.api.middleware.auth as auth_module

        mock_session = MagicMock()
        mock_session.get_user_id.return_value = "regular_user"
        mock_session.get_handle.return_value = "handle"

        mock_user_data = {"email": "user@example.com", "is_admin": False}

        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_user_data

        with patch("bo1.state.repositories.user_repository", mock_repo):
            with pytest.raises(HTTPException) as exc_info:
                await auth_module._require_admin_with_session(session=mock_session)

            assert exc_info.value.status_code == 403
            assert "Admin access required" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_admin_session_allows_admin(self):
        """Admin session auth returns user for admin."""
        import backend.api.middleware.auth as auth_module

        mock_session = MagicMock()
        mock_session.get_user_id.return_value = "admin_user"
        mock_session.get_handle.return_value = "handle"

        mock_user_data = {
            "email": "admin@example.com",
            "is_admin": True,
            "subscription_tier": "enterprise",
        }

        mock_repo = MagicMock()
        mock_repo.get.return_value = mock_user_data

        with patch("bo1.state.repositories.user_repository", mock_repo):
            result = await auth_module._require_admin_with_session(session=mock_session)

            assert result["user_id"] == "admin_user"
            assert result["is_admin"] is True
