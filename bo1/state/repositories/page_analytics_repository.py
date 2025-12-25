"""Repository for page analytics (page views and conversion events).

Provides:
- Record page views with geo data
- Record conversion events
- Query daily stats
- Query geo breakdown
- Query funnel stats (conversion rates)
"""

import logging
from datetime import date, timedelta
from typing import Any
from uuid import uuid4

from psycopg2.extras import Json

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Analytics query timeout (10 seconds) - prevents 502 on slow aggregations
ANALYTICS_TIMEOUT_MS = 10000


class PageAnalyticsRepository(BaseRepository):
    """Repository for page_views and conversion_events tables."""

    def record_page_view(
        self,
        path: str,
        session_id: str,
        country: str | None = None,
        region: str | None = None,
        city: str | None = None,
        referrer: str | None = None,
        user_agent: str | None = None,
        duration_ms: int | None = None,
        scroll_depth: int | None = None,
        is_bot: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record a page view event.

        Args:
            path: Page path (e.g., /, /pricing)
            session_id: Visitor session identifier
            country: ISO 3166-1 alpha-2 country code
            region: Region/state name
            city: City name
            referrer: HTTP referer header
            user_agent: Browser user agent
            duration_ms: Time spent on page
            scroll_depth: Max scroll depth (0-100)
            is_bot: Whether flagged as bot
            metadata: Additional data

        Returns:
            Created page view record
        """
        view_id = str(uuid4())
        query = """
            INSERT INTO page_views (
                id, path, session_id, country, region, city,
                referrer, user_agent, duration_ms, scroll_depth, is_bot, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id, timestamp, path, session_id, country, region, city,
                      referrer, user_agent, duration_ms, scroll_depth, is_bot, metadata
        """
        return self._execute_returning(
            query,
            (
                view_id,
                path,
                session_id,
                country,
                region,
                city,
                referrer,
                user_agent,
                duration_ms,
                scroll_depth,
                is_bot,
                Json(metadata) if metadata else None,
            ),
        )

    def update_page_view(
        self,
        view_id: str,
        duration_ms: int | None = None,
        scroll_depth: int | None = None,
    ) -> dict[str, Any] | None:
        """Update a page view with duration/scroll data (on unload).

        Args:
            view_id: Page view UUID
            duration_ms: Time spent on page
            scroll_depth: Max scroll depth

        Returns:
            Updated record or None
        """
        self._validate_id(view_id, "view_id")
        updates = []
        params: list[Any] = []

        if duration_ms is not None:
            updates.append("duration_ms = %s")
            params.append(duration_ms)
        if scroll_depth is not None:
            updates.append("scroll_depth = %s")
            params.append(scroll_depth)

        if not updates:
            return None

        params.append(view_id)
        query = f"""
            UPDATE page_views
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, timestamp, path, session_id, duration_ms, scroll_depth
        """
        return self._execute_one(query, tuple(params))

    def record_conversion(
        self,
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
            session_id: Visitor session identifier
            element_id: ID of clicked element
            element_text: Text of clicked element
            metadata: Additional data

        Returns:
            Created conversion event record
        """
        event_id = str(uuid4())
        query = """
            INSERT INTO conversion_events (
                id, event_type, source_path, session_id, element_id, element_text, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, timestamp, event_type, source_path, session_id,
                      element_id, element_text, metadata
        """
        return self._execute_returning(
            query,
            (
                event_id,
                event_type,
                source_path,
                session_id,
                element_id,
                element_text,
                Json(metadata) if metadata else None,
            ),
        )

    def get_daily_stats(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        path: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get daily page view statistics.

        Args:
            start_date: Start of date range (default: 30 days ago)
            end_date: End of date range (default: today)
            path: Filter by specific path

        Returns:
            List of daily stats dicts
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        conditions = ["DATE(timestamp) >= %s", "DATE(timestamp) <= %s", "is_bot = false"]
        params: list[Any] = [start_date, end_date]

        if path:
            conditions.append("path = %s")
            params.append(path)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        query = f"""
            SELECT
                DATE(timestamp) as date,
                COUNT(*) as total_views,
                COUNT(DISTINCT session_id) as unique_visitors,
                AVG(duration_ms)::integer as avg_duration_ms,
                AVG(scroll_depth)::integer as avg_scroll_depth
            FROM page_views
            {where_clause}
            GROUP BY DATE(timestamp)
            ORDER BY date DESC
        """
        return self._execute_query(query, tuple(params), statement_timeout_ms=ANALYTICS_TIMEOUT_MS)

    def get_geo_breakdown(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get visitor breakdown by country.

        Args:
            start_date: Start of date range
            end_date: End of date range
            limit: Max countries to return

        Returns:
            List of country stats
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        query = """
            SELECT
                country,
                COUNT(*) as views,
                COUNT(DISTINCT session_id) as visitors
            FROM page_views
            WHERE DATE(timestamp) >= %s
              AND DATE(timestamp) <= %s
              AND is_bot = false
              AND country IS NOT NULL
            GROUP BY country
            ORDER BY visitors DESC
            LIMIT %s
        """
        return self._execute_query(
            query, (start_date, end_date, limit), statement_timeout_ms=ANALYTICS_TIMEOUT_MS
        )

    def get_funnel_stats(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get conversion funnel statistics.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Funnel stats with conversion rates
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Get page views (non-bot)
        views_query = """
            SELECT COUNT(DISTINCT session_id) as unique_visitors
            FROM page_views
            WHERE DATE(timestamp) >= %s
              AND DATE(timestamp) <= %s
              AND is_bot = false
        """
        views_result = self._execute_one(
            views_query, (start_date, end_date), statement_timeout_ms=ANALYTICS_TIMEOUT_MS
        )
        unique_visitors = views_result["unique_visitors"] if views_result else 0

        # Get signup clicks
        clicks_query = """
            SELECT COUNT(DISTINCT session_id) as clickers
            FROM conversion_events
            WHERE DATE(timestamp) >= %s
              AND DATE(timestamp) <= %s
              AND event_type = 'signup_click'
        """
        clicks_result = self._execute_one(
            clicks_query, (start_date, end_date), statement_timeout_ms=ANALYTICS_TIMEOUT_MS
        )
        signup_clicks = clicks_result["clickers"] if clicks_result else 0

        # Get signup completions
        completions_query = """
            SELECT COUNT(DISTINCT session_id) as completers
            FROM conversion_events
            WHERE DATE(timestamp) >= %s
              AND DATE(timestamp) <= %s
              AND event_type = 'signup_complete'
        """
        completions_result = self._execute_one(
            completions_query, (start_date, end_date), statement_timeout_ms=ANALYTICS_TIMEOUT_MS
        )
        signup_completions = completions_result["completers"] if completions_result else 0

        # Calculate rates
        click_rate = (signup_clicks / unique_visitors * 100) if unique_visitors > 0 else 0
        completion_rate = (signup_completions / signup_clicks * 100) if signup_clicks > 0 else 0
        overall_rate = (signup_completions / unique_visitors * 100) if unique_visitors > 0 else 0

        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "unique_visitors": unique_visitors,
            "signup_clicks": signup_clicks,
            "signup_completions": signup_completions,
            "click_through_rate": round(click_rate, 2),
            "completion_rate": round(completion_rate, 2),
            "overall_conversion_rate": round(overall_rate, 2),
        }

    def get_bounce_rate(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        path: str = "/",
    ) -> dict[str, Any]:
        """Get bounce rate for a specific page.

        Bounce = session with only one page view (no duration or < 10s).

        Args:
            start_date: Start of date range
            end_date: End of date range
            path: Page path to analyze

        Returns:
            Bounce rate stats
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        # Get sessions that viewed this path
        query = """
            WITH session_views AS (
                SELECT
                    session_id,
                    COUNT(*) as view_count,
                    MAX(duration_ms) as max_duration
                FROM page_views
                WHERE DATE(timestamp) >= %s
                  AND DATE(timestamp) <= %s
                  AND is_bot = false
                  AND path = %s
                GROUP BY session_id
            )
            SELECT
                COUNT(*) as total_sessions,
                COUNT(*) FILTER (
                    WHERE view_count = 1 AND (max_duration IS NULL OR max_duration < 10000)
                ) as bounced_sessions
            FROM session_views
        """
        result = self._execute_one(
            query, (start_date, end_date, path), statement_timeout_ms=ANALYTICS_TIMEOUT_MS
        )
        if not result:
            return {"bounce_rate": 0.0, "total_sessions": 0, "bounced_sessions": 0}

        total = result["total_sessions"]
        bounced = result["bounced_sessions"]
        rate = (bounced / total * 100) if total > 0 else 0

        return {
            "path": path,
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_sessions": total,
            "bounced_sessions": bounced,
            "bounce_rate": round(rate, 2),
        }

    def get_session_count_last_minutes(self, minutes: int = 1) -> int:
        """Get count of page views in last N minutes (for rate limiting).

        Args:
            minutes: Time window

        Returns:
            Count of views
        """
        query = """
            SELECT COUNT(*) as count
            FROM page_views
            WHERE timestamp > NOW() - INTERVAL '%s minutes'
        """
        result = self._execute_one(query, (minutes,))
        return result["count"] if result else 0

    def get_conversion_events_by_type(
        self,
        event_type: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get conversion events filtered by type.

        Args:
            event_type: Event type to filter
            start_date: Start of date range
            end_date: End of date range
            limit: Max results

        Returns:
            List of conversion events
        """
        if not start_date:
            start_date = date.today() - timedelta(days=30)
        if not end_date:
            end_date = date.today()

        query = """
            SELECT id, timestamp, event_type, source_path, session_id,
                   element_id, element_text, metadata
            FROM conversion_events
            WHERE event_type = %s
              AND DATE(timestamp) >= %s
              AND DATE(timestamp) <= %s
            ORDER BY timestamp DESC
            LIMIT %s
        """
        return self._execute_query(query, (event_type, start_date, end_date, limit))


# Singleton instance
page_analytics_repository = PageAnalyticsRepository()
