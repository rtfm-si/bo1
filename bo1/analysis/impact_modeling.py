"""Impact modeling for proposed changes.

Provides functions to model the financial impact of improving metrics
to industry benchmarks or target values.
"""

from typing import Any


def model_churn_reduction_impact(
    current_churn_rate: float,
    target_churn_rate: float,
    current_mrr: float,
    average_customer_value: float,
) -> dict[str, Any]:
    """Model the impact of reducing churn to a target rate.

    Args:
        current_churn_rate: Current monthly churn rate (percentage)
        target_churn_rate: Target monthly churn rate (percentage)
        current_mrr: Current monthly recurring revenue
        average_customer_value: Average monthly value per customer

    Returns:
        Dict with impact projections and narrative
    """
    if target_churn_rate >= current_churn_rate:
        return {
            "scenario": "No improvement",
            "monthly_revenue_saved": 0,
            "annual_revenue_impact": 0,
            "customer_lifetime_improvement_months": 0,
            "ltv_improvement_per_customer": 0,
            "narrative": "Target churn rate is not lower than current rate.",
            "assumptions": ["No change in churn rate"],
        }

    churn_reduction = current_churn_rate - target_churn_rate

    # Customers retained per month (as percentage of base)
    additional_retention = churn_reduction / 100

    # Monthly revenue saved
    monthly_revenue_saved = current_mrr * additional_retention

    # Annual impact
    annual_revenue_impact = monthly_revenue_saved * 12

    # LTV improvement (simplified: 1/churn_rate months average lifetime)
    current_avg_lifetime = 100 / current_churn_rate if current_churn_rate > 0 else 0
    new_avg_lifetime = 100 / target_churn_rate if target_churn_rate > 0 else 0
    lifetime_improvement = new_avg_lifetime - current_avg_lifetime
    ltv_improvement = lifetime_improvement * average_customer_value

    return {
        "scenario": f"Reduce churn from {current_churn_rate}% to {target_churn_rate}%",
        "monthly_revenue_saved": round(monthly_revenue_saved, 2),
        "annual_revenue_impact": round(annual_revenue_impact, 2),
        "customer_lifetime_improvement_months": round(lifetime_improvement, 1),
        "ltv_improvement_per_customer": round(ltv_improvement, 2),
        "narrative": (
            f"Reducing churn from {current_churn_rate}% to {target_churn_rate}% "
            f"would save approximately ${monthly_revenue_saved:,.0f}/month "
            f"(${annual_revenue_impact:,.0f}/year) and increase average customer "
            f"lifetime by {lifetime_improvement:.1f} months."
        ),
        "assumptions": [
            f"Current MRR: ${current_mrr:,.0f}",
            f"Avg customer value: ${average_customer_value:,.0f}/month",
            "Linear retention model assumed",
        ],
    }


def model_conversion_improvement_impact(
    current_conversion_rate: float,
    target_conversion_rate: float,
    monthly_visitors: int,
    average_order_value: float,
) -> dict[str, Any]:
    """Model impact of improving conversion rate.

    Args:
        current_conversion_rate: Current conversion rate (percentage)
        target_conversion_rate: Target conversion rate (percentage)
        monthly_visitors: Monthly visitor count
        average_order_value: Average order value in dollars

    Returns:
        Dict with impact projections and narrative
    """
    if target_conversion_rate <= current_conversion_rate:
        return {
            "scenario": "No improvement",
            "additional_conversions_per_month": 0,
            "monthly_revenue_increase": 0,
            "annual_revenue_increase": 0,
            "narrative": "Target conversion rate is not higher than current rate.",
            "assumptions": ["No change in conversion rate"],
        }

    current_conversions = monthly_visitors * (current_conversion_rate / 100)
    target_conversions = monthly_visitors * (target_conversion_rate / 100)
    additional_conversions = target_conversions - current_conversions

    monthly_revenue_increase = additional_conversions * average_order_value
    annual_revenue_increase = monthly_revenue_increase * 12

    return {
        "scenario": (
            f"Improve conversion from {current_conversion_rate}% to {target_conversion_rate}%"
        ),
        "additional_conversions_per_month": round(additional_conversions),
        "monthly_revenue_increase": round(monthly_revenue_increase, 2),
        "annual_revenue_increase": round(annual_revenue_increase, 2),
        "narrative": (
            f"Improving conversion from {current_conversion_rate}% to "
            f"{target_conversion_rate}% would generate {additional_conversions:.0f} "
            f"additional sales/month, worth ${monthly_revenue_increase:,.0f}/month "
            f"(${annual_revenue_increase:,.0f}/year)."
        ),
        "assumptions": [
            f"Monthly visitors: {monthly_visitors:,}",
            f"Avg order value: ${average_order_value:,.0f}",
            "Visitor volume assumed constant",
        ],
    }


def model_aov_improvement_impact(
    current_aov: float,
    target_aov: float,
    monthly_orders: int,
) -> dict[str, Any]:
    """Model impact of improving average order value.

    Args:
        current_aov: Current average order value
        target_aov: Target average order value
        monthly_orders: Number of orders per month

    Returns:
        Dict with impact projections and narrative
    """
    if target_aov <= current_aov:
        return {
            "scenario": "No improvement",
            "aov_increase": 0,
            "monthly_revenue_increase": 0,
            "annual_revenue_increase": 0,
            "narrative": "Target AOV is not higher than current AOV.",
            "assumptions": ["No change in AOV"],
        }

    aov_increase = target_aov - current_aov
    monthly_revenue_increase = aov_increase * monthly_orders
    annual_revenue_increase = monthly_revenue_increase * 12

    return {
        "scenario": f"Increase AOV from ${current_aov:.2f} to ${target_aov:.2f}",
        "aov_increase": round(aov_increase, 2),
        "monthly_revenue_increase": round(monthly_revenue_increase, 2),
        "annual_revenue_increase": round(annual_revenue_increase, 2),
        "narrative": (
            f"Increasing AOV by ${aov_increase:.2f} across {monthly_orders:,} "
            f"monthly orders would add ${monthly_revenue_increase:,.0f}/month "
            f"(${annual_revenue_increase:,.0f}/year)."
        ),
        "assumptions": [
            f"Monthly orders: {monthly_orders:,}",
            "Order volume assumed constant",
        ],
    }


def model_retention_improvement_impact(
    current_retention_rate: float,
    target_retention_rate: float,
    customer_base: int,
    average_customer_value: float,
) -> dict[str, Any]:
    """Model impact of improving customer retention rate.

    Args:
        current_retention_rate: Current retention rate (percentage)
        target_retention_rate: Target retention rate (percentage)
        customer_base: Total number of customers
        average_customer_value: Average value per customer per period

    Returns:
        Dict with impact projections and narrative
    """
    if target_retention_rate <= current_retention_rate:
        return {
            "scenario": "No improvement",
            "additional_customers_retained": 0,
            "monthly_revenue_increase": 0,
            "annual_revenue_increase": 0,
            "narrative": "Target retention rate is not higher than current rate.",
            "assumptions": ["No change in retention rate"],
        }

    retention_improvement = (target_retention_rate - current_retention_rate) / 100
    additional_retained = int(customer_base * retention_improvement)
    monthly_revenue_increase = additional_retained * average_customer_value
    annual_revenue_increase = monthly_revenue_increase * 12

    return {
        "scenario": (
            f"Improve retention from {current_retention_rate}% to {target_retention_rate}%"
        ),
        "additional_customers_retained": additional_retained,
        "monthly_revenue_increase": round(monthly_revenue_increase, 2),
        "annual_revenue_increase": round(annual_revenue_increase, 2),
        "narrative": (
            f"Improving retention from {current_retention_rate}% to "
            f"{target_retention_rate}% would retain {additional_retained:,} "
            f"additional customers, worth ${monthly_revenue_increase:,.0f}/month "
            f"(${annual_revenue_increase:,.0f}/year)."
        ),
        "assumptions": [
            f"Customer base: {customer_base:,}",
            f"Avg customer value: ${average_customer_value:,.0f}/month",
        ],
    }


def model_cac_reduction_impact(
    current_cac: float,
    target_cac: float,
    monthly_acquisitions: int,
) -> dict[str, Any]:
    """Model impact of reducing customer acquisition cost.

    Args:
        current_cac: Current CAC
        target_cac: Target CAC
        monthly_acquisitions: Number of customers acquired per month

    Returns:
        Dict with impact projections and narrative
    """
    if target_cac >= current_cac:
        return {
            "scenario": "No improvement",
            "savings_per_customer": 0,
            "monthly_savings": 0,
            "annual_savings": 0,
            "narrative": "Target CAC is not lower than current CAC.",
            "assumptions": ["No change in CAC"],
        }

    savings_per_customer = current_cac - target_cac
    monthly_savings = savings_per_customer * monthly_acquisitions
    annual_savings = monthly_savings * 12

    return {
        "scenario": f"Reduce CAC from ${current_cac:.0f} to ${target_cac:.0f}",
        "savings_per_customer": round(savings_per_customer, 2),
        "monthly_savings": round(monthly_savings, 2),
        "annual_savings": round(annual_savings, 2),
        "narrative": (
            f"Reducing CAC from ${current_cac:.0f} to ${target_cac:.0f} "
            f"would save ${savings_per_customer:.0f} per acquisition, "
            f"totaling ${monthly_savings:,.0f}/month (${annual_savings:,.0f}/year)."
        ),
        "assumptions": [
            f"Monthly acquisitions: {monthly_acquisitions:,}",
            "Acquisition volume assumed constant",
        ],
    }


def select_impact_model(
    metric_name: str,
    current_value: float,
    target_value: float,
    context: dict[str, Any],
) -> dict[str, Any] | None:
    """Select and run appropriate impact model based on metric type.

    Args:
        metric_name: Name of the metric (normalized)
        current_value: Current metric value
        target_value: Target metric value
        context: Business context with relevant parameters

    Returns:
        Impact model result or None if no model applies
    """
    metric_lower = metric_name.lower().replace(" ", "_").replace("-", "_")

    if metric_lower in ("churn_rate", "churn"):
        return model_churn_reduction_impact(
            current_churn_rate=current_value,
            target_churn_rate=target_value,
            current_mrr=context.get("mrr", context.get("revenue", 100000)),
            average_customer_value=context.get("acv", context.get("arpu", 500)),
        )

    if metric_lower in ("conversion_rate", "conversion"):
        return model_conversion_improvement_impact(
            current_conversion_rate=current_value,
            target_conversion_rate=target_value,
            monthly_visitors=context.get("monthly_visitors", 10000),
            average_order_value=context.get("aov", context.get("average_order_value", 85)),
        )

    if metric_lower in ("average_order_value", "aov"):
        return model_aov_improvement_impact(
            current_aov=current_value,
            target_aov=target_value,
            monthly_orders=context.get("monthly_orders", 1000),
        )

    if metric_lower in ("customer_retention_rate", "retention", "retention_rate"):
        return model_retention_improvement_impact(
            current_retention_rate=current_value,
            target_retention_rate=target_value,
            customer_base=context.get("customer_base", context.get("customers", 1000)),
            average_customer_value=context.get("acv", context.get("arpu", 100)),
        )

    if metric_lower in ("customer_acquisition_cost", "cac"):
        return model_cac_reduction_impact(
            current_cac=current_value,
            target_cac=target_value,
            monthly_acquisitions=context.get("monthly_acquisitions", 100),
        )

    return None
