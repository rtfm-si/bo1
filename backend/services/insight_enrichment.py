"""Insight enrichment service for adding market context to user insights.

When a user saves a metric insight (e.g., "Our CAC is $50"), this service
finds industry benchmarks to provide market context (e.g., "Your CAC is
in the 25th percentile for SaaS").

Features:
- Uses IndustryBenchmarkResearcher for benchmark data
- Calculates percentile position relative to industry
- Generates human-readable comparison text
- Caches enrichment results in insight's market_context field
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from backend.services.industry_benchmark_researcher import (
    BenchmarkMetric,
    IndustryBenchmarkResearcher,
)

logger = logging.getLogger(__name__)

# Mapping from metric_key to benchmark metric names
# Maps user-facing keys to industry benchmark field names
METRIC_KEY_TO_BENCHMARK: dict[str, list[str]] = {
    "mrr": ["mrr", "monthly_recurring_revenue"],
    "arr": ["arr", "annual_recurring_revenue"],
    "cac": ["cac", "customer_acquisition_cost"],
    "ltv": ["ltv", "customer_lifetime_value", "clv"],
    "ltv_cac_ratio": ["ltv_cac_ratio", "ltv/cac", "ltv_cac"],
    "churn": ["churn", "churn_rate", "monthly_churn"],
    "nps": ["nps", "net_promoter_score"],
    "gross_margin": ["gross_margin", "gross_margin_percent"],
    "burn_rate": ["burn_rate", "monthly_burn"],
    "runway": ["runway", "runway_months"],
    "aov": ["aov", "average_order_value"],
    "conversion_rate": ["conversion_rate", "conversion"],
    "return_rate": ["return_rate", "returns"],
}


@dataclass
class MarketContextResult:
    """Result of insight enrichment with market context."""

    benchmark_value: float | None = None
    benchmark_percentile: str | None = None  # "p25", "p50", "p75"
    percentile_position: int | None = None  # 0-100
    comparison_text: str | None = None  # Human-readable comparison
    source_url: str | None = None
    enriched_at: datetime | None = None
    confidence: float = 0.0


class InsightEnrichmentService:
    """Enriches user insights with market benchmark context."""

    def __init__(self) -> None:
        """Initialize the enrichment service."""
        self.researcher = IndustryBenchmarkResearcher()

    async def enrich_insight(
        self,
        metric_key: str,
        metric_value: float,
        industry: str,
    ) -> MarketContextResult | None:
        """Enrich a metric insight with market context.

        Args:
            metric_key: The metric identifier (e.g., "cac", "churn")
            metric_value: The user's metric value
            industry: User's industry for benchmark lookup

        Returns:
            MarketContextResult with benchmark comparison, or None if unavailable
        """
        if not industry:
            logger.debug("No industry provided, skipping enrichment")
            return None

        # Get industry benchmarks
        benchmarks = await self.researcher.get_or_research_benchmarks(industry)
        if not benchmarks or not benchmarks.metrics:
            logger.debug(f"No benchmarks found for industry: {industry}")
            return None

        # Find matching benchmark metric
        matching_benchmark = self._find_matching_benchmark(metric_key, benchmarks.metrics)
        if not matching_benchmark:
            logger.debug(f"No matching benchmark for metric: {metric_key}")
            return None

        # Calculate percentile position
        percentile_position, benchmark_percentile, benchmark_value = self._calculate_percentile(
            metric_value, matching_benchmark
        )

        if percentile_position is None:
            logger.debug(f"Could not calculate percentile for {metric_key}")
            return None

        # Generate comparison text
        comparison_text = self._generate_comparison_text(
            metric_key=metric_key,
            user_value=metric_value,
            percentile_position=percentile_position,
            industry=industry,
        )

        return MarketContextResult(
            benchmark_value=benchmark_value,
            benchmark_percentile=benchmark_percentile,
            percentile_position=percentile_position,
            comparison_text=comparison_text,
            source_url=matching_benchmark.source_url,
            enriched_at=datetime.now(UTC),
            confidence=matching_benchmark.confidence,
        )

    def _find_matching_benchmark(
        self, metric_key: str, metrics: list[BenchmarkMetric]
    ) -> BenchmarkMetric | None:
        """Find a benchmark metric matching the user's metric key."""
        # Get possible benchmark names for this metric
        possible_names = METRIC_KEY_TO_BENCHMARK.get(metric_key.lower(), [metric_key.lower()])

        for metric in metrics:
            metric_name_lower = metric.metric.lower().replace(" ", "_")
            if metric_name_lower in possible_names:
                return metric
            # Also check display name
            display_lower = metric.display_name.lower().replace(" ", "_")
            if display_lower in possible_names:
                return metric

        return None

    def _calculate_percentile(
        self, user_value: float, benchmark: BenchmarkMetric
    ) -> tuple[int | None, str | None, float | None]:
        """Calculate user's percentile position relative to benchmark.

        Returns:
            (percentile_position, benchmark_percentile_name, benchmark_value)
        """
        # Get available percentile values
        p25 = benchmark.p25
        p50 = benchmark.p50
        p75 = benchmark.p75

        # Need at least median to calculate
        if p50 is None:
            return None, None, None

        # Determine if lower is better (costs, churn) or higher is better (LTV, margin)
        lower_is_better = benchmark.metric.lower() in (
            "cac",
            "customer_acquisition_cost",
            "churn",
            "churn_rate",
            "monthly_churn",
            "burn_rate",
            "monthly_burn",
            "return_rate",
            "returns",
        )

        # Calculate percentile position (0-100)
        if p25 is not None and p75 is not None:
            # Full IQR available - interpolate position
            if lower_is_better:
                # Lower value = higher percentile
                if user_value <= p25:
                    percentile = 75 + int(25 * (p25 - user_value) / max(p25, 1))
                elif user_value <= p50:
                    percentile = 50 + int(25 * (p50 - user_value) / max(p50 - p25, 1))
                elif user_value <= p75:
                    percentile = 25 + int(25 * (p75 - user_value) / max(p75 - p50, 1))
                else:
                    percentile = max(0, 25 - int(25 * (user_value - p75) / max(p75, 1)))
            else:
                # Higher value = higher percentile
                if user_value >= p75:
                    percentile = 75 + min(25, int(25 * (user_value - p75) / max(p75, 1)))
                elif user_value >= p50:
                    percentile = 50 + int(25 * (user_value - p50) / max(p75 - p50, 1))
                elif user_value >= p25:
                    percentile = 25 + int(25 * (user_value - p25) / max(p50 - p25, 1))
                else:
                    percentile = max(0, int(25 * user_value / max(p25, 1)))

            # Clamp to 0-100
            percentile = max(0, min(100, percentile))

            # Return closest benchmark percentile
            if percentile >= 62:
                return percentile, "p75", p75
            elif percentile >= 37:
                return percentile, "p50", p50
            else:
                return percentile, "p25", p25
        else:
            # Only median available - simple above/below comparison
            if lower_is_better:
                if user_value < p50:
                    return 60, "p50", p50  # Above median (better)
                elif user_value > p50:
                    return 40, "p50", p50  # Below median (worse)
                else:
                    return 50, "p50", p50  # At median
            else:
                if user_value > p50:
                    return 60, "p50", p50  # Above median (better)
                elif user_value < p50:
                    return 40, "p50", p50  # Below median (worse)
                else:
                    return 50, "p50", p50  # At median

    def _generate_comparison_text(
        self,
        metric_key: str,
        user_value: float,
        percentile_position: int,
        industry: str,
    ) -> str:
        """Generate human-readable comparison text."""
        # Format the value based on metric type
        value_str = self._format_metric_value(metric_key, user_value)

        # Ordinal suffix for percentile
        def ordinal(n: int) -> str:
            if 11 <= n % 100 <= 13:
                suffix = "th"
            else:
                suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
            return f"{n}{suffix}"

        percentile_str = ordinal(percentile_position)

        # Performance description
        if percentile_position >= 75:
            performance = "excellent"
        elif percentile_position >= 50:
            performance = "above average"
        elif percentile_position >= 25:
            performance = "below average"
        else:
            performance = "needs improvement"

        metric_display = metric_key.upper().replace("_", " ")

        return f"Your {metric_display} ({value_str}) is in the {percentile_str} percentile for {industry} ({performance})"

    def _format_metric_value(self, metric_key: str, value: float) -> str:
        """Format metric value with appropriate units."""
        key_lower = metric_key.lower()

        if key_lower in ("mrr", "arr", "cac", "ltv", "aov", "burn_rate"):
            # Currency
            if value >= 1000:
                return f"${value:,.0f}"
            return f"${value:.2f}"
        elif key_lower in ("churn", "gross_margin", "conversion_rate", "return_rate"):
            # Percentage
            return f"{value:.1f}%"
        elif key_lower == "ltv_cac_ratio":
            # Ratio
            return f"{value:.1f}x"
        elif key_lower == "runway":
            # Months
            return f"{value:.0f} months"
        elif key_lower == "nps":
            # Score
            return f"{value:+.0f}"
        else:
            return f"{value:.2f}"


def market_context_to_dict(result: MarketContextResult | None) -> dict[str, Any] | None:
    """Convert MarketContextResult to dict for storage."""
    if result is None:
        return None

    return {
        "benchmark_value": result.benchmark_value,
        "benchmark_percentile": result.benchmark_percentile,
        "percentile_position": result.percentile_position,
        "comparison_text": result.comparison_text,
        "source_url": result.source_url,
        "enriched_at": result.enriched_at.isoformat() if result.enriched_at else None,
        "confidence": result.confidence,
    }


def dict_to_market_context(data: dict[str, Any] | None) -> MarketContextResult | None:
    """Convert stored dict back to MarketContextResult."""
    if data is None:
        return None

    enriched_at = data.get("enriched_at")
    if enriched_at and isinstance(enriched_at, str):
        enriched_at = datetime.fromisoformat(enriched_at.replace("Z", "+00:00"))

    return MarketContextResult(
        benchmark_value=data.get("benchmark_value"),
        benchmark_percentile=data.get("benchmark_percentile"),
        percentile_position=data.get("percentile_position"),
        comparison_text=data.get("comparison_text"),
        source_url=data.get("source_url"),
        enriched_at=enriched_at,
        confidence=data.get("confidence", 0.0),
    )
