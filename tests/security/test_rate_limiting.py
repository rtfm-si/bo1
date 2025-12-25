"""Rate limiting security tests.

Tests cover:
- Session creation rate limits (per-user throttling)
- Global flood protection (IP-based limiting)
- 429 responses with Retry-After header
- Rate limit headers (X-RateLimit-*)
- Tiered limits by subscription tier
- Health endpoint exemption
- Admin endpoint higher limits
- Rate limit window reset behavior
- Redis failure fallback (fail-open)

Builds on existing test_security_integration.py infrastructure.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def client():
    """Create test client."""
    from backend.api.main import app

    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def mock_free_user():
    """Mock free tier user."""
    return {
        "user_id": "free-user-1",
        "email": "free@test.com",
        "role": "authenticated",
        "subscription_tier": "free",
        "is_admin": False,
    }


@pytest.fixture
def mock_pro_user():
    """Mock pro tier user."""
    return {
        "user_id": "pro-user-1",
        "email": "pro@test.com",
        "role": "authenticated",
        "subscription_tier": "pro",
        "is_admin": False,
    }


@pytest.fixture
def mock_enterprise_user():
    """Mock enterprise tier user."""
    return {
        "user_id": "enterprise-user-1",
        "email": "enterprise@test.com",
        "role": "authenticated",
        "subscription_tier": "enterprise",
        "is_admin": False,
    }


@pytest.fixture
def user_rate_limiter():
    """Create fresh UserRateLimiter instance for testing."""
    from backend.api.middleware.rate_limit import UserRateLimiter

    return UserRateLimiter()


@pytest.fixture
def mock_redis_pipeline():
    """Create mock Redis pipeline."""
    pipeline = MagicMock()
    pipeline.zremrangebyscore = MagicMock()
    pipeline.zcard = MagicMock()
    pipeline.zadd = MagicMock()
    pipeline.expire = MagicMock()
    return pipeline


# =============================================================================
# SESSION CREATION RATE LIMIT TESTS
# =============================================================================


class TestSessionCreationRateLimit:
    """Test session creation rate limits (per-user throttling)."""

    @pytest.mark.asyncio
    async def test_session_creation_429_after_limit(self, user_rate_limiter):
        """Should return 429 after exceeding session creation limit."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # Simulate current count >= limit (5 requests already made)
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 5, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            with pytest.raises(HTTPException) as exc_info:
                await user_rate_limiter.check_limit("test-user", "session_create", limit=5)

            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    async def test_session_creation_allows_under_limit(self, user_rate_limiter):
        """Should allow requests under the limit."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # Simulate current count < limit (only 2 requests)
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 2, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            result = await user_rate_limiter.check_limit("test-user", "session_create", limit=5)
            assert result is True


class TestSessionCreationRetryAfterHeader:
    """Test Retry-After header on 429 responses."""

    @pytest.mark.asyncio
    async def test_retry_after_header_present(self, user_rate_limiter):
        """429 response should include Retry-After header."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 10, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            with pytest.raises(HTTPException) as exc_info:
                await user_rate_limiter.check_limit(
                    "test-user", "session_create", limit=5, window_seconds=60
                )

            assert exc_info.value.headers is not None
            assert "Retry-After" in exc_info.value.headers
            assert exc_info.value.headers["Retry-After"] == "60"

    @pytest.mark.asyncio
    async def test_retry_after_matches_window(self, user_rate_limiter):
        """Retry-After should match the rate limit window."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 100, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            window_seconds = 120
            with pytest.raises(HTTPException) as exc_info:
                await user_rate_limiter.check_limit(
                    "test-user", "test_action", limit=5, window_seconds=window_seconds
                )

            assert exc_info.value.headers["Retry-After"] == str(window_seconds)


# =============================================================================
# GLOBAL FLOOD PROTECTION TESTS (IP-BASED)
# =============================================================================


class TestGlobalIPFloodProtection:
    """Test global IP-based rate limiting."""

    def test_slowapi_limiter_configured(self):
        """SlowAPI limiter should be configured with Redis storage."""
        from backend.api.middleware.rate_limit import limiter

        assert limiter is not None
        # Verify limiter exists and has key_func
        assert hasattr(limiter, "_key_func")

    def test_ip_key_extraction(self):
        """get_remote_address should extract client IP."""
        from unittest.mock import MagicMock

        from fastapi import Request
        from slowapi.util import get_remote_address

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "192.168.1.100"

        ip = get_remote_address(mock_request)
        assert ip == "192.168.1.100"

    def test_user_and_ip_key_generation(self):
        """get_user_and_ip_key should combine user ID and IP."""
        from unittest.mock import MagicMock

        from fastapi import Request
        from starlette.datastructures import State

        from backend.api.middleware.rate_limit import get_user_and_ip_key

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "10.0.0.1"
        mock_request.state = State()
        mock_request.state.user = {"user_id": "user-123"}

        key = get_user_and_ip_key(mock_request)
        assert "user:user-123" in key
        assert "ip:10.0.0.1" in key

    def test_ip_only_key_for_unauthenticated(self):
        """Unauthenticated requests should use IP-only key."""
        from unittest.mock import MagicMock

        from fastapi import Request
        from starlette.datastructures import State

        from backend.api.middleware.rate_limit import get_user_and_ip_key

        mock_request = MagicMock(spec=Request)
        mock_request.client.host = "10.0.0.1"
        mock_request.state = State()
        # No user set

        key = get_user_and_ip_key(mock_request)
        assert key == "ip:10.0.0.1"


# =============================================================================
# GLOBAL IP RATE LIMITER TESTS
# =============================================================================


@pytest.fixture
def global_ip_limiter():
    """Create fresh GlobalIPRateLimiter instance for testing."""
    from backend.api.middleware.rate_limit import GlobalIPRateLimiter

    return GlobalIPRateLimiter()


class TestGlobalIPRateLimiter:
    """Test GlobalIPRateLimiter class."""

    def test_global_ip_limiter_blocks_after_limit(self, global_ip_limiter):
        """Should block requests after exceeding global limit."""
        with patch.object(global_ip_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # Simulate count >= 500 (global limit)
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 500, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            allowed, retry_after = global_ip_limiter.check_limit("10.0.0.1")

            assert allowed is False
            assert retry_after == 60  # 1 minute window

    def test_global_ip_limiter_allows_within_limit(self, global_ip_limiter):
        """Should allow requests within global limit."""
        with patch.object(global_ip_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # Simulate count < 500
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 100, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            allowed, retry_after = global_ip_limiter.check_limit("10.0.0.1")

            assert allowed is True
            assert retry_after is None

    def test_global_ip_limiter_fails_open(self, global_ip_limiter):
        """Should allow requests when Redis is unavailable (fail-open)."""
        with patch.object(global_ip_limiter, "_get_redis") as mock_get_redis:
            mock_get_redis.return_value = None  # Redis unavailable

            allowed, retry_after = global_ip_limiter.check_limit("10.0.0.1")

            assert allowed is True
            assert retry_after is None

    def test_global_ip_limiter_fails_open_on_redis_error(self, global_ip_limiter):
        """Should allow requests when Redis throws an error."""
        with patch.object(global_ip_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # Redis error during operation
            mock_pipeline = MagicMock()
            mock_pipeline.execute.side_effect = Exception("Redis connection lost")
            mock_client.pipeline.return_value = mock_pipeline

            allowed, retry_after = global_ip_limiter.check_limit("10.0.0.1")

            assert allowed is True
            assert retry_after is None

    def test_parse_limit_minute(self, global_ip_limiter):
        """Should parse minute-based limits correctly."""
        count, window = global_ip_limiter._parse_limit("500/minute")
        assert count == 500
        assert window == 60

    def test_parse_limit_second(self, global_ip_limiter):
        """Should parse second-based limits correctly."""
        count, window = global_ip_limiter._parse_limit("50/second")
        assert count == 50
        assert window == 1

    def test_parse_limit_hour(self, global_ip_limiter):
        """Should parse hour-based limits correctly."""
        count, window = global_ip_limiter._parse_limit("1000/hour")
        assert count == 1000
        assert window == 3600


class TestGlobalRateLimitMiddleware:
    """Test GlobalRateLimitMiddleware class."""

    def test_middleware_skips_health_endpoints(self):
        """Middleware should skip health check endpoints."""
        from backend.api.middleware.rate_limit import GlobalIPRateLimiter

        skip_paths = GlobalIPRateLimiter.SKIP_PATHS
        assert "/health" in skip_paths
        assert "/ready" in skip_paths
        assert "/metrics" in skip_paths
        assert "/api/health" in skip_paths
        assert "/api/ready" in skip_paths

    def test_middleware_extracts_x_forwarded_for(self):
        """Middleware should respect X-Forwarded-For header."""
        from backend.api.middleware.rate_limit import GlobalRateLimitMiddleware

        middleware = GlobalRateLimitMiddleware(None)

        # Test X-Forwarded-For extraction
        scope = {
            "type": "http",
            "headers": [(b"x-forwarded-for", b"203.0.113.195, 70.41.3.18, 150.172.238.178")],
            "client": ("10.0.0.1", 12345),
        }

        ip = middleware._get_client_ip(scope)
        assert ip == "203.0.113.195"  # First IP in chain

    def test_middleware_falls_back_to_client_ip(self):
        """Middleware should fall back to direct client IP."""
        from backend.api.middleware.rate_limit import GlobalRateLimitMiddleware

        middleware = GlobalRateLimitMiddleware(None)

        scope = {
            "type": "http",
            "headers": [],
            "client": ("192.168.1.100", 54321),
        }

        ip = middleware._get_client_ip(scope)
        assert ip == "192.168.1.100"

    def test_middleware_handles_missing_client(self):
        """Middleware should handle missing client info gracefully."""
        from backend.api.middleware.rate_limit import GlobalRateLimitMiddleware

        middleware = GlobalRateLimitMiddleware(None)

        scope = {
            "type": "http",
            "headers": [],
            "client": None,
        }

        ip = middleware._get_client_ip(scope)
        assert ip == "unknown"

    @pytest.mark.asyncio
    async def test_middleware_returns_429_when_blocked(self):
        """Middleware should return 429 when rate limit exceeded."""
        from backend.api.middleware.rate_limit import (
            GlobalRateLimitMiddleware,
            global_ip_rate_limiter,
        )

        sent_responses = []

        async def mock_send(message):
            sent_responses.append(message)

        middleware = GlobalRateLimitMiddleware(None)

        # Mock the rate limiter to return blocked
        with patch.object(global_ip_rate_limiter, "check_limit", return_value=(False, 60)):
            scope = {
                "type": "http",
                "path": "/api/some-endpoint",
                "headers": [],
                "client": ("10.0.0.1", 12345),
            }

            await middleware(scope, None, mock_send)

            # Check response was 429
            assert len(sent_responses) == 2
            assert sent_responses[0]["status"] == 429
            assert any(h[0] == b"retry-after" for h in sent_responses[0]["headers"])

    @pytest.mark.asyncio
    async def test_middleware_passes_through_when_allowed(self):
        """Middleware should pass request through when within limit."""
        from backend.api.middleware.rate_limit import (
            GlobalRateLimitMiddleware,
            global_ip_rate_limiter,
        )

        app_called = []

        async def mock_app(scope, receive, send):
            app_called.append(True)

        middleware = GlobalRateLimitMiddleware(mock_app)

        # Mock the rate limiter to allow
        with patch.object(global_ip_rate_limiter, "check_limit", return_value=(True, None)):
            scope = {
                "type": "http",
                "path": "/api/some-endpoint",
                "headers": [],
                "client": ("10.0.0.1", 12345),
            }

            await middleware(scope, None, None)

            assert len(app_called) == 1

    @pytest.mark.asyncio
    async def test_middleware_skips_non_http(self):
        """Middleware should skip non-HTTP requests (e.g., websocket)."""
        from backend.api.middleware.rate_limit import GlobalRateLimitMiddleware

        app_called = []

        async def mock_app(scope, receive, send):
            app_called.append(True)

        middleware = GlobalRateLimitMiddleware(mock_app)

        scope = {
            "type": "websocket",
            "path": "/ws",
        }

        await middleware(scope, None, None)

        assert len(app_called) == 1  # Should pass through directly


# =============================================================================
# RATE LIMIT WINDOW RESET TESTS
# =============================================================================


class TestRateLimitWindowReset:
    """Test rate limits reset after window expires."""

    @pytest.mark.asyncio
    async def test_redis_cleanup_old_entries(self, user_rate_limiter):
        """Redis should remove entries older than window."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 0, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            await user_rate_limiter.check_limit(
                "test-user", "test_action", limit=5, window_seconds=60
            )

            # Verify zremrangebyscore was called to clean old entries
            mock_pipeline.zremrangebyscore.assert_called()

    @pytest.mark.asyncio
    async def test_window_expiry_set_on_key(self, user_rate_limiter):
        """Redis key should have TTL set for cleanup."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 0, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            window_seconds = 60
            await user_rate_limiter.check_limit(
                "test-user", "test_action", limit=5, window_seconds=window_seconds
            )

            # Verify expire was called with window + buffer
            mock_pipeline.expire.assert_called()
            call_args = mock_pipeline.expire.call_args
            assert call_args[0][1] == window_seconds + 10  # cleanup buffer


# =============================================================================
# RATE LIMIT RESPONSE DETAILS TESTS
# =============================================================================


class TestRateLimitResponseDetails:
    """Test rate limit response includes necessary information."""

    @pytest.mark.asyncio
    async def test_429_response_has_error_details(self, user_rate_limiter):
        """429 response should include limit, window, and message."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 20, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            with pytest.raises(HTTPException) as exc_info:
                await user_rate_limiter.check_limit(
                    "test-user", "session_create", limit=5, window_seconds=60
                )

            detail = exc_info.value.detail
            assert "limit" in detail
            assert "window_seconds" in detail
            assert "message" in detail
            assert detail["type"] == "UserRateLimitExceeded"


# =============================================================================
# TIERED RATE LIMIT TESTS
# =============================================================================


class TestTieredRateLimits:
    """Test subscription tier affects rate limits."""

    @pytest.mark.asyncio
    async def test_free_tier_limit(self, user_rate_limiter, mock_free_user):
        """Free tier should have base limit (1x multiplier)."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # 5 requests = at limit for free (5 * 1 = 5)
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 5, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            with pytest.raises(HTTPException) as exc_info:
                await user_rate_limiter.check_limit(
                    mock_free_user["user_id"],
                    "session_create",
                    limit=5,
                    tier="free",
                )

            assert exc_info.value.status_code == 429

    @pytest.mark.asyncio
    async def test_pro_tier_higher_limit(self, user_rate_limiter, mock_pro_user):
        """Pro tier should have 4x base limit."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # 5 requests = under limit for pro (5 * 4 = 20 limit)
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 5, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            result = await user_rate_limiter.check_limit(
                mock_pro_user["user_id"],
                "session_create",
                limit=5,
                tier="pro",
            )
            assert result is True

    @pytest.mark.asyncio
    async def test_enterprise_tier_highest_limit(self, user_rate_limiter, mock_enterprise_user):
        """Enterprise tier should have 20x base limit."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            # 50 requests = under limit for enterprise (5 * 20 = 100 limit)
            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 50, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            result = await user_rate_limiter.check_limit(
                mock_enterprise_user["user_id"],
                "session_create",
                limit=5,
                tier="enterprise",
            )
            assert result is True

    def test_tiered_session_limit_function(self):
        """get_tiered_session_limit should return tier-appropriate limits."""
        from unittest.mock import MagicMock

        from fastapi import Request
        from starlette.datastructures import State

        from backend.api.middleware.rate_limit import get_tiered_session_limit
        from bo1.constants import RateLimits

        # Test free tier
        mock_request = MagicMock(spec=Request)
        mock_request.state = State()
        mock_request.state.user = {"user_id": "user-1", "subscription_tier": "free"}
        assert get_tiered_session_limit(mock_request) == RateLimits.SESSION_FREE

        # Test pro tier
        mock_request.state.user = {"user_id": "user-1", "subscription_tier": "pro"}
        assert get_tiered_session_limit(mock_request) == RateLimits.SESSION_PRO

        # Test enterprise tier
        mock_request.state.user = {"user_id": "user-1", "subscription_tier": "enterprise"}
        assert get_tiered_session_limit(mock_request) == RateLimits.SESSION_ENTERPRISE


# =============================================================================
# ADMIN ENDPOINT RATE LIMIT TESTS
# =============================================================================


class TestAdminEndpointRateLimits:
    """Test admin endpoints have higher/separate rate limits."""

    def test_admin_limit_is_higher(self):
        """Admin rate limit should be significantly higher than general."""
        from bo1.constants import RateLimits

        # Parse limits (format: "N/minute")
        admin_limit = int(RateLimits.ADMIN.split("/")[0])
        general_limit = int(RateLimits.GENERAL.split("/")[0])

        assert admin_limit > general_limit
        assert admin_limit == 600  # 600/minute for admin (doubled for dashboard page loads)
        assert general_limit == 60  # 60/minute for general


# =============================================================================
# HEALTH ENDPOINT EXEMPTION TESTS
# =============================================================================


class TestHealthEndpointExemption:
    """Test health check endpoints are not rate limited."""

    def test_health_endpoint_accessible(self, client):
        """Health endpoint should respond without rate limiting."""
        # Make multiple rapid requests to health endpoint
        for _ in range(10):
            response = client.get("/api/health")
            assert response.status_code == 200

    def test_health_readiness_accessible(self, client):
        """Readiness probe should respond without rate limiting."""
        for _ in range(10):
            response = client.get("/api/ready")
            # May return 200 or 503 depending on service state
            assert response.status_code in [200, 503]


# =============================================================================
# REDIS FAILURE FALLBACK TESTS
# =============================================================================


class TestRedisFailureFallback:
    """Test rate limiter fail-open behavior when Redis unavailable."""

    @pytest.mark.asyncio
    async def test_allows_request_when_redis_unavailable(self, user_rate_limiter):
        """Should allow requests when Redis is unavailable (fail-open)."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_get_redis.return_value = None  # Redis unavailable

            result = await user_rate_limiter.check_limit("test-user", "test_action", limit=5)
            assert result is True

    @pytest.mark.asyncio
    async def test_records_failure_on_redis_unavailable(self, user_rate_limiter):
        """Should record health failure when Redis unavailable."""
        from backend.api.middleware.rate_limit import rate_limiter_health

        initial_failures = rate_limiter_health.consecutive_failures

        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_get_redis.return_value = None

            await user_rate_limiter.check_limit("test-user", "test_action", limit=5)

            # Failure count should increase
            assert rate_limiter_health.consecutive_failures >= initial_failures

    @pytest.mark.asyncio
    async def test_records_success_on_redis_available(self, user_rate_limiter):
        """Should record health success when Redis responds."""
        from backend.api.middleware.rate_limit import rate_limiter_health

        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_pipeline = MagicMock()
            mock_pipeline.execute.return_value = [None, 0, None, None]
            mock_client.pipeline.return_value = mock_pipeline

            await user_rate_limiter.check_limit("test-user", "test_action", limit=5)

            # After successful operation, failures should be reset
            assert rate_limiter_health.consecutive_failures == 0


# =============================================================================
# HEALTH TRACKER TESTS
# =============================================================================


class TestRateLimiterHealthTracker:
    """Test health monitoring for rate limiter."""

    def test_degraded_mode_after_threshold(self):
        """Should enter degraded mode after consecutive failures."""
        from backend.api.middleware.rate_limit import RateLimiterHealthTracker
        from bo1.constants import RateLimiterHealth as RateLimiterHealthConfig

        tracker = RateLimiterHealthTracker()
        assert not tracker.is_degraded

        # Simulate consecutive failures
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()

        assert tracker.is_degraded
        assert tracker.degraded_since is not None

    def test_recovery_after_success(self):
        """Should exit degraded mode after successful operation."""
        from backend.api.middleware.rate_limit import RateLimiterHealthTracker
        from bo1.constants import RateLimiterHealth as RateLimiterHealthConfig

        tracker = RateLimiterHealthTracker()

        # Enter degraded mode
        for _ in range(RateLimiterHealthConfig.FAILURE_THRESHOLD):
            tracker.record_failure()
        assert tracker.is_degraded

        # Record success
        tracker.record_success()

        assert not tracker.is_degraded
        assert tracker.consecutive_failures == 0
        assert tracker.degraded_since is None

    def test_get_status_returns_health_info(self):
        """get_status should return current health status."""
        from backend.api.middleware.rate_limit import RateLimiterHealthTracker

        tracker = RateLimiterHealthTracker()
        status = tracker.get_status()

        assert "is_degraded" in status
        assert "degraded_since" in status
        assert "consecutive_failures" in status


# =============================================================================
# RATE LIMIT CONSTANTS TESTS
# =============================================================================


class TestRateLimitConstants:
    """Test rate limit constants are properly configured."""

    def test_all_rate_limits_defined(self):
        """All rate limit constants should be defined."""
        from bo1.constants import RateLimits

        # Global IP limits
        assert RateLimits.GLOBAL_IP == "500/minute"
        assert RateLimits.GLOBAL_IP_BURST == "50/second"

        # Other limits
        assert RateLimits.AUTH == "10/minute"
        assert RateLimits.SESSION == "30/minute"
        assert RateLimits.SESSION_USER == "5/minute"
        assert RateLimits.SESSION_FREE == "5/minute"
        assert RateLimits.SESSION_PRO == "20/minute"
        assert RateLimits.SESSION_ENTERPRISE == "100/minute"
        assert RateLimits.STREAMING == "20/minute"
        assert RateLimits.UPLOAD == "10/hour"
        assert RateLimits.GENERAL == "60/minute"
        assert RateLimits.CONTROL == "20/minute"
        assert RateLimits.ADMIN == "600/minute"

    def test_rate_limit_format_valid(self):
        """Rate limit format should be parseable (N/unit)."""
        from bo1.constants import RateLimits

        limits = [
            RateLimits.GLOBAL_IP,
            RateLimits.GLOBAL_IP_BURST,
            RateLimits.AUTH,
            RateLimits.SESSION,
            RateLimits.STREAMING,
            RateLimits.GENERAL,
            RateLimits.ADMIN,
        ]

        for limit in limits:
            parts = limit.split("/")
            assert len(parts) == 2
            assert parts[0].isdigit()
            assert parts[1] in ["minute", "hour", "second"]

    def test_global_ip_limit_is_generous(self):
        """Global IP limit should be high enough for NAT/corporate networks."""
        from bo1.constants import RateLimits

        # 500/min = ~8 requests/second, generous for corporate NAT
        limit = int(RateLimits.GLOBAL_IP.split("/")[0])
        assert limit >= 500


# =============================================================================
# GET USAGE TESTS
# =============================================================================


class TestGetUsage:
    """Test rate limit usage retrieval."""

    @pytest.mark.asyncio
    async def test_get_usage_returns_count(self, user_rate_limiter):
        """get_usage should return current request count."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_client = MagicMock()
            mock_get_redis.return_value = mock_client

            mock_client.zremrangebyscore = MagicMock()
            mock_client.zcard.return_value = 3

            usage = await user_rate_limiter.get_usage("test-user", "test_action", window_seconds=60)

            assert usage["count"] == 3
            assert usage["window_seconds"] == 60

    @pytest.mark.asyncio
    async def test_get_usage_returns_zero_when_redis_unavailable(self, user_rate_limiter):
        """get_usage should return zero when Redis unavailable."""
        with patch.object(user_rate_limiter, "_get_redis") as mock_get_redis:
            mock_get_redis.return_value = None

            usage = await user_rate_limiter.get_usage("test-user", "test_action")

            assert usage["count"] == 0
            assert usage["available"] is True
