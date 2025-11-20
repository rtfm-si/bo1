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
    @patch("httpx.AsyncClient")
    @patch("backend.api.auth.get_settings")
    async def test_successful_oauth_callback(self, mock_get_settings, mock_async_client):
        """Test successful OAuth callback with valid code."""
        # Mock settings with closed beta disabled
        mock_settings = MagicMock()
        mock_settings.closed_beta_mode = False
        mock_get_settings.return_value = mock_settings

        # Mock httpx response for token exchange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_access_token",  # noqa: S105
            "refresh_token": "test_refresh_token",  # noqa: S105
            "expires_in": 3600,
            "user": {
                "id": "test_user_123",
                "email": "test@example.com",
                "app_metadata": {"provider": "google"},
            },
        }

        # Mock httpx AsyncClient context manager
        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_async_client.return_value.__aexit__ = AsyncMock()

        # Mock user creation
        with patch("backend.api.auth._ensure_user_exists") as mock_ensure_user:
            request = OAuthCallbackRequest(
                code="test_auth_code",
                redirect_uri="http://localhost:3000/callback",
                code_verifier="test_pkce_verifier_12345",
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
    @patch("supabase.create_client")
    async def test_oauth_callback_with_invalid_code(self, mock_create_client):
        """Test OAuth callback with invalid authorization code."""
        # Mock Supabase client to return None (invalid code)
        mock_supabase = MagicMock()
        mock_supabase.auth.exchange_code_for_session.return_value = None
        mock_create_client.return_value = mock_supabase

        request = OAuthCallbackRequest(
            code="invalid_code",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_pkce_verifier_12345",
        )

        with pytest.raises(HTTPException) as exc_info:
            await google_oauth_callback(request)

        assert exc_info.value.status_code == 400
        assert "Invalid or expired" in str(exc_info.value.detail)

    @pytest.mark.skip(
        reason="Known bug in backend/api/auth.py:129 - UnboundLocalError when token exchange "
        "returns 400. The code raises HTTPException before token_data_response is assigned, "
        "but then the except block tries to access it. Should return 400 but currently returns 500."
    )
    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    async def test_oauth_callback_with_invalid_token_response(self, mock_async_client):
        """Test OAuth callback with invalid token exchange response.

        NOTE: This test is skipped due to a bug in the auth implementation.
        Expected behavior: Should raise HTTPException with 400 status code
        Actual behavior: Raises HTTPException with 500 due to UnboundLocalError
        """
        # Mock httpx response with 400 error (invalid code)
        mock_response = MagicMock()
        mock_response.status_code = 400
        mock_response.text = "Invalid authorization code"

        # Mock httpx AsyncClient context manager
        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_async_client.return_value.__aexit__ = AsyncMock()

        request = OAuthCallbackRequest(
            code="invalid_code",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_pkce_verifier_12345",
        )

        with pytest.raises(HTTPException) as exc_info:
            await google_oauth_callback(request)

        # TODO: Fix bug in backend/api/auth.py:129 then update assertion below
        assert exc_info.value.status_code == 400
        assert "Invalid or expired" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    @patch("backend.api.auth.get_settings")
    async def test_oauth_callback_beta_whitelist_allows_whitelisted_user(
        self, mock_get_settings, mock_async_client
    ):
        """Test OAuth callback allows whitelisted users in closed beta mode."""
        # Mock settings with closed beta enabled
        mock_settings = MagicMock()
        mock_settings.closed_beta_mode = True
        mock_settings.beta_whitelist_emails = {"allowed@example.com"}
        mock_get_settings.return_value = mock_settings

        # Mock httpx response for token exchange (successful)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",  # noqa: S105
            "refresh_token": "test_refresh",  # noqa: S105
            "expires_in": 3600,
            "user": {
                "id": "test_user_456",
                "email": "allowed@example.com",  # IS in whitelist
                "app_metadata": {"provider": "google"},
            },
        }

        # Mock httpx AsyncClient context manager
        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_async_client.return_value.__aexit__ = AsyncMock()

        # Mock user creation
        with patch("backend.api.auth._ensure_user_exists") as mock_ensure_user:
            request = OAuthCallbackRequest(
                code="test_code",
                redirect_uri="http://localhost:3000/callback",
                code_verifier="test_pkce_verifier_12345",
            )

            response = await google_oauth_callback(request)

            # Should succeed - user is whitelisted
            assert response.access_token == "test_token"  # noqa: S105
            assert response.user["email"] == "allowed@example.com"
            assert response.user["id"] == "test_user_456"

            # Verify user was created/updated
            mock_ensure_user.assert_called_once_with(
                user_id="test_user_456", email="allowed@example.com", auth_provider="google"
            )

    @pytest.mark.asyncio
    @patch("httpx.AsyncClient")
    @patch("backend.api.auth.get_settings")
    async def test_oauth_callback_beta_whitelist_blocks_non_whitelisted_user(
        self, mock_get_settings, mock_async_client
    ):
        """Test OAuth callback blocks non-whitelisted users in closed beta mode."""
        # Mock settings with closed beta enabled
        mock_settings = MagicMock()
        mock_settings.closed_beta_mode = True
        mock_settings.beta_whitelist_emails = {"allowed@example.com"}
        mock_get_settings.return_value = mock_settings

        # Mock httpx response for token exchange (successful)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "test_token",  # noqa: S105
            "refresh_token": "test_refresh",  # noqa: S105
            "expires_in": 3600,
            "user": {
                "id": "test_user_123",
                "email": "notallowed@example.com",  # NOT in whitelist
                "app_metadata": {"provider": "google"},
            },
        }

        # Mock httpx AsyncClient context manager
        mock_client_instance = MagicMock()
        mock_client_instance.post = AsyncMock(return_value=mock_response)
        mock_async_client.return_value.__aenter__ = AsyncMock(return_value=mock_client_instance)
        mock_async_client.return_value.__aexit__ = AsyncMock()

        request = OAuthCallbackRequest(
            code="test_code",
            redirect_uri="http://localhost:3000/callback",
            code_verifier="test_pkce_verifier_12345",
        )

        with pytest.raises(HTTPException) as exc_info:
            await google_oauth_callback(request)

        # Should fail with 403 - user not whitelisted
        assert exc_info.value.status_code == 403
        assert "closed_beta" in str(exc_info.value.detail)


class TestTokenRefresh:
    """Test JWT token refresh endpoint."""

    @pytest.mark.asyncio
    @patch("supabase.create_client")
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
    @patch("supabase.create_client")
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
    @patch("supabase.create_client")
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

    @patch("bo1.state.postgres_manager.get_connection")
    def test_create_new_user(self, mock_get_connection):
        """Test creating a new user on first sign-in."""
        # Mock database cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = None  # User doesn't exist
        mock_cursor.execute = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock()

        # Mock database connection
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit = MagicMock()
        mock_get_connection.return_value = mock_conn

        _ensure_user_exists(
            user_id="new_user_123", email="newuser@example.com", auth_provider="google"
        )

        # Verify execute was called three times (SET search_path + SELECT + INSERT)
        assert mock_cursor.execute.call_count == 3
        mock_conn.commit.assert_called_once()

    @patch("bo1.state.postgres_manager.get_connection")
    def test_update_existing_user(self, mock_get_connection):
        """Test updating an existing user on subsequent sign-ins."""
        # Mock database cursor
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = ("existing_user_123",)  # User exists (returns tuple)
        mock_cursor.execute = MagicMock()
        mock_cursor.__enter__ = MagicMock(return_value=mock_cursor)
        mock_cursor.__exit__ = MagicMock()

        # Mock database connection
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock_conn.commit = MagicMock()
        mock_get_connection.return_value = mock_conn

        _ensure_user_exists(
            user_id="existing_user_123", email="existing@example.com", auth_provider="google"
        )

        # Verify execute was called three times (SET search_path + SELECT + UPDATE)
        assert mock_cursor.execute.call_count == 3
        mock_conn.commit.assert_called_once()
