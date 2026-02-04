"""GSC Sync Service.

Syncs Google Search Console analytics data for published decisions.
Maps GSC page URLs to decision records and stores snapshots.
"""

import logging
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from backend.services.google_search_console import GSCError, get_gsc_client
from bo1.state.repositories.decision_repository import decision_repository
from bo1.state.repositories.gsc_repository import gsc_repository

logger = logging.getLogger(__name__)


class SyncError(Exception):
    """Error during GSC sync operation."""

    pass


def extract_slug_from_url(url: str) -> tuple[str, str] | None:
    """Extract category and slug from a decision URL.

    Expected format: https://boardof.one/decisions/{category}/{slug}

    Args:
        url: Full URL of a page

    Returns:
        Tuple of (category, slug) or None if not a decision URL
    """
    try:
        parsed = urlparse(url)
        path = parsed.path.strip("/")

        # Check if it's a decision URL
        if not path.startswith("decisions/"):
            return None

        parts = path.split("/")
        if len(parts) >= 3:
            # decisions/{category}/{slug}
            category = parts[1]
            slug = parts[2]
            return (category, slug)

        return None
    except Exception:
        return None


def map_url_to_decision(url: str) -> dict[str, Any] | None:
    """Map a URL to a published decision.

    Args:
        url: Full URL from GSC

    Returns:
        Decision record if found, None otherwise
    """
    parsed = extract_slug_from_url(url)
    if not parsed:
        return None

    category, slug = parsed
    return decision_repository.get_by_category_slug(category, slug)


def sync_analytics(
    start_date: date | None = None,
    end_date: date | None = None,
    page_filter: str = "/decisions/",
) -> dict[str, Any]:
    """Sync GSC analytics for all published decisions.

    Args:
        start_date: Start of date range (default: 7 days ago)
        end_date: End of date range (default: yesterday)
        page_filter: URL filter for GSC query (default: /decisions/)

    Returns:
        Sync result with counts and any errors
    """
    # Default to last 7 days (GSC data has ~3 day delay)
    if not end_date:
        end_date = date.today() - timedelta(days=1)
    if not start_date:
        start_date = end_date - timedelta(days=6)

    # Get connection
    connection = gsc_repository.get_connection()
    if not connection:
        raise SyncError("GSC not connected")

    site_url = connection.get("site_url")
    if not site_url:
        raise SyncError("No GSC site selected")

    # Get GSC client
    client = get_gsc_client()
    if not client:
        raise SyncError("Failed to create GSC client")

    result = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "site_url": site_url,
        "pages_fetched": 0,
        "decisions_matched": 0,
        "snapshots_created": 0,
        "errors": [],
    }

    try:
        # Fetch analytics from GSC
        rows = client.get_search_analytics_by_page(
            site_url=site_url,
            start_date=start_date,
            end_date=end_date,
            page_filter=page_filter,
            row_limit=1000,
        )

        result["pages_fetched"] = len(rows)
        logger.info(f"GSC sync: fetched {len(rows)} pages from {start_date} to {end_date}")

        # Map URLs to decisions and create snapshots
        snapshots_to_insert = []
        matched_decisions = set()

        for row in rows:
            decision = map_url_to_decision(row.page)
            if not decision:
                continue

            matched_decisions.add(decision["id"])

            # For aggregate data across date range, we store with end_date
            # In future, could query per-day for time series
            snapshots_to_insert.append(
                {
                    "decision_id": decision["id"],
                    "page_url": row.page,
                    "date": end_date,
                    "impressions": row.impressions,
                    "clicks": row.clicks,
                    "ctr": row.ctr,
                    "position": row.position,
                }
            )

        result["decisions_matched"] = len(matched_decisions)

        # Bulk insert snapshots
        if snapshots_to_insert:
            count = gsc_repository.bulk_upsert_snapshots(snapshots_to_insert)
            result["snapshots_created"] = count

        logger.info(
            f"GSC sync complete: {result['decisions_matched']} decisions, "
            f"{result['snapshots_created']} snapshots"
        )

    except GSCError as e:
        error_msg = f"GSC API error: {e}"
        result["errors"].append(error_msg)
        logger.error(error_msg)

    except Exception as e:
        error_msg = f"Unexpected sync error: {e}"
        result["errors"].append(error_msg)
        logger.exception(error_msg)

    return result


def sync_daily_analytics(days_back: int = 90) -> dict[str, Any]:
    """Sync GSC analytics day-by-day for historical data.

    Fetches data for each day separately to build time series.
    Only fetches dates not already in the database.

    Args:
        days_back: How many days of history to sync

    Returns:
        Sync result with counts
    """
    connection = gsc_repository.get_connection()
    if not connection:
        raise SyncError("GSC not connected")

    site_url = connection.get("site_url")
    if not site_url:
        raise SyncError("No GSC site selected")

    client = get_gsc_client()
    if not client:
        raise SyncError("Failed to create GSC client")

    # Get last sync date to avoid re-fetching
    last_sync = gsc_repository.get_last_sync_date()

    # GSC data has ~3 day delay
    end_date = date.today() - timedelta(days=3)
    start_date = end_date - timedelta(days=days_back)

    # If we have recent data, only fetch new days
    if last_sync and last_sync >= start_date:
        start_date = last_sync + timedelta(days=1)

    if start_date > end_date:
        return {
            "status": "up_to_date",
            "last_sync": last_sync.isoformat() if last_sync else None,
            "days_synced": 0,
        }

    result = {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "days_synced": 0,
        "total_snapshots": 0,
        "errors": [],
    }

    current_date = start_date
    while current_date <= end_date:
        try:
            # Fetch single day
            rows = client.get_search_analytics_by_page(
                site_url=site_url,
                start_date=current_date,
                end_date=current_date,
                page_filter="/decisions/",
                row_limit=1000,
            )

            snapshots = []
            for row in rows:
                decision = map_url_to_decision(row.page)
                if not decision:
                    continue

                snapshots.append(
                    {
                        "decision_id": decision["id"],
                        "page_url": row.page,
                        "date": current_date,
                        "impressions": row.impressions,
                        "clicks": row.clicks,
                        "ctr": row.ctr,
                        "position": row.position,
                    }
                )

            if snapshots:
                gsc_repository.bulk_upsert_snapshots(snapshots)
                result["total_snapshots"] += len(snapshots)

            result["days_synced"] += 1
            logger.debug(f"GSC sync: {current_date} - {len(snapshots)} snapshots")

        except GSCError as e:
            result["errors"].append(f"{current_date}: {e}")
            logger.warning(f"GSC sync error for {current_date}: {e}")

        current_date += timedelta(days=1)

    logger.info(
        f"GSC daily sync complete: {result['days_synced']} days, "
        f"{result['total_snapshots']} snapshots"
    )

    return result
