"""Competitor detection logic using Tavily and Brave Search APIs.

Contains functions for detecting competitors based on business context.
Uses LLM-based extraction to improve quality of detected competitors.
"""

import json
import logging
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import httpx

from backend.api.constants import CompetitorAPIConfig
from backend.api.context.models import (
    CompetitorDetectResponse,
    DetectedCompetitor,
    MarketTrend,
    TrendsRefreshResponse,
)
from backend.api.context.services import auto_save_competitors
from backend.api.context.skeptic import evaluate_competitors_batch
from backend.services.article_fetcher import fetch_articles_batch
from backend.services.article_summarizer import summarize_articles_batch
from bo1.config import get_settings
from bo1.llm.client import ClaudeClient
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.repositories import user_repository

logger = logging.getLogger(__name__)

# Generic terms that indicate non-company names
INVALID_NAME_PATTERNS = [
    "best",
    "top",
    "review",
    "compare",
    "comparison",
    "list",
    "guide",
    "2024",
    "2025",
    "alternative",
    "software",
    "tools",
    "platform",
    "solution",
    "ranking",
    "rated",
]


def _is_valid_competitor_name(name: str) -> bool:
    """Validate that a string is likely a real company name.

    Rejects generic terms, sentences, and invalid patterns.

    Args:
        name: Candidate company name

    Returns:
        True if name appears to be a valid company name
    """
    if not name or len(name) < 2:
        return False

    # Too long - likely a sentence, not a company name
    if len(name) > 40:
        return False

    name_lower = name.lower()

    # Reject if starts with generic terms
    if name_lower.startswith(("the best", "top ", "best ", "how to")):
        return False

    # Reject if starts with a number (e.g., "10 Best Tools")
    if name[0].isdigit():
        return False

    # Reject if contains invalid patterns
    for pattern in INVALID_NAME_PATTERNS:
        if pattern in name_lower:
            return False

    # Accept if matches known valid patterns
    # CamelCase (e.g., "HubSpot", "ClickUp")
    if re.match(r"^[A-Z][a-z]+[A-Z][a-z]+", name):
        return True

    # Ends with common domain-style suffixes
    if any(name_lower.endswith(suffix) for suffix in [".io", ".ai", ".com", ".co"]):
        return True

    # Single or two-word proper noun (e.g., "Notion", "Monday", "Linear")
    words = name.split()
    if 1 <= len(words) <= 3 and all(w[0].isupper() for w in words if w):
        return True

    # If none of the above, accept cautiously if it looks proper-nouny
    return name[0].isupper() and len(words) <= 4


def _normalize_competitor_url(url: str | None, company_name: str) -> str | None:
    """Normalize and validate a competitor URL.

    Extracts actual company domain from G2/Capterra links or guesses from name.

    Args:
        url: Raw URL from search results (may be G2/Capterra link)
        company_name: Company name for domain guessing

    Returns:
        Normalized company URL or None
    """
    if not url:
        # Try to guess domain from company name
        return _guess_domain_from_name(company_name)

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # If it's a review site, try to extract the company domain
        review_sites = [
            "g2.com",
            "capterra.com",
            "trustradius.com",
            "getapp.com",
            "alternativeto.net",
        ]
        if any(site in domain for site in review_sites):
            # G2 pattern: g2.com/products/companyname/...
            # Capterra pattern: capterra.com/p/123456/companyname/
            # Try to extract company name from path and guess domain
            return _guess_domain_from_name(company_name)

        # Already a company domain
        return f"https://{domain}"

    except Exception:
        return _guess_domain_from_name(company_name)


def _guess_domain_from_name(company_name: str) -> str | None:
    """Guess company domain from name.

    Args:
        company_name: Company name

    Returns:
        Guessed domain URL or None
    """
    if not company_name:
        return None

    # Normalize: lowercase, remove spaces and special chars
    clean_name = re.sub(r"[^a-z0-9]", "", company_name.lower())

    if len(clean_name) < 2:
        return None

    # Common patterns
    return f"https://{clean_name}.com"


def _normalize_competitor_name(name: str) -> str:
    """Normalize a competitor name for deduplication.

    Args:
        name: Raw company name

    Returns:
        Normalized name for comparison
    """
    if not name:
        return ""

    # Lowercase
    normalized = name.lower().strip()

    # Remove common suffixes
    suffixes = [
        ", inc.",
        ", inc",
        " inc.",
        " inc",
        ", llc",
        " llc",
        ", ltd",
        " ltd",
        ".com",
        ".io",
        ".ai",
        ".co",
        " software",
        " platform",
        " app",
    ]
    for suffix in suffixes:
        if normalized.endswith(suffix):
            normalized = normalized[: -len(suffix)]

    # Remove special characters for comparison
    normalized = re.sub(r"[^a-z0-9]", "", normalized)

    return normalized


def _deduplicate_competitors(
    competitors: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Deduplicate competitors by normalized name.

    Merges data from duplicates, keeping the one with most info.

    Args:
        competitors: List of competitor dicts

    Returns:
        Deduplicated list
    """
    seen: dict[str, dict[str, Any]] = {}

    for comp in competitors:
        name = comp.get("name", "")
        normalized = _normalize_competitor_name(name)

        if not normalized:
            continue

        if normalized in seen:
            # Merge: prefer entries with more data
            existing = seen[normalized]
            # Keep better URL
            if not existing.get("url") and comp.get("url"):
                existing["url"] = comp["url"]
            # Keep better description
            if not existing.get("description") and comp.get("description"):
                existing["description"] = comp["description"]
            # Keep higher confidence
            confidence_rank = {"high": 3, "medium": 2, "low": 1}
            if confidence_rank.get(comp.get("confidence"), 0) > confidence_rank.get(
                existing.get("confidence"), 0
            ):
                existing["confidence"] = comp["confidence"]
        else:
            seen[normalized] = comp

    return list(seen.values())


async def _extract_competitors_with_llm(
    results: list[dict[str, Any]],
    company_name: str | None,
) -> list[dict[str, Any]]:
    """Use LLM to extract actual company names from search results.

    Args:
        results: Tavily search results with titles, URLs, content
        company_name: User's company name to exclude

    Returns:
        List of dicts with name, url, description, confidence
    """
    if not results:
        return []

    # Build context from search results
    context_parts = []
    for i, result in enumerate(results, 1):
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")[:300]
        context_parts.append(f"{i}. Title: {title}\n   URL: {url}\n   Content: {content}")

    context = "\n\n".join(context_parts)

    prompt = f"""Extract ONLY real company names from these search results.
I need actual software/SaaS company names, NOT generic terms like "Top 10 Tools" or "Best Software".

SEARCH RESULTS:
{context}

RULES:
1. Return ONLY actual company names (e.g., "Notion", "Asana", "Monday.com", "HubSpot")
2. DO NOT include generic terms like "Top Productivity Tools", "Best CRM Software", "2024 Guide"
3. DO NOT include the user's own company{f': "{company_name}"' if company_name else ""}
4. Each name should be a real company you're confident exists
5. Include URL if available from the results (extract the company's actual domain, not the G2/Capterra page)
6. Write a brief 1-2 sentence description of what the company does based on the search content
7. Classify the competitor type: "direct" (same product), "indirect" (different approach to same problem), or "adjacent" (related market)

Return a JSON array of objects with this format:
[
  {{"name": "CompanyName", "url": "https://company.com", "description": "Brief description of what they do", "category": "direct/indirect/adjacent", "confidence": "high/medium/low"}},
  ...
]

Return ONLY the JSON array, no other text. If no valid companies found, return [].
"""

    try:
        client = ClaudeClient()
        response, _ = await client.call(
            model="haiku",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
            max_tokens=1000,
            prefill="[",
        )

        # Parse JSON response
        try:
            extracted = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON array from response
            json_match = re.search(r"\[[\s\S]*\]", response)
            if json_match:
                extracted = json.loads(json_match.group())
            else:
                logger.warning(f"Failed to parse LLM response: {response[:200]}")
                return []

        # Filter through validation
        validated = []
        for item in extracted:
            name = item.get("name", "")
            if _is_valid_competitor_name(name):
                # Normalize URL
                item["url"] = _normalize_competitor_url(item.get("url"), name)
                validated.append(item)

        # Deduplicate by normalized name
        return _deduplicate_competitors(validated)

    except Exception as e:
        log_error(
            logger, ErrorCode.SERVICE_EXECUTION_ERROR, f"LLM competitor extraction failed: {e}"
        )
        return []


async def detect_competitors_for_user(
    user_id: str,
    industry: str | None = None,
    product_description: str | None = None,
) -> CompetitorDetectResponse:
    """Detect competitors using Tavily Search API.

    First checks if competitors were already detected during website enrichment.
    If not, uses Tavily to search G2, Capterra, and other review sites.

    Args:
        user_id: User ID
        industry: Optional industry override
        product_description: Optional product description override

    Returns:
        CompetitorDetectResponse with detected competitors
    """
    logger.info(f"Detecting competitors for user {user_id}")

    # Load user context
    context_data = user_repository.get_context(user_id)

    # First, check if we already have enriched competitors
    if context_data:
        enriched_competitors = context_data.get("detected_competitors", [])
        if enriched_competitors and len(enriched_competitors) > 0:
            logger.info(f"Using {len(enriched_competitors)} pre-enriched competitors")
            detected = [
                DetectedCompetitor(name=name, url=None, description=None)
                for name in enriched_competitors[:10]
            ]
            # Run skeptic evaluation
            detected = await evaluate_competitors_batch(detected, context_data)
            # Auto-save pre-enriched competitors
            await auto_save_competitors(user_id, detected)
            return CompetitorDetectResponse(
                success=True,
                competitors=detected,
            )

    # Get context for search
    company_name = context_data.get("company_name") if context_data else None
    target_market = context_data.get("target_market") if context_data else None
    business_model = context_data.get("business_model") if context_data else None

    if context_data:
        industry = industry or context_data.get("industry")
        product_description = product_description or context_data.get("product_description")

    if not company_name and not industry and not product_description:
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error="Please complete the Overview tab first (company name, industry, or product description required).",
        )

    settings = get_settings()
    if not settings.tavily_api_key:
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error="Tavily Search API not configured. Please try again later.",
        )

    # Build targeted search query using all available context
    search_query = _build_competitor_search_query(
        company_name=company_name,
        industry=industry,
        product_description=product_description,
        target_market=target_market,
        business_model=business_model,
    )
    logger.info(f"Tavily competitor search: {search_query}")

    try:
        competitors = await _search_competitors_tavily(
            settings.tavily_api_key, search_query, company_name, context_data
        )

        if not competitors:
            return CompetitorDetectResponse(
                success=False,
                competitors=[],
                error="No competitors found. Try adding more context about your company or industry.",
            )

        # Auto-save detected competitors to Competitor Watch
        await auto_save_competitors(user_id, competitors[:8])

        return CompetitorDetectResponse(
            success=True,
            competitors=competitors[:8],  # Return top 8 quality results
        )

    except httpx.HTTPError as e:
        log_error(
            logger, ErrorCode.SERVICE_EXECUTION_ERROR, f"Tavily API error: {e}", user_id=user_id
        )
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error="Search service temporarily unavailable. Please try again later.",
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Competitor detection failed: {e}",
            user_id=user_id,
        )
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error=f"Detection failed: {str(e)}",
        )


def _build_competitor_search_query(
    company_name: str | None,
    industry: str | None,
    product_description: str | None,
    target_market: str | None = None,
    business_model: str | None = None,
) -> str:
    """Build a search query for competitor discovery.

    Uses multiple context fields to create a focused search query
    that yields more relevant competitor results.

    Args:
        company_name: Company name (most specific)
        industry: Industry vertical (e.g., "SaaS", "Healthcare")
        product_description: Product/service description
        target_market: Target customer segment (e.g., "SMBs", "Enterprise")
        business_model: Business model (e.g., "B2B", "Marketplace")

    Returns:
        Search query string optimized for competitor discovery
    """
    query_parts = []

    if company_name:
        # Direct competitor search - most effective
        return f'"{company_name}" competitors alternatives'

    # Build query from available context (order matters for relevance)
    if business_model:
        # Normalize common business model terms for search
        bm_term = business_model.lower()
        if "b2b" in bm_term:
            query_parts.append("B2B")
        elif "b2c" in bm_term:
            query_parts.append("B2C")
        elif "saas" in bm_term:
            query_parts.append("SaaS")
        elif "marketplace" in bm_term:
            query_parts.append("marketplace")

    if industry:
        query_parts.append(industry)

    if target_market:
        # Extract key terms from target market
        market_lower = target_market.lower()
        if "enterprise" in market_lower:
            query_parts.append("enterprise")
        elif "smb" in market_lower or "small business" in market_lower:
            query_parts.append("SMB")
        elif "startup" in market_lower:
            query_parts.append("startup")

    # Add product context if available
    if product_description:
        # Take first meaningful portion of description
        desc_snippet = product_description[:60].strip()
        # Remove trailing partial words
        if " " in desc_snippet:
            desc_snippet = desc_snippet.rsplit(" ", 1)[0]
        query_parts.append(desc_snippet)

    if query_parts:
        query = " ".join(query_parts)
        return f"best {query} software companies competitors"

    # Fallback - should rarely reach here
    return "top software companies competitors alternatives"


async def _search_competitors_tavily(
    api_key: str,
    search_query: str,
    company_name: str | None,
    company_context: dict | None = None,
) -> list[DetectedCompetitor]:
    """Search for competitors using Tavily API with LLM extraction.

    Uses LLM-based extraction to identify real company names from results.
    Falls back to direct search if initial results are insufficient.
    Runs skeptic evaluation to assess relevance of each competitor.

    Args:
        api_key: Tavily API key
        search_query: Search query
        company_name: Company name to exclude from results
        company_context: User's business context for relevance evaluation

    Returns:
        List of detected competitors with relevance scores
    """
    async with httpx.AsyncClient(timeout=CompetitorAPIConfig.TAVILY_TIMEOUT) as client:
        response = await client.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": search_query,
                "search_depth": "advanced",
                "include_domains": [
                    "g2.com",
                    "capterra.com",
                    "trustradius.com",
                    "getapp.com",
                    "softwareadvice.com",
                    "alternativeto.net",
                ],
                "max_results": 10,
            },
        )
        response.raise_for_status()
        data = response.json()

    results = data.get("results", [])

    # Use LLM to extract real company names
    extracted = await _extract_competitors_with_llm(results, company_name)

    # If we got <3 valid names, try fallback search
    if len(extracted) < 3 and company_name:
        logger.info(f"Only {len(extracted)} competitors found, trying fallback search")
        fallback_results = await _fallback_competitor_search(api_key, company_name)
        if fallback_results:
            # Merge and dedupe
            seen_names = {e.get("name", "").lower() for e in extracted}
            for item in fallback_results:
                if item.get("name", "").lower() not in seen_names:
                    extracted.append(item)
                    seen_names.add(item.get("name", "").lower())

    # Convert to DetectedCompetitor objects
    competitors = []
    for item in extracted:
        competitors.append(
            DetectedCompetitor(
                name=item.get("name", ""),
                url=item.get("url"),
                description=item.get("description"),
            )
        )

    # Run skeptic evaluation if we have context
    if competitors and company_context:
        logger.info(f"Running skeptic evaluation for {len(competitors)} competitors")
        competitors = await evaluate_competitors_batch(competitors, company_context)

    return competitors


async def _fallback_competitor_search(
    api_key: str,
    company_name: str,
) -> list[dict[str, Any]]:
    """Run fallback search with more targeted query.

    Args:
        api_key: Tavily API key
        company_name: Company name for targeted search

    Returns:
        List of extracted competitor dicts
    """
    try:
        async with httpx.AsyncClient(timeout=CompetitorAPIConfig.TAVILY_TIMEOUT) as client:
            # More targeted query
            response = await client.post(
                "https://api.tavily.com/search",
                json={
                    "api_key": api_key,
                    "query": f'"{company_name}" vs alternatives competitors',
                    "search_depth": "advanced",
                    "max_results": 8,
                },
            )
            response.raise_for_status()
            data = response.json()

        results = data.get("results", [])
        return await _extract_competitors_with_llm(results, company_name)

    except Exception as e:
        logger.warning(f"Fallback competitor search failed: {e}")
        return []


async def refresh_market_trends(
    user_id: str,
    industry: str | None = None,
) -> TrendsRefreshResponse:
    """Refresh market trends using Brave Search.

    Args:
        user_id: User ID
        industry: Optional industry override

    Returns:
        TrendsRefreshResponse with market trends
    """
    logger.info(f"Refreshing trends for user {user_id}")

    # Get industry from request or saved context
    if not industry:
        context_data = user_repository.get_context(user_id)
        if context_data:
            industry = context_data.get("industry")

    if not industry:
        return TrendsRefreshResponse(
            success=False,
            trends=[],
            error="No industry available. Please set your industry first.",
        )

    settings = get_settings()
    if not settings.brave_api_key:
        return TrendsRefreshResponse(
            success=False,
            trends=[],
            error="Brave Search API not configured. Please try again later.",
        )

    try:
        trends = await _search_trends_brave(settings.brave_api_key, industry)
        return TrendsRefreshResponse(
            success=True,
            trends=trends,
        )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Trends refresh failed: {e}",
            user_id=user_id,
        )
        return TrendsRefreshResponse(
            success=False,
            trends=[],
            error=f"Refresh failed: {str(e)}",
        )


async def _search_trends_brave(
    api_key: str,
    industry: str,
) -> list[MarketTrend]:
    """Search for market trends using Brave API, then fetch and summarize articles.

    Pipeline:
    1. Search Brave for industry trends
    2. Fetch article content from top URLs
    3. Summarize articles with Claude Haiku
    4. Return enriched MarketTrend objects

    Args:
        api_key: Brave API key
        industry: Industry to search for

    Returns:
        List of market trends with AI-generated summaries
    """
    async with httpx.AsyncClient(timeout=CompetitorAPIConfig.BRAVE_TIMEOUT) as client:
        response = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={"X-Subscription-Token": api_key},
            params={
                "q": f"{industry} industry trends 2025 insights market analysis",
                "count": 10,
                "freshness": "pw",  # Past week
            },
        )
        response.raise_for_status()
        data = response.json()

    # Extract trends from search results
    results = data.get("web", {}).get("results", [])
    if not results:
        return []

    # Take top 5 results for processing
    top_results = results[:5]

    # Step 2: Fetch article content in parallel
    urls = [r.get("url", "") for r in top_results if r.get("url")]
    fetch_results = await fetch_articles_batch(
        urls,
        max_concurrent=CompetitorAPIConfig.MAX_CONCURRENT,
        total_timeout=CompetitorAPIConfig.ARTICLE_FETCH_TIMEOUT,
    )

    # Build URL -> content map
    url_content_map = {fr.url: fr.content for fr in fetch_results if fr.success and fr.content}

    # Step 3: Prepare articles for summarization
    articles_to_summarize = []
    for result in top_results:
        url = result.get("url", "")
        content = url_content_map.get(url)
        if content:
            articles_to_summarize.append(
                {
                    "url": url,
                    "content": content,
                    "title": result.get("title", ""),
                }
            )

    # Step 4: Summarize articles with LLM
    summaries = []
    if articles_to_summarize:
        summaries = await summarize_articles_batch(articles_to_summarize, max_concurrent=3)

    # Build URL -> summary map
    url_summary_map = {s.url: s for s in summaries if s.success}

    # Step 5: Build enriched MarketTrend objects
    trends = []
    now = datetime.now(UTC)

    for result in top_results:
        title = result.get("title", "")
        url = result.get("url", "")
        description = result.get("description", "")

        if not title:
            continue

        # Check if we have a summary for this URL
        article_summary = url_summary_map.get(url)

        if article_summary and article_summary.summary:
            # Use AI-generated summary
            trends.append(
                MarketTrend(
                    trend=title,
                    source=result.get("profile", {}).get("name", "Web"),
                    source_url=url,
                    summary=article_summary.summary,
                    key_points=article_summary.key_points,
                    fetched_at=now,
                )
            )
        else:
            # Fallback to search snippet
            trends.append(
                MarketTrend(
                    trend=f"{title}: {description[:150]}..." if description else title,
                    source=result.get("profile", {}).get("name", "Web"),
                    source_url=url,
                    summary=None,
                    key_points=None,
                    fetched_at=None,
                )
            )

    logger.info(f"Built {len(trends)} trends, {len(url_summary_map)} with AI summaries")
    return trends
