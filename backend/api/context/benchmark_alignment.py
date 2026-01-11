"""Objective-aware benchmark alignment.

Maps business objectives and stages to relevant benchmark metrics,
providing relevance scores and explanations for prioritization.
"""

from dataclasses import dataclass

from bo1.analysis.benchmarks import INDUSTRY_BENCHMARKS, normalize_metric_name

# Metrics most relevant to each business objective
OBJECTIVE_METRICS: dict[str, list[str]] = {
    "acquire_customers": [
        "customer_acquisition_cost",
        "conversion_rate",
        "ltv_cac_ratio",
        "payback_period",
    ],
    "improve_retention": [
        "churn_rate",
        "net_revenue_retention",
        "customer_retention_rate",
        "repeat_purchase_rate",
    ],
    "raise_capital": [
        "monthly_recurring_revenue_growth",
        "gross_margin",
        "ltv_cac_ratio",
        "net_revenue_retention",
    ],
    "launch_product": [
        "conversion_rate",
        "customer_acquisition_cost",
        "average_order_value",
        "activation_rate",
    ],
    "reduce_costs": [
        "gross_margin",
        "payback_period",
        "customer_acquisition_cost",
        "return_rate",
    ],
}

# Objective-specific relevance reasons
OBJECTIVE_REASONS: dict[str, str] = {
    "acquire_customers": "Key for customer acquisition",
    "improve_retention": "Critical for retention",
    "raise_capital": "Important for fundraising",
    "launch_product": "Essential for product launch",
    "reduce_costs": "Key cost efficiency metric",
}

# Stage modifiers - adjust relevance scores based on business stage
STAGE_WEIGHTS: dict[str, dict[str, float]] = {
    "idea": {
        "conversion_rate": 1.5,  # Focus on validation
        "customer_acquisition_cost": 0.8,  # Less relevant early
        "activation_rate": 1.3,
    },
    "early": {
        "customer_acquisition_cost": 1.3,  # Unit economics
        "churn_rate": 1.2,
        "conversion_rate": 1.2,
    },
    "growing": {
        "net_revenue_retention": 1.3,  # Efficiency
        "ltv_cac_ratio": 1.2,
        "monthly_recurring_revenue_growth": 1.2,
    },
    "scaling": {
        "gross_margin": 1.3,  # Profitability
        "payback_period": 1.2,
        "net_revenue_retention": 1.1,
    },
}

# Stage-specific additional relevance reasons
STAGE_REASONS: dict[str, dict[str, str]] = {
    "idea": {
        "conversion_rate": "Critical for idea validation",
        "activation_rate": "Key for early traction",
    },
    "early": {
        "customer_acquisition_cost": "Focus on unit economics",
        "churn_rate": "Retention matters now",
    },
    "growing": {
        "net_revenue_retention": "Expansion drives growth",
        "ltv_cac_ratio": "Efficiency becomes crucial",
    },
    "scaling": {
        "gross_margin": "Profitability focus",
        "payback_period": "Capital efficiency",
    },
}


@dataclass
class AlignedBenchmark:
    """A benchmark metric with relevance scoring."""

    metric_key: str
    relevance_score: float  # 0.0-1.0
    relevance_reason: str | None
    is_objective_aligned: bool  # True if metric matches user's objective


def score_benchmark_relevance(
    metric_key: str,
    objective: str | None,
    stage: str | None,
) -> tuple[float, str | None, bool]:
    """Score a benchmark metric's relevance based on objective and stage.

    Args:
        metric_key: Normalized metric identifier
        objective: User's primary_objective (e.g., "acquire_customers")
        stage: User's business_stage (e.g., "early")

    Returns:
        Tuple of (relevance_score, relevance_reason, is_objective_aligned)
        - relevance_score: 0.0-1.0 (higher = more relevant)
        - relevance_reason: Human-readable explanation (or None)
        - is_objective_aligned: True if metric matches user's objective
    """
    canonical = normalize_metric_name(metric_key)

    base_score = 0.5  # Default score for unaligned metrics
    reason = None
    is_aligned = False

    # Check objective alignment
    if objective and objective in OBJECTIVE_METRICS:
        objective_metrics = OBJECTIVE_METRICS[objective]
        if canonical in objective_metrics:
            # Position in list affects score (first = most important)
            position = objective_metrics.index(canonical)
            base_score = 1.0 - (position * 0.15)  # 1.0, 0.85, 0.70, 0.55
            reason = OBJECTIVE_REASONS.get(objective)
            is_aligned = True

    # Apply stage modifier
    if stage and stage in STAGE_WEIGHTS:
        stage_weight = STAGE_WEIGHTS[stage].get(canonical, 1.0)
        base_score = min(1.0, base_score * stage_weight)

        # Override reason with stage-specific if available
        if stage in STAGE_REASONS and canonical in STAGE_REASONS[stage]:
            reason = STAGE_REASONS[stage][canonical]

    # Clamp to valid range
    final_score = max(0.0, min(1.0, base_score))

    return (final_score, reason, is_aligned)


def get_aligned_benchmarks(
    industry: str,
    objective: str | None,
    stage: str | None,
) -> list[AlignedBenchmark]:
    """Get benchmarks for an industry with relevance scoring.

    Args:
        industry: Industry name (e.g., "saas", "ecommerce")
        objective: User's primary objective (optional)
        stage: User's business stage (optional)

    Returns:
        List of AlignedBenchmark objects sorted by relevance (highest first)
    """
    # Normalize industry name
    normalized_industry = industry.lower().replace(" ", "_").replace("-", "_")
    industry_benchmarks = INDUSTRY_BENCHMARKS.get(normalized_industry, {})

    if not industry_benchmarks:
        return []

    aligned: list[AlignedBenchmark] = []

    for metric_key in industry_benchmarks:
        score, reason, is_aligned = score_benchmark_relevance(metric_key, objective, stage)
        aligned.append(
            AlignedBenchmark(
                metric_key=metric_key,
                relevance_score=score,
                relevance_reason=reason,
                is_objective_aligned=is_aligned,
            )
        )

    # Sort by relevance score (highest first), then alphabetically for ties
    aligned.sort(key=lambda x: (-x.relevance_score, x.metric_key))

    return aligned


def get_available_objectives() -> list[str]:
    """Get list of supported business objectives."""
    return list(OBJECTIVE_METRICS.keys())


def get_available_stages() -> list[str]:
    """Get list of supported business stages."""
    return list(STAGE_WEIGHTS.keys())
