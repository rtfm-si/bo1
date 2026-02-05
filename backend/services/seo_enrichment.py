"""SEO enrichment service for decisions.

Generates SEO keywords, meta titles, and finds related decisions.
Uses Haiku for cost efficiency.
"""

import logging
from dataclasses import dataclass

from bo1.config import resolve_model_alias
from bo1.llm.client import ClaudeClient
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response_parser import extract_json_from_response
from bo1.state.repositories.decision_repository import decision_repository

logger = logging.getLogger(__name__)

# Use Haiku for cost efficiency (~$0.002/decision)
MODEL = "haiku"


@dataclass
class SEOEnrichment:
    """SEO enrichment result."""

    seo_keywords: list[str]  # 5-8 keywords
    meta_title: str  # 50-60 chars, SEO-optimized
    related_decision_ids: list[str]  # Top 3-5 related


SEO_ENRICHMENT_PROMPT = """Analyze this decision for SEO optimization.

Title: {title}
Category: {category}
Synthesis: {synthesis}

Generate:
1. seo_keywords: 5-8 specific search terms founders would use when facing this decision
   - Focus on transactional/commercial intent ("should I...", "how to decide...")
   - Include category-specific terms
   - Mix short-tail and long-tail keywords

2. meta_title: 50-60 character SEO title
   - Include primary keyword near start
   - Make it compelling and specific
   - Different from display title

Output JSON:
{{
    "seo_keywords": ["keyword1", "keyword2", ...],
    "meta_title": "SEO-optimized title here"
}}"""


async def enrich_decision_seo(
    decision_id: str,
    title: str | None = None,
    category: str | None = None,
    synthesis: str | None = None,
) -> SEOEnrichment:
    """Generate SEO enrichment for a decision.

    Args:
        decision_id: Decision UUID
        title: Decision title (fetched if not provided)
        category: Decision category (fetched if not provided)
        synthesis: Decision synthesis (fetched if not provided)

    Returns:
        SEOEnrichment with keywords, meta_title, and related_decision_ids
    """
    # Fetch decision data if not provided
    if not all([title, category, synthesis]):
        decision = decision_repository.get_by_id(decision_id)
        if not decision:
            raise ValueError(f"Decision {decision_id} not found")
        title = title or decision.get("title", "")
        category = category or decision.get("category", "")
        synthesis = synthesis or decision.get("synthesis", "")

    # Truncate synthesis for prompt efficiency
    synthesis_truncated = (synthesis or "")[:2000]

    prompt = SEO_ENRICHMENT_PROMPT.format(
        title=title,
        category=category,
        synthesis=synthesis_truncated,
    )

    client = ClaudeClient()

    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias(MODEL),
        prompt_type="seo_enrichment",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # Lower temp for consistency
            max_tokens=1024,
            prefill="{",
        )
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    data = extract_json_from_response(response)

    seo_keywords = data.get("seo_keywords", [])[:8]
    meta_title = data.get("meta_title", title)[:70]

    # Find related decisions by keyword overlap
    related_ids: list[str] = []
    if seo_keywords and category:
        related = decision_repository.find_similar_by_keywords(
            category=category,
            keywords=seo_keywords,
            exclude_id=decision_id,
            limit=5,
        )
        related_ids = [str(r["id"]) for r in related]

    logger.info(
        f"SEO enrichment for decision {decision_id}: "
        f"{len(seo_keywords)} keywords, {len(related_ids)} related"
    )

    return SEOEnrichment(
        seo_keywords=seo_keywords,
        meta_title=meta_title,
        related_decision_ids=related_ids,
    )


async def backfill_seo_fields(limit: int = 50) -> dict[str, int]:
    """Backfill SEO fields for decisions missing them.

    Args:
        limit: Max decisions to process

    Returns:
        Dict with counts: {enriched: N, skipped: N, failed: N}
    """
    # Get decisions without seo_keywords
    decisions = decision_repository.list_decisions_without_seo(limit=limit)

    results = {"enriched": 0, "skipped": 0, "failed": 0}

    for decision in decisions:
        decision_id = str(decision["id"])

        # Skip if already has keywords
        if decision.get("seo_keywords"):
            results["skipped"] += 1
            continue

        try:
            enrichment = await enrich_decision_seo(
                decision_id=decision_id,
                title=decision.get("title"),
                category=decision.get("category"),
                synthesis=decision.get("synthesis"),
            )

            # Update decision
            decision_repository.update(
                decision_id,
                seo_keywords=enrichment.seo_keywords,
                meta_title=enrichment.meta_title,
                related_decision_ids=enrichment.related_decision_ids,
            )
            results["enriched"] += 1

        except Exception as e:
            logger.error(f"SEO enrichment failed for {decision_id}: {e}")
            results["failed"] += 1

    logger.info(f"SEO backfill complete: {results}")
    return results
