"""Page analytics service for landing page metrics.

Provides:
- Geo location detection from IP addresses
- Bot detection from user agents
- Page view and conversion event recording
- Analytics aggregation and reporting
"""

import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Any

import httpx

from bo1.state.repositories.page_analytics_repository import page_analytics_repository

logger = logging.getLogger(__name__)

# Common bot user agent patterns
BOT_PATTERNS = [
    r"bot",
    r"crawler",
    r"spider",
    r"scraper",
    r"curl",
    r"wget",
    r"python-requests",
    r"httpx",
    r"go-http-client",
    r"java/",
    r"libwww",
    r"headless",
    r"phantom",
    r"selenium",
    r"puppeteer",
    r"playwright",
    r"googlebot",
    r"bingbot",
    r"slurp",
    r"duckduckbot",
    r"baiduspider",
    r"yandexbot",
    r"facebookexternalhit",
    r"twitterbot",
    r"linkedinbot",
    r"applebot",
    r"semrush",
    r"ahrefs",
    r"mj12bot",
    r"dotbot",
]

BOT_REGEX = re.compile("|".join(BOT_PATTERNS), re.IGNORECASE)


@dataclass
class GeoLocation:
    """Geo location data from IP lookup."""

    country: str | None
    region: str | None
    city: str | None
    success: bool


async def lookup_geo_from_ip(ip_address: str) -> GeoLocation:
    """Look up geo location from IP address using ip-api.com.

    Args:
        ip_address: Client IP address

    Returns:
        GeoLocation with country, region, city
    """
    # Skip private/localhost IPs
    if ip_address.startswith(("127.", "10.", "192.168.", "172.16.", "::1", "localhost")):
        return GeoLocation(country=None, region=None, city=None, success=False)

    try:
        async with httpx.AsyncClient(timeout=2.0) as client:
            # ip-api.com free tier (no API key needed)
            # Rate limit: 45 requests/minute from same IP
            response = await client.get(
                f"http://ip-api.com/json/{ip_address}",
                params={"fields": "status,country,countryCode,region,regionName,city"},
            )

            if response.status_code != 200:
                logger.warning(f"Geo lookup failed: HTTP {response.status_code}")
                return GeoLocation(country=None, region=None, city=None, success=False)

            data = response.json()

            if data.get("status") != "success":
                return GeoLocation(country=None, region=None, city=None, success=False)

            return GeoLocation(
                country=data.get("countryCode"),  # 2-letter ISO code
                region=data.get("regionName"),
                city=data.get("city"),
                success=True,
            )

    except httpx.TimeoutException:
        logger.warning(f"Geo lookup timeout for {ip_address}")
        return GeoLocation(country=None, region=None, city=None, success=False)
    except Exception as e:
        logger.warning(f"Geo lookup error for {ip_address}: {e}")
        return GeoLocation(country=None, region=None, city=None, success=False)


def detect_bot(user_agent: str | None) -> bool:
    """Detect if user agent indicates a bot.

    Args:
        user_agent: HTTP User-Agent header

    Returns:
        True if likely a bot
    """
    if not user_agent:
        return True  # No user agent = suspicious
    return bool(BOT_REGEX.search(user_agent))


async def record_page_view(
    path: str,
    session_id: str,
    ip_address: str | None = None,
    referrer: str | None = None,
    user_agent: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a page view with geo detection.

    Args:
        path: Page path
        session_id: Visitor session ID
        ip_address: Client IP for geo lookup
        referrer: HTTP referer
        user_agent: Browser user agent
        metadata: Additional data

    Returns:
        Created page view record
    """
    # Detect bot
    is_bot = detect_bot(user_agent)

    # Geo lookup (async, with fallback)
    geo = GeoLocation(country=None, region=None, city=None, success=False)
    if ip_address and not is_bot:
        geo = await lookup_geo_from_ip(ip_address)

    return page_analytics_repository.record_page_view(
        path=path,
        session_id=session_id,
        country=geo.country,
        region=geo.region,
        city=geo.city,
        referrer=referrer,
        user_agent=user_agent,
        is_bot=is_bot,
        metadata=metadata,
    )


def update_page_view(
    view_id: str,
    duration_ms: int | None = None,
    scroll_depth: int | None = None,
) -> dict[str, Any] | None:
    """Update page view with engagement metrics.

    Args:
        view_id: Page view UUID
        duration_ms: Time on page
        scroll_depth: Max scroll depth

    Returns:
        Updated record or None
    """
    return page_analytics_repository.update_page_view(
        view_id=view_id,
        duration_ms=duration_ms,
        scroll_depth=scroll_depth,
    )


def record_conversion(
    event_type: str,
    source_path: str,
    session_id: str,
    element_id: str | None = None,
    element_text: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Record a conversion event.

    Args:
        event_type: Event type (signup_click, signup_complete, cta_click)
        source_path: Page where event occurred
        session_id: Visitor session ID
        element_id: Clicked element ID
        element_text: Clicked element text
        metadata: Additional data

    Returns:
        Created conversion record
    """
    return page_analytics_repository.record_conversion(
        event_type=event_type,
        source_path=source_path,
        session_id=session_id,
        element_id=element_id,
        element_text=element_text,
        metadata=metadata,
    )


def get_landing_page_metrics(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get comprehensive landing page analytics.

    Args:
        start_date: Start of date range
        end_date: End of date range

    Returns:
        Dict with daily_stats, geo_breakdown, funnel, bounce_rate
    """
    return {
        "daily_stats": page_analytics_repository.get_daily_stats(start_date, end_date, path="/"),
        "geo_breakdown": page_analytics_repository.get_geo_breakdown(start_date, end_date),
        "funnel": page_analytics_repository.get_funnel_stats(start_date, end_date),
        "bounce_rate": page_analytics_repository.get_bounce_rate(start_date, end_date, path="/"),
    }


def get_daily_stats(
    start_date: date | None = None,
    end_date: date | None = None,
    path: str | None = None,
) -> list[dict[str, Any]]:
    """Get daily page view statistics."""
    return page_analytics_repository.get_daily_stats(start_date, end_date, path)


def get_geo_breakdown(
    start_date: date | None = None,
    end_date: date | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    """Get visitor breakdown by country."""
    return page_analytics_repository.get_geo_breakdown(start_date, end_date, limit)


def get_funnel_stats(
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Get conversion funnel statistics."""
    return page_analytics_repository.get_funnel_stats(start_date, end_date)


def get_bounce_rate(
    start_date: date | None = None,
    end_date: date | None = None,
    path: str = "/",
) -> dict[str, Any]:
    """Get bounce rate for a page."""
    return page_analytics_repository.get_bounce_rate(start_date, end_date, path)
