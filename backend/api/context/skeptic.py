"""Skeptic evaluation for competitor relevance.

Validates detected competitors against user's business context to assess:
- Similar product: Do they solve the same core problem?
- Same ICP: Do they target similar customer profile?
- Same market: Are they in the same geographic/market segment?

Includes confidence-weighted scoring and Redis caching for efficiency.
"""

import hashlib
import json
import logging
import re

from backend.api.context.models import DetectedCompetitor, RelevanceFlags
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Lazy-initialized Redis manager for caching
_redis_manager: RedisManager | None = None


def _get_redis_manager() -> RedisManager:
    """Get or create Redis manager instance."""
    global _redis_manager
    if _redis_manager is None:
        _redis_manager = RedisManager()
    return _redis_manager


# Confidence multipliers for weighted scoring
CONFIDENCE_WEIGHTS = {
    "high": 1.0,
    "medium": 0.7,
    "low": 0.4,
}

# Cache TTL: 24 hours
SKEPTIC_CACHE_TTL = 86400


def _get_cache_key(competitor_name: str, context_hash: str) -> str:
    """Build cache key for skeptic evaluation.

    Args:
        competitor_name: Normalized competitor name
        context_hash: Hash of user context

    Returns:
        Cache key string
    """
    # Normalize name for caching
    normalized = competitor_name.lower().strip()
    normalized = re.sub(r"[^a-z0-9]", "", normalized)
    return f"skeptic:eval:{normalized}:{context_hash}"


def _hash_context(company_context: dict) -> str:
    """Create a hash of relevant context fields.

    Args:
        company_context: User's business context

    Returns:
        SHA256 hash of context
    """
    # Only include fields that affect evaluation
    relevant_fields = [
        company_context.get("company_name", ""),
        company_context.get("product_description", ""),
        company_context.get("industry", ""),
        company_context.get("target_market", ""),
        company_context.get("ideal_customer_profile", ""),
        company_context.get("target_geography", ""),
        company_context.get("business_model", ""),
    ]
    content = "|".join(str(f) for f in relevant_fields)
    return hashlib.sha256(content.encode()).hexdigest()[:16]


async def _get_cached_evaluation(cache_key: str) -> dict | None:
    """Get cached skeptic evaluation.

    Args:
        cache_key: Cache key

    Returns:
        Cached evaluation dict or None
    """
    try:
        redis_manager = _get_redis_manager()
        client = redis_manager.client
        if client:
            cached = client.get(cache_key)
            if cached:
                return json.loads(cached)
    except Exception as e:
        logger.debug(f"Cache get failed: {e}")
    return None


async def _set_cached_evaluation(cache_key: str, evaluation: dict) -> None:
    """Cache skeptic evaluation.

    Args:
        cache_key: Cache key
        evaluation: Evaluation dict to cache
    """
    try:
        redis_manager = _get_redis_manager()
        client = redis_manager.client
        if client:
            client.set(cache_key, json.dumps(evaluation), ex=SKEPTIC_CACHE_TTL)
    except Exception as e:
        logger.debug(f"Cache set failed: {e}")


async def evaluate_competitor_relevance(
    competitor: DetectedCompetitor,
    company_context: dict,
) -> DetectedCompetitor:
    """Evaluate a single competitor's relevance to user's business.

    Args:
        competitor: The detected competitor
        company_context: User's business context dict

    Returns:
        DetectedCompetitor with relevance fields populated
    """
    # Build context summary for evaluation
    context_summary = _build_context_summary(company_context)

    if not context_summary:
        # Not enough context to evaluate, return as-is
        return competitor

    prompt = _build_skeptic_prompt(competitor, context_summary)

    try:
        client = ClaudeClient()
        response, _ = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=500,
            prefill="{",
        )

        result = _parse_skeptic_response(response)

        if result:
            flags = RelevanceFlags(
                similar_product=result.get("similar_product", False),
                same_icp=result.get("same_icp", False),
                same_market=result.get("same_market", False),
            )

            # Calculate base score: 1.0 for 3 checks, 0.66 for 2, 0.33 for 1, 0.0 for 0
            checks_passed = sum([flags.similar_product, flags.same_icp, flags.same_market])
            base_score = checks_passed / 3

            # Apply confidence weighting
            confidence = result.get("confidence", "medium")
            weight = CONFIDENCE_WEIGHTS.get(confidence, 0.7)
            score = round(base_score * weight, 2)

            # Generate warning if <2 checks pass
            warning = None
            if checks_passed < 2:
                warning = result.get("warning") or _generate_warning(flags, competitor.name)

            return DetectedCompetitor(
                name=competitor.name,
                url=competitor.url,
                description=competitor.description,
                relevance_score=score,
                relevance_flags=flags,
                relevance_warning=warning,
            )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Skeptic evaluation failed for {competitor.name}: {e}",
        )

    # Return original on error
    return competitor


async def evaluate_competitors_batch(
    competitors: list[DetectedCompetitor],
    company_context: dict,
) -> list[DetectedCompetitor]:
    """Evaluate relevance for a batch of competitors.

    Uses a single LLM call to evaluate all competitors for efficiency.

    Args:
        competitors: List of detected competitors
        company_context: User's business context dict

    Returns:
        List of competitors with relevance fields populated
    """
    if not competitors:
        return []

    context_summary = _build_context_summary(company_context)
    if not context_summary:
        return competitors

    # Generate context hash for caching
    context_hash = _hash_context(company_context)

    # Check cache for each competitor, separate cached from uncached
    cached_results: dict[str, dict] = {}
    uncached_competitors: list[tuple[int, DetectedCompetitor]] = []

    for i, competitor in enumerate(competitors):
        cache_key = _get_cache_key(competitor.name, context_hash)
        cached = await _get_cached_evaluation(cache_key)
        if cached:
            cached_results[competitor.name] = cached
            logger.debug(f"Cache hit for {competitor.name}")
        else:
            uncached_competitors.append((i, competitor))

    # If all cached, build results from cache
    if not uncached_competitors:
        logger.info(f"All {len(competitors)} competitors found in cache")
        return _build_evaluated_from_cache(competitors, cached_results)

    # Build prompt for uncached competitors only
    uncached_list = [c for _, c in uncached_competitors]
    prompt = _build_batch_skeptic_prompt(uncached_list, context_summary)

    try:
        client = ClaudeClient()
        response, _ = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=2000,
            prefill="[",
        )

        results = _parse_batch_response(response)

        if results:
            # Cache new results
            for j, (_orig_idx, competitor) in enumerate(uncached_competitors):
                if j < len(results):
                    cache_key = _get_cache_key(competitor.name, context_hash)
                    await _set_cached_evaluation(cache_key, results[j])
                    cached_results[competitor.name] = results[j]

            # Build final evaluated list in original order
            return _build_evaluated_from_cache(competitors, cached_results)

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Batch skeptic evaluation failed: {e}",
        )

    return competitors


def _build_evaluated_from_cache(
    competitors: list[DetectedCompetitor],
    cached_results: dict[str, dict],
) -> list[DetectedCompetitor]:
    """Build evaluated competitor list from cached results.

    Args:
        competitors: Original competitor list
        cached_results: Dict of competitor name -> evaluation result

    Returns:
        List of DetectedCompetitor with relevance fields populated
    """
    evaluated = []
    for competitor in competitors:
        result = cached_results.get(competitor.name)
        if result:
            flags = RelevanceFlags(
                similar_product=result.get("similar_product", False),
                same_icp=result.get("same_icp", False),
                same_market=result.get("same_market", False),
            )

            # Calculate base score
            checks_passed = sum([flags.similar_product, flags.same_icp, flags.same_market])
            base_score = checks_passed / 3

            # Apply confidence weighting
            confidence = result.get("confidence", "medium")
            weight = CONFIDENCE_WEIGHTS.get(confidence, 0.7)
            score = round(base_score * weight, 2)

            warning = None
            if checks_passed < 2:
                warning = result.get("warning") or _generate_warning(flags, competitor.name)

            evaluated.append(
                DetectedCompetitor(
                    name=competitor.name,
                    url=competitor.url,
                    description=competitor.description,
                    relevance_score=score,
                    relevance_flags=flags,
                    relevance_warning=warning,
                )
            )
        else:
            evaluated.append(competitor)
    return evaluated


def _build_context_summary(company_context: dict) -> str | None:
    """Build a summary of company context for evaluation.

    Args:
        company_context: User's business context dict

    Returns:
        Summary string or None if insufficient context
    """
    parts = []

    if company_context.get("company_name"):
        parts.append(f"Company: {company_context['company_name']}")

    if company_context.get("product_description"):
        parts.append(f"Product: {company_context['product_description'][:200]}")

    if company_context.get("industry"):
        parts.append(f"Industry: {company_context['industry']}")

    if company_context.get("target_market"):
        parts.append(f"Target Market: {company_context['target_market'][:150]}")

    if company_context.get("ideal_customer_profile"):
        parts.append(f"ICP: {company_context['ideal_customer_profile'][:150]}")

    if company_context.get("target_geography"):
        parts.append(f"Geography: {company_context['target_geography']}")

    if company_context.get("business_model"):
        parts.append(f"Model: {company_context['business_model']}")

    if len(parts) < 2:
        return None

    return "\n".join(parts)


def _build_skeptic_prompt(competitor: DetectedCompetitor, context_summary: str) -> str:
    """Build the skeptic evaluation prompt for a single competitor.

    Args:
        competitor: The competitor to evaluate
        context_summary: Company context summary

    Returns:
        Prompt string
    """
    competitor_info = f"Name: {competitor.name}"
    if competitor.url:
        competitor_info += f"\nURL: {competitor.url}"
    if competitor.description:
        competitor_info += f"\nDescription: {competitor.description}"

    return f"""Evaluate if this company is a relevant competitor.

MY COMPANY:
{context_summary}

POTENTIAL COMPETITOR:
{competitor_info}

Answer these three questions with reasoning:
1. similar_product: Do they solve the SAME core problem as my company? (not just similar industry)
2. same_icp: Do they target SIMILAR customers? (size, role, industry)
3. same_market: Are they in the SAME geographic/market segment?

Return JSON:
{{
  "similar_product": true/false,
  "similar_product_reasoning": "1 sentence why",
  "same_icp": true/false,
  "same_icp_reasoning": "1 sentence why",
  "same_market": true/false,
  "same_market_reasoning": "1 sentence why",
  "confidence": "high/medium/low",
  "warning": "brief explanation if <2 checks pass, else null"
}}

Confidence levels:
- high: Clear evidence from description/URL that this is a real competitor
- medium: Likely a competitor but limited information to confirm
- low: Uncertain - could be tangentially related or different space

Be skeptical - only return true if there's clear overlap. Return ONLY JSON."""


def _build_batch_skeptic_prompt(competitors: list[DetectedCompetitor], context_summary: str) -> str:
    """Build batch evaluation prompt for multiple competitors.

    Args:
        competitors: List of competitors to evaluate
        context_summary: Company context summary

    Returns:
        Prompt string
    """
    competitors_list = []
    for i, c in enumerate(competitors):
        info = f"{i + 1}. {c.name}"
        if c.url:
            info += f" ({c.url})"
        if c.description:
            info += f" - {c.description[:100]}"
        competitors_list.append(info)

    competitors_text = "\n".join(competitors_list)

    return f"""Evaluate if these companies are relevant competitors.

MY COMPANY:
{context_summary}

POTENTIAL COMPETITORS:
{competitors_text}

For EACH competitor, answer:
1. similar_product: Do they solve the SAME core problem? (not just similar industry)
2. same_icp: Do they target SIMILAR customers? (size, role, industry)
3. same_market: Are they in the SAME geographic/market segment?

Return a JSON array with one object per competitor in order:
[
  {{
    "similar_product": true/false,
    "similar_product_reasoning": "1 sentence why",
    "same_icp": true/false,
    "same_icp_reasoning": "1 sentence why",
    "same_market": true/false,
    "same_market_reasoning": "1 sentence why",
    "confidence": "high/medium/low",
    "warning": "explanation if <2 pass, else null"
  }},
  ...
]

Confidence levels:
- high: Clear evidence this is a real competitor
- medium: Likely a competitor but limited information
- low: Uncertain - could be tangentially related

Be skeptical - only return true for clear overlap. Return ONLY the JSON array."""


def _parse_skeptic_response(response: str) -> dict | None:
    """Parse single skeptic evaluation response.

    Args:
        response: Raw LLM response

    Returns:
        Parsed dict or None
    """
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r"\{[\s\S]*\}", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    logger.warning(f"Failed to parse skeptic response: {response[:200]}")
    return None


def _parse_batch_response(response: str) -> list[dict] | None:
    """Parse batch skeptic evaluation response.

    Args:
        response: Raw LLM response

    Returns:
        List of parsed dicts or None
    """
    try:
        return json.loads(response)
    except json.JSONDecodeError:
        json_match = re.search(r"\[[\s\S]*\]", response)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass
    logger.warning(f"Failed to parse batch skeptic response: {response[:200]}")
    return None


def _generate_warning(flags: RelevanceFlags, competitor_name: str) -> str:
    """Generate a warning message for low-relevance competitors.

    Args:
        flags: The relevance flags
        competitor_name: Name of the competitor

    Returns:
        Warning message
    """
    missing = []
    if not flags.similar_product:
        missing.append("different product focus")
    if not flags.same_icp:
        missing.append("different target customers")
    if not flags.same_market:
        missing.append("different market segment")

    return f"{competitor_name}: {', '.join(missing)}"
