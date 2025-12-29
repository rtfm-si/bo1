"""Centralized plan configuration for all tier limits and features.

This module is the single source of truth for:
- Subscription tier definitions (free, starter, pro, enterprise)
- Usage limits (meetings, datasets, mentor chats, API calls)
- Feature flags per tier
- Pricing information
- Benchmark visibility limits
- Cost thresholds

Now reads core pricing from database (billing_products, billing_prices)
with fallback to hardcoded defaults for operational fields.

Usage:
    from bo1.billing import PlanConfig

    # Get all info for a tier
    tier = PlanConfig.get_tier("pro")

    # Check specific limit
    limit = PlanConfig.get_limit("free", "meetings_monthly")

    # Check feature availability
    enabled = PlanConfig.is_feature_enabled("starter", "api_access")
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FairUsageLimits:
    """Daily cost limits per feature for fair usage capping.

    All values in USD. -1.0 = unlimited.
    """

    mentor_chat: float  # Daily limit for mentor chat LLM costs
    dataset_qa: float  # Daily limit for dataset Q&A LLM costs
    competitor_analysis: float  # Daily limit for competitor detection/enrichment
    meeting: float  # Daily limit per meeting (not total)


@dataclass(frozen=True)
class TierConfig:
    """Configuration for a single subscription tier."""

    # Display info
    name: str
    price_monthly_cents: int  # 0 for free, custom pricing for enterprise
    features_display: list[str]  # Marketing feature list

    # Usage limits (-1 = unlimited)
    meetings_monthly: int
    datasets_total: int
    mentor_daily: int
    api_daily: int
    benchmarks_visible: int  # -1 = unlimited
    seo_analyses_monthly: int  # SEO trend analyses per month
    seo_articles_monthly: int  # SEO article generations per month
    peer_benchmarks_visible: int  # Peer comparison metrics visible (-1 = unlimited)
    marketing_assets_total: int  # Marketing collateral bank storage limit

    # Cost limits
    cost_per_session: float

    # Fair usage daily cost limits per feature
    fair_usage: FairUsageLimits

    # Feature flags
    features: dict[str, bool]


@dataclass(frozen=True)
class MeetingBundleConfig:
    """Configuration for a one-time meeting bundle."""

    meetings: int
    price_cents: int  # In GBP pence
    price_id_env_var: str  # Environment variable for Stripe price ID


class PlanConfig:
    """Centralized plan configuration.

    Reads core pricing from database with fallback to hardcoded defaults.
    Caches DB data for 5 minutes to avoid repeated queries.
    """

    # Cache settings
    _db_cache: dict[str, TierConfig] | None = None
    _db_cache_time: float = 0
    _bundle_cache: dict[int, MeetingBundleConfig] | None = None
    CACHE_TTL: int = 300  # 5 minutes

    # Fair usage soft warning threshold (percentage of daily limit)
    FAIR_USAGE_SOFT_CAP_PCT: float = 0.80  # Warn at 80%
    # Fair usage hard cap threshold (percentage of daily limit)
    FAIR_USAGE_HARD_CAP_PCT: float = 1.00  # Block at 100%

    # Default operational settings not stored in DB
    _TIER_DEFAULTS: dict[str, dict[str, Any]] = {
        "free": {
            "benchmarks_visible": 3,
            "seo_analyses_monthly": 1,
            "seo_articles_monthly": 1,
            "peer_benchmarks_visible": 3,
            "marketing_assets_total": 10,
            "cost_per_session": 0.50,
            "fair_usage": FairUsageLimits(
                mentor_chat=0.50,
                dataset_qa=0.25,
                competitor_analysis=0.10,
                meeting=0.50,
            ),
            "features_display": [
                "3 meetings per month",
                "Basic expert panel",
                "Community support",
            ],
        },
        "starter": {
            "benchmarks_visible": 5,
            "seo_analyses_monthly": 5,
            "seo_articles_monthly": 5,
            "peer_benchmarks_visible": 5,
            "marketing_assets_total": 50,
            "cost_per_session": 1.00,
            "fair_usage": FairUsageLimits(
                mentor_chat=2.00,
                dataset_qa=1.00,
                competitor_analysis=0.50,
                meeting=1.00,
            ),
            "features_display": [
                "20 meetings per month",
                "All expert personas",
                "Email support",
                "Priority processing",
            ],
        },
        "pro": {
            "benchmarks_visible": -1,
            "seo_analyses_monthly": -1,
            "seo_articles_monthly": -1,
            "peer_benchmarks_visible": -1,
            "marketing_assets_total": 500,
            "cost_per_session": 2.00,
            "fair_usage": FairUsageLimits(
                mentor_chat=10.00,
                dataset_qa=5.00,
                competitor_analysis=2.00,
                meeting=2.00,
            ),
            "features_display": [
                "Unlimited meetings",
                "All expert personas",
                "Priority support",
                "API access",
                "Custom expert personas",
            ],
        },
        "enterprise": {
            "benchmarks_visible": -1,
            "seo_analyses_monthly": -1,
            "seo_articles_monthly": -1,
            "peer_benchmarks_visible": -1,
            "marketing_assets_total": -1,
            "cost_per_session": 10.00,
            "fair_usage": FairUsageLimits(
                mentor_chat=-1.0,
                dataset_qa=-1.0,
                competitor_analysis=-1.0,
                meeting=-1.0,
            ),
            "features_display": [
                "Everything in Pro",
                "Dedicated support",
                "SLA guarantee",
                "Custom integrations",
                "On-premise option",
            ],
        },
    }

    # Hardcoded fallback (used if DB unavailable)
    TIERS: dict[str, TierConfig] = {
        "free": TierConfig(
            name="Free",
            price_monthly_cents=0,
            features_display=[
                "3 meetings per month",
                "Basic expert panel",
                "Community support",
            ],
            meetings_monthly=3,
            datasets_total=5,
            mentor_daily=10,
            api_daily=0,
            benchmarks_visible=3,
            seo_analyses_monthly=1,
            seo_articles_monthly=1,
            peer_benchmarks_visible=3,
            marketing_assets_total=10,
            cost_per_session=0.50,
            fair_usage=FairUsageLimits(
                mentor_chat=0.50,  # $0.50/day for mentor chat
                dataset_qa=0.25,  # $0.25/day for dataset Q&A
                competitor_analysis=0.10,  # $0.10/day for competitor analysis
                meeting=0.50,  # $0.50/meeting
            ),
            features={
                "meetings": True,
                "datasets": True,
                "mentor": True,
                "api_access": False,
                "priority_support": False,
                "advanced_analytics": False,
                "custom_personas": False,
                "session_export": True,
                "session_sharing": True,
                "seo_tools": True,
                "peer_benchmarks": True,
            },
        ),
        "starter": TierConfig(
            name="Starter",
            price_monthly_cents=2900,  # $29.00
            features_display=[
                "20 meetings per month",
                "All expert personas",
                "Email support",
                "Priority processing",
            ],
            meetings_monthly=20,
            datasets_total=25,
            mentor_daily=50,
            api_daily=100,
            benchmarks_visible=5,
            seo_analyses_monthly=5,
            seo_articles_monthly=5,
            peer_benchmarks_visible=5,
            marketing_assets_total=50,
            cost_per_session=1.00,
            fair_usage=FairUsageLimits(
                mentor_chat=2.00,  # $2/day for mentor chat
                dataset_qa=1.00,  # $1/day for dataset Q&A
                competitor_analysis=0.50,  # $0.50/day for competitor analysis
                meeting=1.00,  # $1/meeting
            ),
            features={
                "meetings": True,
                "datasets": True,
                "mentor": True,
                "api_access": True,
                "priority_support": False,
                "advanced_analytics": True,
                "custom_personas": False,
                "session_export": True,
                "session_sharing": True,
                "seo_tools": True,
                "peer_benchmarks": True,
            },
        ),
        "pro": TierConfig(
            name="Pro",
            price_monthly_cents=9900,  # $99.00
            features_display=[
                "Unlimited meetings",
                "All expert personas",
                "Priority support",
                "API access",
                "Custom expert personas",
            ],
            meetings_monthly=-1,  # Unlimited
            datasets_total=100,
            mentor_daily=-1,  # Unlimited
            api_daily=1000,
            benchmarks_visible=-1,  # Unlimited
            seo_analyses_monthly=-1,  # Unlimited
            seo_articles_monthly=-1,  # Unlimited
            peer_benchmarks_visible=-1,  # Unlimited
            marketing_assets_total=500,
            cost_per_session=2.00,
            fair_usage=FairUsageLimits(
                mentor_chat=10.00,  # $10/day for mentor chat
                dataset_qa=5.00,  # $5/day for dataset Q&A
                competitor_analysis=2.00,  # $2/day for competitor analysis
                meeting=2.00,  # $2/meeting
            ),
            features={
                "meetings": True,
                "datasets": True,
                "mentor": True,
                "api_access": True,
                "priority_support": True,
                "advanced_analytics": True,
                "custom_personas": True,
                "session_export": True,
                "session_sharing": True,
                "seo_tools": True,
                "peer_benchmarks": True,
            },
        ),
        "enterprise": TierConfig(
            name="Enterprise",
            price_monthly_cents=0,  # Custom pricing
            features_display=[
                "Everything in Pro",
                "Dedicated support",
                "SLA guarantee",
                "Custom integrations",
                "On-premise option",
            ],
            meetings_monthly=-1,  # Unlimited
            datasets_total=100,
            mentor_daily=-1,  # Unlimited
            api_daily=1000,
            benchmarks_visible=-1,  # Unlimited
            seo_analyses_monthly=-1,  # Unlimited
            seo_articles_monthly=-1,  # Unlimited
            peer_benchmarks_visible=-1,  # Unlimited
            marketing_assets_total=-1,  # Unlimited
            cost_per_session=10.00,
            fair_usage=FairUsageLimits(
                mentor_chat=-1.0,  # Unlimited
                dataset_qa=-1.0,  # Unlimited
                competitor_analysis=-1.0,  # Unlimited
                meeting=-1.0,  # Unlimited per meeting
            ),
            features={
                "meetings": True,
                "datasets": True,
                "mentor": True,
                "api_access": True,
                "priority_support": True,
                "advanced_analytics": True,
                "custom_personas": True,
                "session_export": True,
                "session_sharing": True,
                "seo_tools": True,
                "peer_benchmarks": True,
            },
        ),
    }

    # Meeting bundles: one-time purchases (£10/meeting)
    MEETING_BUNDLES: dict[int, MeetingBundleConfig] = {
        1: MeetingBundleConfig(
            meetings=1,
            price_cents=1000,  # £10
            price_id_env_var="STRIPE_PRICE_BUNDLE_1",
        ),
        3: MeetingBundleConfig(
            meetings=3,
            price_cents=3000,  # £30
            price_id_env_var="STRIPE_PRICE_BUNDLE_3",
        ),
        5: MeetingBundleConfig(
            meetings=5,
            price_cents=5000,  # £50
            price_id_env_var="STRIPE_PRICE_BUNDLE_5",
        ),
        9: MeetingBundleConfig(
            meetings=9,
            price_cents=9000,  # £90
            price_id_env_var="STRIPE_PRICE_BUNDLE_9",
        ),
    }

    # Mapping for API billing endpoints (backward compat with PLAN_CONFIG format)
    _PLAN_CONFIG_COMPAT: dict[str, dict[str, Any]] | None = None

    @classmethod
    def _load_from_db(cls) -> dict[str, TierConfig]:
        """Load tier configs from database.

        Returns dict of slug -> TierConfig, merging DB data with operational defaults.
        """
        try:
            from bo1.state.database import db_session

            tiers: dict[str, TierConfig] = {}

            with db_session() as conn:
                with conn.cursor() as cur:
                    # Load subscription products
                    cur.execute("""
                        SELECT bp.slug, bp.name, bp.description,
                               bp.meetings_monthly, bp.datasets_total,
                               bp.mentor_daily, bp.api_daily, bp.features,
                               pr.amount_cents
                        FROM billing_products bp
                        LEFT JOIN billing_prices pr ON pr.product_id = bp.id AND pr.active = true
                        WHERE bp.type = 'subscription' AND bp.active = true
                        ORDER BY bp.display_order
                    """)
                    products = cur.fetchall()

                    for row in products:
                        slug = row["slug"]
                        defaults = cls._TIER_DEFAULTS.get(slug, cls._TIER_DEFAULTS["free"])

                        # Merge DB features with any missing defaults
                        features = row["features"] or {}
                        default_features = {
                            "meetings": True,
                            "datasets": True,
                            "mentor": True,
                            "api_access": False,
                            "priority_support": False,
                            "advanced_analytics": False,
                            "custom_personas": False,
                            "session_export": True,
                            "session_sharing": True,
                            "seo_tools": True,
                            "peer_benchmarks": True,
                        }
                        default_features.update(features)

                        tiers[slug] = TierConfig(
                            name=row["name"],
                            price_monthly_cents=row["amount_cents"] or 0,
                            features_display=defaults["features_display"],
                            meetings_monthly=row["meetings_monthly"] or 0,
                            datasets_total=row["datasets_total"] or 0,
                            mentor_daily=row["mentor_daily"] or 0,
                            api_daily=row["api_daily"] or 0,
                            benchmarks_visible=defaults["benchmarks_visible"],
                            seo_analyses_monthly=defaults["seo_analyses_monthly"],
                            seo_articles_monthly=defaults["seo_articles_monthly"],
                            peer_benchmarks_visible=defaults["peer_benchmarks_visible"],
                            marketing_assets_total=defaults["marketing_assets_total"],
                            cost_per_session=defaults["cost_per_session"],
                            fair_usage=defaults["fair_usage"],
                            features=default_features,
                        )

            return tiers if tiers else cls.TIERS

        except Exception as e:
            logger.warning(f"Failed to load billing from DB, using defaults: {e}")
            return cls.TIERS

    @classmethod
    def _load_bundles_from_db(cls) -> dict[int, MeetingBundleConfig]:
        """Load meeting bundles from database."""
        try:
            from bo1.state.database import db_session

            bundles: dict[int, MeetingBundleConfig] = {}

            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        SELECT bp.slug, bp.meetings_monthly,
                               pr.amount_cents, pr.stripe_price_id
                        FROM billing_products bp
                        JOIN billing_prices pr ON pr.product_id = bp.id AND pr.active = true
                        WHERE bp.type = 'one_time' AND bp.active = true
                        ORDER BY bp.display_order
                    """)
                    products = cur.fetchall()

                    for row in products:
                        meetings = row["meetings_monthly"] or 0
                        if meetings > 0:
                            bundles[meetings] = MeetingBundleConfig(
                                meetings=meetings,
                                price_cents=row["amount_cents"] or 0,
                                price_id_env_var=f"STRIPE_PRICE_BUNDLE_{meetings}",
                            )

            return bundles if bundles else cls.MEETING_BUNDLES

        except Exception as e:
            logger.warning(f"Failed to load bundles from DB, using defaults: {e}")
            return cls.MEETING_BUNDLES

    @classmethod
    def _get_cached_tiers(cls) -> dict[str, TierConfig]:
        """Get tiers with caching."""
        now = time.time()
        if cls._db_cache is None or (now - cls._db_cache_time) > cls.CACHE_TTL:
            cls._db_cache = cls._load_from_db()
            cls._db_cache_time = now
        return cls._db_cache

    @classmethod
    def _get_cached_bundles(cls) -> dict[int, MeetingBundleConfig]:
        """Get bundles with caching."""
        now = time.time()
        if cls._bundle_cache is None or (now - cls._db_cache_time) > cls.CACHE_TTL:
            cls._bundle_cache = cls._load_bundles_from_db()
        return cls._bundle_cache

    @classmethod
    def invalidate_cache(cls) -> None:
        """Invalidate the cache to force reload from DB."""
        cls._db_cache = None
        cls._bundle_cache = None
        cls._db_cache_time = 0

    @classmethod
    def get_tier(cls, tier: str) -> TierConfig:
        """Get full configuration for a tier.

        Args:
            tier: Subscription tier name (free, starter, pro, enterprise)

        Returns:
            TierConfig with all tier settings
        """
        tiers = cls._get_cached_tiers()
        return tiers.get(tier.lower(), tiers.get("free", cls.TIERS["free"]))

    @classmethod
    def get_limit(cls, tier: str, limit_key: str) -> int:
        """Get a specific limit for a tier.

        Args:
            tier: Subscription tier
            limit_key: One of: meetings_monthly, datasets_total, mentor_daily,
                       api_daily, benchmarks_visible

        Returns:
            Limit value (-1 = unlimited)
        """
        config = cls.get_tier(tier)
        return getattr(config, limit_key, 0)

    @classmethod
    def get_limits(cls, tier: str) -> dict[str, int]:
        """Get all limits for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Dict with meetings_monthly, datasets_total, mentor_daily, api_daily
        """
        config = cls.get_tier(tier)
        return {
            "meetings_monthly": config.meetings_monthly,
            "datasets_total": config.datasets_total,
            "mentor_daily": config.mentor_daily,
            "api_daily": config.api_daily,
        }

    @classmethod
    def get_features(cls, tier: str) -> dict[str, bool]:
        """Get all feature flags for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Dict of feature name -> enabled
        """
        config = cls.get_tier(tier)
        return config.features.copy()

    @classmethod
    def is_feature_enabled(cls, tier: str, feature: str) -> bool:
        """Check if a feature is enabled for a tier.

        Args:
            tier: Subscription tier
            feature: Feature name

        Returns:
            True if feature is enabled
        """
        config = cls.get_tier(tier)
        return config.features.get(feature, False)

    @classmethod
    def is_unlimited(cls, limit: int) -> bool:
        """Check if a limit value represents unlimited.

        Args:
            limit: Limit value

        Returns:
            True if limit is -1 (unlimited)
        """
        return limit == -1

    @classmethod
    def get_cost_per_session(cls, tier: str) -> float:
        """Get cost limit per session for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Maximum cost per session in USD
        """
        config = cls.get_tier(tier)
        return config.cost_per_session

    @classmethod
    def get_plan_config(cls) -> dict[str, dict[str, Any]]:
        """Get billing API compatible config (backward compat).

        Returns dict in format expected by billing.py endpoints:
        {
            "free": {
                "name": "Free",
                "price_monthly": 0,
                "meetings_limit": 3,
                "features": [...]
            }
        }
        """
        if cls._PLAN_CONFIG_COMPAT is None:
            cls._PLAN_CONFIG_COMPAT = {}
            for tier_name, config in cls.TIERS.items():
                cls._PLAN_CONFIG_COMPAT[tier_name] = {
                    "name": config.name,
                    "price_monthly": config.price_monthly_cents,
                    "meetings_limit": config.meetings_monthly
                    if config.meetings_monthly != -1
                    else None,
                    "features": config.features_display,
                }
        return cls._PLAN_CONFIG_COMPAT

    @classmethod
    def get_benchmark_limit(cls, tier: str) -> int:
        """Get benchmark visibility limit for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Number of benchmarks visible (-1 for unlimited)
        """
        config = cls.get_tier(tier)
        return config.benchmarks_visible

    @classmethod
    def get_seo_analyses_limit(cls, tier: str) -> int:
        """Get SEO analyses limit for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Number of SEO analyses per month (-1 for unlimited)
        """
        config = cls.get_tier(tier)
        return config.seo_analyses_monthly

    @classmethod
    def get_seo_articles_limit(cls, tier: str) -> int:
        """Get SEO articles generation limit for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Number of SEO article generations per month (-1 for unlimited)
        """
        config = cls.get_tier(tier)
        return config.seo_articles_monthly

    @classmethod
    def get_marketing_assets_limit(cls, tier: str) -> int:
        """Get marketing assets storage limit for a tier.

        Args:
            tier: Subscription tier

        Returns:
            Maximum number of marketing assets allowed (-1 for unlimited)
        """
        config = cls.get_tier(tier)
        return config.marketing_assets_total

    @classmethod
    def get_meeting_bundle(cls, meetings: int) -> MeetingBundleConfig | None:
        """Get meeting bundle config by size.

        Args:
            meetings: Number of meetings in bundle (1, 3, 5, or 9)

        Returns:
            MeetingBundleConfig or None if invalid size
        """
        bundles = cls._get_cached_bundles()
        return bundles.get(meetings)

    @classmethod
    def get_all_bundles(cls) -> list[MeetingBundleConfig]:
        """Get all available meeting bundles.

        Returns:
            List of MeetingBundleConfig sorted by size
        """
        bundles = cls._get_cached_bundles()
        return [bundles[k] for k in sorted(bundles.keys())]

    @classmethod
    def get_meetings_for_price_id(cls, price_id: str) -> int | None:
        """Get number of meetings for a bundle price ID.

        Args:
            price_id: Stripe price ID

        Returns:
            Number of meetings or None if not a bundle
        """
        import os

        # First try DB lookup
        try:
            from bo1.state.database import db_session

            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT bp.meetings_monthly
                        FROM billing_prices pr
                        JOIN billing_products bp ON bp.id = pr.product_id
                        WHERE pr.stripe_price_id = %s AND bp.type = 'one_time'
                    """,
                        (price_id,),
                    )
                    row = cur.fetchone()
                    if row and row["meetings_monthly"] is not None:
                        return int(row["meetings_monthly"])
        except Exception:  # noqa: BLE001, S110
            pass  # Fall through to env var lookup

        # Fall back to env var lookup
        for bundle in cls.MEETING_BUNDLES.values():
            env_price = os.environ.get(bundle.price_id_env_var)
            if env_price and env_price == price_id:
                return bundle.meetings
        return None

    @classmethod
    def get_fair_usage_limits(cls, tier: str) -> FairUsageLimits:
        """Get fair usage limits for a tier.

        Args:
            tier: Subscription tier

        Returns:
            FairUsageLimits with daily cost caps per feature
        """
        config = cls.get_tier(tier)
        return config.fair_usage

    @classmethod
    def get_fair_usage_limit(cls, tier: str, feature: str) -> float:
        """Get fair usage daily limit for a specific feature.

        Args:
            tier: Subscription tier
            feature: Feature name (mentor_chat, dataset_qa, competitor_analysis, meeting)

        Returns:
            Daily cost limit in USD (-1.0 for unlimited)
        """
        limits = cls.get_fair_usage_limits(tier)
        return getattr(limits, feature, -1.0)

    @classmethod
    def is_fair_usage_unlimited(cls, limit: float) -> bool:
        """Check if a fair usage limit is unlimited.

        Args:
            limit: Limit value

        Returns:
            True if limit is -1.0 (unlimited)
        """
        return limit < 0
