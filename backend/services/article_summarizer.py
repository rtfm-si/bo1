"""Article summarizer service for market trends.

Uses Claude Haiku to generate concise summaries and key points from article content.
Cost: ~$0.001/article (Haiku is very cheap)
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any

from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.logging.errors import ErrorCode, log_error
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)


# System prompt for article summarization
ARTICLE_SUMMARY_SYSTEM_PROMPT = """You are a business news analyst. Summarize articles for busy entrepreneurs.

Given article content, extract:
1. A 2-3 sentence summary of the key points
2. Exactly 3 actionable takeaways as bullet points

RULES:
- Be concise and business-focused
- Focus on implications for business owners
- Skip promotional content or ads
- If content is too short/unclear, say so

Output JSON only:
{
  "summary": "2-3 sentence summary...",
  "key_points": ["Point 1", "Point 2", "Point 3"]
}"""


@dataclass
class ArticleSummary:
    """Result of article summarization."""

    url: str
    summary: str | None = None
    key_points: list[str] | None = None
    success: bool = False
    error: str | None = None


async def summarize_article(
    url: str,
    content: str,
    title: str | None = None,
) -> ArticleSummary:
    """Summarize a single article using Claude Haiku.

    Args:
        url: Article URL (for reference)
        content: Extracted article text
        title: Optional article title for context

    Returns:
        ArticleSummary with results or error
    """
    if not content or len(content) < 100:
        return ArticleSummary(url=url, error="Content too short")

    # Truncate content to ~4000 chars for Haiku (cost efficiency)
    truncated_content = content[:4000]
    if len(content) > 4000:
        truncated_content += "..."

    user_prompt = f"""Summarize this article for a business owner.

Title: {title or "Unknown"}

Content:
{truncated_content}

Output JSON only."""

    try:
        broker = PromptBroker()
        request = PromptRequest(
            system=ARTICLE_SUMMARY_SYSTEM_PROMPT,
            user_message=user_prompt,
            model="haiku",
            max_tokens=400,
            temperature=0.2,
            agent_type="ArticleSummarizer",
            prompt_type="article_summary",
        )

        response = await broker.call(request)
        result = _parse_summary_response(url, response.content)
        return result

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Article summarization failed: {e}",
            url=url[:100],
        )
        return ArticleSummary(url=url, error=str(e)[:100])


def _parse_summary_response(url: str, response_text: str) -> ArticleSummary:
    """Parse LLM response into ArticleSummary.

    Args:
        url: Article URL
        response_text: Raw LLM response (expected JSON)

    Returns:
        Parsed ArticleSummary
    """
    try:
        data, errors = parse_json_with_fallback(response_text, context="article_summarizer")
        if data is None:
            return ArticleSummary(url=url, error=f"Parse error: {errors}")

        summary = data.get("summary")
        key_points = data.get("key_points", [])

        # Validate key_points
        if not isinstance(key_points, list):
            key_points = []
        key_points = [str(p)[:200] for p in key_points[:3] if p]

        if not summary:
            return ArticleSummary(url=url, error="No summary in response")

        return ArticleSummary(
            url=url,
            summary=str(summary)[:500],
            key_points=key_points,
            success=True,
        )

    except (json.JSONDecodeError, KeyError, TypeError) as e:
        logger.warning(f"Failed to parse article summary: {e}")
        return ArticleSummary(url=url, error=f"Parse error: {e}")


async def summarize_articles_batch(
    articles: list[dict[str, Any]],
    max_concurrent: int = 3,
) -> list[ArticleSummary]:
    """Summarize multiple articles in parallel.

    Args:
        articles: List of dicts with 'url', 'content', and optional 'title'
        max_concurrent: Maximum concurrent LLM calls

    Returns:
        List of ArticleSummary objects (same order as input)
    """
    if not articles:
        return []

    # Filter to articles with content
    valid_articles = [a for a in articles if a.get("content")]
    if not valid_articles:
        return [ArticleSummary(url=a.get("url", ""), error="No content") for a in articles]

    # Limit concurrent requests using semaphore
    semaphore = asyncio.Semaphore(max_concurrent)

    async def summarize_with_semaphore(article: dict) -> ArticleSummary:
        async with semaphore:
            return await summarize_article(
                url=article.get("url", ""),
                content=article.get("content", ""),
                title=article.get("title"),
            )

    try:
        # Build tasks for articles with content, track original indices
        tasks = []
        task_indices = []
        for i, article in enumerate(articles):
            if article.get("content"):
                tasks.append(summarize_with_semaphore(article))
                task_indices.append(i)

        # Execute all tasks
        summaries = await asyncio.gather(*tasks, return_exceptions=True)

        # Build result list maintaining original order
        results = [ArticleSummary(url=a.get("url", ""), error="No content") for a in articles]
        for task_idx, summary in zip(task_indices, summaries, strict=False):
            if isinstance(summary, Exception):
                results[task_idx] = ArticleSummary(
                    url=articles[task_idx].get("url", ""), error=str(summary)[:100]
                )
            else:
                results[task_idx] = summary

        successful = sum(1 for r in results if r.success)
        logger.info(f"Summarized {successful}/{len(articles)} articles")

        return results

    except Exception as e:
        logger.warning(f"Article batch summarization failed: {e}")
        return [ArticleSummary(url=a.get("url", ""), error=str(e)[:100]) for a in articles]
