"""Topic discovery service for blog content generation.

Finds relevant topics for blog posts based on:
- Business context focus areas
- Industry trends
- Competitor gaps
"""

import json
import logging
import os
from dataclasses import dataclass

from anthropic import RateLimitError

from bo1.llm.client import ClaudeClient

logger = logging.getLogger(__name__)

# Enable mock mode for local dev without LLM calls
USE_MOCK_TOPIC_DISCOVERY = os.getenv("USE_MOCK_TOPIC_DISCOVERY", "").lower() == "true"


class TopicDiscoveryError(Exception):
    """Raised when topic discovery fails."""

    def __init__(self, message: str, error_type: str = "unknown") -> None:
        """Initialize TopicDiscoveryError.

        Args:
            message: Error message
            error_type: Type of error (rate_limit, parse_error, unknown)
        """
        super().__init__(message)
        self.error_type = error_type


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

IMPORTANT: You MUST respond with ONLY valid JSON matching this exact schema. No text before or after.
{{
    "topics": [
        {{
            "title": "Topic title (string)",
            "description": "Brief description of what the post would cover (string)",
            "keywords": ["keyword1", "keyword2", "keyword3"],
            "relevance_score": 0.85,
            "source": "context"
        }}
    ]
}}

Rules for the JSON:
- relevance_score must be a number between 0 and 1
- source must be one of: "context", "trend", "gap"
- keywords must be an array of strings
- Return exactly 5 topics"""


# Mock topics for local development
MOCK_TOPICS = [
    Topic(
        title="How AI-Powered Decision Making is Transforming Business Strategy",
        description="Explore how AI deliberation tools help leaders make better, faster decisions",
        keywords=["AI decisions", "business strategy", "AI tools"],
        relevance_score=0.92,
        source="context",
    ),
    Topic(
        title="The Rise of Asynchronous Collaboration in Remote Teams",
        description="Best practices for effective async communication in distributed teams",
        keywords=["async collaboration", "remote work", "team productivity"],
        relevance_score=0.88,
        source="trend",
    ),
    Topic(
        title="Data-Driven vs Intuition: Finding the Right Balance",
        description="When to trust the numbers and when to go with your gut",
        keywords=["data-driven", "intuition", "decision making"],
        relevance_score=0.85,
        source="gap",
    ),
    Topic(
        title="Building a Second Brain for Your Business",
        description="How to create systems that capture and leverage organizational knowledge",
        keywords=["knowledge management", "second brain", "productivity"],
        relevance_score=0.82,
        source="context",
    ),
    Topic(
        title="The Hidden Costs of Decision Fatigue in Leadership",
        description="Strategies to reduce cognitive load and make better decisions",
        keywords=["decision fatigue", "leadership", "productivity"],
        relevance_score=0.80,
        source="trend",
    ),
]


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

    Raises:
        TopicDiscoveryError: If discovery fails after retries
    """
    # Return mock topics if mock mode enabled
    if USE_MOCK_TOPIC_DISCOVERY:
        logger.info("Using mock topics (USE_MOCK_TOPIC_DISCOVERY=true)")
        return MOCK_TOPICS

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

    max_attempts = 2
    last_error: Exception | None = None

    for attempt in range(max_attempts):
        try:
            response, usage = await client.call(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.6,  # Lower for more predictable JSON output
                max_tokens=2048,
                prefill="{",
            )

            json_str = "{" + response
            logger.debug(f"Topic discovery raw response (attempt {attempt + 1}): {json_str[:500]}")

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

        except RateLimitError as e:
            logger.error(f"Rate limit exceeded during topic discovery: {e}")
            raise TopicDiscoveryError(
                "Rate limit exceeded. Please try again in a few minutes.",
                error_type="rate_limit",
            ) from e
        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(
                f"Failed to parse topic discovery response (attempt {attempt + 1}/{max_attempts}): {e}"
            )
            if attempt < max_attempts - 1:
                continue  # Retry
        except KeyError as e:
            last_error = e
            logger.warning(
                f"Missing field in topic discovery (attempt {attempt + 1}/{max_attempts}): {e}"
            )
            if attempt < max_attempts - 1:
                continue  # Retry
        except Exception as e:
            logger.error(f"Unexpected error during topic discovery: {type(e).__name__}: {e}")
            raise TopicDiscoveryError(
                f"Failed to discover topics: {e}",
                error_type="unknown",
            ) from e

    # All retries exhausted
    error_msg = f"Failed to parse LLM response after {max_attempts} attempts"
    if last_error:
        error_msg = f"{error_msg}: {last_error}"
    logger.error(error_msg)
    raise TopicDiscoveryError(error_msg, error_type="parse_error")


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
