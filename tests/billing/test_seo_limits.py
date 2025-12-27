"""Tests for SEO analyses limits in PlanConfig.

Validates that SEO analyses limits are correctly configured for all tiers.
"""

from bo1.billing import PlanConfig


class TestSeoAnalysesLimits:
    """Tests for SEO analyses limits per tier."""

    def test_free_tier_seo_limit(self):
        """Free tier should have 1 SEO analysis per month."""
        assert PlanConfig.get_seo_analyses_limit("free") == 1

    def test_starter_tier_seo_limit(self):
        """Starter tier should have 5 SEO analyses per month."""
        assert PlanConfig.get_seo_analyses_limit("starter") == 5

    def test_pro_tier_seo_limit(self):
        """Pro tier should have unlimited SEO analyses."""
        assert PlanConfig.get_seo_analyses_limit("pro") == -1

    def test_enterprise_tier_seo_limit(self):
        """Enterprise tier should have unlimited SEO analyses."""
        assert PlanConfig.get_seo_analyses_limit("enterprise") == -1

    def test_seo_analyses_in_tier_config(self):
        """Verify seo_analyses_monthly is accessible via tier config."""
        tier = PlanConfig.get_tier("free")
        assert hasattr(tier, "seo_analyses_monthly")
        assert tier.seo_analyses_monthly == 1


class TestSeoToolsFeatureFlag:
    """Tests for SEO tools feature flag per tier."""

    def test_free_tier_has_seo_tools(self):
        """Free tier should have SEO tools enabled."""
        assert PlanConfig.is_feature_enabled("free", "seo_tools") is True

    def test_starter_tier_has_seo_tools(self):
        """Starter tier should have SEO tools enabled."""
        assert PlanConfig.is_feature_enabled("starter", "seo_tools") is True

    def test_pro_tier_has_seo_tools(self):
        """Pro tier should have SEO tools enabled."""
        assert PlanConfig.is_feature_enabled("pro", "seo_tools") is True

    def test_enterprise_tier_has_seo_tools(self):
        """Enterprise tier should have SEO tools enabled."""
        assert PlanConfig.is_feature_enabled("enterprise", "seo_tools") is True

    def test_seo_tools_in_features_dict(self):
        """Verify seo_tools is in the features dict."""
        features = PlanConfig.get_features("free")
        assert "seo_tools" in features
        assert features["seo_tools"] is True


class TestSeoUnlimitedCheck:
    """Tests for is_unlimited helper with SEO limits."""

    def test_free_tier_is_not_unlimited(self):
        """Free tier SEO limit is not unlimited."""
        limit = PlanConfig.get_seo_analyses_limit("free")
        assert PlanConfig.is_unlimited(limit) is False

    def test_starter_tier_is_not_unlimited(self):
        """Starter tier SEO limit is not unlimited."""
        limit = PlanConfig.get_seo_analyses_limit("starter")
        assert PlanConfig.is_unlimited(limit) is False

    def test_pro_tier_is_unlimited(self):
        """Pro tier SEO limit is unlimited."""
        limit = PlanConfig.get_seo_analyses_limit("pro")
        assert PlanConfig.is_unlimited(limit) is True

    def test_enterprise_tier_is_unlimited(self):
        """Enterprise tier SEO limit is unlimited."""
        limit = PlanConfig.get_seo_analyses_limit("enterprise")
        assert PlanConfig.is_unlimited(limit) is True
