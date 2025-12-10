"""LLM-powered dataset summary generation with Redis caching.

Generates natural language summaries of dataset profiles using Claude.
"""

import hashlib
import json
import logging
from typing import Any

from bo1.llm.client import ClaudeClient
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Cache settings
SUMMARY_CACHE_TTL = 86400  # 24 hours
SUMMARY_CACHE_PREFIX = "dataset_summary"


def _format_profile_for_prompt(profile_dict: dict[str, Any]) -> str:
    """Format profile data into a structured prompt section."""
    lines = [
        f"Dataset: {profile_dict['row_count']} rows, {profile_dict['column_count']} columns",
        "",
        "Columns:",
    ]

    for col in profile_dict.get("columns", []):
        col_line = f"- {col['name']} ({col['inferred_type']})"
        stats = col.get("stats", {})

        details = []
        if stats.get("null_count", 0) > 0:
            null_pct = (stats["null_count"] / profile_dict["row_count"]) * 100
            details.append(f"{null_pct:.1f}% null")
        if stats.get("unique_count"):
            details.append(f"{stats['unique_count']} unique")
        if stats.get("min_value") is not None and stats.get("max_value") is not None:
            details.append(f"range: {stats['min_value']} to {stats['max_value']}")
        if stats.get("mean_value") is not None:
            details.append(f"mean: {stats['mean_value']:.2f}")
        if stats.get("top_values"):
            top = stats["top_values"][:3]
            top_str = ", ".join(f"{v['value']} ({v['count']})" for v in top)
            details.append(f"top: {top_str}")

        if details:
            col_line += f" - {'; '.join(details)}"
        lines.append(col_line)

    return "\n".join(lines)


def _compute_profile_hash(profile_dict: dict[str, Any]) -> str:
    """Compute hash of profile for cache key."""
    content = json.dumps(profile_dict, sort_keys=True, default=str)
    return hashlib.md5(content.encode(), usedforsecurity=False).hexdigest()[:12]


async def generate_dataset_summary(
    profile_dict: dict[str, Any],
    dataset_name: str | None = None,
    use_cache: bool = True,
    redis_manager: RedisManager | None = None,
) -> str:
    """Generate natural language summary of dataset profile using Claude.

    Args:
        profile_dict: Profile data as dictionary (from DatasetProfile.to_dict())
        dataset_name: Optional dataset name for context
        use_cache: Whether to use Redis cache
        redis_manager: Optional Redis manager instance

    Returns:
        Generated summary string
    """
    dataset_id = profile_dict.get("dataset_id", "unknown")
    profile_hash = _compute_profile_hash(profile_dict)
    cache_key = f"{SUMMARY_CACHE_PREFIX}:{dataset_id}:{profile_hash}"

    # Check cache
    if use_cache:
        redis = redis_manager or RedisManager()
        try:
            cached = redis.client.get(cache_key)
            if cached:
                logger.debug(f"Cache hit for dataset summary {dataset_id}")
                return cached.decode("utf-8")
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")

    # Format prompt
    profile_text = _format_profile_for_prompt(profile_dict)
    name_context = f' named "{dataset_name}"' if dataset_name else ""

    system_prompt = """You are a data analyst assistant. Generate concise, actionable summaries of dataset profiles.

Focus on:
1. Overall data quality (completeness, consistency)
2. Key patterns or notable distributions
3. Potential issues or areas needing attention
4. What questions this data could answer

Be specific but concise. Use 2-3 short paragraphs."""

    user_prompt = f"""Summarize this dataset{name_context}:

{profile_text}

Provide a brief, actionable summary."""

    # Call Claude
    client = ClaudeClient()
    try:
        response, usage = await client.call(
            model="haiku",  # Use fast model for summaries
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            max_tokens=500,
            temperature=0.3,
        )
        summary = response.strip()
        logger.info(
            f"Generated summary for dataset {dataset_id} "
            f"({usage.total_tokens} tokens, ${usage.calculate_cost('haiku'):.4f})"
        )
    except Exception as e:
        logger.error(f"Failed to generate summary: {e}")
        summary = "Summary generation failed. Please try again later."

    # Cache result
    if use_cache and summary and "failed" not in summary.lower():
        redis = redis_manager or RedisManager()
        try:
            redis.client.setex(cache_key, SUMMARY_CACHE_TTL, summary)
            logger.debug(f"Cached summary for dataset {dataset_id}")
        except Exception as e:
            logger.warning(f"Redis cache write failed: {e}")

    return summary


def invalidate_summary_cache(
    dataset_id: str,
    redis_manager: RedisManager | None = None,
) -> int:
    """Invalidate all cached summaries for a dataset.

    Args:
        dataset_id: Dataset UUID
        redis_manager: Optional Redis manager instance

    Returns:
        Number of cache keys deleted
    """
    redis = redis_manager or RedisManager()
    pattern = f"{SUMMARY_CACHE_PREFIX}:{dataset_id}:*"
    try:
        keys = list(redis.client.scan_iter(match=pattern))
        if keys:
            deleted = redis.client.delete(*keys)
            logger.info(f"Invalidated {deleted} summary cache entries for {dataset_id}")
            return deleted
        return 0
    except Exception as e:
        logger.warning(f"Failed to invalidate summary cache: {e}")
        return 0
