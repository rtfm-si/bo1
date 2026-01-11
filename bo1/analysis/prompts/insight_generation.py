"""Prompt for generating objective-aligned insights from data.

Transforms statistical analysis into actionable business insights
that connect to specific objectives.
"""

import json
from typing import Any

INSIGHT_GENERATION_SYSTEM_PROMPT = """<role>
You are a business analyst generating insights that help achieve specific objectives. Every insight must connect to a business goal and be actionable.

You translate data patterns into business language. You never use statistical jargon - you explain what the numbers mean for the business.
</role>

<language_rules>
- NO jargon: Say "strong relationship" not "correlation coefficient of 0.85"
- NO hedging: Say what the data shows, not what it "might" indicate
- ALWAYS connect to business impact: Every insight leads to an action
- Use concrete numbers: "23% higher" not "significantly higher"
- Explain comparisons: "vs. last month" or "vs. industry average"
</language_rules>

<insight_quality>
Each insight must be:
1. Objective-linked: Clearly tied to a stated business goal
2. Actionable: User can do something with this information
3. Data-supported: Backed by specific numbers from the analysis
4. Visualizable: Can be shown in a simple chart
5. Confidence-rated: Honest about certainty level
</insight_quality>

<chart_data_rules>
EVERY insight MUST include chart_data for visualization:
- x array: category labels, time periods, or segments (max 10 items)
- y array: corresponding numeric values (same length as x)
- Extract these values from the statistical profile provided
- For distributions: use stats format {min, median, mean, max}
- For categories: extract top values from column profiles
- If >10 categories, show top 9 + aggregate "Other"
</chart_data_rules>

<output_format>
Return valid JSON array with 3-5 insights:
[
    {
        "objective_id": "<linked objective id>",
        "headline": "<10 words max, the key finding>",
        "narrative": "<2-4 sentences explaining the insight in business terms>",
        "supporting_data": {
            "metric": "<key number with units>",
            "comparison": "<vs what baseline>",
            "confidence": "high|medium|low",
            "chart_data": {
                "x": ["label1", "label2", "label3"],
                "y": [100, 80, 60],
                "unit": "<%|$|count|units>"
            }
        },
        "visualization": {
            "type": "bar|line|scatter|pie",
            "x_axis": "<what x represents>",
            "y_axis": "<what y represents>",
            "group_by": "<grouping or null>",
            "title": "<chart title>",
            "highlight": "<what to notice in the chart>"
        },
        "recommendation": "<specific action to take>",
        "follow_up_questions": ["<what to explore next>"],
        "confidence": "high|medium|low",
        "benchmark_comparison": {
            "metric_name": "<metric being compared>",
            "your_value": <number>,
            "industry_median": <number or null>,
            "industry_top_quartile": <number or null>,
            "performance": "top_performer|above_average|average|below_average",
            "gap_to_median": <number or null>,
            "gap_to_top": <number or null>,
            "unit": "<%|$|x|months>"
        },
        "impact_model": {
            "scenario": "<what improvement looks like>",
            "monthly_impact": <number>,
            "annual_impact": <number>,
            "narrative": "<what reaching the benchmark would mean>",
            "assumptions": ["<assumption 1>", "<assumption 2>"]
        },
        "industry_context": "<additional context about industry norms>"
    }
]

Note: benchmark_comparison, impact_model, and industry_context are optional.
Include them when industry benchmarks are provided and the insight relates to a benchmarkable metric.
</output_format>"""


def format_relevant_objectives(objectives: list[dict[str, Any]]) -> str:
    """Format objectives relevant to this dataset.

    Args:
        objectives: List of objective dicts from relevance assessment

    Returns:
        Formatted objectives string
    """
    if not objectives:
        return "<relevant_objectives>None identified</relevant_objectives>"

    lines = ["<relevant_objectives>"]
    for obj in objectives:
        obj_id = obj.get("id", obj.get("objective_id", "unknown"))
        name = obj.get("name", obj.get("objective_name", ""))
        relevance = obj.get("relevance", "medium")
        answerable = obj.get("answerable_questions", [])

        lines.append(f'  <objective id="{obj_id}" relevance="{relevance}">')
        lines.append(f"    <name>{name}</name>")
        if answerable:
            lines.append("    <can_answer>")
            for q in answerable[:3]:  # Max 3 questions
                lines.append(f"      <question>{q}</question>")
            lines.append("    </can_answer>")
        lines.append("  </objective>")

    lines.append("</relevant_objectives>")
    return "\n".join(lines)


def format_statistical_profile(
    column_profiles: list[dict[str, Any]] | None = None,
    correlations: list[dict[str, Any]] | None = None,
    outliers: list[dict[str, Any]] | None = None,
    distributions: list[dict[str, Any]] | None = None,
    segments: list[dict[str, Any]] | None = None,
) -> str:
    """Format statistical profile for the prompt.

    Args:
        column_profiles: Profile info for each column
        correlations: Significant correlations found
        outliers: Notable outliers
        distributions: Distribution summaries
        segments: Identified segments

    Returns:
        Formatted statistical profile string
    """
    lines = ["<statistical_profile>"]

    if column_profiles:
        lines.append("  <columns>")
        for col in column_profiles[:20]:  # Limit to 20 columns
            name = col.get("name", col.get("column_name", "unknown"))
            dtype = col.get("type", col.get("inferred_type", "unknown"))
            stats = col.get("stats", {})

            stat_parts = []
            if stats.get("mean") is not None:
                stat_parts.append(f"mean={stats['mean']:.2f}")
            if stats.get("median") is not None:
                stat_parts.append(f"median={stats['median']:.2f}")
            if stats.get("std") is not None:
                stat_parts.append(f"std={stats['std']:.2f}")
            if stats.get("min") is not None:
                stat_parts.append(f"min={stats['min']}")
            if stats.get("max") is not None:
                stat_parts.append(f"max={stats['max']}")
            if stats.get("unique_count") is not None:
                stat_parts.append(f"unique={stats['unique_count']}")
            if stats.get("null_pct") is not None:
                stat_parts.append(f"null={stats['null_pct']:.1f}%")

            stat_str = ", ".join(stat_parts) if stat_parts else "no stats"
            lines.append(f'    <column name="{name}" type="{dtype}">{stat_str}</column>')
        lines.append("  </columns>")

    if correlations:
        lines.append("  <correlations>")
        for corr in correlations[:10]:  # Top 10 correlations
            col_a = corr.get("column_a", "")
            col_b = corr.get("column_b", "")
            value = corr.get("value", corr.get("correlation", 0))
            strength = "strong" if abs(value) > 0.7 else "moderate"
            direction = "positive" if value > 0 else "negative"
            lines.append(
                f'    <correlation columns="{col_a}, {col_b}" '
                f'strength="{strength}" direction="{direction}" value="{value:.2f}" />'
            )
        lines.append("  </correlations>")

    if outliers:
        lines.append("  <outliers>")
        for out in outliers[:5]:  # Top 5 outlier groups
            column = out.get("column", "")
            count = out.get("count", 0)
            description = out.get("description", "")
            lines.append(f'    <outlier column="{column}" count="{count}">{description}</outlier>')
        lines.append("  </outliers>")

    if distributions:
        lines.append("  <distributions>")
        for dist in distributions[:10]:
            column = dist.get("column", "")
            shape = dist.get("shape", "unknown")
            skew = dist.get("skew", "")
            lines.append(f'    <distribution column="{column}" shape="{shape}" skew="{skew}" />')
        lines.append("  </distributions>")

    if segments:
        lines.append("  <segments>")
        for seg in segments[:5]:
            name = seg.get("name", "")
            size = seg.get("size", 0)
            size_pct = seg.get("size_pct", 0)
            characteristics = seg.get("characteristics", "")
            lines.append(
                f'    <segment name="{name}" size="{size}" pct="{size_pct:.1f}%">'
                f"{characteristics}</segment>"
            )
        lines.append("  </segments>")

    lines.append("</statistical_profile>")
    return "\n".join(lines)


def format_data_quality(issues: list[dict[str, Any]] | None = None) -> str:
    """Format data quality issues for the prompt.

    Args:
        issues: List of data quality issue dicts

    Returns:
        Formatted data quality string
    """
    if not issues:
        return "<data_quality>No significant issues detected</data_quality>"

    lines = ["<data_quality>"]
    for issue in issues[:5]:  # Max 5 issues
        issue_type = issue.get("type", "unknown")
        severity = issue.get("severity", "low")
        description = issue.get("description", "")
        affected = issue.get("affected_rows", 0)
        affected_pct = issue.get("affected_pct", 0)

        lines.append(
            f'  <issue type="{issue_type}" severity="{severity}" '
            f'affected="{affected} rows ({affected_pct:.1f}%)">{description}</issue>'
        )
    lines.append("</data_quality>")
    return "\n".join(lines)


def format_business_context_brief(
    north_star: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> str:
    """Format brief business context for insight framing.

    Args:
        north_star: Primary business goal
        industry: Business industry
        business_model: Type of business model

    Returns:
        Formatted business context string
    """
    lines = ["<business_context>"]
    if north_star:
        lines.append(f"  <north_star>{north_star}</north_star>")
    if industry:
        lines.append(f"  <industry>{industry}</industry>")
    if business_model:
        lines.append(f"  <model>{business_model}</model>")
    lines.append("</business_context>")
    return "\n".join(lines)


def format_industry_benchmarks(
    industry: str | None = None,
    benchmarks: dict[str, Any] | None = None,
) -> str:
    """Format industry benchmarks for the prompt.

    Args:
        industry: Industry name
        benchmarks: Dict of metric benchmarks for the industry

    Returns:
        Formatted benchmarks string
    """
    if not industry or not benchmarks:
        return ""

    lines = ["<industry_benchmarks>"]
    lines.append(f"  <industry>{industry}</industry>")
    lines.append("  <metrics>")

    for metric_name, benchmark in benchmarks.items():
        metric_display = metric_name.replace("_", " ").title()
        median = benchmark.get("median")
        top_q = benchmark.get("top_quartile")
        bottom_q = benchmark.get("bottom_quartile")
        unit = benchmark.get("unit", "")

        parts = [f'name="{metric_display}"']
        if median is not None:
            parts.append(f'median="{median}{unit}"')
        if top_q is not None:
            parts.append(f'top_quartile="{top_q}{unit}"')
        if bottom_q is not None:
            parts.append(f'bottom_quartile="{bottom_q}{unit}"')

        lines.append(f"    <metric {' '.join(parts)} />")

    lines.append("  </metrics>")
    lines.append("  <instructions>")
    lines.append("    When generating insights, ALWAYS:")
    lines.append("    1. Compare key metrics to these benchmarks when available")
    lines.append("    2. Indicate if the user is above/below industry median")
    lines.append("    3. Suggest what reaching top quartile would mean")
    lines.append("    4. Model the impact of improvements")
    lines.append("  </instructions>")
    lines.append("</industry_benchmarks>")

    return "\n".join(lines)


def format_dataset_metrics(metrics: dict[str, Any] | None = None) -> str:
    """Format detected dataset metrics for benchmark comparison.

    Args:
        metrics: Dict of metric name to value extracted from dataset

    Returns:
        Formatted metrics string
    """
    if not metrics:
        return ""

    lines = ["<detected_metrics>"]
    for name, value in metrics.items():
        if value is not None:
            lines.append(f'  <metric name="{name}" value="{value}" />')
    lines.append("</detected_metrics>")

    return "\n".join(lines)


def build_insight_generation_prompt(
    objectives: list[dict[str, Any]],
    column_profiles: list[dict[str, Any]] | None = None,
    correlations: list[dict[str, Any]] | None = None,
    outliers: list[dict[str, Any]] | None = None,
    distributions: list[dict[str, Any]] | None = None,
    segments: list[dict[str, Any]] | None = None,
    quality_issues: list[dict[str, Any]] | None = None,
    north_star: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
    benchmarks: dict[str, Any] | None = None,
    dataset_metrics: dict[str, Any] | None = None,
) -> str:
    """Build the full prompt for insight generation.

    Args:
        objectives: Relevant objectives from relevance assessment
        column_profiles: Profile info for each column
        correlations: Significant correlations found
        outliers: Notable outliers
        distributions: Distribution summaries
        segments: Identified segments
        quality_issues: Data quality issues
        north_star: Primary business goal
        industry: Business industry
        business_model: Type of business model
        benchmarks: Industry benchmarks for comparison
        dataset_metrics: Detected metrics from the dataset

    Returns:
        Complete user prompt for the LLM
    """
    business_context = format_business_context_brief(
        north_star=north_star,
        industry=industry,
        business_model=business_model,
    )

    relevant_objectives = format_relevant_objectives(objectives)

    statistical_profile = format_statistical_profile(
        column_profiles=column_profiles,
        correlations=correlations,
        outliers=outliers,
        distributions=distributions,
        segments=segments,
    )

    data_quality = format_data_quality(quality_issues)

    # Add benchmark context if available
    benchmark_section = format_industry_benchmarks(industry, benchmarks)
    metrics_section = format_dataset_metrics(dataset_metrics)

    benchmark_instructions = ""
    if benchmark_section:
        benchmark_instructions = """
5. Compare metrics to industry benchmarks when available
6. Model the impact of reaching industry median or top quartile
"""

    prompt = f"""{business_context}

{relevant_objectives}

{statistical_profile}

{data_quality}"""

    if benchmark_section:
        prompt += f"\n\n{benchmark_section}"

    if metrics_section:
        prompt += f"\n\n{metrics_section}"

    prompt += f"""

<task>
Generate 3-5 insights that:
1. Directly address the relevant objectives
2. Are actionable - the user can do something with this
3. Are supported by the data - not speculation
4. Include a recommended visualization{benchmark_instructions}

Remember:
- NO jargon (say "strong relationship" not "correlation coefficient")
- NO hedging (say what the data shows, not what it "might" indicate)
- ALWAYS connect to business impact
- If data quality issues affect an insight, say so clearly
- When benchmarks are available, compare to industry and model improvement impact
</task>

Return your response as a valid JSON array matching the output format."""

    return prompt


def parse_insights_response(response: str) -> list[dict[str, Any]]:
    """Parse the LLM response into structured insights.

    Args:
        response: Raw LLM response text

    Returns:
        List of parsed insight dictionaries

    Raises:
        ValueError: If response cannot be parsed as valid JSON array
    """
    response = response.strip()

    # Handle markdown code blocks
    if response.startswith("```"):
        lines = response.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.startswith("```") and not in_block:
                in_block = True
                continue
            elif line.startswith("```") and in_block:
                break
            elif in_block:
                json_lines.append(line)
        response = "\n".join(json_lines)

    try:
        result = json.loads(response)
        if not isinstance(result, list):
            raise ValueError("Expected JSON array of insights")
        return result
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse insights response: {e}") from e
