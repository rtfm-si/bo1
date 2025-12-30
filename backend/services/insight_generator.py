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
    ColumnSemantic,
    DataIdentity,
    DataQualityScore,
    DatasetInsights,
    HeadlineMetric,
    Insight,
    InsightSeverity,
    InsightType,
    SemanticColumnType,
    SuggestedQuestion,
)
from bo1.llm.client import ClaudeClient
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Cache settings
INSIGHT_CACHE_TTL = 86400  # 24 hours
INSIGHT_CACHE_PREFIX = "dataset_insights"

INSIGHT_SYSTEM_PROMPT = """You are a friendly business advisor helping startup founders understand their data. Your job is to look at their numbers and explain what they mean in plain English - like a smart colleague who's good with spreadsheets.

COMMUNICATION STYLE:
- Write like you're talking to a smart friend, not a data scientist
- Use everyday language: "your best customers" not "high-value cohort"
- Focus on what matters to a founder: customers, money, growth, problems to fix
- Be specific with numbers but explain what they mean

WHAT TO FOCUS ON:
1. The story this data tells about their business
2. Things that look good (celebrate wins!)
3. Things that might need attention (flag gently)
4. Questions they should probably ask next

You output ONLY valid JSON matching the schema provided. No markdown, no explanation, just JSON."""

INSIGHT_USER_PROMPT = """Analyze this dataset and provide structured business intelligence.

DATASET: {dataset_name}
ROWS: {row_count:,}
COLUMNS: {column_count}

COLUMN DETAILS:
{column_details}

SAMPLE DATA (first 5 rows):
{sample_data}

Respond with ONLY this JSON structure (no markdown, no explanation):

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
      "headline": "Short headline (max 10 words)",
      "detail": "Full explanation with specific numbers",
      "metric": "Related metric if applicable, or null",
      "action": "Suggested action to take, or null"
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

Generate 3-5 headline metrics, 4-6 insights, and 3-5 suggested questions.
Provide column_semantics for ALL columns.

IMPORTANT TONE GUIDELINES:
- Write headlines and descriptions like you're talking to a friend
- Use "you/your" - make it personal: "Your top customers..." not "The top customers..."
- Celebrate good things: "Nice! Your revenue is growing" not just "Revenue increased"
- Be gentle with problems: "Worth keeping an eye on..." not "Critical issue detected"
- Suggest questions that feel natural: "Who are your best customers?" not "Segment by customer value"
- Keep it encouraging - founders need support, not more stress"""


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

    metadata = {"tokens_used": 0, "model_used": "sonnet", "cached": False}

    # Check cache
    if use_cache:
        redis = redis_manager or RedisManager()
        try:
            if redis.client is not None:
                cached = redis.client.get(cache_key)
                if cached and isinstance(cached, bytes):
                    logger.debug(f"Cache hit for dataset insights {dataset_id}")
                    cached_data = json.loads(cached.decode("utf-8"))
                    insights = DatasetInsights(**cached_data)
                    metadata["cached"] = True
                    return insights, metadata
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
                logger.debug(f"Cached insights for dataset {dataset_id}")
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
