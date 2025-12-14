"""Topic discovery service for blog content generation.

Finds relevant topics for blog posts based on:
- Business context focus areas
- Industry trends
- Competitor gaps
"""

import json
import logging
from dataclasses import dataclass

from bo1.llm.client import ClaudeClient

logger = logging.getLogger(__name__)

# Use Haiku for cost efficiency
MODEL = "haiku"


@dataclass
class Topic:
    """Discovered topic for content generation."""

    title: str
    description: str
    keywords: list[str]
    relevance_score: float  # 0-1
    source: str  # "context", "trend", "gap"


TOPIC_DISCOVERY_PROMPT = """You are an expert content strategist. Discover relevant blog topics based on the provided context.

Industry: {industry}
Focus Areas: {focus_areas}
Existing Topics to Avoid: {existing_topics}

Generate 5 unique, high-value blog topic ideas that would resonate with business leaders in this industry.

For each topic, consider:
1. Search volume potential (trending keywords)
2. Business relevance to the industry
3. Actionable insights opportunity
4. Competitive gap (topics not well covered)

Output as JSON:
{{
    "topics": [
        {{
            "title": "Topic title",
            "description": "Brief description of what the post would cover",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "relevance_score": 0.95,
            "source": "context|trend|gap"
        }}
    ]
}}"""


async def discover_topics(
    industry: str | None = None,
    focus_areas: list[str] | None = None,
    existing_topics: list[str] | None = None,
) -> list[Topic]:
    """Discover relevant blog topics.

    Args:
        industry: Industry vertical (e.g., "SaaS", "E-commerce")
        focus_areas: Business focus areas from context
        existing_topics: Topics already covered to avoid duplication

    Returns:
        List of discovered Topic objects
    """
    industry_str = industry or "technology and business"
    focus_str = (
        ", ".join(focus_areas) if focus_areas else "business growth, productivity, decision-making"
    )
    existing_str = ", ".join(existing_topics) if existing_topics else "none"

    client = ClaudeClient()

    prompt = TOPIC_DISCOVERY_PROMPT.format(
        industry=industry_str,
        focus_areas=focus_str,
        existing_topics=existing_str,
    )

    try:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.8,  # Higher for creativity
            max_tokens=2048,
            prefill="{",
        )

        json_str = "{" + response
        data = json.loads(json_str)

        topics = []
        for item in data.get("topics", []):
            topics.append(
                Topic(
                    title=item["title"],
                    description=item["description"],
                    keywords=item.get("keywords", []),
                    relevance_score=float(item.get("relevance_score", 0.5)),
                    source=item.get("source", "context"),
                )
            )

        logger.info(
            f"Discovered {len(topics)} topics for industry={industry_str} "
            f"(tokens: {usage.total_tokens}, cost: ${usage.calculate_cost(MODEL):.4f})"
        )

        return topics

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse topic discovery response: {e}")
        return []
    except KeyError as e:
        logger.error(f"Missing field in topic discovery: {e}")
        return []


async def generate_topic_from_context(
    business_context: dict,
) -> list[Topic]:
    """Generate topics from business context data.

    Uses structured business context (focus areas, metrics, competitors)
    to generate highly relevant topics.

    Args:
        business_context: Business context dict from context API

    Returns:
        List of Topic objects
    """
    # Extract relevant fields from context
    industry = business_context.get("industry", "")
    focus_areas = business_context.get("focus_areas", [])
    competitors = business_context.get("competitors", [])
    metrics = business_context.get("key_metrics", {})

    # Build enhanced prompt with full context
    context_summary = f"""
Industry: {industry}
Focus Areas: {", ".join(focus_areas) if focus_areas else "General business"}
Key Competitors: {", ".join(competitors) if competitors else "Not specified"}
Key Metrics: {json.dumps(metrics) if metrics else "Not specified"}
"""

    client = ClaudeClient()

    prompt = f"""Based on this business context, suggest 5 blog topics that would drive organic traffic and establish thought leadership:

{context_summary}

Generate topics that:
1. Address common challenges in this industry
2. Provide competitive differentiation
3. Target high-intent search keywords
4. Offer actionable insights

Output as JSON:
{{
    "topics": [
        {{
            "title": "Topic title",
            "description": "Brief description",
            "keywords": ["keyword1", "keyword2"],
            "relevance_score": 0.95,
            "source": "context"
        }}
    ]
}}"""

    try:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
            prefill="{",
        )

        json_str = "{" + response
        data = json.loads(json_str)

        topics = []
        for item in data.get("topics", []):
            topics.append(
                Topic(
                    title=item["title"],
                    description=item["description"],
                    keywords=item.get("keywords", []),
                    relevance_score=float(item.get("relevance_score", 0.5)),
                    source="context",
                )
            )

        logger.info(
            f"Generated {len(topics)} topics from business context (tokens: {usage.total_tokens})"
        )
        return topics

    except (json.JSONDecodeError, KeyError) as e:
        logger.error(f"Failed to generate context-based topics: {e}")
        return []


def filter_topics(
    topics: list[Topic],
    min_relevance: float = 0.5,
    max_topics: int = 5,
) -> list[Topic]:
    """Filter and rank discovered topics.

    Args:
        topics: List of discovered topics
        min_relevance: Minimum relevance score threshold
        max_topics: Maximum topics to return

    Returns:
        Filtered and sorted topic list
    """
    filtered = [t for t in topics if t.relevance_score >= min_relevance]
    sorted_topics = sorted(filtered, key=lambda t: t.relevance_score, reverse=True)
    return sorted_topics[:max_topics]
