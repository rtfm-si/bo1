"""Skeptic evaluation for competitor relevance.

Validates detected competitors against user's business context to assess:
- Similar product: Do they solve the same core problem?
- Same ICP: Do they target similar customer profile?
- Same market: Are they in the same geographic/market segment?
"""

import json
import logging
import re

from backend.api.context.models import DetectedCompetitor, RelevanceFlags
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error

logger = logging.getLogger(__name__)


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

            # Calculate score: 1.0 for 3 checks, 0.66 for 2, 0.33 for 1, 0.0 for 0
            checks_passed = sum([flags.similar_product, flags.same_icp, flags.same_market])
            score = round(checks_passed / 3, 2)

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

    prompt = _build_batch_skeptic_prompt(competitors, context_summary)

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
            evaluated = []
            for i, competitor in enumerate(competitors):
                if i < len(results):
                    result = results[i]
                    flags = RelevanceFlags(
                        similar_product=result.get("similar_product", False),
                        same_icp=result.get("same_icp", False),
                        same_market=result.get("same_market", False),
                    )

                    checks_passed = sum([flags.similar_product, flags.same_icp, flags.same_market])
                    score = round(checks_passed / 3, 2)

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

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Batch skeptic evaluation failed: {e}",
        )

    return competitors


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

Answer these three questions:
1. similar_product: Do they solve the SAME core problem as my company? (not just similar industry)
2. same_icp: Do they target SIMILAR customers? (size, role, industry)
3. same_market: Are they in the SAME geographic/market segment?

Return JSON:
{{
  "similar_product": true/false,
  "same_icp": true/false,
  "same_market": true/false,
  "warning": "brief explanation if <2 checks pass, else null"
}}

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
  {{"similar_product": true/false, "same_icp": true/false, "same_market": true/false, "warning": "explanation if <2 pass, else null"}},
  ...
]

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
