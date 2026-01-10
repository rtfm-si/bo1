"""Insight generation module for objective-aligned data analysis.

Transforms statistical analysis into actionable business insights
that connect to specific objectives.
"""

import logging
import uuid
from typing import Any

from bo1.analysis.benchmarks import (
    get_benchmarks_for_industry,
)
from bo1.analysis.prompts.insight_generation import (
    INSIGHT_GENERATION_SYSTEM_PROMPT,
    build_insight_generation_prompt,
    parse_insights_response,
)
from bo1.llm.client import ClaudeClient
from bo1.models.dataset_objective_analysis import (
    BenchmarkComparison,
    ChartType,
    ConfidenceLevel,
    ImpactModel,
    Insight,
    InsightVisualization,
    RelevanceAssessment,
)

logger = logging.getLogger(__name__)


def _extract_dataset_metrics(
    column_profiles: list[dict[str, Any]] | None = None,
    investigation: dict[str, Any] | None = None,
    context: dict[str, Any] | None = None,
) -> dict[str, float]:
    """Extract metrics from dataset for benchmark comparison.

    Looks for common business metrics in column names and data.

    Args:
        column_profiles: Column profile information
        investigation: Pre-computed investigation results
        context: Business context with any explicit metrics

    Returns:
        Dict of metric name to value
    """
    metrics: dict[str, float] = {}

    # Check context for explicit metrics
    if context:
        metric_fields = [
            "churn_rate",
            "cac",
            "ltv",
            "aov",
            "conversion_rate",
            "retention_rate",
            "mrr",
            "arr",
            "gross_margin",
        ]
        for field in metric_fields:
            val = context.get(field)
            if val is not None and isinstance(val, (int, float)):
                metrics[field] = float(val)

    # Try to detect metrics from column names
    if column_profiles:
        metric_keywords = {
            "churn": "churn_rate",
            "conversion": "conversion_rate",
            "retention": "retention_rate",
            "aov": "average_order_value",
            "order_value": "average_order_value",
            "ltv": "lifetime_value",
            "lifetime": "lifetime_value",
            "cac": "customer_acquisition_cost",
            "acquisition_cost": "customer_acquisition_cost",
        }

        for col in column_profiles:
            col_name = col.get("name", col.get("column_name", "")).lower()
            col_stats = col.get("stats", {})

            for keyword, metric_name in metric_keywords.items():
                if keyword in col_name and metric_name not in metrics:
                    # Use mean or median if available
                    val = col_stats.get("mean") or col_stats.get("median")
                    if val is not None:
                        metrics[metric_name] = float(val)

    return metrics


async def generate_insights(
    profile: dict[str, Any],
    context: dict[str, Any] | None = None,
    relevance: RelevanceAssessment | None = None,
    investigation: dict[str, Any] | None = None,
) -> list[Insight]:
    """Generate objective-aligned insights from data analysis.

    Uses the insight_generation prompt to create actionable insights
    that connect to business objectives.

    Args:
        profile: Dataset profile with column stats, distributions, etc.
            Expected keys:
            - column_profiles: list[dict] with stats per column
            - correlations: list[dict] of significant correlations
            - outliers: list[dict] of notable outliers
        context: Business context dict with:
            - north_star: Primary business goal
            - industry: Business industry
            - business_model: Type of business model
        relevance: RelevanceAssessment from assess_relevance()
        investigation: Pre-computed deterministic analysis results with:
            - correlations, outliers, distributions, segments, data_quality

    Returns:
        List of Insight models with headlines, narratives, and recommendations
    """
    # Extract objectives from relevance assessment
    objectives: list[dict[str, Any]] = []
    if relevance:
        for match in relevance.objective_matches:
            if match.relevance.value in ["high", "medium"]:
                objectives.append(
                    {
                        "id": match.objective_id,
                        "objective_id": match.objective_id,
                        "name": match.objective_name,
                        "objective_name": match.objective_name,
                        "relevance": match.relevance.value,
                        "answerable_questions": match.answerable_questions,
                    }
                )

    # If no relevant objectives, generate open exploration insights
    if not objectives:
        objectives = [
            {
                "id": "open_exploration",
                "objective_id": "open_exploration",
                "name": "Data Exploration",
                "objective_name": "Data Exploration",
                "relevance": "medium",
                "answerable_questions": ["What patterns exist in the data?"],
            }
        ]

    # Extract analysis data from investigation or profile
    column_profiles = (
        investigation.get("descriptive_stats", {}).get("columns", []) if investigation else []
    )
    if not column_profiles:
        column_profiles = profile.get("column_profiles", profile.get("columns", []))

    correlations = investigation.get("correlations", {}).get("pairs", []) if investigation else []
    if not correlations:
        correlations = profile.get("correlations", [])

    outliers = investigation.get("outliers", {}).get("outliers", []) if investigation else []
    if not outliers:
        outliers = profile.get("outliers", [])

    distributions = []
    if investigation and investigation.get("descriptive_stats"):
        for col in investigation["descriptive_stats"].get("columns", []):
            if col.get("distribution_shape"):
                distributions.append(
                    {
                        "column": col.get("column"),
                        "shape": col.get("distribution_shape"),
                        "skew": col.get("skewness", ""),
                    }
                )

    segments = (
        investigation.get("segmentation_suggestions", {}).get("suggested_segments", [])
        if investigation
        else []
    )

    quality_issues = []
    if investigation and investigation.get("data_quality"):
        dq = investigation["data_quality"]
        for issue in dq.get("issues", []):
            quality_issues.append(
                {
                    "type": issue.get("type", "unknown"),
                    "severity": issue.get("severity", "low"),
                    "description": issue.get("description", ""),
                    "affected_rows": issue.get("affected_rows", 0),
                    "affected_pct": issue.get("affected_pct", 0),
                }
            )

    # Extract context
    north_star = context.get("north_star_goal", context.get("north_star")) if context else None
    industry = context.get("industry") if context else None
    business_model = context.get("business_model") if context else None

    # Get industry benchmarks if industry is available
    benchmarks = get_benchmarks_for_industry(industry) if industry else {}

    # Extract detected metrics from dataset for benchmark comparison
    dataset_metrics = _extract_dataset_metrics(
        column_profiles=column_profiles,
        investigation=investigation,
        context=context,
    )

    # Build the prompt
    user_prompt = build_insight_generation_prompt(
        objectives=objectives,
        column_profiles=column_profiles,
        correlations=correlations,
        outliers=outliers,
        distributions=distributions,
        segments=segments,
        quality_issues=quality_issues,
        north_star=north_star,
        industry=industry,
        business_model=business_model,
        benchmarks=benchmarks if benchmarks else None,
        dataset_metrics=dataset_metrics if dataset_metrics else None,
    )

    # Call LLM
    client = ClaudeClient()
    try:
        response_text, usage = await client.call(
            model="sonnet",
            system=INSIGHT_GENERATION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            cache_system=True,
            temperature=0.5,  # Allow some creativity for insights
            prefill="[",
        )

        # Parse response
        raw_insights = parse_insights_response(response_text)

        # Convert to typed models
        return _parse_insights(raw_insights)

    except Exception as e:
        logger.error(f"Error generating insights: {e}")
        # Return a fallback insight
        return [
            Insight(
                id=str(uuid.uuid4()),
                objective_id=None,
                objective_name=None,
                headline="Analysis encountered an issue",
                narrative=f"Unable to generate insights: {e}. Please try again or contact support.",
                supporting_data={},
                visualization=None,
                recommendation="Review your data and try uploading again.",
                follow_up_questions=[],
                confidence=ConfidenceLevel.LOW,
                benchmark_comparison=None,
                impact_model=None,
                industry_context=None,
            )
        ]


def _parse_benchmark_comparison(raw: dict[str, Any] | None) -> BenchmarkComparison | None:
    """Parse benchmark comparison from raw LLM response.

    Args:
        raw: Raw benchmark comparison dict from LLM

    Returns:
        BenchmarkComparison model or None
    """
    if not raw or not isinstance(raw, dict):
        return None

    # Validate required fields
    metric_name = raw.get("metric_name")
    your_value = raw.get("your_value")
    performance = raw.get("performance", "average")

    if not metric_name or your_value is None:
        return None

    try:
        return BenchmarkComparison(
            metric_name=str(metric_name),
            your_value=float(your_value),
            industry_median=float(raw["industry_median"]) if raw.get("industry_median") else None,
            industry_top_quartile=float(raw["industry_top_quartile"])
            if raw.get("industry_top_quartile")
            else None,
            performance=str(performance),
            gap_to_median=float(raw["gap_to_median"]) if raw.get("gap_to_median") else None,
            gap_to_top=float(raw["gap_to_top"]) if raw.get("gap_to_top") else None,
            unit=raw.get("unit", ""),
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse benchmark comparison: {e}")
        return None


def _parse_impact_model(raw: dict[str, Any] | None) -> ImpactModel | None:
    """Parse impact model from raw LLM response.

    Args:
        raw: Raw impact model dict from LLM

    Returns:
        ImpactModel model or None
    """
    if not raw or not isinstance(raw, dict):
        return None

    # Validate required fields
    scenario = raw.get("scenario")
    monthly_impact = raw.get("monthly_impact")
    annual_impact = raw.get("annual_impact")
    narrative = raw.get("narrative")

    if not all([scenario, narrative]) or monthly_impact is None or annual_impact is None:
        return None

    try:
        return ImpactModel(
            scenario=str(scenario),
            monthly_impact=float(monthly_impact),
            annual_impact=float(annual_impact),
            narrative=str(narrative),
            assumptions=raw.get("assumptions", []),
        )
    except (ValueError, TypeError) as e:
        logger.warning(f"Failed to parse impact model: {e}")
        return None


def _parse_insights(raw_insights: list[dict[str, Any]]) -> list[Insight]:
    """Parse raw LLM response into typed Insight models.

    Args:
        raw_insights: List of parsed JSON insight dicts

    Returns:
        List of Insight models
    """
    insights = []

    for i, raw in enumerate(raw_insights):
        insight_id = raw.get("id", str(uuid.uuid4()))

        # Parse confidence
        try:
            confidence_str = raw.get("confidence", "medium").lower()
            confidence = ConfidenceLevel(confidence_str)
        except ValueError:
            confidence = ConfidenceLevel.MEDIUM

        # Parse visualization
        visualization = None
        raw_viz = raw.get("visualization")
        if raw_viz and isinstance(raw_viz, dict):
            try:
                chart_type_str = raw_viz.get("type", "bar").lower()
                chart_type = ChartType(chart_type_str)
            except ValueError:
                chart_type = ChartType.BAR

            visualization = InsightVisualization(
                type=chart_type,
                x_axis=raw_viz.get("x_axis"),
                y_axis=raw_viz.get("y_axis"),
                group_by=raw_viz.get("group_by"),
                title=raw_viz.get("title", f"Chart {i + 1}"),
            )

        # Parse supporting data
        supporting_data = raw.get("supporting_data", {})
        if isinstance(supporting_data, dict):
            # Ensure confidence in supporting data matches overall confidence
            if "confidence" in supporting_data:
                supporting_data["confidence"] = confidence.value

        # Parse benchmark comparison
        benchmark_comparison = _parse_benchmark_comparison(raw.get("benchmark_comparison"))

        # Parse impact model
        impact_model = _parse_impact_model(raw.get("impact_model"))

        insights.append(
            Insight(
                id=insight_id,
                objective_id=raw.get("objective_id"),
                objective_name=raw.get("objective_name"),
                headline=raw.get("headline", "Insight")[:100],  # Max 100 chars
                narrative=raw.get("narrative", ""),
                supporting_data=supporting_data,
                visualization=visualization,
                recommendation=raw.get("recommendation", ""),
                follow_up_questions=raw.get("follow_up_questions", []),
                confidence=confidence,
                benchmark_comparison=benchmark_comparison,
                impact_model=impact_model,
                industry_context=raw.get("industry_context"),
            )
        )

    return insights


async def generate_open_exploration_insights(
    profile: dict[str, Any],
    investigation: dict[str, Any] | None = None,
) -> list[Insight]:
    """Generate insights for open exploration mode (no specific objectives).

    Used when dataset has low relevance to objectives or user has no objectives.

    Args:
        profile: Dataset profile with column stats
        investigation: Pre-computed deterministic analysis

    Returns:
        List of Insight models focused on patterns and anomalies
    """
    # Call generate_insights with no context/relevance to trigger open exploration
    return await generate_insights(
        profile=profile,
        context=None,
        relevance=None,
        investigation=investigation,
    )
