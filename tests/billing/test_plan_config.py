"""Tests for centralized PlanConfig."""

from bo1.billing import PlanConfig
from bo1.billing.config import TierConfig


class TestPlanConfigTiers:
    """Tests for tier retrieval."""

    def test_get_tier_free(self):
        """Free tier should return correct config."""
        tier = PlanConfig.get_tier("free")
        assert isinstance(tier, TierConfig)
        assert tier.name == "Free"
        assert tier.price_monthly_cents == 0

    def test_get_tier_starter(self):
        """Starter tier should return correct config."""
        tier = PlanConfig.get_tier("starter")
        assert tier.name == "Starter"
        assert tier.price_monthly_cents == 2900

    def test_get_tier_pro(self):
        """Pro tier should return correct config."""
        tier = PlanConfig.get_tier("pro")
        assert tier.name == "Pro"
        assert tier.price_monthly_cents == 9900

    def test_get_tier_enterprise(self):
        """Enterprise tier should return correct config."""
        tier = PlanConfig.get_tier("enterprise")
        assert tier.name == "Enterprise"
        assert tier.price_monthly_cents == 0  # Custom pricing

    def test_get_tier_unknown_defaults_to_free(self):
        """Unknown tier should default to free."""
        tier = PlanConfig.get_tier("nonexistent")
        assert tier.name == "Free"

    def test_get_tier_case_insensitive(self):
        """get_tier should be case insensitive."""
        assert PlanConfig.get_tier("FREE").name == "Free"
        assert PlanConfig.get_tier("Pro").name == "Pro"
        assert PlanConfig.get_tier("STARTER").name == "Starter"


class TestPlanConfigLimits:
    """Tests for usage limits - validates values match deprecated TierLimits."""

    def test_free_limits(self):
        """Free tier limits should match original TierLimits."""
        assert PlanConfig.get_limit("free", "meetings_monthly") == 3
        assert PlanConfig.get_limit("free", "datasets_total") == 5
        assert PlanConfig.get_limit("free", "mentor_daily") == 10
        assert PlanConfig.get_limit("free", "api_daily") == 0

    def test_starter_limits(self):
        """Starter tier limits should match original TierLimits."""
        assert PlanConfig.get_limit("starter", "meetings_monthly") == 20
        assert PlanConfig.get_limit("starter", "datasets_total") == 25
        assert PlanConfig.get_limit("starter", "mentor_daily") == 50
        assert PlanConfig.get_limit("starter", "api_daily") == 100

    def test_pro_limits(self):
        """Pro tier limits should match original TierLimits."""
        assert PlanConfig.get_limit("pro", "meetings_monthly") == -1  # Unlimited
        assert PlanConfig.get_limit("pro", "datasets_total") == 100
        assert PlanConfig.get_limit("pro", "mentor_daily") == -1  # Unlimited
        assert PlanConfig.get_limit("pro", "api_daily") == 1000

    def test_enterprise_limits(self):
        """Enterprise tier should match pro limits."""
        assert PlanConfig.get_limit("enterprise", "meetings_monthly") == -1
        assert PlanConfig.get_limit("enterprise", "datasets_total") == 100
        assert PlanConfig.get_limit("enterprise", "mentor_daily") == -1
        assert PlanConfig.get_limit("enterprise", "api_daily") == 1000

    def test_get_limits_returns_dict(self):
        """get_limits should return all limits as dict."""
        limits = PlanConfig.get_limits("free")
        assert isinstance(limits, dict)
        assert limits["meetings_monthly"] == 3
        assert limits["datasets_total"] == 5
        assert limits["mentor_daily"] == 10
        assert limits["api_daily"] == 0

    def test_is_unlimited(self):
        """is_unlimited should return True for -1."""
        assert PlanConfig.is_unlimited(-1) is True
        assert PlanConfig.is_unlimited(0) is False
        assert PlanConfig.is_unlimited(100) is False


class TestPlanConfigFeatures:
    """Tests for feature flags - validates values match deprecated TierFeatureFlags."""

    def test_free_features(self):
        """Free tier features should match original TierFeatureFlags."""
        features = PlanConfig.get_features("free")
        assert features["meetings"] is True
        assert features["datasets"] is True
        assert features["mentor"] is True
        assert features["api_access"] is False
        assert features["priority_support"] is False
        assert features["advanced_analytics"] is False
        assert features["custom_personas"] is False

    def test_starter_features(self):
        """Starter tier features should match original TierFeatureFlags."""
        features = PlanConfig.get_features("starter")
        assert features["api_access"] is True
        assert features["advanced_analytics"] is True
        assert features["priority_support"] is False
        assert features["custom_personas"] is False

    def test_pro_features(self):
        """Pro tier features should match original TierFeatureFlags."""
        features = PlanConfig.get_features("pro")
        assert features["api_access"] is True
        assert features["priority_support"] is True
        assert features["advanced_analytics"] is True
        assert features["custom_personas"] is True

    def test_enterprise_features(self):
        """Enterprise tier should have same features as pro."""
        features = PlanConfig.get_features("enterprise")
        assert features["api_access"] is True
        assert features["priority_support"] is True
        assert features["advanced_analytics"] is True
        assert features["custom_personas"] is True

    def test_is_feature_enabled(self):
        """is_feature_enabled should check specific features."""
        assert PlanConfig.is_feature_enabled("free", "meetings") is True
        assert PlanConfig.is_feature_enabled("free", "api_access") is False
        assert PlanConfig.is_feature_enabled("pro", "api_access") is True

    def test_get_features_returns_copy(self):
        """get_features should return a copy, not the original dict."""
        features1 = PlanConfig.get_features("free")
        features2 = PlanConfig.get_features("free")
        features1["meetings"] = False
        assert features2["meetings"] is True  # Should not be affected


class TestPlanConfigBenchmarks:
    """Tests for benchmark limits - validates values match deprecated IndustryBenchmarkLimits."""

    def test_free_benchmark_limit(self):
        """Free tier should have 3 visible benchmarks."""
        assert PlanConfig.get_benchmark_limit("free") == 3

    def test_starter_benchmark_limit(self):
        """Starter tier should have 5 visible benchmarks."""
        assert PlanConfig.get_benchmark_limit("starter") == 5

    def test_pro_benchmark_limit(self):
        """Pro tier should have unlimited benchmarks."""
        assert PlanConfig.get_benchmark_limit("pro") == -1

    def test_enterprise_benchmark_limit(self):
        """Enterprise tier should have unlimited benchmarks."""
        assert PlanConfig.get_benchmark_limit("enterprise") == -1


class TestPlanConfigCost:
    """Tests for cost thresholds."""

    def test_free_cost_per_session(self):
        """Free tier should have $0.50 session cost limit."""
        assert PlanConfig.get_cost_per_session("free") == 0.50

    def test_starter_cost_per_session(self):
        """Starter tier should have $1.00 session cost limit."""
        assert PlanConfig.get_cost_per_session("starter") == 1.00

    def test_pro_cost_per_session(self):
        """Pro tier should have $2.00 session cost limit."""
        assert PlanConfig.get_cost_per_session("pro") == 2.00

    def test_enterprise_cost_per_session(self):
        """Enterprise tier should have $10.00 session cost limit."""
        assert PlanConfig.get_cost_per_session("enterprise") == 10.00


class TestPlanConfigBackwardCompat:
    """Tests for backward compatibility with billing.py PLAN_CONFIG format."""

    def test_get_plan_config_structure(self):
        """get_plan_config should return dict in expected format."""
        config = PlanConfig.get_plan_config()
        assert "free" in config
        assert "starter" in config
        assert "pro" in config
        assert "enterprise" in config

    def test_get_plan_config_free_tier(self):
        """Free tier should have correct structure."""
        config = PlanConfig.get_plan_config()["free"]
        assert config["name"] == "Free"
        assert config["price_monthly"] == 0
        assert config["meetings_limit"] == 3
        assert isinstance(config["features"], list)

    def test_get_plan_config_pro_unlimited(self):
        """Pro tier meetings_limit should be None (not -1) for API compat."""
        config = PlanConfig.get_plan_config()["pro"]
        assert config["meetings_limit"] is None  # None = unlimited in billing API

    def test_get_plan_config_cached(self):
        """get_plan_config should return cached value on second call."""
        config1 = PlanConfig.get_plan_config()
        config2 = PlanConfig.get_plan_config()
        assert config1 is config2  # Same object (cached)


class TestPlanConfigFairUsage:
    """Tests for fair usage limits."""

    def test_free_fair_usage_limits(self):
        """Free tier should have conservative fair usage limits."""
        limits = PlanConfig.get_fair_usage_limits("free")
        assert limits.mentor_chat == 0.50
        assert limits.dataset_qa == 0.25
        assert limits.competitor_analysis == 0.10
        assert limits.meeting == 0.50

    def test_starter_fair_usage_limits(self):
        """Starter tier should have higher fair usage limits."""
        limits = PlanConfig.get_fair_usage_limits("starter")
        assert limits.mentor_chat == 2.00
        assert limits.dataset_qa == 1.00
        assert limits.competitor_analysis == 0.50
        assert limits.meeting == 1.00

    def test_pro_fair_usage_limits(self):
        """Pro tier should have generous fair usage limits."""
        limits = PlanConfig.get_fair_usage_limits("pro")
        assert limits.mentor_chat == 10.00
        assert limits.dataset_qa == 5.00
        assert limits.competitor_analysis == 2.00
        assert limits.meeting == 2.00

    def test_enterprise_fair_usage_unlimited(self):
        """Enterprise tier should have unlimited fair usage."""
        limits = PlanConfig.get_fair_usage_limits("enterprise")
        assert limits.mentor_chat < 0  # Unlimited
        assert limits.dataset_qa < 0
        assert limits.competitor_analysis < 0
        assert limits.meeting < 0

    def test_get_fair_usage_limit_single_feature(self):
        """get_fair_usage_limit should return limit for specific feature."""
        assert PlanConfig.get_fair_usage_limit("free", "mentor_chat") == 0.50
        assert PlanConfig.get_fair_usage_limit("starter", "dataset_qa") == 1.00
        assert PlanConfig.get_fair_usage_limit("enterprise", "mentor_chat") < 0

    def test_is_fair_usage_unlimited(self):
        """is_fair_usage_unlimited should correctly identify unlimited limits."""
        assert PlanConfig.is_fair_usage_unlimited(-1.0) is True
        assert PlanConfig.is_fair_usage_unlimited(-0.1) is True
        assert PlanConfig.is_fair_usage_unlimited(0.0) is False
        assert PlanConfig.is_fair_usage_unlimited(0.50) is False

    def test_fair_usage_soft_cap_threshold(self):
        """Soft cap threshold should be 80%."""
        assert PlanConfig.FAIR_USAGE_SOFT_CAP_PCT == 0.80

    def test_fair_usage_hard_cap_threshold(self):
        """Hard cap threshold should be 100%."""
        assert PlanConfig.FAIR_USAGE_HARD_CAP_PCT == 1.00
