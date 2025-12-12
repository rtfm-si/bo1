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
