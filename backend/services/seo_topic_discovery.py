"""SEO topic discovery service for high-intent founder traffic.

Generates topic suggestions for decision content pipeline.
Uses Sonnet for quality (topic strategy requires nuance).
"""

import logging
from dataclasses import dataclass

from bo1.config import resolve_model_alias
from bo1.llm.client import ClaudeClient
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response_parser import extract_json_from_response

logger = logging.getLogger(__name__)

# Use Sonnet for quality - topic strategy requires nuance
MODEL = "sonnet"

VALID_CATEGORIES = [
    "hiring",
    "pricing",
    "fundraising",
    "marketing",
    "strategy",
    "product",
    "operations",
    "growth",
]


@dataclass
class TopicSuggestion:
    """A suggested decision topic for content creation."""

    topic: str  # "Should I hire a fractional CTO?"
    category: str  # hiring
    search_intent: str  # transactional/informational
    estimated_volume: str  # low/medium/high
    keyword_cluster: list[str]  # Related search terms
    authority_angle: str  # Why Bo1 is authoritative


TOPIC_DISCOVERY_PROMPT = """You are an SEO strategist for Board of One, a decision-support tool for founders.

Board of One helps founders make strategic decisions by providing multiple expert perspectives (Growth Operator, Financial Strategist, Risk Analyst, etc.) and synthesizing them into balanced recommendations.

{category_instruction}

Generate {count} high-intent decision topics that founders actively search for.

Focus on:
1. Transactional/commercial intent ("should I...", "how to decide...", "when to...")
2. Specific founder pain points with clear decision points
3. Topics where multi-expert perspective adds unique value
4. Questions that don't have simple yes/no answers

For each topic provide:
- topic: The decision question as a clear title (suitable as page H1)
- category: One of {categories}
- search_intent: "transactional" (ready to act) or "informational" (researching)
- estimated_volume: "low" (niche), "medium" (moderate), "high" (broad appeal)
- keyword_cluster: 3-5 related keywords founders might search
- authority_angle: Why Board of One's multi-expert approach is uniquely valuable for this topic

Output as JSON array:
[
    {{
        "topic": "Should I hire a fractional CTO or build an internal team?",
        "category": "hiring",
        "search_intent": "transactional",
        "estimated_volume": "medium",
        "keyword_cluster": ["fractional cto cost", "when to hire cto", "fractional vs full-time cto", "startup cto hiring"],
        "authority_angle": "Weighing growth speed vs technical debt requires balancing multiple expert viewpoints"
    }}
]"""


async def discover_topics(
    category: str | None = None,
    count: int = 10,
) -> list[TopicSuggestion]:
    """Discover high-intent decision topics for content pipeline.

    Args:
        category: Optional category filter (e.g., "hiring", "pricing")
        count: Number of topics to generate (default 10)

    Returns:
        List of TopicSuggestion objects
    """
    if category and category not in VALID_CATEGORIES:
        raise ValueError(f"Invalid category. Must be one of: {VALID_CATEGORIES}")

    category_instruction = (
        f"Focus specifically on the '{category}' category."
        if category
        else "Cover a mix of categories relevant to startup founders."
    )

    prompt = TOPIC_DISCOVERY_PROMPT.format(
        category_instruction=category_instruction,
        count=count,
        categories=VALID_CATEGORIES,
    )

    client = ClaudeClient()

    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias(MODEL),
        prompt_type="seo_topic_discovery",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # Higher temp for creative variety
            max_tokens=4096,
            prefill="[",
        )
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    data = extract_json_from_response(response)

    # Handle both array and object responses
    topics_data = data if isinstance(data, list) else data.get("topics", [])

    topics = []
    for item in topics_data[:count]:
        # Validate category
        item_category = item.get("category", "strategy")
        if item_category not in VALID_CATEGORIES:
            item_category = "strategy"

        topics.append(
            TopicSuggestion(
                topic=item.get("topic", ""),
                category=item_category,
                search_intent=item.get("search_intent", "transactional"),
                estimated_volume=item.get("estimated_volume", "medium"),
                keyword_cluster=item.get("keyword_cluster", [])[:5],
                authority_angle=item.get("authority_angle", ""),
            )
        )

    logger.info(
        f"Topic discovery: generated {len(topics)} topics "
        f"(category={category}, tokens={usage.total_tokens})"
    )

    return topics
