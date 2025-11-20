"""Tests for OAuth authentication endpoints.

Tests:
- Google OAuth callback flow
- JWT token refresh
- User creation on first sign-in
- Beta whitelist validation
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException

from backend.api.auth import (
    OAuthCallbackRequest,
    _ensure_user_exists,
    google_oauth_callback,
    refresh_token,
    signout,
)


class TestGoogleOAuthCallback:
    """Test Google OAuth callback endpoint."""

    @pytest.mark.asyncio
    @patch("backend.api.auth.create_client")
    async def test_successful_oauth_callback(self, mock_create_client):
        """Test successful OAuth callback with valid code."""
        # Mock Supabase client response
        mock_session = MagicMock()
        mock_session.access_token = "test_access_token"  # noqa: S105  # Test mock token
        mock_session.refresh_token = "test_refresh_token"  # noqa: S105  # Test mock token
        mock_session.expires_in = 3600

        mock_user = MagicMock()
        mock_user.id = "test_user_123"
        mock_user.email = "test@example.com"
        mock_user.user_metadata = {"subscription_tier": "free"}

        mock_auth_response = MagicMock()
        mock_auth_response.session = mock_session
        mock_auth_response.user = mock_user

        mock_supabase = MagicMock()
        mock_supabase.auth.exchange_code_for_session.return_value = mock_auth_response
        mock_create_client.return_value = mock_supabase

        # Mock user creation
        with patch(
            "backend.api.auth._ensure_user_exists", new_callable=AsyncMock
        ) as mock_ensure_user:
            request = OAuthCallbackRequest(
                code="test_auth_code", redirect_uri="http://localhost:3000/callback"
            )

            response = await google_oauth_callback(request)

            # Assertions
            assert response.access_token == "test_access_token"  # noqa: S105
            assert response.refresh_token == "test_refresh_token"  # noqa: S105
            assert response.expires_in == 3600
            assert response.user["id"] == "test_user_123"
            assert response.user["email"] == "test@example.com"
            assert response.user["auth_provider"] == "google"

            # Verify user was created/updated
            mock_ensure_user.assert_called_once_with(
                user_id="test_user_123", email="test@example.com", auth_provider="google"
            )

    @pytest.mark.asyncio
    @patch("backend.api.auth.create_client")
    async def test_oauth_callback_with_invalid_code(self, mock_create_client):
        """Test OAuth callback with invalid authorization code."""
        # Mock Supabase client to return None (invalid code)
        mock_supabase = MagicMock()
        mock_supabase.auth.exchange_code_for_session.return_value = None
        mock_create_client.return_value = mock_supabase

        request = OAuthCallbackRequest(
            code="invalid_code", redirect_uri="http://localhost:3000/callback"
        )

        with pytest.raises(HTTPException) as exc_info:
            await google_oauth_callback(request)

        assert exc_info.value.status_code == 400
        assert "Invalid or expired" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("backend.api.auth.GOOGLE_OAUTH_CLIENT_ID", "")
    async def test_oauth_callback_without_credentials(self):
        """Test OAuth callback when Google credentials not configured."""
        request = OAuthCallbackRequest(
            code="test_code", redirect_uri="http://localhost:3000/callback"
        )

        with pytest.raises(HTTPException) as exc_info:
            await google_oauth_callback(request)

        assert exc_info.value.status_code == 500
        assert "not configured" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("backend.api.auth.create_client")
    @patch("backend.api.auth.get_settings")
    async def test_oauth_callback_beta_whitelist_block(self, mock_get_settings, mock_create_client):
        """Test OAuth callback blocks non-whitelisted users in closed beta mode."""
        # Mock settings with closed beta enabled
        mock_settings = MagicMock()
        mock_settings.closed_beta_mode = True
        mock_settings.beta_whitelist_emails = {"allowed@example.com"}
        mock_get_settings.return_value = mock_settings

        # Mock successful OAuth response
        mock_session = MagicMock()
        mock_session.access_token = "test_token"  # noqa: S105  # Test mock token
        mock_user = MagicMock()
        mock_user.id = "test_user_123"
        mock_user.email = "notallowed@example.com"  # Not in whitelist
        mock_auth_response = MagicMock()
        mock_auth_response.session = mock_session
        mock_auth_response.user = mock_user

        mock_supabase = MagicMock()
        mock_supabase.auth.exchange_code_for_session.return_value = mock_auth_response
        mock_create_client.return_value = mock_supabase

        request = OAuthCallbackRequest(
            code="test_code", redirect_uri="http://localhost:3000/callback"
        )

        with pytest.raises(HTTPException) as exc_info:
            await google_oauth_callback(request)

        assert exc_info.value.status_code == 403
        assert "closed_beta" in str(exc_info.value.detail)


class TestTokenRefresh:
    """Test JWT token refresh endpoint."""

    @pytest.mark.asyncio
    @patch("backend.api.auth.create_client")
    async def test_successful_token_refresh(self, mock_create_client):
        """Test successful token refresh with valid refresh token."""
        mock_session = MagicMock()
        mock_session.access_token = "new_access_token"  # noqa: S105  # Test mock token
        mock_session.refresh_token = "new_refresh_token"  # noqa: S105  # Test mock token
        mock_session.expires_in = 3600

        mock_user = MagicMock()
        mock_user.id = "test_user_123"
        mock_user.email = "test@example.com"
        mock_user.app_metadata = {"provider": "google"}
        mock_user.user_metadata = {"subscription_tier": "free"}

        mock_auth_response = MagicMock()
        mock_auth_response.session = mock_session
        mock_auth_response.user = mock_user

        mock_supabase = MagicMock()
        mock_supabase.auth.refresh_session.return_value = mock_auth_response
        mock_create_client.return_value = mock_supabase

        response = await refresh_token("valid_refresh_token")

        assert response.access_token == "new_access_token"  # noqa: S105
        assert response.refresh_token == "new_refresh_token"  # noqa: S105
        assert response.expires_in == 3600

    @pytest.mark.asyncio
    @patch("backend.api.auth.create_client")
    async def test_token_refresh_with_invalid_token(self, mock_create_client):
        """Test token refresh with invalid refresh token."""
        mock_supabase = MagicMock()
        mock_supabase.auth.refresh_session.return_value = None
        mock_create_client.return_value = mock_supabase

        with pytest.raises(HTTPException) as exc_info:
            await refresh_token("invalid_token")

        assert exc_info.value.status_code == 401


class TestSignout:
    """Test signout endpoint."""

    @pytest.mark.asyncio
    @patch("backend.api.auth.create_client")
    async def test_successful_signout(self, mock_create_client):
        """Test successful signout."""
        mock_supabase = MagicMock()
        mock_supabase.auth.sign_out.return_value = None
        mock_create_client.return_value = mock_supabase

        response = await signout("valid_access_token")

        assert response["message"] == "Successfully signed out"
        mock_supabase.auth.sign_out.assert_called_once_with("valid_access_token")


class TestEnsureUserExists:
    """Test user creation/update function."""

    @pytest.mark.asyncio
    @patch("backend.api.auth.get_database_session")
    async def test_create_new_user(self, mock_get_db_session):
        """Test creating a new user on first sign-in."""
        # Mock database session
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None  # User doesn't exist

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db_session.return_value.__aexit__ = AsyncMock()

        await _ensure_user_exists(
            user_id="new_user_123", email="newuser@example.com", auth_provider="google"
        )

        # Verify execute was called twice (SELECT + INSERT)
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("backend.api.auth.get_database_session")
    async def test_update_existing_user(self, mock_get_db_session):
        """Test updating an existing user on subsequent sign-ins."""
        # Mock database session
        mock_result = MagicMock()
        mock_result.fetchone.return_value = {"id": "existing_user_123"}  # User exists

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(return_value=mock_result)
        mock_session.commit = AsyncMock()

        mock_get_db_session.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_get_db_session.return_value.__aexit__ = AsyncMock()

        await _ensure_user_exists(
            user_id="existing_user_123", email="existing@example.com", auth_provider="google"
        )

        # Verify execute was called twice (SELECT + UPDATE)
        assert mock_session.execute.call_count == 2
        mock_session.commit.assert_called_once()
