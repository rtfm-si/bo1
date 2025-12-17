"""Competitor detection logic using Tavily and Brave Search APIs.

Contains functions for detecting competitors based on business context.
Uses LLM-based extraction to improve quality of detected competitors.
"""

import json
import logging
import re
from typing import Any

import httpx

from backend.api.context.models import (
    CompetitorDetectResponse,
    DetectedCompetitor,
    MarketTrend,
    TrendsRefreshResponse,
)
from backend.api.context.services import auto_save_competitors
from bo1.config import get_settings
from bo1.llm.client import ClaudeClient
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
5. Include URL if available from the results

Return a JSON array of objects with this format:
[
  {{"name": "CompanyName", "url": "https://...", "confidence": "high/medium/low"}},
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
                validated.append(item)

        return validated

    except Exception as e:
        logger.error(f"LLM competitor extraction failed: {e}")
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
            # Auto-save pre-enriched competitors
            await auto_save_competitors(user_id, detected)
            return CompetitorDetectResponse(
                success=True,
                competitors=detected,
            )

    # Get context for search
    company_name = context_data.get("company_name") if context_data else None

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

    # Build targeted search query for competitor discovery
    search_query = _build_competitor_search_query(company_name, industry, product_description)
    logger.info(f"Tavily competitor search: {search_query}")

    try:
        competitors = await _search_competitors_tavily(
            settings.tavily_api_key, search_query, company_name
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
        logger.error(f"Tavily API error: {e}")
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error="Search service temporarily unavailable. Please try again later.",
        )
    except Exception as e:
        logger.error(f"Competitor detection failed: {e}")
        return CompetitorDetectResponse(
            success=False,
            competitors=[],
            error=f"Detection failed: {str(e)}",
        )


def _build_competitor_search_query(
    company_name: str | None,
    industry: str | None,
    product_description: str | None,
) -> str:
    """Build a search query for competitor discovery.

    Args:
        company_name: Company name
        industry: Industry
        product_description: Product description

    Returns:
        Search query string
    """
    if company_name:
        return f'"{company_name}" competitors alternatives'
    elif industry and product_description:
        return f"best {industry} software companies {product_description[:50]}"
    else:
        return f"top {industry or product_description[:80]} companies competitors"


async def _search_competitors_tavily(
    api_key: str,
    search_query: str,
    company_name: str | None,
) -> list[DetectedCompetitor]:
    """Search for competitors using Tavily API with LLM extraction.

    Uses LLM-based extraction to identify real company names from results.
    Falls back to direct search if initial results are insufficient.

    Args:
        api_key: Tavily API key
        search_query: Search query
        company_name: Company name to exclude from results

    Returns:
        List of detected competitors
    """
    async with httpx.AsyncClient(timeout=60.0) as client:
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
        async with httpx.AsyncClient(timeout=60.0) as client:
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
        logger.error(f"Trends refresh failed: {e}")
        return TrendsRefreshResponse(
            success=False,
            trends=[],
            error=f"Refresh failed: {str(e)}",
        )


async def _search_trends_brave(
    api_key: str,
    industry: str,
) -> list[MarketTrend]:
    """Search for market trends using Brave API.

    Args:
        api_key: Brave API key
        industry: Industry to search for

    Returns:
        List of market trends
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
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
    trends = []

    for result in results[:5]:
        title = result.get("title", "")
        url = result.get("url", "")
        description = result.get("description", "")

        if title and description:
            trends.append(
                MarketTrend(
                    trend=f"{title}: {description[:150]}...",
                    source=result.get("profile", {}).get("name", "Web"),
                    source_url=url,
                )
            )

    return trends
