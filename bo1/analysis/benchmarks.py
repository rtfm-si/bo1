"""Industry benchmarks for data analysis enrichment.

Provides benchmark data and comparison utilities for enriching insights
with industry context and performance comparisons.
"""

from typing import Any

# Industry benchmark data (can be expanded or moved to database later)
INDUSTRY_BENCHMARKS: dict[str, dict[str, dict[str, Any]]] = {
    "saas": {
        "churn_rate": {
            "median": 5.0,
            "top_quartile": 3.0,
            "bottom_quartile": 8.0,
            "unit": "%",
        },
        "customer_acquisition_cost": {"median": 200, "unit": "$"},
        "lifetime_value": {"median": 2400, "unit": "$"},
        "ltv_cac_ratio": {"median": 3.0, "top_quartile": 5.0, "unit": "x"},
        "net_revenue_retention": {
            "median": 100,
            "top_quartile": 120,
            "bottom_quartile": 90,
            "unit": "%",
        },
        "monthly_recurring_revenue_growth": {
            "median": 10,
            "top_quartile": 20,
            "bottom_quartile": 5,
            "unit": "%",
        },
        "gross_margin": {
            "median": 70,
            "top_quartile": 80,
            "bottom_quartile": 60,
            "unit": "%",
        },
        "payback_period": {
            "median": 12,
            "top_quartile": 8,
            "bottom_quartile": 18,
            "unit": "months",
        },
    },
    "ecommerce": {
        "conversion_rate": {
            "median": 2.5,
            "top_quartile": 4.0,
            "bottom_quartile": 1.5,
            "unit": "%",
        },
        "cart_abandonment_rate": {
            "median": 70,
            "top_quartile": 60,
            "bottom_quartile": 80,
            "unit": "%",
        },
        "average_order_value": {"median": 85, "unit": "$"},
        "customer_retention_rate": {
            "median": 30,
            "top_quartile": 45,
            "bottom_quartile": 20,
            "unit": "%",
        },
        "repeat_purchase_rate": {
            "median": 27,
            "top_quartile": 40,
            "bottom_quartile": 15,
            "unit": "%",
        },
        "email_open_rate": {
            "median": 15,
            "top_quartile": 25,
            "bottom_quartile": 10,
            "unit": "%",
        },
        "return_rate": {
            "median": 20,
            "top_quartile": 10,
            "bottom_quartile": 30,
            "unit": "%",
        },
    },
    "marketplace": {
        "take_rate": {
            "median": 15,
            "top_quartile": 20,
            "bottom_quartile": 10,
            "unit": "%",
        },
        "gmv_growth": {
            "median": 30,
            "top_quartile": 50,
            "bottom_quartile": 15,
            "unit": "%",
        },
        "seller_churn": {
            "median": 20,
            "top_quartile": 10,
            "bottom_quartile": 30,
            "unit": "%",
        },
        "buyer_retention": {
            "median": 40,
            "top_quartile": 55,
            "bottom_quartile": 25,
            "unit": "%",
        },
        "buyer_seller_ratio": {"median": 10, "top_quartile": 15, "unit": "x"},
    },
    "fintech": {
        "customer_acquisition_cost": {"median": 150, "unit": "$"},
        "lifetime_value": {"median": 1800, "unit": "$"},
        "activation_rate": {
            "median": 40,
            "top_quartile": 60,
            "bottom_quartile": 25,
            "unit": "%",
        },
        "monthly_active_users_growth": {
            "median": 15,
            "top_quartile": 30,
            "unit": "%",
        },
        "default_rate": {
            "median": 3,
            "top_quartile": 1.5,
            "bottom_quartile": 5,
            "unit": "%",
        },
    },
    "subscription": {
        "churn_rate": {
            "median": 6.0,
            "top_quartile": 4.0,
            "bottom_quartile": 10.0,
            "unit": "%",
        },
        "trial_to_paid_conversion": {
            "median": 25,
            "top_quartile": 40,
            "bottom_quartile": 15,
            "unit": "%",
        },
        "upgrade_rate": {"median": 5, "top_quartile": 10, "unit": "%"},
        "downgrade_rate": {
            "median": 3,
            "top_quartile": 1,
            "bottom_quartile": 5,
            "unit": "%",
        },
    },
}

# Metric aliases for flexible matching
METRIC_ALIASES: dict[str, str] = {
    "churn": "churn_rate",
    "cac": "customer_acquisition_cost",
    "ltv": "lifetime_value",
    "aov": "average_order_value",
    "arr_growth": "monthly_recurring_revenue_growth",
    "mrr_growth": "monthly_recurring_revenue_growth",
    "conversion": "conversion_rate",
    "retention": "customer_retention_rate",
    "nrr": "net_revenue_retention",
}


def get_benchmarks_for_industry(industry: str) -> dict[str, dict[str, Any]]:
    """Get benchmarks for a specific industry.

    Args:
        industry: Industry name (case-insensitive, supports spaces and hyphens)

    Returns:
        Dict of metric benchmarks for the industry, empty dict if not found
    """
    normalized = industry.lower().replace(" ", "_").replace("-", "_")
    return INDUSTRY_BENCHMARKS.get(normalized, {})


def get_available_industries() -> list[str]:
    """Get list of industries with available benchmarks.

    Returns:
        List of industry names
    """
    return list(INDUSTRY_BENCHMARKS.keys())


def normalize_metric_name(metric_name: str) -> str:
    """Normalize metric name to canonical form.

    Args:
        metric_name: Metric name (potentially an alias)

    Returns:
        Canonical metric name
    """
    normalized = metric_name.lower().replace(" ", "_").replace("-", "_")
    return METRIC_ALIASES.get(normalized, normalized)


def compare_to_benchmark(value: float, metric_name: str, industry: str) -> dict[str, Any] | None:
    """Compare a value to industry benchmark.

    Args:
        value: The value to compare
        metric_name: Name of the metric (supports aliases)
        industry: Industry to compare against

    Returns:
        Comparison result with performance level and gap, or None if no benchmark
    """
    benchmarks = get_benchmarks_for_industry(industry)
    canonical_metric = normalize_metric_name(metric_name)

    if canonical_metric not in benchmarks:
        return None

    benchmark = benchmarks[canonical_metric]
    median = benchmark.get("median")
    top_quartile = benchmark.get("top_quartile")
    bottom_quartile = benchmark.get("bottom_quartile")

    if median is None:
        return None

    # Determine if higher or lower is better based on metric type
    # For rates like churn, lower is better; for revenue metrics, higher is better
    lower_is_better = canonical_metric in {
        "churn_rate",
        "cart_abandonment_rate",
        "seller_churn",
        "default_rate",
        "downgrade_rate",
        "return_rate",
        "payback_period",
    }

    # Determine performance level
    if lower_is_better:
        if top_quartile and value <= top_quartile:
            performance = "top_performer"
        elif value <= median:
            performance = "above_average"
        elif bottom_quartile and value >= bottom_quartile:
            performance = "below_average"
        else:
            performance = "average"
    else:
        if top_quartile and value >= top_quartile:
            performance = "top_performer"
        elif value >= median:
            performance = "above_average"
        elif bottom_quartile and value <= bottom_quartile:
            performance = "below_average"
        else:
            performance = "average"

    gap_to_median = value - median
    gap_to_top = value - top_quartile if top_quartile else None

    return {
        "metric": canonical_metric,
        "your_value": value,
        "industry_median": median,
        "industry_top_quartile": top_quartile,
        "industry_bottom_quartile": bottom_quartile,
        "performance": performance,
        "gap_to_median": gap_to_median,
        "gap_to_top": gap_to_top,
        "unit": benchmark.get("unit", ""),
        "lower_is_better": lower_is_better,
    }


def get_benchmark_context_for_metric(metric_name: str, industry: str) -> str | None:
    """Get a human-readable context string for a metric benchmark.

    Args:
        metric_name: Name of the metric
        industry: Industry to get benchmarks for

    Returns:
        Context string or None if no benchmark
    """
    benchmarks = get_benchmarks_for_industry(industry)
    canonical_metric = normalize_metric_name(metric_name)

    if canonical_metric not in benchmarks:
        return None

    benchmark = benchmarks[canonical_metric]
    median = benchmark.get("median")
    top_quartile = benchmark.get("top_quartile")
    unit = benchmark.get("unit", "")

    if median is None:
        return None

    context = f"Industry median: {median}{unit}"
    if top_quartile:
        context += f", top performers: {top_quartile}{unit}"

    return context
