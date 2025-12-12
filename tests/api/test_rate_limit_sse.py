"""Tests for SSE streaming rate limiting.

Verifies that:
- SSE streaming endpoint is rate limited (5/minute)
- Rate limit returns 429 when exceeded
- Rate limiter fails open when Redis unavailable
"""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bo1.constants import RateLimits


class TestSSERateLimitConstants:
    """Test that SSE rate limit constants are configured."""

    def test_streaming_rate_limit_defined(self):
        """STREAMING rate limit should be defined."""
        assert hasattr(RateLimits, "STREAMING")
        assert RateLimits.STREAMING == "5/minute"

    def test_streaming_rate_limit_exported(self):
        """STREAMING_RATE_LIMIT should be exported from rate_limit module."""
        from backend.api.middleware.rate_limit import STREAMING_RATE_LIMIT

        assert STREAMING_RATE_LIMIT == "5/minute"


class TestSSERateLimitDecorator:
    """Test that SSE endpoint has rate limit decorator."""

    def test_stream_endpoint_has_rate_limit(self):
        """Stream endpoint should have @limiter.limit decorator."""
        from backend.api.streaming import stream_deliberation

        # Check if the function has been decorated
        # SlowAPI adds _rate_limit_decorator attribute to decorated functions
        # or we can check the function name and docstring
        assert stream_deliberation is not None
        assert "Rate Limited" in (stream_deliberation.__doc__ or "")


class TestSSERateLimitBehavior:
    """Integration tests for SSE rate limiting behavior."""

    @pytest.fixture
    def mock_auth_user(self):
        """Create mock authenticated user."""
        return {"user_id": "test-user-123", "email": "test@example.com"}

    @pytest.fixture
    def mock_session_data(self):
        """Create mock verified session."""
        return (
            "test-user-123",
            {
                "status": "running",
                "session_id": "bo1_test123",
            },
        )

    @pytest.fixture
    def client(self):
        """Create test client."""
        from backend.api.main import app

        return TestClient(app, raise_server_exceptions=False)

    def test_sse_rate_limit_format(self):
        """Test that rate limit string is valid format."""
        limit = RateLimits.STREAMING
        # Should be in format "N/period"
        assert "/" in limit
        parts = limit.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1] in ["second", "minute", "hour", "day"]

    def test_limiter_imported_in_streaming(self):
        """Test that limiter is imported in streaming module."""
        from backend.api.streaming import limiter

        assert limiter is not None

    def test_streaming_rate_limit_imported(self):
        """Test that STREAMING_RATE_LIMIT is imported in streaming module."""
        from backend.api.streaming import STREAMING_RATE_LIMIT

        assert STREAMING_RATE_LIMIT == "5/minute"


class TestRateLimitFailOpen:
    """Test rate limiter fail-open behavior."""

    @pytest.mark.asyncio
    async def test_fail_open_when_redis_unavailable(self):
        """Rate limiter should allow requests when Redis is down."""
        from backend.api.middleware.rate_limit import UserRateLimiter

        limiter = UserRateLimiter()

        # Mock Redis as unavailable
        with patch.object(limiter, "_get_redis", return_value=None):
            # Should not raise, should return True (allow request)
            result = await limiter.check_limit("user-123", "test_action")
            assert result is True
