"""LLM-powered dataset insight generation.

Generates structured business intelligence from dataset profiles.
"""

import asyncio
import hashlib
import json
import logging
from typing import Any

from pydantic import ValidationError

from backend.api.models import (
    BusinessDomain,
    ChartSpec,
    ColumnSemantic,
    DataIdentity,
    DataQualityScore,
    DatasetInsights,
    HeadlineMetric,
    Insight,
    InsightSeverity,
    InsightType,
    SemanticColumnType,
    SuggestedChart,
    SuggestedQuestion,
)
from bo1.llm.client import ClaudeClient
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Cache settings
INSIGHT_CACHE_TTL = 86400  # 24 hours
INSIGHT_CACHE_PREFIX = "dataset_insights"

INSIGHT_SYSTEM_PROMPT = """You are a sharp business analyst helping founders understand their data. Your job is to find the actual story in their numbers - patterns, anomalies, opportunities they might miss.

CONTEXT EXTRACTION - Before analyzing, infer from:
- Dataset name: "sales_2024" → sales data, likely revenue focus
- Column names: "customer_id", "mrr", "churn_date" → SaaS metrics
- Value patterns: dates, currencies, percentages reveal business type
- Row meaning: each row is likely an order/customer/transaction/event

INSIGHT QUALITY RULES:
- NEVER state obvious facts ("data loaded", "X rows exist", "Y columns present")
- NEVER restate row/column counts as insights
- Every insight must reveal something non-obvious or actionable
- Focus on: trends, correlations, outliers, segments, benchmarks
- Compare to typical benchmarks when domain is clear (e.g., "30% churn is high for SaaS")

COMMUNICATION STYLE:
- Plain English, not jargon
- Specific numbers with context ("$47 average order, which is healthy for e-commerce")
- Personal tone: "your revenue" not "the revenue"

You output ONLY valid JSON. No markdown, no explanation."""

ENHANCED_INSIGHT_SYSTEM_PROMPT = """You are a sharp business analyst helping founders understand their data and take action. You have access to:
1. The dataset profile (columns, types, statistics)
2. Pre-computed investigation findings (column roles, outliers, correlations, data quality)
3. The user's business context (goals, KPIs, objectives)

Your job is to synthesize ALL of this information to provide highly personalized, actionable insights and next steps.

CRITICAL RULES:
- Prioritize insights relevant to the user's stated goals and KPIs
- Connect investigation findings to business impact
- Suggest specific questions they should ask based on their objectives
- Compare metrics to industry benchmarks when industry is known
- Be specific about column names and actual values found

COMMUNICATION STYLE:
- Personal: "your data shows" not "the data shows"
- Actionable: every insight should have a clear next step
- Specific: use actual column names and values from the investigation
- Honest: flag data quality issues that might affect reliability

You output ONLY valid JSON. No markdown, no explanation."""

INSIGHT_USER_PROMPT = """Analyze this dataset and provide structured business intelligence.

DATASET: {dataset_name}
ROWS: {row_count:,}
COLUMNS: {column_count}

COLUMN DETAILS:
{column_details}

SAMPLE DATA (first rows):
{sample_data}

STEP 1 - CONTEXT INFERENCE (do this mentally first):
- What business domain does "{dataset_name}" suggest?
- What does each row likely represent based on column names?
- What metrics/KPIs can be calculated from these columns?
- What time period does this cover (if dates exist)?
- What business questions could this data answer?

STEP 2 - Generate insights that would genuinely help a founder understand their business.

Respond with ONLY this JSON structure:

{{
  "identity": {{
    "domain": "ecommerce|saas|services|marketing|finance|operations|hr|product|unknown",
    "confidence": 0.0-1.0,
    "entity_type": "what each row represents (orders, customers, sessions, etc.)",
    "description": "Plain English description of what this dataset contains and its purpose",
    "time_range": "detected time span if dates exist, e.g. 'Jan 2024 - Mar 2024' or null"
  }},
  "headline_metrics": [
    {{
      "label": "Metric name (Total Revenue, Avg Order Value, etc.)",
      "value": "Formatted value with units ($127,450, 1,234 orders, etc.)",
      "context": "Additional context (across 3 months, per customer, etc.) or null",
      "trend": "Trend if detectable (+15% MoM) or null",
      "is_good": true/false/null
    }}
  ],
  "insights": [
    {{
      "type": "trend|pattern|anomaly|risk|opportunity|benchmark",
      "severity": "positive|neutral|warning|critical",
      "headline": "Short headline revealing a finding (max 10 words)",
      "detail": "Specific numbers + what they mean for the business",
      "metric": "The actual metric value discussed, or null",
      "action": "Concrete next step the founder could take, or null"
    }}
  ],
  "quality": {{
    "overall_score": 0-100,
    "completeness": 0-100,
    "consistency": 0-100,
    "freshness": 0-100 or null,
    "issues": ["Specific quality issues found"],
    "missing_data": ["Important data types that are missing"],
    "suggestions": ["How to improve the dataset"]
  }},
  "suggested_questions": [
    {{
      "question": "A question worth exploring with this data",
      "category": "performance|trend|segment|comparison|prediction",
      "why_relevant": "Why this question matters"
    }}
  ],
  "column_semantics": [
    {{
      "column_name": "exact column name",
      "technical_type": "integer|float|date|text|etc",
      "semantic_type": "revenue|customer_id|order_date|quantity|status|etc",
      "confidence": 0.0-1.0,
      "business_meaning": "What this column represents in business terms",
      "sample_insight": "Quick insight about this column, or null"
    }}
  ],
  "narrative_summary": "2-3 paragraph prose summary for users who prefer reading"
}}

Generate 3-5 headline metrics (business KPIs, not row/column counts).
Generate 4-6 insights that reveal actual findings (trends, patterns, anomalies, opportunities).
Generate 3-5 suggested questions for deeper exploration.
Provide column_semantics for ALL columns.

CRITICAL - INSIGHT QUALITY CHECK:
Before including an insight, ask: "Would a founder say 'I didn't know that' or 'that's useful'?"
✗ BAD: "Data loaded successfully" / "Dataset has 1,775 rows" / "6 columns present"
✓ GOOD: "Your average order value of $47 is 20% above e-commerce benchmarks"
✓ GOOD: "Revenue peaked in March - worth investigating what drove that spike"
✓ GOOD: "15% of orders have no customer_id - you're losing attribution data"

TONE:
- Personal: "your revenue" not "the revenue"
- Specific: include actual numbers
- Actionable: suggest what to do about findings
- Encouraging but honest"""


def _format_column_details(profile_dict: dict[str, Any]) -> str:
    """Format column profile data for the prompt."""
    lines = []
    for col in profile_dict.get("columns", []):
        parts = [f"- {col['name']} ({col['inferred_type']})"]

        stats = col.get("stats", {})
        details = []

        if stats.get("null_count", 0) > 0:
            null_pct = (stats["null_count"] / max(profile_dict["row_count"], 1)) * 100
            details.append(f"{null_pct:.0f}% null")
        if stats.get("unique_count"):
            details.append(f"{stats['unique_count']} unique")
        if stats.get("min_value") is not None:
            details.append(f"min={stats['min_value']}")
        if stats.get("max_value") is not None:
            details.append(f"max={stats['max_value']}")
        if stats.get("mean_value") is not None:
            details.append(f"mean={stats['mean_value']:.2f}")
        if stats.get("sample_values"):
            samples = stats["sample_values"][:3]
            details.append(f"samples: {samples}")

        if details:
            parts.append(f"  [{', '.join(details)}]")

        lines.append("".join(parts))

    return "\n".join(lines)


def _format_sample_data(profile_dict: dict[str, Any]) -> str:
    """Format sample data rows for context."""
    # Extract from sample_values in columns
    columns = profile_dict.get("columns", [])
    if not columns:
        return "No sample data available"

    # Build table header
    headers = [col["name"] for col in columns]
    header_line = " | ".join(headers)

    # Get samples (limited view)
    sample_rows = []
    for i in range(min(3, profile_dict.get("row_count", 0))):
        row_vals = []
        for col in columns:
            samples = col.get("stats", {}).get("sample_values", [])
            val = samples[i] if i < len(samples) else "..."
            row_vals.append(str(val)[:20])  # Truncate long values
        sample_rows.append(" | ".join(row_vals))

    if not sample_rows:
        return "No sample data available"

    return f"{header_line}\n" + "\n".join(sample_rows)


def _compute_insight_hash(profile_dict: dict[str, Any]) -> str:
    """Compute hash for cache key."""
    content = json.dumps(profile_dict, sort_keys=True, default=str)
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]


def _parse_llm_response(response: str) -> dict[str, Any]:
    """Parse LLM JSON response, handling potential formatting issues."""
    # Clean up response
    text = response.strip()

    # Remove markdown code blocks if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

    # Try to extract JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start >= 0 and end > start:
        text = text[start:end]

    return json.loads(text)


def _generate_chart_suggestions(profile_dict: dict[str, Any]) -> list[SuggestedChart]:
    """Generate chart suggestions based on column types and statistics.

    Heuristics:
    - Numeric columns → histogram for distribution
    - Categorical + numeric → bar chart by category
    - Date + numeric → time series line chart
    - Two numeric columns → scatter plot

    Limits scan to first 20 columns to avoid overwhelming wide datasets.
    """
    columns = profile_dict.get("columns", [])[:20]  # Limit to first 20 columns
    if not columns:
        return []

    suggestions: list[SuggestedChart] = []

    # Classify columns by type
    numeric_cols: list[dict] = []
    categorical_cols: list[dict] = []
    date_cols: list[dict] = []

    for col in columns:
        col_type = col.get("inferred_type", "").lower()
        col.get("name", "")
        stats = col.get("stats", {})
        unique_count = stats.get("unique_count", 0) or 0
        row_count = profile_dict.get("row_count", 1) or 1

        # Classify by type and cardinality
        if col_type in ("integer", "float", "number", "numeric"):
            numeric_cols.append(col)
        elif col_type in ("date", "datetime", "timestamp"):
            date_cols.append(col)
        elif col_type in ("string", "text", "category", "object"):
            # Only treat as categorical if cardinality is reasonable (< 50 unique or < 20% of rows)
            if unique_count > 0 and (unique_count < 50 or unique_count / row_count < 0.2):
                categorical_cols.append(col)

    # Priority 1: Time series (date + numeric)
    if date_cols and numeric_cols:
        date_col = date_cols[0]
        # Pick numeric column with highest variance if available
        numeric_col = _pick_best_numeric(numeric_cols)
        suggestions.append(
            SuggestedChart(
                chart_spec=ChartSpec(
                    chart_type="line",
                    x_field=date_col["name"],
                    y_field=numeric_col["name"],
                    title=f"{numeric_col['name']} over time",
                ),
                title=f"{numeric_col['name']} Trend",
                rationale=f"Shows how {numeric_col['name']} changes over time using {date_col['name']}",
            )
        )

    # Priority 2: Category breakdown (categorical + numeric)
    if categorical_cols and numeric_cols:
        cat_col = _pick_best_categorical(categorical_cols)
        numeric_col = _pick_best_numeric(numeric_cols)
        suggestions.append(
            SuggestedChart(
                chart_spec=ChartSpec(
                    chart_type="bar",
                    x_field=cat_col["name"],
                    y_field=numeric_col["name"],
                    title=f"{numeric_col['name']} by {cat_col['name']}",
                ),
                title=f"{numeric_col['name']} by {cat_col['name']}",
                rationale=f"Compare {numeric_col['name']} across different {cat_col['name']} values",
            )
        )

    # Priority 3: Numeric distribution (histogram)
    if numeric_cols:
        numeric_col = _pick_best_numeric(numeric_cols)
        suggestions.append(
            SuggestedChart(
                chart_spec=ChartSpec(
                    chart_type="bar",  # Histogram rendered as bar chart
                    x_field=numeric_col["name"],
                    y_field=numeric_col["name"],  # Will be aggregated as count
                    title=f"Distribution of {numeric_col['name']}",
                ),
                title=f"{numeric_col['name']} Distribution",
                rationale=f"See how {numeric_col['name']} values are distributed",
            )
        )

    # Priority 4: Scatter plot (two numeric columns)
    if len(numeric_cols) >= 2:
        col1 = numeric_cols[0]
        col2 = numeric_cols[1]
        suggestions.append(
            SuggestedChart(
                chart_spec=ChartSpec(
                    chart_type="scatter",
                    x_field=col1["name"],
                    y_field=col2["name"],
                    title=f"{col1['name']} vs {col2['name']}",
                ),
                title=f"{col1['name']} vs {col2['name']}",
                rationale=f"Explore relationship between {col1['name']} and {col2['name']}",
            )
        )

    # Priority 5: Pie chart for categorical distribution
    if categorical_cols:
        cat_col = _pick_best_categorical(categorical_cols)
        suggestions.append(
            SuggestedChart(
                chart_spec=ChartSpec(
                    chart_type="pie",
                    x_field=cat_col["name"],
                    y_field=cat_col["name"],  # Count aggregation
                    title=f"Distribution of {cat_col['name']}",
                ),
                title=f"{cat_col['name']} Breakdown",
                rationale=f"See the proportional breakdown of {cat_col['name']} categories",
            )
        )

    # Limit to 3 suggestions
    return suggestions[:3]


def _pick_best_numeric(cols: list[dict]) -> dict:
    """Pick the numeric column with highest variance (most interesting)."""
    if not cols:
        return {}

    # Score by variance/range if available, else by name heuristics
    best = cols[0]
    best_score = 0.0

    for col in cols:
        stats = col.get("stats", {})
        col_name = col.get("name", "").lower()

        # Prefer revenue/value/amount columns
        score = 0.0
        if any(kw in col_name for kw in ("revenue", "amount", "value", "price", "cost", "total")):
            score += 100

        # Add variance-based scoring if available
        std_dev = stats.get("std_dev")
        if std_dev is not None:
            score += float(std_dev)

        if score > best_score:
            best_score = score
            best = col

    return best


def _pick_best_categorical(cols: list[dict]) -> dict:
    """Pick categorical column with reasonable cardinality (3-20 values ideal)."""
    if not cols:
        return {}

    best = cols[0]
    best_score = 0.0

    for col in cols:
        stats = col.get("stats", {})
        col_name = col.get("name", "").lower()
        unique_count = stats.get("unique_count", 0) or 0

        # Prefer columns with 3-20 unique values (good for charts)
        score = 0.0
        if 3 <= unique_count <= 20:
            score += 50
        elif unique_count < 3:
            score += 10
        else:
            score += max(0, 30 - (unique_count - 20))

        # Prefer meaningful categorical names
        if any(kw in col_name for kw in ("category", "type", "status", "region", "segment")):
            score += 30

        if score > best_score:
            best_score = score
            best = col

    return best


def _build_fallback_insights(
    profile_dict: dict[str, Any],
    dataset_name: str,
) -> DatasetInsights:
    """Build minimal insights when LLM fails."""
    columns = profile_dict.get("columns", [])
    row_count = profile_dict.get("row_count", 0) or 0
    col_count = profile_dict.get("column_count", 0) or 0

    # Basic column semantics
    column_semantics = []
    for col in columns:
        column_semantics.append(
            ColumnSemantic(
                column_name=col.get("name", "unknown"),
                technical_type=col.get("inferred_type", "unknown"),
                semantic_type=SemanticColumnType.UNKNOWN,
                confidence=0.5,
                business_meaning=f"{col.get('inferred_type', 'unknown')} column",
                sample_insight=None,
            )
        )

    # Calculate basic completeness
    total_cells = row_count * col_count
    null_cells = sum(col.get("stats", {}).get("null_count", 0) or 0 for col in columns)
    completeness = int(100 * (1 - null_cells / max(total_cells, 1)))

    return DatasetInsights(
        identity=DataIdentity(
            domain=BusinessDomain.UNKNOWN,
            confidence=0.3,
            entity_type="records",
            description=f"Dataset with {row_count:,} rows and {col_count} columns",
            time_range=None,
        ),
        headline_metrics=[
            HeadlineMetric(label="Total Rows", value=f"{row_count:,}", context=None),
            HeadlineMetric(label="Columns", value=str(col_count), context=None),
        ],
        insights=[
            Insight(
                type=InsightType.PATTERN,
                severity=InsightSeverity.NEUTRAL,
                headline="Data loaded successfully",
                detail=f"Dataset contains {row_count:,} records across {col_count} columns. "
                "Use the chat to explore specific patterns.",
                metric=None,
                action="Ask a question about this data to get started",
            )
        ],
        quality=DataQualityScore(
            overall_score=completeness,
            completeness=completeness,
            consistency=70,
            freshness=None,
            issues=[],
            missing_data=[],
            suggestions=["Generate a full profile to see detailed analysis"],
        ),
        suggested_questions=[
            SuggestedQuestion(
                question="What are the key trends in this data?",
                category="trend",
                why_relevant="Understanding trends helps identify growth or decline patterns",
            ),
            SuggestedQuestion(
                question="Are there any outliers or anomalies?",
                category="performance",
                why_relevant="Outliers can indicate data quality issues or important exceptions",
            ),
        ],
        column_semantics=column_semantics,
        narrative_summary=f"This dataset named '{dataset_name}' contains {row_count:,} records "
        f"with {col_count} columns. Generate a full profile to receive detailed business insights.",
        suggested_charts=_generate_chart_suggestions(profile_dict),
    )


async def generate_dataset_insights(
    profile_dict: dict[str, Any],
    dataset_name: str,
    use_cache: bool = True,
    redis_manager: RedisManager | None = None,
) -> tuple[DatasetInsights, dict[str, Any]]:
    """Generate structured business insights from dataset profile.

    Args:
        profile_dict: Profile data from DatasetProfile.to_dict()
        dataset_name: Name of the dataset
        use_cache: Whether to use Redis cache
        redis_manager: Optional Redis manager instance

    Returns:
        Tuple of (DatasetInsights, metadata dict with tokens/cost)
    """
    dataset_id = profile_dict.get("dataset_id", "unknown")
    profile_hash = _compute_insight_hash(profile_dict)
    cache_key = f"{INSIGHT_CACHE_PREFIX}:{dataset_id}:{profile_hash}"
    logger.info(f"[Insights] dataset={dataset_id[:8]}... hash={profile_hash} use_cache={use_cache}")

    metadata = {"tokens_used": 0, "model_used": "sonnet", "cached": False}

    # Check cache
    if use_cache:
        redis = redis_manager or RedisManager()
        try:
            if redis.client is not None:
                cached = redis.client.get(cache_key)
                if cached:
                    # decode_responses=True means we get str, not bytes
                    cached_str = cached if isinstance(cached, str) else cached.decode("utf-8")
                    logger.info(f"[Insights] CACHE HIT for {dataset_id[:8]}...")
                    cached_data = json.loads(cached_str)
                    insights = DatasetInsights(**cached_data)
                    metadata["cached"] = True
                    return insights, metadata
                else:
                    logger.info(f"[Insights] CACHE MISS for {dataset_id[:8]}... (key not found)")
            else:
                logger.warning("[Insights] Redis client is None - cache disabled")
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

    # Format prompt
    column_details = _format_column_details(profile_dict)
    sample_data = _format_sample_data(profile_dict)

    user_prompt = INSIGHT_USER_PROMPT.format(
        dataset_name=dataset_name,
        row_count=profile_dict.get("row_count", 0),
        column_count=profile_dict.get("column_count", 0),
        column_details=column_details,
        sample_data=sample_data,
    )

    # Call Claude (use Sonnet for better reasoning) with timeout
    client = ClaudeClient()
    response = None
    llm_timeout = 30  # 30 second timeout for LLM call

    try:
        # Wrap LLM call in timeout
        async def _call_llm() -> tuple[str, Any]:
            return await client.call(
                model="sonnet",
                system=INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=3000,
                temperature=0.2,
            )

        response, usage = await asyncio.wait_for(_call_llm(), timeout=llm_timeout)
        metadata["tokens_used"] = usage.total_tokens
        metadata["cost"] = usage.calculate_cost("sonnet")

        # Parse response
        parsed = _parse_llm_response(response)
        # Add chart suggestions (not generated by LLM - done heuristically)
        parsed["suggested_charts"] = [
            chart.model_dump() for chart in _generate_chart_suggestions(profile_dict)
        ]
        insights = DatasetInsights(**parsed)

        logger.info(
            f"Generated insights for dataset {dataset_id} "
            f"({usage.total_tokens} tokens, ${metadata['cost']:.4f})"
        )

    except TimeoutError:
        logger.warning(f"LLM call timed out after {llm_timeout}s for dataset {dataset_id}")
        insights = _build_fallback_insights(profile_dict, dataset_name)

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse insight JSON: {e}")
        if response:
            logger.debug(f"Raw response: {response[:500]}...")
        insights = _build_fallback_insights(profile_dict, dataset_name)

    except ValidationError as e:
        logger.error(f"Insight validation failed: {e}")
        if response:
            logger.debug(f"Raw response: {response[:500]}...")
        insights = _build_fallback_insights(profile_dict, dataset_name)

    except Exception as e:
        logger.error(f"Failed to generate insights: {e}", exc_info=True)
        insights = _build_fallback_insights(profile_dict, dataset_name)

    # Cache result
    if use_cache and insights:
        redis = redis_manager or RedisManager()
        try:
            if redis.client is not None:
                cache_data = insights.model_dump(mode="json")
                redis.client.setex(cache_key, INSIGHT_CACHE_TTL, json.dumps(cache_data))
                logger.info(
                    f"[Insights] CACHED insights for {dataset_id[:8]}... (TTL={INSIGHT_CACHE_TTL}s)"
                )
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    return insights, metadata


def invalidate_insight_cache(
    dataset_id: str,
    redis_manager: RedisManager | None = None,
) -> int:
    """Invalidate cached insights for a dataset.

    Args:
        dataset_id: Dataset UUID
        redis_manager: Optional Redis manager instance

    Returns:
        Number of cache keys deleted
    """
    redis = redis_manager or RedisManager()
    pattern = f"{INSIGHT_CACHE_PREFIX}:{dataset_id}:*"
    try:
        if redis.client is None:
            return 0
        keys = list(redis.client.scan_iter(match=pattern))
        if keys:
            deleted = int(redis.client.delete(*keys) or 0)
            logger.info(f"Invalidated {deleted} insight cache entries for {dataset_id}")
            return deleted
        return 0
    except Exception as e:
        logger.warning(f"Failed to invalidate insight cache: {e}")
        return 0


# Enhanced prompt for insights informed by investigation and business context
ENHANCED_USER_PROMPT = """Analyze this dataset with the provided investigation findings and business context.

DATASET: {dataset_name}
ROWS: {row_count:,}
COLUMNS: {column_count}

=== COLUMN DETAILS ===
{column_details}

=== INVESTIGATION FINDINGS ===
{investigation_summary}

=== BUSINESS CONTEXT ===
{business_context}

Based on ALL the above, generate insights that:
1. Directly address the user's business goals and KPIs
2. Highlight investigation findings relevant to their objectives
3. Suggest specific questions tied to their industry and context
4. Flag any data quality issues that could affect their analysis

Respond with ONLY this JSON structure:

{{
  "identity": {{
    "domain": "ecommerce|saas|services|marketing|finance|operations|hr|product|unknown",
    "confidence": 0.0-1.0,
    "entity_type": "what each row represents",
    "description": "Plain English description tailored to their stated goals",
    "time_range": "detected time span or null"
  }},
  "headline_metrics": [
    {{
      "label": "Metric name - PRIORITIZE their stated key_metrics",
      "value": "Formatted value",
      "context": "How this relates to their goals",
      "trend": "Trend if detectable",
      "is_good": true/false/null based on their KPIs
    }}
  ],
  "insights": [
    {{
      "type": "trend|pattern|anomaly|risk|opportunity|benchmark",
      "severity": "positive|neutral|warning|critical",
      "headline": "Short headline connecting finding to their goal",
      "detail": "Specific numbers + what they mean for THEIR business",
      "metric": "The actual metric value",
      "action": "Concrete next step aligned with their objectives"
    }}
  ],
  "quality": {{
    "overall_score": 0-100,
    "completeness": 0-100,
    "consistency": 0-100,
    "freshness": 0-100 or null,
    "issues": ["Issues that could affect their analysis"],
    "missing_data": ["Data they need for their stated goals"],
    "suggestions": ["How to improve data for their use case"]
  }},
  "suggested_questions": [
    {{
      "question": "Question directly tied to their objectives",
      "category": "performance|trend|segment|comparison|prediction",
      "why_relevant": "Why this matters for their specific goal"
    }}
  ],
  "column_semantics": [
    {{
      "column_name": "exact column name",
      "technical_type": "from investigation",
      "semantic_type": "from investigation column roles",
      "confidence": 0.0-1.0,
      "business_meaning": "What this means for their business",
      "sample_insight": "Quick insight relevant to their goals"
    }}
  ],
  "narrative_summary": "2-3 paragraph summary focused on their specific business context and goals"
}}

CRITICAL: Generate insights that would genuinely help THIS user with THEIR stated goals.
- If they want to reduce churn, focus on churn-related findings
- If they want to increase revenue, highlight revenue opportunities
- If they specified KPIs, compare their data against those targets"""


def _format_investigation_summary(investigation: dict[str, Any] | None) -> str:
    """Format investigation findings for the enhanced prompt."""
    if not investigation:
        return "No investigation data available."

    lines = []

    # Column roles
    roles = investigation.get("column_roles", {})
    if roles:
        id_cols = roles.get("id_columns", [])
        ts_cols = roles.get("timestamp_columns", [])
        metric_cols = roles.get("metric_columns", [])
        dim_cols = roles.get("dimension_columns", [])
        if id_cols:
            lines.append(f"- ID columns: {', '.join(id_cols)}")
        if ts_cols:
            lines.append(f"- Timestamp columns: {', '.join(ts_cols)}")
        if metric_cols:
            lines.append(f"- Metric columns: {', '.join(metric_cols)}")
        if dim_cols:
            lines.append(f"- Dimension columns: {', '.join(dim_cols)}")

    # Missingness
    missingness = investigation.get("missingness", {})
    if missingness:
        high_null = missingness.get("high_null_columns", [])
        if high_null:
            lines.append(f"- HIGH NULL COLUMNS (>20%): {', '.join(high_null)}")
        cols_with_nulls = missingness.get("columns_with_nulls", 0)
        if cols_with_nulls:
            lines.append(f"- {cols_with_nulls} columns have some null values")

    # Outliers
    outliers = investigation.get("outliers", {})
    if outliers:
        outlier_list = outliers.get("outliers", [])
        if outlier_list:
            outlier_summary = [
                f"{o['column']} ({o['outlier_count']} outliers)" for o in outlier_list[:5]
            ]
            lines.append(f"- OUTLIERS DETECTED: {', '.join(outlier_summary)}")

    # Correlations
    correlations = investigation.get("correlations", {})
    if correlations:
        leakage = correlations.get("potential_leakage", [])
        if leakage:
            leak_summary = [
                f"{p['column_a']} <-> {p['column_b']} ({p['correlation']:.2f})" for p in leakage[:3]
            ]
            lines.append(f"- POTENTIAL LEAKAGE: {', '.join(leak_summary)}")
        strong_pos = correlations.get("top_positive", [])
        if strong_pos:
            pos_summary = [
                f"{p['column_a']} <-> {p['column_b']} (+{p['correlation']:.2f})"
                for p in strong_pos[:3]
            ]
            lines.append(f"- Strong positive correlations: {', '.join(pos_summary)}")

    # Time series readiness
    ts = investigation.get("time_series_readiness", {})
    if ts:
        if ts.get("is_ready"):
            lines.append(
                f"- TIME SERIES READY: column={ts.get('timestamp_column')}, "
                f"frequency={ts.get('detected_frequency')}"
            )
            if ts.get("gap_count", 0) > 0:
                lines.append(f"  WARNING: {ts['gap_count']} gaps detected in time series")
        else:
            lines.append("- Not suitable for time series analysis")

    # Segmentation opportunities
    seg = investigation.get("segmentation_builder", {})
    if seg:
        opps = seg.get("opportunities", [])
        if opps:
            seg_summary = [f"{o['dimension']} x {o['metric']}" for o in opps[:3]]
            lines.append(f"- SEGMENTATION OPPORTUNITIES: {', '.join(seg_summary)}")

    # Data quality
    dq = investigation.get("data_quality", {})
    if dq:
        score = dq.get("overall_score", 0)
        lines.append(f"- DATA QUALITY SCORE: {score}/100")
        issues = dq.get("issues", [])
        if issues:
            for issue in issues[:3]:
                lines.append(f"  - {issue.get('column')}: {issue.get('description')}")

    return "\n".join(lines) if lines else "No significant findings from investigation."


def _format_business_context(context: dict[str, Any] | None) -> str:
    """Format business context for the enhanced prompt."""
    if not context:
        return "No business context provided. Infer from data patterns."

    lines = []

    if context.get("business_goal"):
        lines.append(f"GOAL: {context['business_goal']}")

    if context.get("industry"):
        lines.append(f"INDUSTRY: {context['industry']}")

    if context.get("key_metrics"):
        metrics = context["key_metrics"]
        if isinstance(metrics, list):
            lines.append(f"KEY METRICS: {', '.join(metrics)}")
        else:
            lines.append(f"KEY METRICS: {metrics}")

    if context.get("kpis"):
        kpis = context["kpis"]
        if isinstance(kpis, list):
            lines.append(f"KPI TARGETS: {', '.join(kpis)}")
        else:
            lines.append(f"KPI TARGETS: {kpis}")

    if context.get("objectives"):
        lines.append(f"OBJECTIVES: {context['objectives']}")

    if context.get("additional_context"):
        lines.append(f"ADDITIONAL CONTEXT: {context['additional_context']}")

    return "\n".join(lines) if lines else "No business context provided."


async def generate_enhanced_insights(
    profile_dict: dict[str, Any],
    dataset_name: str,
    investigation: dict[str, Any] | None = None,
    business_context: dict[str, Any] | None = None,
    use_cache: bool = True,
    redis_manager: RedisManager | None = None,
) -> tuple[DatasetInsights, dict[str, Any]]:
    """Generate enhanced insights using investigation findings and business context.

    This is an upgraded version of generate_dataset_insights that incorporates:
    - Pre-computed investigation findings (column roles, outliers, correlations, etc.)
    - User-provided business context (goals, KPIs, objectives)

    Args:
        profile_dict: Profile data from DatasetProfile.to_dict()
        dataset_name: Name of the dataset
        investigation: Investigation findings from DeterministicAnalyzer
        business_context: User's business context (goals, KPIs, industry, etc.)
        use_cache: Whether to use Redis cache
        redis_manager: Optional Redis manager instance

    Returns:
        Tuple of (DatasetInsights, metadata dict with tokens/cost)
    """
    # If no investigation or context, fall back to standard insights
    if not investigation and not business_context:
        return await generate_dataset_insights(profile_dict, dataset_name, use_cache, redis_manager)

    dataset_id = profile_dict.get("dataset_id", "unknown")
    # Include investigation and context in cache hash
    cache_content = {
        "profile": profile_dict,
        "investigation": investigation,
        "context": business_context,
    }
    import json as _json

    cache_hash = hashlib.md5(
        _json.dumps(cache_content, sort_keys=True, default=str).encode(),
        usedforsecurity=False,
    ).hexdigest()[:12]
    cache_key = f"{INSIGHT_CACHE_PREFIX}:enhanced:{dataset_id}:{cache_hash}"
    logger.info(
        f"[EnhancedInsights] dataset={dataset_id[:8]}... hash={cache_hash} "
        f"has_investigation={investigation is not None} has_context={business_context is not None}"
    )

    metadata = {"tokens_used": 0, "model_used": "sonnet", "cached": False, "enhanced": True}

    # Check cache
    if use_cache:
        redis = redis_manager or RedisManager()
        try:
            if redis.client is not None:
                cached = redis.client.get(cache_key)
                if cached:
                    cached_str = cached if isinstance(cached, str) else cached.decode("utf-8")
                    logger.info(f"[EnhancedInsights] CACHE HIT for {dataset_id[:8]}...")
                    cached_data = json.loads(cached_str)
                    insights = DatasetInsights(**cached_data)
                    metadata["cached"] = True
                    return insights, metadata
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

    # Format prompt components
    column_details = _format_column_details(profile_dict)
    investigation_summary = _format_investigation_summary(investigation)
    context_summary = _format_business_context(business_context)

    user_prompt = ENHANCED_USER_PROMPT.format(
        dataset_name=dataset_name,
        row_count=profile_dict.get("row_count", 0),
        column_count=profile_dict.get("column_count", 0),
        column_details=column_details,
        investigation_summary=investigation_summary,
        business_context=context_summary,
    )

    # Call Claude with enhanced system prompt
    client = ClaudeClient()
    response = None
    llm_timeout = 45  # Slightly longer timeout for enhanced analysis

    try:

        async def _call_llm() -> tuple[str, Any]:
            return await client.call(
                model="sonnet",
                system=ENHANCED_INSIGHT_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
                max_tokens=4000,  # More tokens for richer insights
                temperature=0.2,
            )

        response, usage = await asyncio.wait_for(_call_llm(), timeout=llm_timeout)
        metadata["tokens_used"] = usage.total_tokens
        metadata["cost"] = usage.calculate_cost("sonnet")

        # Parse response
        parsed = _parse_llm_response(response)
        # Add chart suggestions
        parsed["suggested_charts"] = [
            chart.model_dump() for chart in _generate_chart_suggestions(profile_dict)
        ]
        insights = DatasetInsights(**parsed)

        logger.info(
            f"Generated enhanced insights for dataset {dataset_id} "
            f"({usage.total_tokens} tokens, ${metadata['cost']:.4f})"
        )

    except TimeoutError:
        logger.warning(f"Enhanced LLM call timed out after {llm_timeout}s")
        # Fall back to standard insights
        return await generate_dataset_insights(profile_dict, dataset_name, use_cache, redis_manager)

    except (json.JSONDecodeError, ValidationError) as e:
        logger.error(f"Failed to parse enhanced insight JSON: {e}")
        return await generate_dataset_insights(profile_dict, dataset_name, use_cache, redis_manager)

    except Exception as e:
        logger.error(f"Failed to generate enhanced insights: {e}", exc_info=True)
        return await generate_dataset_insights(profile_dict, dataset_name, use_cache, redis_manager)

    # Cache result
    if use_cache and insights:
        redis = redis_manager or RedisManager()
        try:
            if redis.client is not None:
                cache_data = insights.model_dump(mode="json")
                redis.client.setex(cache_key, INSIGHT_CACHE_TTL, json.dumps(cache_data))
                logger.info(f"[EnhancedInsights] CACHED for {dataset_id[:8]}...")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    return insights, metadata
