"""Topic discovery service for blog content generation.

Finds relevant topics for blog posts based on:
- Web research (Brave + Tavily)
- Bo1 positioning pillars
- LLM scoring of search results
"""

import json
import logging
import os
from dataclasses import dataclass
from typing import Any

import httpx
from anthropic import RateLimitError

from bo1.config import get_settings, resolve_model_alias
from bo1.llm.client import ClaudeClient
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response_parser import extract_json_from_response

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

            raw_response = response  # prefill already included by client
            logger.info(
                f"Topic discovery raw response (attempt {attempt + 1}): {raw_response[:500]}"
            )

            # Extract JSON using robust parser that handles markdown/xml wrappers
            data = extract_json_from_response(raw_response)

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

        json_str = response  # prefill already included by client
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


# =============================================================================
# Topic Proposer (research-backed blog topic proposals)
# =============================================================================


@dataclass
class TopicProposal:
    """Proposed blog topic with rationale."""

    title: str
    rationale: str
    suggested_keywords: list[str]
    source: str  # "web-research", "llm-generated"


# Blog-specific search queries for web research
BLOG_BRAVE_QUERIES = [
    # Multi-agent decision making
    "AI multi-agent decision making for business leaders",
    "consensus-based AI tools strategic decisions",
    "multi-agent deliberation frameworks startups",
    # Data analytics for founders
    "data-driven decision making solo founders",
    "startup analytics tools founder productivity",
    "business intelligence small teams AI",
    # SEO content + broader founder topics
    "AI content generation SEO strategy",
    "solo founder scaling decisions hiring vs automation",
    "startup founder common strategic mistakes",
]

BLOG_TAVILY_QUERIES = [
    "trending AI decision-making tools for startup founders",
    "emerging trends multi-agent AI systems business applications",
]


async def _brave_search(queries: list[str]) -> list[dict[str, Any]]:
    """Run Brave searches and collect raw results."""
    settings = get_settings()
    api_key = settings.brave_api_key

    if not api_key:
        logger.warning("BRAVE_API_KEY not set - skipping Brave search")
        return []

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for query in queries:
            try:
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": api_key},
                    params={"q": query, "count": 5},
                    timeout=10.0,
                )
                response.raise_for_status()
                data = response.json()
                for r in data.get("web", {}).get("results", []):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "snippet": r.get("description", ""),
                            "url": r.get("url", ""),
                            "source": "brave",
                        }
                    )
            except Exception as e:
                logger.warning(f"Brave search failed for '{query[:50]}': {e}")

    logger.info(f"Blog Brave: collected {len(results)} results from {len(queries)} queries")
    return results


async def _tavily_search(queries: list[str]) -> list[dict[str, Any]]:
    """Run Tavily deep searches and collect raw results."""
    settings = get_settings()
    api_key = settings.tavily_api_key

    if not api_key:
        logger.warning("TAVILY_API_KEY not set - skipping Tavily search")
        return []

    results: list[dict[str, Any]] = []
    async with httpx.AsyncClient() as client:
        for query in queries:
            try:
                response = await client.post(
                    "https://api.tavily.com/search",
                    json={
                        "api_key": api_key,
                        "query": query,
                        "search_depth": "advanced",
                        "include_answer": True,
                        "include_raw_content": False,
                        "max_results": 5,
                    },
                    timeout=15.0,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("answer"):
                    results.append(
                        {
                            "title": query,
                            "snippet": data["answer"],
                            "url": "",
                            "source": "tavily",
                        }
                    )

                for r in data.get("results", []):
                    results.append(
                        {
                            "title": r.get("title", ""),
                            "snippet": r.get("content", ""),
                            "url": r.get("url", ""),
                            "source": "tavily",
                        }
                    )
            except Exception as e:
                logger.warning(f"Tavily search failed for '{query[:50]}': {e}")

    logger.info(f"Blog Tavily: collected {len(results)} results from {len(queries)} queries")
    return results


TOPIC_PROPOSAL_PROMPT = """You are an SEO content strategist for Board of One (Bo1), an AI tool that helps founders make strategic decisions through multi-agent expert deliberation.

Bo1's 3 expertise pillars:
1. **Multi-agent decision making** — AI personas debate decisions from finance, ops, strategy angles
2. **Data analytics for founders** — data-driven insights that replace expensive advisory hires
3. **SEO content & founder productivity** — thought leadership for solo founders scaling without big teams

## Task
Analyze the web research below and propose {count} blog topics that:
- Are backed by evidence from the search results (reference real trends, data, or articles)
- Target high-intent keywords founders would actually search
- Position Bo1 as the expert in multi-agent AI decision-making
- Are NOT duplicates of existing posts listed below

## Existing blog posts (skip these):
{existing_posts}

## Web Research Results
{search_results}

Output as JSON:
{{
    "topics": [
        {{
            "title": "Compelling, SEO-friendly topic title",
            "rationale": "Why this topic matters and what search evidence supports it",
            "suggested_keywords": ["keyword1", "keyword2", "keyword3"],
            "source": "web-research"
        }}
    ]
}}"""


async def _llm_only_propose(
    existing_titles: list[str],
    count: int,
) -> list[TopicProposal]:
    """Fallback: propose topics without web research (LLM-only).

    Used when Brave/Tavily API keys are missing or searches fail.
    """
    client = ClaudeClient()

    prompt = f"""You are an SEO content strategist for Board of One (Bo1), an AI tool that helps founders make strategic decisions through multi-agent expert deliberation.

Bo1's 3 expertise pillars:
1. Multi-agent decision making — AI personas debate decisions from finance, ops, strategy angles
2. Data analytics for founders — data-driven insights replacing expensive advisory hires
3. SEO content & founder productivity — thought leadership for solo founders scaling without big teams

Existing blog posts (skip these):
{chr(10).join(f"- {t}" for t in existing_titles) if existing_titles else "None"}

Generate {count} blog topic proposals that position Bo1 as an expert.

Output as JSON:
{{"topics": [{{"title": "...", "rationale": "...", "suggested_keywords": ["..."], "source": "llm-generated"}}]}}"""

    try:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7,
            max_tokens=2048,
            prefill="{",
        )
        data = extract_json_from_response(response)
        proposals = []
        for item in data.get("topics", []):
            proposals.append(
                TopicProposal(
                    title=item["title"],
                    rationale=item["rationale"],
                    suggested_keywords=item.get("suggested_keywords", []),
                    source="llm-generated",
                )
            )
        logger.info(f"LLM-only proposed {len(proposals)} topics (tokens: {usage.total_tokens})")
        return proposals[:count]
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"LLM-only topic proposal failed: {e}")
        return []


async def propose_topics(
    existing_titles: list[str],
    count: int = 5,
) -> list[TopicProposal]:
    """Propose new blog topics backed by web research.

    Flow:
    1. Brave + Tavily searches for trending content
    2. Haiku scores and proposes topics from results
    3. Falls back to LLM-only if search APIs unavailable

    Args:
        existing_titles: Titles of existing blog posts
        count: Number of topics to propose

    Returns:
        List of TopicProposal objects
    """
    # 1. Run web research
    brave_results = await _brave_search(BLOG_BRAVE_QUERIES)
    tavily_results = await _tavily_search(BLOG_TAVILY_QUERIES)
    all_results = brave_results + tavily_results

    # Fallback to LLM-only if no search results
    if not all_results:
        logger.info("No search results - falling back to LLM-only proposals")
        return await _llm_only_propose(existing_titles, count)

    # 2. Format results for LLM scoring (cap at 40)
    search_text = "\n\n".join(
        f"[{r['source']}] {r['title']}\n{r['snippet'][:300]}" for r in all_results[:40]
    )

    prompt = TOPIC_PROPOSAL_PROMPT.format(
        count=count,
        existing_posts="\n".join(f"- {t}" for t in existing_titles) if existing_titles else "None",
        search_results=search_text,
    )

    # 3. Call Haiku for scoring
    client = ClaudeClient()
    try:
        with CostTracker.track_call(
            provider="anthropic",
            operation_type="completion",
            model_name=resolve_model_alias(MODEL),
            prompt_type="blog_topic_proposal",
            cost_category="internal_seo",
        ) as cost_record:
            response, usage = await client.call(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=2048,
                prefill="{",
            )
            cost_record.input_tokens = usage.input_tokens
            cost_record.output_tokens = usage.output_tokens
            cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
            cost_record.cache_read_tokens = usage.cache_read_tokens or 0

        data = extract_json_from_response(response)

        proposals = []
        for item in data.get("topics", []):
            proposals.append(
                TopicProposal(
                    title=item["title"],
                    rationale=item["rationale"],
                    suggested_keywords=item.get("suggested_keywords", []),
                    source=item.get("source", "web-research"),
                )
            )

        logger.info(
            f"Proposed {len(proposals)} research-backed topics (tokens: {usage.total_tokens})"
        )
        return proposals[:count]

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"Research-backed proposal failed: {e} - falling back to LLM-only")
        return await _llm_only_propose(existing_titles, count)
