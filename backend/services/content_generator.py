"""AI-powered blog content generation service.

Uses Claude (Haiku for cost efficiency) to generate SEO-optimized blog posts
from topics and keywords.
"""

import json
import logging
from dataclasses import dataclass

from bo1.config import resolve_model_alias
from bo1.llm.client import ClaudeClient, TokenUsage
from bo1.llm.cost_tracker import CostTracker
from bo1.llm.response_parser import extract_json_from_response

logger = logging.getLogger(__name__)

# Use Haiku for cost efficiency
MODEL = "haiku"

BLOG_GENERATION_PROMPT = """You are an expert SEO content writer specializing in business technology and decision-making.

Generate a high-quality blog post based on the provided topic and keywords.

Topic: {topic}
Target Keywords: {keywords}

Requirements:
1. Write in a professional but engaging tone
2. Include the target keywords naturally (aim for 1-2% keyword density)
3. Structure with clear headings (H2, H3) for SEO
4. Include a compelling introduction that hooks the reader
5. Provide actionable insights and practical takeaways
6. End with a conclusion that summarizes key points
7. Target length: 1000-1500 words

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

    client = ClaudeClient()

    prompt = BLOG_GENERATION_PROMPT.format(
        topic=topic,
        keywords=keywords_str,
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
