"""Tests for usage tracking service.

Note: TestTierLimits and TestTierFeatureFlags test the deprecated classes in
bo1.constants for backward compatibility. The canonical source of truth is
now bo1.billing.PlanConfig, which has its own tests in tests/billing/test_plan_config.py.
"""

from unittest.mock import MagicMock, patch

from bo1.constants import TierFeatureFlags, TierLimits, UsageMetrics


class TestTierLimits:
    """Tests for deprecated TierLimits (backward compat)."""

    def test_get_limits_free(self):
        """Free tier should have base limits."""
        limits = TierLimits.get_limits("free")
        assert limits["meetings_monthly"] == 3
        assert limits["datasets_total"] == 5
        assert limits["mentor_daily"] == 10
        assert limits["api_daily"] == 0

    def test_get_limits_starter(self):
        """Starter tier should have increased limits."""
        limits = TierLimits.get_limits("starter")
        assert limits["meetings_monthly"] == 20
        assert limits["datasets_total"] == 25
        assert limits["mentor_daily"] == 50
        assert limits["api_daily"] == 100

    def test_get_limits_pro(self):
        """Pro tier should have unlimited meetings and mentor chats."""
        limits = TierLimits.get_limits("pro")
        assert limits["meetings_monthly"] == -1  # Unlimited
        assert limits["datasets_total"] == 100
        assert limits["mentor_daily"] == -1  # Unlimited
        assert limits["api_daily"] == 1000

    def test_get_limits_enterprise(self):
        """Enterprise tier should match pro limits."""
        limits = TierLimits.get_limits("enterprise")
        assert limits["meetings_monthly"] == -1
        assert limits["datasets_total"] == 100
        assert limits["mentor_daily"] == -1
        assert limits["api_daily"] == 1000

    def test_get_limits_unknown_tier(self):
        """Unknown tiers should default to free."""
        limits = TierLimits.get_limits("nonexistent")
        assert limits == TierLimits.get_limits("free")

    def test_get_limit_specific_metric(self):
        """get_limit should return specific metric limit."""
        assert TierLimits.get_limit("free", "meetings_monthly") == 3
        assert TierLimits.get_limit("pro", "meetings_monthly") == -1

    def test_is_unlimited(self):
        """is_unlimited should return True for -1."""
        assert TierLimits.is_unlimited(-1) is True
        assert TierLimits.is_unlimited(0) is False
        assert TierLimits.is_unlimited(100) is False


class TestTierFeatureFlags:
    """Tests for deprecated TierFeatureFlags (backward compat)."""

    def test_free_tier_features(self):
        """Free tier should have limited features."""
        features = TierFeatureFlags.get_features("free")
        assert features["meetings"] is True
        assert features["datasets"] is True
        assert features["mentor"] is True
        assert features["api_access"] is False
        assert features["priority_support"] is False
        assert features["advanced_analytics"] is False
        assert features["custom_personas"] is False

    def test_starter_tier_features(self):
        """Starter tier should have API access and analytics."""
        features = TierFeatureFlags.get_features("starter")
        assert features["api_access"] is True
        assert features["advanced_analytics"] is True
        assert features["priority_support"] is False
        assert features["custom_personas"] is False

    def test_pro_tier_features(self):
        """Pro tier should have all features."""
        features = TierFeatureFlags.get_features("pro")
        assert features["api_access"] is True
        assert features["priority_support"] is True
        assert features["advanced_analytics"] is True
        assert features["custom_personas"] is True

    def test_is_feature_enabled(self):
        """is_feature_enabled should check specific features."""
        assert TierFeatureFlags.is_feature_enabled("free", "meetings") is True
        assert TierFeatureFlags.is_feature_enabled("free", "api_access") is False
        assert TierFeatureFlags.is_feature_enabled("pro", "api_access") is True

    def test_unknown_tier_defaults_to_free(self):
        """Unknown tier should default to free features."""
        features = TierFeatureFlags.get_features("unknown")
        assert features == TierFeatureFlags.get_features("free")


class TestUsageMetrics:
    """Tests for UsageMetrics configuration."""

    def test_metric_names(self):
        """Metric names should be defined."""
        assert UsageMetrics.MEETINGS_CREATED == "meetings_created"
        assert UsageMetrics.DATASETS_UPLOADED == "datasets_uploaded"
        assert UsageMetrics.MENTOR_CHATS == "mentor_chats"
        assert UsageMetrics.API_CALLS == "api_calls"

    def test_all_metrics(self):
        """ALL should contain all metric names."""
        assert len(UsageMetrics.ALL) == 4
        assert UsageMetrics.MEETINGS_CREATED in UsageMetrics.ALL
        assert UsageMetrics.DATASETS_UPLOADED in UsageMetrics.ALL
        assert UsageMetrics.MENTOR_CHATS in UsageMetrics.ALL
        assert UsageMetrics.API_CALLS in UsageMetrics.ALL

    def test_key_patterns(self):
        """Key patterns should contain placeholders."""
        assert "{user_id}" in UsageMetrics.DAILY_KEY_PATTERN
        assert "{metric}" in UsageMetrics.DAILY_KEY_PATTERN
        assert "{date}" in UsageMetrics.DAILY_KEY_PATTERN
        assert "{year_month}" in UsageMetrics.MONTHLY_KEY_PATTERN


class TestUsageTracking:
    """Tests for usage tracking service functions."""

    @patch("backend.services.usage_tracking._get_redis")
    def test_increment_usage_with_redis(self, mock_get_redis):
        """increment_usage should use Redis when available."""
        from backend.services.usage_tracking import increment_usage

        mock_redis = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [5, True]
        mock_redis.pipeline.return_value = mock_pipe
        mock_get_redis.return_value = mock_redis

        result = increment_usage("user123", UsageMetrics.MENTOR_CHATS, 1)

        assert result == 5
        mock_pipe.incrby.assert_called_once()
        mock_pipe.expire.assert_called_once()

    @patch("backend.services.usage_tracking._get_redis")
    def test_get_usage_with_redis(self, mock_get_redis):
        """get_usage should return count from Redis."""
        from backend.services.usage_tracking import get_usage

        mock_redis = MagicMock()
        mock_redis.get.return_value = "10"
        mock_get_redis.return_value = mock_redis

        result = get_usage("user123", UsageMetrics.MENTOR_CHATS)

        assert result == 10

    @patch("backend.services.usage_tracking._get_redis")
    def test_get_usage_returns_zero_when_empty(self, mock_get_redis):
        """get_usage should return 0 when key doesn't exist."""
        from backend.services.usage_tracking import get_usage

        mock_redis = MagicMock()
        mock_redis.get.return_value = None
        mock_get_redis.return_value = mock_redis

        result = get_usage("user123", UsageMetrics.MENTOR_CHATS)

        assert result == 0

    @patch("backend.services.usage_tracking.get_usage")
    def test_check_limit_allows_when_under(self, mock_get_usage):
        """check_limit should allow when under limit."""
        from backend.services.usage_tracking import check_limit

        mock_get_usage.return_value = 2

        result = check_limit("user123", UsageMetrics.MEETINGS_CREATED, "free")

        assert result.allowed is True
        assert result.current == 2
        assert result.limit == 3
        assert result.remaining == 1

    @patch("backend.services.usage_tracking.get_usage")
    def test_check_limit_blocks_when_at_limit(self, mock_get_usage):
        """check_limit should block when at limit."""
        from backend.services.usage_tracking import check_limit

        mock_get_usage.return_value = 3

        result = check_limit("user123", UsageMetrics.MEETINGS_CREATED, "free")

        assert result.allowed is False
        assert result.current == 3
        assert result.limit == 3
        assert result.remaining == 0

    @patch("backend.services.usage_tracking.get_usage")
    def test_check_limit_allows_unlimited(self, mock_get_usage):
        """check_limit should always allow for unlimited (-1) limits."""
        from backend.services.usage_tracking import check_limit

        mock_get_usage.return_value = 1000

        result = check_limit("user123", UsageMetrics.MEETINGS_CREATED, "pro")

        assert result.allowed is True
        assert result.limit == -1
        assert result.remaining == -1

    @patch("backend.services.usage_tracking.check_tier_override")
    def test_get_effective_tier_with_override(self, mock_check_override):
        """get_effective_tier should return override tier when active."""
        from backend.services.usage_tracking import get_effective_tier

        mock_check_override.return_value = {
            "tier": "pro",
            "reason": "beta tester",
        }

        result = get_effective_tier("user123", "free")

        assert result == "pro"

    @patch("backend.services.usage_tracking.check_tier_override")
    def test_get_effective_tier_without_override(self, mock_check_override):
        """get_effective_tier should return base tier when no override."""
        from backend.services.usage_tracking import get_effective_tier

        mock_check_override.return_value = None

        result = get_effective_tier("user123", "free")

        assert result == "free"
