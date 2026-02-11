"""AI-powered blog content generation service.

Uses Claude (Haiku for cost efficiency) to generate SEO-optimized blog posts
from topics and keywords, grounded with Brave + Tavily web research.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx

from backend.services.tavily_client import get_tavily_client
from bo1.config import get_settings, resolve_model_alias
from bo1.llm.client import ClaudeClient, TokenUsage
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response_parser import extract_json_from_response

logger = logging.getLogger(__name__)

# Use Haiku for cost efficiency
MODEL = "haiku"


async def _brave_search_topic(queries: list[str]) -> list[dict[str, Any]]:
    """Run Brave searches for blog content research."""
    settings = get_settings()
    api_key = settings.brave_api_key

    if not api_key:
        logger.warning("BRAVE_API_KEY not set - skipping Brave research")
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
                        }
                    )
            except Exception as e:
                logger.warning(f"Brave research failed for '{query[:50]}': {e}")
    return results


async def _tavily_search_topic(query: str) -> list[dict[str, Any]]:
    """Run a single Tavily deep search for blog content research."""
    if not get_settings().tavily_api_key:
        logger.warning("TAVILY_API_KEY not set - skipping Tavily research")
        return []

    results: list[dict[str, Any]] = []
    try:
        data = await get_tavily_client().search(
            query,
            search_depth="advanced",
            include_answer=True,
            timeout=15.0,
        )

        if data.get("answer"):
            results.append(
                {
                    "title": query,
                    "snippet": data["answer"],
                    "url": "",
                }
            )

        for r in data.get("results", []):
            results.append(
                {
                    "title": r.get("title", ""),
                    "snippet": r.get("content", ""),
                    "url": r.get("url", ""),
                }
            )
    except Exception as e:
        logger.warning(f"Tavily research failed for '{query[:50]}': {e}")
    return results


async def _research_topic(topic: str, keywords: list[str] | None = None) -> str:
    """Research a topic via Brave + Tavily before generating content.

    Returns formatted research context string, or empty string if no results.
    """
    keyword_str = keywords[0] if keywords else ""

    # 2 Brave queries + 1 Tavily query
    brave_queries = [topic]
    if keyword_str:
        brave_queries.append(f"{topic} {keyword_str}")

    brave_results = await _brave_search_topic(brave_queries)
    tavily_results = await _tavily_search_topic(f"{topic} trends data")

    all_results = brave_results + tavily_results
    if not all_results:
        return ""

    # Cap at 20 results, format as context
    lines = []
    for r in all_results[:20]:
        snippet = r["snippet"][:300] if r["snippet"] else ""
        url = r.get("url", "")
        source_ref = f" ({url})" if url else ""
        lines.append(f"- {r['title']}{source_ref}\n  {snippet}")

    research_text = "\n\n".join(lines)
    logger.info(f"Researched topic '{topic[:50]}': {len(all_results)} results")
    return research_text


BLOG_GENERATION_PROMPT = """You are an expert SEO content writer for Board of One (Bo1), an AI-powered tool that helps founders make strategic decisions through multi-agent expert deliberation.

Bo1's expertise: multi-agent decision making, data analytics for founders, AI-powered productivity.

Generate a high-quality blog post based on the provided topic, keywords, and research.

Topic: {topic}
Target Keywords: {keywords}
{research_section}
Requirements:
1. Write in a professional but engaging tone
2. Include the target keywords naturally (aim for 1-2% keyword density)
3. Structure with clear headings (H2, H3) for SEO
   - CRITICAL: Each heading must be on its own line, followed by a blank line before content
   - Correct: "## My Heading\\n\\nParagraph text here..."
   - Wrong: "## My Heading Paragraph text continues on same line..."
4. Include a compelling introduction that hooks the reader
5. Provide actionable insights and practical takeaways
6. Reference real data, trends, or sources from the research section when available
7. Where relevant, mention how AI-powered deliberation tools help founders make better decisions
8. End with a conclusion that summarizes key points
9. Target length: 1000-1500 words

Output your response as JSON with the following structure:
{{
    "title": "SEO-optimized title (50-60 characters)",
    "excerpt": "Compelling meta description (150-160 characters)",
    "content": "Full blog post in Markdown format",
    "meta_title": "SEO title for search engines",
    "meta_description": "SEO meta description"
}}"""


@dataclass
class BlogContent:
    """Generated blog content."""

    title: str
    excerpt: str
    content: str
    meta_title: str
    meta_description: str
    usage: TokenUsage | None = None


async def generate_blog_post(
    topic: str,
    keywords: list[str] | None = None,
) -> BlogContent:
    """Generate a blog post using Claude.

    Args:
        topic: Topic to write about
        keywords: Optional list of SEO target keywords

    Returns:
        BlogContent with generated content

    Raises:
        ValueError: If generation fails or returns invalid format
    """
    keywords_str = ", ".join(keywords) if keywords else "business decisions, AI, productivity"

    # Research the topic before generating
    research_context = await _research_topic(topic, keywords)
    research_section = ""
    if research_context:
        research_section = (
            f"\nWeb Research (reference real data/sources from this):\n{research_context}\n"
        )

    client = ClaudeClient()

    prompt = BLOG_GENERATION_PROMPT.format(
        topic=topic,
        keywords=keywords_str,
        research_section=research_section,
    )

    max_retries = 1
    last_error: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            # On retry, add explicit JSON instruction
            messages = [{"role": "user", "content": prompt}]
            if attempt > 0:
                messages.append(
                    {
                        "role": "user",
                        "content": "Your previous response could not be parsed as JSON. "
                        "Please respond with ONLY valid JSON, no markdown or extra text.",
                    }
                )

            # Track cost with internal_seo category
            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
                model_name=resolve_model_alias(MODEL),
                prompt_type="blog_generation",
                cost_category="internal_seo",
            ) as cost_record:
                response, usage = await client.call(
                    model=MODEL,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=4096,
                    prefill="{",
                )
                # Populate cost record with usage data
                cost_record.input_tokens = usage.input_tokens
                cost_record.output_tokens = usage.output_tokens
                cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
                cost_record.cache_read_tokens = usage.cache_read_tokens or 0

            # Parse JSON response using robust parser
            json_str = response  # prefill already included by client
            try:
                data = extract_json_from_response(json_str)
            except json.JSONDecodeError:
                # Log raw response for debugging
                logger.warning(
                    f"JSON parse failed (attempt {attempt + 1}/{max_retries + 1}). "
                    f"Raw response preview: {response[:200]}..."
                )
                raise

            logger.info(
                f"Generated blog post: '{data.get('title', 'Untitled')}' "
                f"(tokens: {usage.total_tokens}, cost: ${usage.calculate_cost(MODEL):.4f})"
            )

            return BlogContent(
                title=data["title"],
                excerpt=data["excerpt"],
                content=data["content"],
                meta_title=data.get("meta_title", data["title"]),
                meta_description=data.get("meta_description", data["excerpt"]),
                usage=usage,
            )

        except json.JSONDecodeError as e:
            last_error = e
            if attempt < max_retries:
                logger.warning(
                    f"Retrying blog generation after JSON parse failure (attempt {attempt + 1})"
                )
                continue
            logger.error(
                f"Failed to parse blog generation response after {max_retries + 1} attempts: {e}"
            )
            raise ValueError("Blog generation returned invalid JSON format") from e
        except KeyError as e:
            logger.error(f"Missing required field in blog generation: {e}")
            raise ValueError(f"Blog generation missing required field: {e}") from e

    # Should not reach here, but safety fallback
    raise ValueError("Blog generation failed") from last_error


async def generate_blog_outline(
    topic: str,
    keywords: list[str] | None = None,
) -> dict:
    """Generate just an outline for a blog post.

    Useful for previewing structure before full generation.

    Args:
        topic: Topic to outline
        keywords: Optional SEO keywords

    Returns:
        Dict with title, sections list
    """
    keywords_str = ", ".join(keywords) if keywords else "business decisions, AI"

    outline_prompt = f"""Generate a blog post outline for the topic: {topic}

Target Keywords: {keywords_str}

Output JSON with:
{{
    "title": "Proposed title",
    "sections": [
        {{"heading": "Section title", "points": ["key point 1", "key point 2"]}}
    ]
}}"""

    client = ClaudeClient()

    # Track cost with internal_seo category
    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias(MODEL),
        prompt_type="blog_outline",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": outline_prompt}],
            temperature=0.7,
            max_tokens=1024,
            prefill="{",
        )
        # Populate cost record with usage data
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    # Extract JSON using robust parser that handles markdown/xml wrappers
    data = extract_json_from_response(response)

    logger.info(
        f"Generated outline for: '{data.get('title', topic)}' (tokens: {usage.total_tokens})"
    )

    return data


async def regenerate_blog_post(
    original: BlogContent,
    changes: list[str] | None = None,
    tone: str | None = None,
) -> BlogContent:
    """Regenerate a blog post with specific changes and/or tone adjustment.

    Args:
        original: Original blog content to regenerate
        changes: List of specific changes to make (max 3)
        tone: Desired tone (Professional, Friendly, Technical, Persuasive, Conversational)

    Returns:
        Regenerated BlogContent

    Raises:
        ValueError: If generation fails or returns invalid format
    """
    # Build the changes section
    changes_text = ""
    if changes:
        changes_list = [c for c in changes[:3] if c.strip()]  # Max 3 changes
        if changes_list:
            changes_text = "\n\nPlease make these specific changes:\n" + "\n".join(
                f"- {c}" for c in changes_list
            )

    # Build tone instruction
    tone_text = ""
    if tone:
        tone_text = f"\n\nWrite in a {tone.lower()} tone of voice."

    regenerate_prompt = f"""Regenerate the following blog post with improvements.

Original article:
Title: {original.title}
Content:
{original.content}
{changes_text}{tone_text}

Maintain the same topic and SEO focus, but apply the requested changes/tone.
Keep the article length similar (1000-1500 words).
Output your response as JSON with:
{{
    "title": "Improved title (50-60 characters)",
    "excerpt": "Compelling meta description (150-160 characters)",
    "content": "Regenerated content in Markdown",
    "meta_title": "SEO title",
    "meta_description": "SEO meta description"
}}"""

    client = ClaudeClient()

    # Track cost with internal_seo category
    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias(MODEL),
        prompt_type="blog_regeneration",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": regenerate_prompt}],
            temperature=0.7,
            max_tokens=4096,
            prefill="{",
        )
        # Populate cost record with usage data
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    # Extract JSON using robust parser (prefill already included by client)
    data = extract_json_from_response(response)

    logger.info(
        f"Regenerated blog post: '{data.get('title', 'Untitled')}' (tokens: {usage.total_tokens})"
    )

    return BlogContent(
        title=data["title"],
        excerpt=data["excerpt"],
        content=data["content"],
        meta_title=data.get("meta_title", data["title"]),
        meta_description=data.get("meta_description", data["excerpt"]),
        usage=usage,
    )


async def improve_blog_post(
    content: str,
    instructions: str,
) -> BlogContent:
    """Improve an existing blog post based on instructions.

    Args:
        content: Existing blog post content
        instructions: What to improve (e.g., "make more engaging", "add more keywords")

    Returns:
        Improved BlogContent
    """
    improve_prompt = f"""Improve the following blog post based on these instructions: {instructions}

Current content:
{content}

Output your response as JSON with:
{{
    "title": "Improved title",
    "excerpt": "Improved excerpt",
    "content": "Improved content in Markdown",
    "meta_title": "SEO title",
    "meta_description": "SEO description"
}}"""

    client = ClaudeClient()

    # Track cost with internal_seo category
    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=resolve_model_alias(MODEL),
        prompt_type="blog_improvement",
        cost_category="internal_seo",
    ) as cost_record:
        response, usage = await client.call(
            model=MODEL,
            messages=[{"role": "user", "content": improve_prompt}],
            temperature=0.7,
            max_tokens=4096,
            prefill="{",
        )
        # Populate cost record with usage data
        cost_record.input_tokens = usage.input_tokens
        cost_record.output_tokens = usage.output_tokens
        cost_record.cache_creation_tokens = usage.cache_creation_tokens or 0
        cost_record.cache_read_tokens = usage.cache_read_tokens or 0

    # Extract JSON using robust parser (prefill already included by client)
    data = extract_json_from_response(response)

    logger.info(
        f"Improved blog post: '{data.get('title', 'Untitled')}' (tokens: {usage.total_tokens})"
    )

    return BlogContent(
        title=data["title"],
        excerpt=data["excerpt"],
        content=data["content"],
        meta_title=data.get("meta_title", data["title"]),
        meta_description=data.get("meta_description", data["excerpt"]),
        usage=usage,
    )
