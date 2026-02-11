"""Tests for Industry Benchmarks API endpoints.

Tests tier-based benchmark filtering, comparison endpoint, and percentile calculations.
"""

from unittest.mock import patch

from backend.api.industry_insights import (
    BENCHMARK_DATA,
    LOWER_IS_BETTER_METRICS,
    BenchmarkCategory,
    calculate_percentile,
    get_benchmarks_for_industry,
    get_performance_status,
    get_stub_insights,
    get_upgrade_prompt,
    get_user_tier,
)
from bo1.billing import PlanConfig


class TestTierLimits:
    """Test tier-based benchmark limit constants via PlanConfig."""

    def test_free_tier_limit(self):
        """Free tier should allow 3 benchmarks."""
        assert PlanConfig.get_benchmark_limit("free") == 3

    def test_starter_tier_limit(self):
        """Starter tier should allow 5 benchmarks."""
        assert PlanConfig.get_benchmark_limit("starter") == 5

    def test_pro_tier_unlimited(self):
        """Pro tier should have unlimited (-1) benchmarks."""
        assert PlanConfig.get_benchmark_limit("pro") == -1

    def test_enterprise_tier_unlimited(self):
        """Enterprise tier should have unlimited benchmarks."""
        assert PlanConfig.get_benchmark_limit("enterprise") == -1

    def test_unknown_tier_defaults_to_free(self):
        """Unknown tier should default to free limit."""
        assert PlanConfig.get_benchmark_limit("unknown") == 3
        assert PlanConfig.get_benchmark_limit("") == 3


class TestGetStubInsights:
    """Test the get_stub_insights function with tier filtering."""

    def test_free_tier_limits_benchmarks(self):
        """Free tier should lock benchmarks beyond limit."""
        insights, locked_count = get_stub_insights("SaaS", "free")

        benchmarks = [i for i in insights if i.insight_type == "benchmark"]
        unlocked = [b for b in benchmarks if not b.locked]
        locked = [b for b in benchmarks if b.locked]

        assert len(unlocked) == 3
        assert locked_count == len(locked)
        assert locked_count == len(benchmarks) - 3

    def test_starter_tier_limits_benchmarks(self):
        """Starter tier should lock benchmarks beyond 5."""
        insights, locked_count = get_stub_insights("SaaS", "starter")

        benchmarks = [i for i in insights if i.insight_type == "benchmark"]
        unlocked = [b for b in benchmarks if not b.locked]

        assert len(unlocked) == 5
        assert locked_count == len(benchmarks) - 5

    def test_pro_tier_no_limits(self):
        """Pro tier should have no locked benchmarks."""
        insights, locked_count = get_stub_insights("SaaS", "pro")

        benchmarks = [i for i in insights if i.insight_type == "benchmark"]
        locked = [b for b in benchmarks if b.locked]

        assert len(locked) == 0
        assert locked_count == 0

    def test_trends_not_limited(self):
        """Trends should never be tier-limited."""
        insights, _ = get_stub_insights("SaaS", "free")

        trends = [i for i in insights if i.insight_type == "trend"]
        locked_trends = [t for t in trends if t.locked]

        assert len(locked_trends) == 0

    def test_best_practices_not_limited(self):
        """Best practices should never be tier-limited."""
        insights, _ = get_stub_insights("SaaS", "free")

        practices = [i for i in insights if i.insight_type == "best_practice"]
        locked_practices = [p for p in practices if p.locked]

        assert len(locked_practices) == 0


class TestGetBenchmarksForIndustry:
    """Test industry matching for benchmarks."""

    def test_direct_saas_match(self):
        """SaaS industry should return SaaS benchmarks."""
        benchmarks = get_benchmarks_for_industry("SaaS")
        assert len(benchmarks) == len(BENCHMARK_DATA["SaaS"])

    def test_case_insensitive_match(self):
        """Industry matching should be case-insensitive."""
        benchmarks = get_benchmarks_for_industry("saas")
        assert len(benchmarks) == len(BENCHMARK_DATA["SaaS"])

    def test_software_maps_to_saas(self):
        """Software industry should map to SaaS."""
        benchmarks = get_benchmarks_for_industry("B2B Software")
        assert len(benchmarks) == len(BENCHMARK_DATA["SaaS"])

    def test_ecommerce_match(self):
        """E-commerce variations should match."""
        benchmarks = get_benchmarks_for_industry("E-commerce")
        assert len(benchmarks) == len(BENCHMARK_DATA["E-commerce"])

        benchmarks = get_benchmarks_for_industry("Online Retail Store")
        assert len(benchmarks) == len(BENCHMARK_DATA["E-commerce"])

    def test_fintech_match(self):
        """Fintech variations should match."""
        benchmarks = get_benchmarks_for_industry("Fintech")
        assert len(benchmarks) == len(BENCHMARK_DATA["Fintech"])

        benchmarks = get_benchmarks_for_industry("Payment Processing")
        assert len(benchmarks) == len(BENCHMARK_DATA["Fintech"])

    def test_marketplace_match(self):
        """Marketplace variations should match."""
        benchmarks = get_benchmarks_for_industry("Marketplace")
        assert len(benchmarks) == len(BENCHMARK_DATA["Marketplace"])

    def test_unknown_defaults_to_saas(self):
        """Unknown industry should default to SaaS."""
        benchmarks = get_benchmarks_for_industry("Unknown Industry")
        assert len(benchmarks) == len(BENCHMARK_DATA["SaaS"])


class TestCalculatePercentile:
    """Test percentile calculation function."""

    def test_below_p25(self):
        """Value below P25 should be in 0-25 range."""
        percentile = calculate_percentile(10, 20, 40, 60)
        assert 0 <= percentile < 25

    def test_at_p25(self):
        """Value at P25 should be around 25."""
        percentile = calculate_percentile(20, 20, 40, 60)
        assert 20 <= percentile <= 30

    def test_at_median(self):
        """Value at median should be around 50."""
        percentile = calculate_percentile(40, 20, 40, 60)
        assert 45 <= percentile <= 55

    def test_at_p75(self):
        """Value at P75 should be around 75."""
        percentile = calculate_percentile(60, 20, 40, 60)
        assert 70 <= percentile <= 80

    def test_above_p75(self):
        """Value above P75 should be in 75-100 range."""
        percentile = calculate_percentile(80, 20, 40, 60)
        assert 75 <= percentile <= 100

    def test_lower_is_better(self):
        """Metrics where lower is better should invert percentile."""
        # For churn, 1% is better than 5%
        percentile_low = calculate_percentile(1, 5, 3, 1.5, lower_is_better=True)
        percentile_high = calculate_percentile(5, 5, 3, 1.5, lower_is_better=True)

        assert percentile_low > percentile_high

    def test_zero_values_handled(self):
        """Zero values should not cause division errors."""
        percentile = calculate_percentile(0, 0, 0.1, 0.2)
        assert percentile >= 0


class TestPerformanceStatus:
    """Test performance status derivation from percentile."""

    def test_below_average_status(self):
        """Percentile < 25 should be below_average."""
        assert get_performance_status(10) == "below_average"
        assert get_performance_status(24) == "below_average"

    def test_average_status(self):
        """Percentile 25-49 should be average."""
        assert get_performance_status(25) == "average"
        assert get_performance_status(49) == "average"

    def test_above_average_status(self):
        """Percentile 50-74 should be above_average."""
        assert get_performance_status(50) == "above_average"
        assert get_performance_status(74) == "above_average"

    def test_top_performer_status(self):
        """Percentile >= 75 should be top_performer."""
        assert get_performance_status(75) == "top_performer"
        assert get_performance_status(100) == "top_performer"


class TestGetUpgradePrompt:
    """Test upgrade prompt generation."""

    def test_no_prompt_when_no_locked(self):
        """No prompt when no benchmarks are locked."""
        assert get_upgrade_prompt("free", 0) is None
        assert get_upgrade_prompt("starter", 0) is None
        assert get_upgrade_prompt("pro", 0) is None

    def test_free_tier_prompt(self):
        """Free tier should get upgrade prompt."""
        prompt = get_upgrade_prompt("free", 5)
        assert prompt is not None
        assert "Starter" in prompt
        assert "Pro" in prompt

    def test_starter_tier_prompt(self):
        """Starter tier should get Pro upgrade prompt."""
        prompt = get_upgrade_prompt("starter", 3)
        assert prompt is not None
        assert "Pro" in prompt

    def test_pro_tier_no_prompt(self):
        """Pro tier should not get upgrade prompt even with locked count."""
        assert get_upgrade_prompt("pro", 5) is None


class TestBenchmarkCategories:
    """Test benchmark category enum and data structure."""

    def test_all_categories_defined(self):
        """All expected categories should be defined."""
        assert BenchmarkCategory.GROWTH.value == "growth"
        assert BenchmarkCategory.RETENTION.value == "retention"
        assert BenchmarkCategory.EFFICIENCY.value == "efficiency"
        assert BenchmarkCategory.ENGAGEMENT.value == "engagement"

    def test_benchmark_data_has_categories(self):
        """All benchmark data should have valid categories."""
        for _segment, benchmarks in BENCHMARK_DATA.items():
            for bm in benchmarks:
                assert "category" in bm
                assert bm["category"] in [c.value for c in BenchmarkCategory]


class TestLowerIsBetterMetrics:
    """Test metrics where lower values are better."""

    def test_churn_is_lower_is_better(self):
        """Churn should be a lower-is-better metric."""
        assert "monthly_churn" in LOWER_IS_BETTER_METRICS

    def test_cac_payback_is_lower_is_better(self):
        """CAC payback should be a lower-is-better metric."""
        assert "cac_payback" in LOWER_IS_BETTER_METRICS

    def test_cart_abandonment_is_lower_is_better(self):
        """Cart abandonment should be a lower-is-better metric."""
        assert "cart_abandonment" in LOWER_IS_BETTER_METRICS


class TestGetUserTier:
    """Test user tier retrieval with mocking."""

    @patch("backend.api.utils.db_helpers.execute_query")
    def test_returns_user_tier(self, mock_query):
        """Should return user's subscription tier from database."""
        mock_query.return_value = {"subscription_tier": "pro"}
        tier = get_user_tier("user-123")
        assert tier == "pro"

    @patch("backend.api.utils.db_helpers.execute_query")
    def test_defaults_to_free_on_error(self, mock_query):
        """Should default to free tier on database error."""
        mock_query.side_effect = Exception("DB error")
        tier = get_user_tier("user-123")
        assert tier == "free"

    @patch("backend.api.utils.db_helpers.execute_query")
    def test_defaults_to_free_when_not_found(self, mock_query):
        """Should default to free when user not found."""
        mock_query.return_value = None
        tier = get_user_tier("user-123")
        assert tier == "free"

    @patch("backend.api.utils.db_helpers.execute_query")
    def test_defaults_to_free_when_tier_null(self, mock_query):
        """Should default to free when tier is null."""
        mock_query.return_value = {"subscription_tier": None}
        tier = get_user_tier("user-123")
        assert tier == "free"
