"""Tests for admin rate limit configuration.

Verifies that admin endpoints use higher rate limits (300/minute)
to support dashboard page loads that fire multiple API requests in parallel.
"""

from pathlib import Path

from bo1.constants import RateLimits


class TestAdminRateLimitConstants:
    """Tests for admin rate limit constants."""

    def test_admin_rate_limit_exists(self):
        """Admin rate limit constant is defined."""
        assert hasattr(RateLimits, "ADMIN")
        assert RateLimits.ADMIN == "300/minute"

    def test_admin_rate_limit_higher_than_general(self):
        """Admin rate limit is higher than general rate limit."""
        # Parse rate limits (format: "N/minute")
        admin_limit = int(RateLimits.ADMIN.split("/")[0])
        general_limit = int(RateLimits.GENERAL.split("/")[0])

        assert admin_limit > general_limit
        assert admin_limit >= 300  # At least 300/minute for admin

    def test_admin_rate_limit_format(self):
        """Admin rate limit has correct format."""
        assert "/" in RateLimits.ADMIN
        assert RateLimits.ADMIN.endswith("/minute")


class TestAdminRateLimitImports:
    """Tests for admin rate limit exports."""

    def test_admin_rate_limit_exported_from_middleware(self):
        """ADMIN_RATE_LIMIT is exported from rate_limit middleware."""
        from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT

        assert ADMIN_RATE_LIMIT == RateLimits.ADMIN
        assert ADMIN_RATE_LIMIT == "300/minute"


class TestAdminEndpointRateLimits:
    """Tests verifying admin endpoints use admin rate limits.

    These tests read the source files directly to avoid import issues.
    """

    # All admin modules that should have rate limiting
    ADMIN_MODULES = [
        "alerts",
        "beta_whitelist",
        "blog",
        "cost_analytics",
        "costs",
        "email_stats",
        "embeddings",
        "extended_kpis",
        "feature_flags",
        "feedback",
        "impersonation",
        "metrics",
        "observability",
        "ops",
        "partitions",
        "promotions",
        "research_cache",
        "runtime_config",
        "session_control",
        "user_metrics",
        "users",
        "waitlist",
    ]

    def _check_rate_limit_in_module(self, module_name: str) -> None:
        """Helper to check rate limiting is properly configured in a module."""
        source_path = Path(f"backend/api/admin/{module_name}.py")
        source = source_path.read_text()

        assert "ADMIN_RATE_LIMIT" in source, f"{module_name}.py missing ADMIN_RATE_LIMIT"
        assert "@limiter.limit" in source, f"{module_name}.py missing @limiter.limit"
        assert "from backend.api.middleware.rate_limit import" in source, (
            f"{module_name}.py missing rate_limit import"
        )

    def test_all_admin_modules_have_rate_limiting(self):
        """All admin modules have rate limiting configured."""
        for module in self.ADMIN_MODULES:
            self._check_rate_limit_in_module(module)

    def test_user_metrics_endpoint_has_rate_limit_decorator(self):
        """user_metrics endpoints have @limiter.limit decorator."""
        self._check_rate_limit_in_module("user_metrics")

    def test_observability_endpoint_has_rate_limit_decorator(self):
        """observability endpoint has @limiter.limit decorator."""
        self._check_rate_limit_in_module("observability")

    def test_session_control_endpoint_has_rate_limit_decorator(self):
        """session_control kill-history endpoint has @limiter.limit decorator."""
        self._check_rate_limit_in_module("session_control")
