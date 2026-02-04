"""Google Search Console repository for GSC connection and snapshot data.

Handles:
- Admin-level GSC OAuth connection storage
- Per-decision search analytics snapshots
- Aggregated metrics queries
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from typing import Any

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class GSCRepository(BaseRepository):
    """Repository for GSC connection and snapshot operations."""

    # =========================================================================
    # Connection Management (Admin-level OAuth)
    # =========================================================================

    def get_connection(self) -> dict[str, Any] | None:
        """Get the current GSC connection (single admin connection)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, access_token, refresh_token, expires_at,
                           site_url, connected_by, connected_at, updated_at
                    FROM gsc_connection
                    ORDER BY id DESC
                    LIMIT 1
                    """
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def save_connection(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
        site_url: str,
        connected_by: str,
    ) -> dict[str, Any]:
        """Save or update the GSC connection.

        Uses upsert pattern - replaces existing connection if any.

        Args:
            access_token: Encrypted OAuth access token
            refresh_token: Encrypted OAuth refresh token
            expires_at: Token expiry timestamp
            site_url: Selected GSC property URL
            connected_by: User ID who connected

        Returns:
            Saved connection record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Delete any existing connection (single admin connection)
                cur.execute("DELETE FROM gsc_connection")

                cur.execute(
                    """
                    INSERT INTO gsc_connection (
                        access_token, refresh_token, expires_at,
                        site_url, connected_by
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, access_token, refresh_token, expires_at,
                              site_url, connected_by, connected_at, updated_at
                    """,
                    (access_token, refresh_token, expires_at, site_url, connected_by),
                )
                result = cur.fetchone()
                logger.info(f"GSC connection saved by user {connected_by} for {site_url}")
                return dict(result) if result else {}

    def update_connection_tokens(
        self,
        access_token: str,
        refresh_token: str | None,
        expires_at: datetime | None,
    ) -> bool:
        """Update tokens after refresh.

        Args:
            access_token: New encrypted access token
            refresh_token: New encrypted refresh token (may be same)
            expires_at: New expiry timestamp

        Returns:
            True if updated
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE gsc_connection
                    SET access_token = %s,
                        refresh_token = COALESCE(%s, refresh_token),
                        expires_at = %s,
                        updated_at = NOW()
                    WHERE id = (SELECT id FROM gsc_connection LIMIT 1)
                    RETURNING id
                    """,
                    (access_token, refresh_token, expires_at),
                )
                result = cur.fetchone()
                if result:
                    logger.debug("GSC connection tokens refreshed")
                return result is not None

    def update_site_url(self, site_url: str) -> bool:
        """Update the selected GSC property.

        Args:
            site_url: New site URL to track

        Returns:
            True if updated
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE gsc_connection
                    SET site_url = %s, updated_at = NOW()
                    WHERE id = (SELECT id FROM gsc_connection LIMIT 1)
                    RETURNING id
                    """,
                    (site_url,),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"GSC site URL updated to {site_url}")
                return result is not None

    def delete_connection(self) -> bool:
        """Delete the GSC connection (disconnect)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM gsc_connection RETURNING id")
                result = cur.fetchone()
                if result:
                    logger.info("GSC connection deleted")
                return result is not None

    # =========================================================================
    # Snapshot Management (Per-decision analytics)
    # =========================================================================

    def upsert_snapshot(
        self,
        decision_id: str,
        page_url: str,
        snapshot_date: date,
        impressions: int,
        clicks: int,
        ctr: float | None,
        position: float | None,
    ) -> dict[str, Any]:
        """Upsert a search analytics snapshot for a decision.

        Args:
            decision_id: Published decision ID
            page_url: Full URL of the decision page
            snapshot_date: Date of the analytics data
            impressions: Number of impressions
            clicks: Number of clicks
            ctr: Click-through rate (0-1)
            position: Average search position

        Returns:
            Upserted snapshot record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO gsc_snapshots (
                        decision_id, page_url, date, impressions, clicks, ctr, position
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id, date) DO UPDATE SET
                        page_url = EXCLUDED.page_url,
                        impressions = EXCLUDED.impressions,
                        clicks = EXCLUDED.clicks,
                        ctr = EXCLUDED.ctr,
                        position = EXCLUDED.position,
                        fetched_at = NOW()
                    RETURNING id, decision_id, page_url, date, impressions, clicks,
                              ctr, position, fetched_at
                    """,
                    (decision_id, page_url, snapshot_date, impressions, clicks, ctr, position),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def bulk_upsert_snapshots(self, snapshots: list[dict[str, Any]]) -> int:
        """Bulk upsert multiple snapshots efficiently.

        Args:
            snapshots: List of snapshot dicts with keys:
                decision_id, page_url, date, impressions, clicks, ctr, position

        Returns:
            Number of rows upserted
        """
        if not snapshots:
            return 0

        with db_session() as conn:
            with conn.cursor() as cur:
                # Use executemany with ON CONFLICT
                values = [
                    (
                        s["decision_id"],
                        s["page_url"],
                        s["date"],
                        s.get("impressions", 0),
                        s.get("clicks", 0),
                        s.get("ctr"),
                        s.get("position"),
                    )
                    for s in snapshots
                ]
                cur.executemany(
                    """
                    INSERT INTO gsc_snapshots (
                        decision_id, page_url, date, impressions, clicks, ctr, position
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (decision_id, date) DO UPDATE SET
                        page_url = EXCLUDED.page_url,
                        impressions = EXCLUDED.impressions,
                        clicks = EXCLUDED.clicks,
                        ctr = EXCLUDED.ctr,
                        position = EXCLUDED.position,
                        fetched_at = NOW()
                    """,
                    values,
                )
                logger.info(f"Bulk upserted {len(snapshots)} GSC snapshots")
                return len(snapshots)

    def get_snapshots_for_decision(
        self,
        decision_id: str,
        start_date: date | None = None,
        end_date: date | None = None,
        limit: int = 90,
    ) -> list[dict[str, Any]]:
        """Get snapshots for a specific decision.

        Args:
            decision_id: Published decision ID
            start_date: Filter from date (inclusive)
            end_date: Filter to date (inclusive)
            limit: Maximum rows to return

        Returns:
            List of snapshot records ordered by date desc
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                conditions = ["decision_id = %s"]
                params: list[Any] = [decision_id]

                if start_date:
                    conditions.append("date >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("date <= %s")
                    params.append(end_date)

                params.append(limit)

                cur.execute(
                    f"""
                    SELECT id, decision_id, page_url, date, impressions, clicks,
                           ctr, position, fetched_at
                    FROM gsc_snapshots
                    WHERE {" AND ".join(conditions)}
                    ORDER BY date DESC
                    LIMIT %s
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]

    def get_aggregated_metrics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
    ) -> dict[str, Any]:
        """Get aggregated metrics across all decisions.

        Args:
            start_date: Filter from date
            end_date: Filter to date

        Returns:
            Dict with total impressions, clicks, avg_ctr, avg_position
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                conditions = []
                params: list[Any] = []

                if start_date:
                    conditions.append("date >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("date <= %s")
                    params.append(end_date)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                cur.execute(
                    f"""
                    SELECT
                        COALESCE(SUM(impressions), 0) as total_impressions,
                        COALESCE(SUM(clicks), 0) as total_clicks,
                        CASE WHEN SUM(impressions) > 0
                             THEN SUM(clicks)::float / SUM(impressions)
                             ELSE 0 END as avg_ctr,
                        AVG(position) as avg_position,
                        COUNT(DISTINCT decision_id) as decision_count,
                        MIN(date) as earliest_date,
                        MAX(date) as latest_date
                    FROM gsc_snapshots
                    {where_clause}
                    """,
                    params,
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_decisions_with_metrics(
        self,
        start_date: date | None = None,
        end_date: date | None = None,
        order_by: str = "impressions",
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """Get decisions ranked by search metrics.

        Args:
            start_date: Filter from date
            end_date: Filter to date
            order_by: Column to sort by (impressions, clicks, ctr, position)
            limit: Maximum rows

        Returns:
            List of decisions with aggregated metrics
        """
        # Validate order_by to prevent SQL injection
        valid_order_by = {"impressions", "clicks", "ctr", "position"}
        if order_by not in valid_order_by:
            order_by = "impressions"

        # For position, lower is better (ASC), for others higher is better (DESC)
        order_dir = "ASC" if order_by == "position" else "DESC"

        with db_session() as conn:
            with conn.cursor() as cur:
                conditions = []
                params: list[Any] = []

                if start_date:
                    conditions.append("s.date >= %s")
                    params.append(start_date)
                if end_date:
                    conditions.append("s.date <= %s")
                    params.append(end_date)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                params.append(limit)

                cur.execute(
                    f"""
                    SELECT
                        d.id,
                        d.title,
                        d.slug,
                        d.category,
                        SUM(s.impressions) as impressions,
                        SUM(s.clicks) as clicks,
                        CASE WHEN SUM(s.impressions) > 0
                             THEN SUM(s.clicks)::float / SUM(s.impressions)
                             ELSE 0 END as ctr,
                        AVG(s.position) as position,
                        MAX(s.date) as last_data_date
                    FROM gsc_snapshots s
                    JOIN published_decisions d ON d.id = s.decision_id
                    {where_clause}
                    GROUP BY d.id, d.title, d.slug, d.category
                    ORDER BY {order_by} {order_dir} NULLS LAST
                    LIMIT %s
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]

    def get_last_sync_date(self) -> date | None:
        """Get the most recent snapshot date (last sync)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT MAX(date) as last_date FROM gsc_snapshots")
                result = cur.fetchone()
                return result["last_date"] if result else None

    def delete_old_snapshots(self, before_date: date) -> int:
        """Delete snapshots older than a given date.

        Args:
            before_date: Delete snapshots before this date

        Returns:
            Number of rows deleted
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM gsc_snapshots WHERE date < %s",
                    (before_date,),
                )
                count: int = cur.rowcount or 0
                if count > 0:
                    logger.info(f"Deleted {count} old GSC snapshots before {before_date}")
                return count


# Singleton instance
gsc_repository = GSCRepository()
