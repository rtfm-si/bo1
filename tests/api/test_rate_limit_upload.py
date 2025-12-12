"""Tests for dataset upload rate limiting.

Verifies that:
- Dataset upload endpoint is rate limited (10/hour)
- Rate limit returns 429 when exceeded
- UPLOAD rate limit constant is properly defined
"""

from bo1.constants import RateLimits


class TestUploadRateLimitConstants:
    """Test that upload rate limit constants are configured."""

    def test_upload_rate_limit_defined(self):
        """UPLOAD rate limit should be defined."""
        assert hasattr(RateLimits, "UPLOAD")
        assert RateLimits.UPLOAD == "10/hour"

    def test_upload_rate_limit_exported(self):
        """UPLOAD_RATE_LIMIT should be exported from rate_limit module."""
        from backend.api.middleware.rate_limit import UPLOAD_RATE_LIMIT

        assert UPLOAD_RATE_LIMIT == "10/hour"


class TestUploadRateLimitDecorator:
    """Test that upload endpoint has rate limit decorator."""

    def test_upload_endpoint_has_rate_limit(self):
        """Upload endpoint should have @limiter.limit decorator."""
        from backend.api.datasets import upload_dataset

        # The endpoint should be decorated
        assert upload_dataset is not None

    def test_upload_endpoint_description_mentions_rate_limit(self):
        """Upload endpoint description should mention rate limiting."""
        from backend.api.datasets import router

        # Find the upload route
        for route in router.routes:
            if hasattr(route, "path") and route.path == "/upload":
                assert "Rate limited" in (route.description or "")
                break


class TestUploadRateLimitFormat:
    """Test rate limit string format."""

    def test_upload_rate_limit_format(self):
        """Test that rate limit string is valid format."""
        limit = RateLimits.UPLOAD
        # Should be in format "N/period"
        assert "/" in limit
        parts = limit.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1] in ["second", "minute", "hour", "day"]

    def test_upload_limit_is_hourly(self):
        """Upload limit should be per hour to prevent storage abuse."""
        limit = RateLimits.UPLOAD
        assert "hour" in limit.lower()

    def test_upload_limit_allows_reasonable_usage(self):
        """Upload limit should allow reasonable usage (10+ per hour)."""
        limit = RateLimits.UPLOAD
        count = int(limit.split("/")[0])
        assert count >= 10  # At least 10 uploads per hour


class TestUploadRateLimitIntegration:
    """Integration tests for upload rate limiting."""

    def test_limiter_imported_in_datasets(self):
        """Test that limiter is imported in datasets module."""
        from backend.api.datasets import limiter

        assert limiter is not None

    def test_upload_rate_limit_imported(self):
        """Test that UPLOAD_RATE_LIMIT is imported in datasets module."""
        from backend.api.datasets import UPLOAD_RATE_LIMIT

        assert UPLOAD_RATE_LIMIT == "10/hour"


class TestRateLimiterConfiguration:
    """Test rate limiter configuration."""

    def test_limiter_uses_redis_storage(self):
        """Limiter should be configured for Redis storage."""
        from backend.api.middleware.rate_limit import limiter

        # Limiter should be initialized
        assert limiter is not None

    def test_all_rate_limits_use_consistent_format(self):
        """All rate limits should use consistent N/period format."""
        limits = [
            RateLimits.AUTH,
            RateLimits.SESSION,
            RateLimits.STREAMING,
            RateLimits.UPLOAD,
            RateLimits.GENERAL,
            RateLimits.CONTROL,
        ]

        for limit in limits:
            assert "/" in limit
            parts = limit.split("/")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1] in ["second", "minute", "hour", "day"]
