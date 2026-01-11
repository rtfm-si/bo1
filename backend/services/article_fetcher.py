"""Article content fetcher for market trends.

Async utility to fetch and extract text content from article URLs.
Reuses strip_html_to_text from trend_summary_generator.

Handles:
- Timeout (5s max per article)
- Paywall/blocked content detection
- HTML-to-text extraction
"""

import asyncio
import logging
from dataclasses import dataclass

import httpx

from backend.services.trend_summary_generator import strip_html_to_text

logger = logging.getLogger(__name__)

# Configuration
FETCH_TIMEOUT = 5.0  # Per-URL timeout
MAX_CONTENT_BYTES = 15000  # 15KB max raw HTML
MIN_CONTENT_LENGTH = 200  # Minimum chars for valid content


@dataclass
class FetchResult:
    """Result of article fetch attempt."""

    url: str
    content: str | None = None
    success: bool = False
    error: str | None = None


# Patterns that indicate paywalled/blocked content
PAYWALL_INDICATORS = [
    "subscribe to continue",
    "subscription required",
    "sign in to read",
    "create an account",
    "premium content",
    "members only",
    "please log in",
    "access denied",
    "403 forbidden",
]


def _detect_paywall(content: str) -> bool:
    """Detect if content appears to be paywalled or blocked.

    Args:
        content: Extracted text content

    Returns:
        True if content appears paywalled
    """
    content_lower = content.lower()
    for indicator in PAYWALL_INDICATORS:
        if indicator in content_lower:
            return True
    return False


async def fetch_article_content(url: str) -> FetchResult:
    """Fetch and extract text content from a URL.

    Args:
        url: URL to fetch content from

    Returns:
        FetchResult with content or error
    """
    if not url:
        return FetchResult(url=url or "", error="No URL provided")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                url,
                timeout=FETCH_TIMEOUT,
                headers={
                    "User-Agent": "Mozilla/5.0 (compatible; Bo1Bot/1.0; +https://bo1.ai)",
                    "Accept": "text/html,application/xhtml+xml",
                },
                follow_redirects=True,
            )
            response.raise_for_status()

            # Check content type - only process HTML
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type and "application/xhtml" not in content_type:
                return FetchResult(url=url, error=f"Non-HTML content: {content_type[:50]}")

            # Truncate raw content to limit
            raw_html = response.text[:MAX_CONTENT_BYTES]

            # Convert HTML to text
            text_content = strip_html_to_text(raw_html, max_chars=8000)

            # Minimum viable content check
            if len(text_content) < MIN_CONTENT_LENGTH:
                return FetchResult(url=url, error="Content too short after extraction")

            # Check for paywall
            if _detect_paywall(text_content):
                return FetchResult(url=url, error="Paywall detected")

            return FetchResult(url=url, content=text_content, success=True)

    except httpx.TimeoutException:
        return FetchResult(url=url, error="Timeout")
    except httpx.HTTPStatusError as e:
        return FetchResult(url=url, error=f"HTTP {e.response.status_code}")
    except Exception as e:
        logger.debug(f"Failed to fetch URL content: {e}")
        return FetchResult(url=url, error=str(e)[:100])


async def fetch_articles_batch(
    urls: list[str],
    max_concurrent: int = 3,
    total_timeout: float = 12.0,
) -> list[FetchResult]:
    """Fetch multiple articles in parallel with rate limiting.

    Args:
        urls: List of URLs to fetch
        max_concurrent: Maximum concurrent requests
        total_timeout: Total timeout for all fetches

    Returns:
        List of FetchResult objects (same order as input URLs)
    """
    if not urls:
        return []

    # Limit concurrent requests using semaphore
    semaphore = asyncio.Semaphore(max_concurrent)

    async def fetch_with_semaphore(url: str) -> FetchResult:
        async with semaphore:
            return await fetch_article_content(url)

    try:
        # Fetch all URLs in parallel with total timeout
        tasks = [fetch_with_semaphore(url) for url in urls]
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=total_timeout,
        )

        # Convert exceptions to FetchResult objects
        processed_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                processed_results.append(FetchResult(url=urls[i], error=str(result)[:100]))
            else:
                processed_results.append(result)

        successful = sum(1 for r in processed_results if r.success)
        logger.info(f"Fetched {successful}/{len(urls)} articles successfully")

        return processed_results

    except TimeoutError:
        logger.warning(f"Article batch fetch timed out after {total_timeout}s")
        # Return partial results for any completed fetches
        return [FetchResult(url=url, error="Batch timeout") for url in urls]
    except Exception as e:
        logger.warning(f"Article batch fetch failed: {e}")
        return [FetchResult(url=url, error=str(e)[:100]) for url in urls]
