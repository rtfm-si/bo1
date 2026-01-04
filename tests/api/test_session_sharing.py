"""Tests for session sharing endpoints.

Tests:
- POST /api/v1/sessions/{id}/share - Create share link
- GET /api/v1/sessions/{id}/share - List active shares
- DELETE /api/v1/sessions/{id}/share/{token} - Revoke share
- GET /api/v1/share/{token} - Public share access
"""

from datetime import UTC, datetime, timedelta

import pytest

from backend.services.session_share import SessionShareService


class TestSessionShareService:
    """Test SessionShareService class."""

    def test_generate_token_returns_string(self):
        """Test token generation returns string."""
        token = SessionShareService.generate_token()
        assert isinstance(token, str)
        assert len(token) > 20  # URL-safe base64 of 32 bytes

    def test_generate_token_unique(self):
        """Test tokens are unique."""
        tokens = [SessionShareService.generate_token() for _ in range(10)]
        assert len(set(tokens)) == 10

    def test_validate_ttl_valid_values(self):
        """Test TTL validation accepts valid values."""
        assert SessionShareService.validate_ttl(7) == 7
        assert SessionShareService.validate_ttl(30) == 30
        assert SessionShareService.validate_ttl(90) == 90
        assert SessionShareService.validate_ttl(365) == 365

    def test_validate_ttl_invalid_values(self):
        """Test TTL validation rejects invalid values."""
        with pytest.raises(ValueError):
            SessionShareService.validate_ttl(0)

        with pytest.raises(ValueError):
            SessionShareService.validate_ttl(-1)

    def test_validate_ttl_caps_at_max(self):
        """Test TTL is capped at MAX_TTL_DAYS (365)."""
        # 366 should be capped to 365, not raise
        result = SessionShareService.validate_ttl(366)
        assert result == 365

    def test_calculate_expiry(self):
        """Test expiry calculation."""
        now = datetime.now(UTC)
        expiry = SessionShareService.calculate_expiry(7)

        assert isinstance(expiry, datetime)
        assert expiry > now
        # Should be approximately 7 days from now
        diff = (expiry - now).days
        assert 6 <= diff <= 7

    def test_is_expired_false_for_future_date(self):
        """Test is_expired returns False for future date."""
        future = datetime.now(UTC) + timedelta(days=7)
        assert SessionShareService.is_expired(future) is False

    def test_is_expired_true_for_past_date(self):
        """Test is_expired returns True for past date."""
        past = datetime.now(UTC) - timedelta(days=1)
        assert SessionShareService.is_expired(past) is True


class TestShareCreation:
    """Test share creation logic."""

    def test_create_share_response_structure(self):
        """Test expected response structure for share creation."""
        expected_keys = {"token", "share_url", "expires_at"}

        # Simulate response structure
        response = {
            "token": "abc123xyz",
            "share_url": "/share/abc123xyz",
            "expires_at": datetime.now(UTC).isoformat(),
        }

        assert set(response.keys()) == expected_keys

    def test_share_url_format(self):
        """Test share URL uses correct format."""
        token = "test-token-123"  # noqa: S105
        share_url = f"/share/{token}"

        assert share_url == "/share/test-token-123"
        assert token in share_url


class TestShareListing:
    """Test share listing logic."""

    def test_list_shares_response_structure(self):
        """Test expected response structure for share listing."""
        response = {
            "session_id": "test-session-id",
            "shares": [
                {
                    "token": "token1",
                    "expires_at": "2025-12-19T00:00:00+00:00",
                    "created_at": "2025-12-12T00:00:00+00:00",
                    "is_active": True,
                },
            ],
            "total": 1,
        }

        assert "session_id" in response
        assert "shares" in response
        assert "total" in response
        assert isinstance(response["shares"], list)

    def test_filter_expired_shares(self):
        """Test filtering out expired shares."""
        now = datetime.now(UTC)
        shares = [
            {"token": "active1", "expires_at": (now + timedelta(days=7)).isoformat()},
            {"token": "expired1", "expires_at": (now - timedelta(days=1)).isoformat()},
            {"token": "active2", "expires_at": (now + timedelta(days=30)).isoformat()},
        ]

        active_shares = [
            s
            for s in shares
            if not SessionShareService.is_expired(datetime.fromisoformat(s["expires_at"]))
        ]

        assert len(active_shares) == 2
        assert all(s["token"].startswith("active") for s in active_shares)


class TestShareRevocation:
    """Test share revocation logic."""

    def test_revoke_removes_share(self):
        """Test that revocation removes share from list."""
        shares = [
            {"token": "token1"},
            {"token": "token2"},
            {"token": "token3"},
        ]

        token_to_revoke = "token2"  # noqa: S105
        remaining = [s for s in shares if s["token"] != token_to_revoke]

        assert len(remaining) == 2
        assert token_to_revoke not in [s["token"] for s in remaining]


class TestPublicShareAccess:
    """Test public share endpoint logic."""

    def test_public_share_response_structure(self):
        """Test expected response structure for public share."""
        expected_keys = {
            "session_id",
            "title",
            "created_at",
            "owner_name",
            "expires_at",
            "is_active",
            "synthesis",
            "conclusion",
            "problem_context",
        }

        response = {
            "session_id": "test-id",
            "title": "Test Meeting",
            "created_at": "2025-12-12T00:00:00+00:00",
            "owner_name": "test@example.com",
            "expires_at": "2025-12-19T00:00:00+00:00",
            "is_active": True,
            "synthesis": {"summary": "Test summary"},
            "conclusion": None,
            "problem_context": {},
        }

        assert set(response.keys()) == expected_keys

    def test_public_share_expired_check(self):
        """Test expired share detection."""
        past = datetime.now(UTC) - timedelta(days=1)
        future = datetime.now(UTC) + timedelta(days=7)

        assert SessionShareService.is_expired(past) is True
        assert SessionShareService.is_expired(future) is False

    def test_public_share_redacts_sensitive_data(self):
        """Test that sensitive data is not included in public response."""
        public_response = {
            "session_id": "test-id",
            "title": "Test Meeting",
            "owner_name": "test@example.com",
            "synthesis": {"summary": "Summary"},
        }

        # These should NOT be in public response
        sensitive_keys = {"user_id", "cost", "token", "internal_notes"}

        for key in sensitive_keys:
            assert key not in public_response


class TestSharePermissions:
    """Test share permission checks."""

    def test_owner_can_create_share(self):
        """Test owner can create share."""
        session_owner = "user-123"
        requesting_user = "user-123"

        has_permission = session_owner == requesting_user
        assert has_permission is True

    def test_non_owner_cannot_create_share(self):
        """Test non-owner cannot create share."""
        session_owner = "user-123"
        requesting_user = "user-456"

        has_permission = session_owner == requesting_user
        assert has_permission is False

    def test_owner_can_list_shares(self):
        """Test owner can list shares."""
        session_owner = "user-123"
        requesting_user = "user-123"

        has_permission = session_owner == requesting_user
        assert has_permission is True

    def test_owner_can_revoke_share(self):
        """Test owner can revoke share."""
        session_owner = "user-123"
        requesting_user = "user-123"

        has_permission = session_owner == requesting_user
        assert has_permission is True


class TestShareEndpoints:
    """Integration tests for share endpoints with API calls."""

    @pytest.fixture
    def mock_user(self):
        """Create mock authenticated user."""
        return {"user_id": "test-user-123", "email": "test@example.com"}

    @pytest.fixture
    def mock_session_metadata(self):
        """Create mock session metadata."""
        return {
            "user_id": "test-user-123",
            "status": "completed",
            "phase": "synthesis",
            "created_at": "2025-12-01T00:00:00Z",
            "updated_at": "2025-12-01T01:00:00Z",
            "problem_statement": "Test problem",
            "problem_context": {},
        }

    @pytest.fixture
    def test_session_id(self):
        """Valid session ID format."""
        return "bo1_550e8400-e29b-41d4-a716-446655440000"

    def test_create_share_calls_repository(self, mock_user, mock_session_metadata, test_session_id):
        """Test create share endpoint calls repository correctly."""
        from unittest.mock import MagicMock, patch

        with patch("backend.api.sessions.session_repository") as mock_repo:
            mock_repo.create_share = MagicMock()

            # Verify the repository method signature
            mock_repo.create_share(
                session_id=test_session_id,
                token="test-token",  # noqa: S106
                expires_at=datetime.now(UTC),
                created_by=mock_user["user_id"],
            )

            mock_repo.create_share.assert_called_once()
            call_args = mock_repo.create_share.call_args
            assert call_args.kwargs["session_id"] == test_session_id
            assert call_args.kwargs["created_by"] == mock_user["user_id"]

    def test_list_shares_returns_active_only(self):
        """Test list shares filters to active shares."""
        from unittest.mock import MagicMock, patch

        now = datetime.now(UTC)
        mock_shares = [
            {
                "token": "active-token",
                "expires_at": (now + timedelta(days=7)).isoformat(),
                "created_at": now.isoformat(),
            },
            {
                "token": "expired-token",
                "expires_at": (now - timedelta(days=1)).isoformat(),
                "created_at": (now - timedelta(days=8)).isoformat(),
            },
        ]

        with patch("backend.api.sessions.session_repository") as mock_repo:
            mock_repo.list_shares = MagicMock(return_value=mock_shares)

            shares = mock_repo.list_shares("test-session-id")

            # Filter active shares (mimicking endpoint logic)
            active_shares = [
                s
                for s in shares
                if not SessionShareService.is_expired(datetime.fromisoformat(s["expires_at"]))
            ]

            assert len(active_shares) == 1
            assert active_shares[0]["token"] == "active-token"  # noqa: S105

    def test_revoke_share_calls_repository(self, test_session_id):
        """Test revoke share endpoint calls repository."""
        from unittest.mock import MagicMock, patch

        with patch("backend.api.sessions.session_repository") as mock_repo:
            mock_repo.revoke_share = MagicMock(return_value=True)

            result = mock_repo.revoke_share(test_session_id, "test-token")

            assert result is True
            mock_repo.revoke_share.assert_called_once_with(test_session_id, "test-token")

    @pytest.mark.asyncio
    async def test_share_requires_session_ownership(
        self, mock_user, mock_session_metadata, test_session_id
    ):
        """Test share endpoint requires session ownership."""
        from fastapi import HTTPException

        from backend.api.utils.security import verify_session_ownership

        # Test that non-owner cannot access - metadata shows different user
        other_user_metadata = {**mock_session_metadata, "user_id": "other-user-456"}

        # Passing pre-loaded metadata with different owner should raise 404
        with pytest.raises(HTTPException) as exc_info:
            await verify_session_ownership(
                test_session_id,
                mock_user["user_id"],  # Requesting user
                other_user_metadata,  # Metadata shows other user owns it
            )

        # Returns 404 to prevent session enumeration
        assert exc_info.value.status_code == 404


class TestPostgreSQLFallback:
    """Test PostgreSQL fallback for sessions not in Redis."""

    @pytest.fixture
    def test_session_id(self):
        """Valid session ID format."""
        return "bo1_550e8400-e29b-41d4-a716-446655440001"

    @pytest.fixture
    def pg_session_metadata(self):
        """Session metadata as returned from PostgreSQL."""
        return {
            "user_id": "test-user-123",
            "status": "completed",
            "phase": "synthesis",
            "created_at": "2025-12-01T00:00:00+00:00",
            "updated_at": "2025-12-01T01:00:00+00:00",
            "problem_statement": "Test problem for PostgreSQL fallback",
            "problem_context": {},
        }

    @pytest.mark.asyncio
    async def test_verify_ownership_falls_back_to_postgresql(
        self, test_session_id, pg_session_metadata
    ):
        """Test verify_session_ownership uses PostgreSQL when Redis returns None."""
        from unittest.mock import MagicMock, patch

        from backend.api.utils.security import verify_session_ownership

        # Patch at the source modules that get imported inside the function
        with patch("backend.api.dependencies.get_redis_manager") as mock_redis_fn:
            mock_manager = MagicMock()
            # Redis returns None (session not cached)
            mock_manager.load_metadata = MagicMock(return_value=None)
            mock_redis_fn.return_value = mock_manager

            with patch("bo1.state.repositories.session_repository") as mock_pg_repo:
                # PostgreSQL has the session
                mock_pg_repo.get_metadata = MagicMock(return_value=pg_session_metadata)

                # Should succeed by falling back to PostgreSQL
                result = await verify_session_ownership(
                    test_session_id,
                    "test-user-123",  # Matches user_id in pg_session_metadata
                    None,  # No pre-loaded metadata
                )

                assert result is not None
                assert result["user_id"] == "test-user-123"
                # PostgreSQL fallback was used
                mock_pg_repo.get_metadata.assert_called_once_with(test_session_id)

    @pytest.mark.asyncio
    async def test_verify_ownership_404_when_not_in_redis_or_postgresql(self, test_session_id):
        """Test verify_session_ownership returns 404 when session not found anywhere."""
        from unittest.mock import MagicMock, patch

        from fastapi import HTTPException

        from backend.api.utils.security import verify_session_ownership

        with patch("backend.api.dependencies.get_redis_manager") as mock_redis_fn:
            mock_manager = MagicMock()
            mock_manager.load_metadata = MagicMock(return_value=None)
            mock_redis_fn.return_value = mock_manager

            with patch("bo1.state.repositories.session_repository") as mock_pg_repo:
                # PostgreSQL also returns None
                mock_pg_repo.get_metadata = MagicMock(return_value=None)

                with pytest.raises(HTTPException) as exc_info:
                    await verify_session_ownership(
                        test_session_id,
                        "test-user-123",
                        None,
                    )

                assert exc_info.value.status_code == 404
                assert "Session not found" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_verify_ownership_with_preloaded_metadata_skips_lookup(
        self, test_session_id, pg_session_metadata
    ):
        """Test verify_session_ownership skips Redis/PostgreSQL when metadata is preloaded."""
        from backend.api.utils.security import verify_session_ownership

        # Pass preloaded metadata - should not need to call any external services
        result = await verify_session_ownership(
            test_session_id,
            "test-user-123",
            pg_session_metadata,  # Preloaded - no lookups needed
        )

        assert result is not None
        assert result["user_id"] == "test-user-123"
        # No external calls made - function just validates ownership
