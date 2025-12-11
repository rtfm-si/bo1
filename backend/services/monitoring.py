"""Session monitoring service for runaway detection.

Detects sessions that:
- Exceed duration threshold (stuck sessions)
- Exceed cost threshold (runaway costs)
- Have no recent events (stale sessions)

Used by background monitoring task to alert admins.
"""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Default thresholds (can be overridden via Settings)
DEFAULT_MAX_DURATION_MINS = 30
DEFAULT_MAX_COST_USD = 5.0
DEFAULT_STALE_MINS = 5


@dataclass
class RunawaySessionResult:
    """Result from runaway session detection."""

    session_id: str
    user_id: str
    reason: Literal["duration", "cost", "stale"]
    duration_minutes: float
    cost_usd: float
    last_event_minutes_ago: float | None
    started_at: datetime

    @property
    def reason_description(self) -> str:
        """Human-readable reason for runaway status."""
        if self.reason == "duration":
            return f"Duration exceeded: {self.duration_minutes:.1f} mins"
        elif self.reason == "cost":
            return f"Cost exceeded: ${self.cost_usd:.2f}"
        else:
            mins = self.last_event_minutes_ago or 0
            return f"No events for {mins:.1f} mins"


def detect_runaway_sessions(
    max_duration_mins: float | None = None,
    max_cost_usd: float | None = None,
    stale_mins: float | None = None,
) -> list[RunawaySessionResult]:
    """Detect runaway sessions based on thresholds.

    Args:
        max_duration_mins: Max session duration before flagged (default: 30)
        max_cost_usd: Max session cost before flagged (default: $5.00)
        stale_mins: Minutes since last event to consider stale (default: 5)

    Returns:
        List of RunawaySessionResult for sessions exceeding thresholds
    """
    # Use provided values or fall back to defaults
    max_duration = max_duration_mins or DEFAULT_MAX_DURATION_MINS
    max_cost = max_cost_usd or DEFAULT_MAX_COST_USD
    stale_threshold = stale_mins or DEFAULT_STALE_MINS

    now = datetime.now(UTC)
    results: list[RunawaySessionResult] = []

    with db_session() as conn:
        with conn.cursor() as cur:
            # Query in-progress sessions with latest event time
            cur.execute(
                """
                SELECT
                    s.id as session_id,
                    s.user_id,
                    s.total_cost,
                    s.created_at,
                    MAX(se.created_at) as last_event_at
                FROM sessions s
                LEFT JOIN session_events se ON se.session_id = s.id
                WHERE s.status IN ('created', 'running', 'in_progress')
                GROUP BY s.id, s.user_id, s.total_cost, s.created_at
                """
            )

            for row in cur.fetchall():
                session_id = row["session_id"]
                user_id = row["user_id"]
                cost = row["total_cost"] or 0.0
                created_at = row["created_at"]
                last_event_at = row["last_event_at"]

                # Make created_at timezone-aware if needed
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=UTC)

                # Calculate duration
                duration_mins = (now - created_at).total_seconds() / 60

                # Calculate time since last event
                last_event_mins: float | None = None
                if last_event_at:
                    if last_event_at.tzinfo is None:
                        last_event_at = last_event_at.replace(tzinfo=UTC)
                    last_event_mins = (now - last_event_at).total_seconds() / 60

                # Check thresholds
                reason: Literal["duration", "cost", "stale"] | None = None

                if cost >= max_cost:
                    reason = "cost"
                elif duration_mins >= max_duration:
                    reason = "duration"
                elif last_event_mins is not None and last_event_mins >= stale_threshold:
                    reason = "stale"

                if reason:
                    results.append(
                        RunawaySessionResult(
                            session_id=session_id,
                            user_id=user_id,
                            reason=reason,
                            duration_minutes=duration_mins,
                            cost_usd=cost,
                            last_event_minutes_ago=last_event_mins,
                            started_at=created_at,
                        )
                    )

    logger.info(f"Runaway detection: found {len(results)} sessions exceeding thresholds")
    return results


def get_session_kill_history(
    limit: int = 50,
    session_id: str | None = None,
) -> list[dict]:
    """Get session kill audit history.

    Args:
        limit: Max records to return
        session_id: Filter to specific session (optional)

    Returns:
        List of kill audit records
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            if session_id:
                cur.execute(
                    """
                    SELECT id, session_id, killed_by, reason, cost_at_kill, created_at
                    FROM session_kills
                    WHERE session_id = %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (session_id, limit),
                )
            else:
                cur.execute(
                    """
                    SELECT id, session_id, killed_by, reason, cost_at_kill, created_at
                    FROM session_kills
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
            return [dict(row) for row in cur.fetchall()]


def record_session_kill(
    session_id: str,
    killed_by: str,
    reason: str,
    cost_at_kill: float | None = None,
) -> int | None:
    """Record a session kill in the audit log.

    Args:
        session_id: Session that was killed
        killed_by: User ID or "system" for automated kills
        reason: Reason for the kill
        cost_at_kill: Session cost at time of kill

    Returns:
        Audit record ID or None if failed
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO session_kills (session_id, killed_by, reason, cost_at_kill)
                VALUES (%s, %s, %s, %s)
                RETURNING id
                """,
                (session_id, killed_by, reason, cost_at_kill),
            )
            result = cur.fetchone()
            return result["id"] if result else None
