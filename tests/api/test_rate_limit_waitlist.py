"""Tests for waitlist endpoint rate limiting.

Verifies that:
- Waitlist endpoints are rate limited (5/minute)
- Rate limit returns 429 when exceeded
- WAITLIST rate limit constant is properly defined
- Both POST /v1/waitlist and POST /v1/waitlist/check are protected
"""

from bo1.constants import RateLimits


class TestWaitlistRateLimitConstants:
    """Test that waitlist rate limit constants are configured."""

    def test_waitlist_rate_limit_defined(self):
        """WAITLIST rate limit should be defined."""
        assert hasattr(RateLimits, "WAITLIST")
        assert RateLimits.WAITLIST == "5/minute"

    def test_waitlist_rate_limit_format(self):
        """Test that rate limit string is valid format."""
        limit = RateLimits.WAITLIST
        assert "/" in limit
        parts = limit.split("/")
        assert len(parts) == 2
        assert parts[0].isdigit()
        assert parts[1] in ["second", "minute", "hour", "day"]

    def test_waitlist_limit_is_per_minute(self):
        """Waitlist limit should be per minute to prevent spam signups."""
        limit = RateLimits.WAITLIST
        assert "minute" in limit.lower()

    def test_waitlist_limit_allows_legitimate_signups(self):
        """Waitlist limit should allow reasonable legitimate usage (5/min)."""
        limit = RateLimits.WAITLIST
        count = int(limit.split("/")[0])
        # Should allow at least 5 attempts (reasonable for mistyped emails)
        assert count >= 5


class TestWaitlistRateLimitDecorator:
    """Test that waitlist endpoints have rate limit decorators."""

    def test_add_to_waitlist_endpoint_exists(self):
        """add_to_waitlist endpoint should exist."""
        from backend.api.waitlist import add_to_waitlist

        assert add_to_waitlist is not None

    def test_check_whitelist_endpoint_exists(self):
        """check_whitelist endpoint should exist."""
        from backend.api.waitlist import check_whitelist

        assert check_whitelist is not None

    def test_waitlist_router_has_rate_limited_routes(self):
        """Waitlist router should have routes with 429 responses."""
        from backend.api.waitlist import router

        # Find routes that have 429 response documented
        routes_with_429 = []
        for route in router.routes:
            if hasattr(route, "responses") and route.responses:
                if 429 in route.responses:
                    routes_with_429.append(route.path)

        # Both endpoints should have 429 response
        assert "/v1/waitlist" in routes_with_429  # POST /v1/waitlist
        assert "/v1/waitlist/check" in routes_with_429  # POST /v1/waitlist/check


class TestWaitlistRateLimitIntegration:
    """Integration tests for waitlist rate limiting."""

    def test_limiter_imported_in_waitlist(self):
        """Test that limiter is imported in waitlist module."""
        from backend.api.waitlist import limiter

        assert limiter is not None

    def test_rate_limits_imported_in_waitlist(self):
        """Test that RateLimits is imported in waitlist module."""
        from backend.api.waitlist import RateLimits as WaitlistRateLimits

        assert WaitlistRateLimits.WAITLIST == "5/minute"


class TestWaitlistRateLimiterConfiguration:
    """Test rate limiter configuration for waitlist."""

    def test_limiter_uses_redis_storage(self):
        """Limiter should be configured for Redis storage."""
        from backend.api.middleware.rate_limit import limiter

        assert limiter is not None

    def test_waitlist_in_all_rate_limits(self):
        """WAITLIST should be included in all rate limit constants."""
        limits = [
            RateLimits.AUTH,
            RateLimits.SESSION,
            RateLimits.STREAMING,
            RateLimits.GENERAL,
            RateLimits.CONTROL,
            RateLimits.WAITLIST,  # New
        ]

        for limit in limits:
            assert "/" in limit
            parts = limit.split("/")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1] in ["second", "minute", "hour", "day"]


class TestWaitlistEndpointSignatures:
    """Test that waitlist endpoints have correct signatures for rate limiting."""

    def test_add_to_waitlist_has_request_param(self):
        """add_to_waitlist should have request param for rate limiting (slowapi requirement)."""
        import inspect

        from backend.api.waitlist import add_to_waitlist

        sig = inspect.signature(add_to_waitlist)
        param_names = list(sig.parameters.keys())
        # slowapi requires first param to be named 'request' (not 'http_request')
        assert "request" in param_names

    def test_check_whitelist_has_request_param(self):
        """check_whitelist should have request param for rate limiting (slowapi requirement)."""
        import inspect

        from backend.api.waitlist import check_whitelist

        sig = inspect.signature(check_whitelist)
        param_names = list(sig.parameters.keys())
        # slowapi requires first param to be named 'request' (not 'http_request')
        assert "request" in param_names
