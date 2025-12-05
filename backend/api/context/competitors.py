"""Competitor detection logic using Tavily and Brave Search APIs.

Contains functions for detecting competitors based on business context.
"""

import logging
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
from bo1.state.postgres_manager import load_user_context

logger = logging.getLogger(__name__)


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
    context_data = load_user_context(user_id)

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
    """Search for competitors using Tavily API.

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

    return _extract_competitors_from_results(data.get("results", []), company_name)


def _extract_competitors_from_results(
    results: list[dict[str, Any]],
    company_name: str | None,
) -> list[DetectedCompetitor]:
    """Extract competitor names from search results.

    Args:
        results: Tavily search results
        company_name: Company name to exclude

    Returns:
        List of detected competitors
    """
    competitors = []
    seen_names: set[str] = set()

    # Skip words that indicate generic content, not company names
    skip_words = [
        "best",
        "top",
        "review",
        "compare",
        "alternative",
        "software",
        "2024",
        "2025",
        "guide",
        "list",
    ]

    for result in results:
        title = result.get("title", "")
        url = result.get("url", "")
        content = result.get("content", "")

        # Extract company name from title
        # G2/Capterra titles often like "Company Name Reviews 2025"
        name = title.split(" Reviews")[0].split(" vs ")[0].split(" -")[0].split(" |")[0].strip()

        # Validate name
        if not name or len(name) < 2 or len(name) > 50:
            continue
        if company_name and name.lower() == company_name.lower():
            continue
        if name.lower() in seen_names:
            continue
        if any(skip in name.lower() for skip in skip_words):
            continue

        seen_names.add(name.lower())
        competitors.append(
            DetectedCompetitor(
                name=name,
                url=url,
                description=content[:200] if content else None,
            )
        )

    return competitors


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
        context_data = load_user_context(user_id)
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
