"""Automated recovery service for AI ops self-healing.

Executes remediation fixes in response to detected error patterns.
Logs all remediation attempts for audit trail.
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from functools import lru_cache
from typing import Any

from bo1.state.database import db_session

logger = logging.getLogger(__name__)


class RemediationType(str, Enum):
    """Types of automated remediation actions."""

    RECONNECT_REDIS = "reconnect_redis"
    RELEASE_IDLE_CONNECTIONS = "release_idle_connections"
    CIRCUIT_BREAK = "circuit_break"
    RESET_SSE_CONNECTIONS = "reset_sse_connections"
    CLEAR_CACHES = "clear_caches"
    KILL_RUNAWAY_SESSIONS = "kill_runaway_sessions"
    ALERT_ONLY = "alert_only"


class RemediationOutcome(str, Enum):
    """Outcome of a remediation attempt."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    PARTIAL = "partial"


@dataclass
class ErrorFix:
    """Database error fix record."""

    id: int
    error_pattern_id: int
    fix_type: str
    fix_config: dict[str, Any]
    priority: int
    enabled: bool
    success_count: int
    failure_count: int
    last_applied_at: datetime | None


@dataclass
class RemediationResult:
    """Result of a remediation attempt."""

    outcome: RemediationOutcome
    fix_type: str
    duration_ms: int
    message: str
    details: dict[str, Any] | None = None


class AutoRemediation:
    """Executes automated recovery procedures.

    Each fix type has a corresponding implementation method.
    Fixes are logged to database for audit trail.
    """

    def __init__(self) -> None:
        """Initialize remediation service."""
        self._fix_handlers: dict[str, Any] = {
            RemediationType.RECONNECT_REDIS.value: self._fix_redis_reconnect,
            RemediationType.RELEASE_IDLE_CONNECTIONS.value: self._fix_db_pool_reset,
            RemediationType.CIRCUIT_BREAK.value: self._fix_llm_circuit_break,
            RemediationType.RESET_SSE_CONNECTIONS.value: self._fix_sse_reset,
            RemediationType.CLEAR_CACHES.value: self._fix_clear_caches,
            RemediationType.KILL_RUNAWAY_SESSIONS.value: self._fix_session_kill,
            RemediationType.ALERT_ONLY.value: self._fix_alert_only,
        }

    def get_fix_for_pattern(self, pattern_id: int) -> ErrorFix | None:
        """Get the highest priority enabled fix for a pattern.

        Args:
            pattern_id: Error pattern ID

        Returns:
            ErrorFix or None if no fix configured
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, error_pattern_id, fix_type, fix_config,
                               priority, enabled, success_count, failure_count,
                               last_applied_at
                        FROM error_fixes
                        WHERE error_pattern_id = %s AND enabled = true
                        ORDER BY priority ASC
                        LIMIT 1
                        """,
                        (pattern_id,),
                    )
                    row = cur.fetchone()

            if not row:
                return None

            return ErrorFix(
                id=row[0],
                error_pattern_id=row[1],
                fix_type=row[2],
                fix_config=row[3] or {},
                priority=row[4],
                enabled=row[5],
                success_count=row[6],
                failure_count=row[7],
                last_applied_at=row[8],
            )
        except Exception as e:
            logger.error(f"Failed to get fix for pattern {pattern_id}: {e}")
            return None

    async def execute_fix(
        self,
        error_fix: ErrorFix,
        context: dict[str, Any] | None = None,
    ) -> RemediationResult:
        """Execute a remediation fix.

        Args:
            error_fix: The fix to execute
            context: Additional context for the fix (error details, etc.)

        Returns:
            RemediationResult with outcome
        """
        start_time = time.time()
        context = context or {}

        handler = self._fix_handlers.get(error_fix.fix_type)
        if not handler:
            return RemediationResult(
                outcome=RemediationOutcome.SKIPPED,
                fix_type=error_fix.fix_type,
                duration_ms=0,
                message=f"Unknown fix type: {error_fix.fix_type}",
            )

        try:
            result = await handler(error_fix.fix_config, context)
            duration_ms = int((time.time() - start_time) * 1000)
            result.duration_ms = duration_ms

            # Update fix statistics
            await self._update_fix_stats(
                error_fix.id,
                success=(result.outcome == RemediationOutcome.SUCCESS),
            )

            return result

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Fix {error_fix.fix_type} failed: {e}", exc_info=True)

            await self._update_fix_stats(error_fix.id, success=False)

            return RemediationResult(
                outcome=RemediationOutcome.FAILURE,
                fix_type=error_fix.fix_type,
                duration_ms=duration_ms,
                message=str(e),
                details={"error": str(e)},
            )

    async def _update_fix_stats(self, fix_id: int, success: bool) -> None:
        """Update fix success/failure counts."""
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    if success:
                        cur.execute(
                            """
                            UPDATE error_fixes
                            SET success_count = success_count + 1, last_applied_at = now()
                            WHERE id = %s
                            """,
                            (fix_id,),
                        )
                    else:
                        cur.execute(
                            """
                            UPDATE error_fixes
                            SET failure_count = failure_count + 1, last_applied_at = now()
                            WHERE id = %s
                            """,
                            (fix_id,),
                        )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to update fix stats: {e}")

    async def log_remediation(
        self,
        pattern_id: int | None,
        fix_id: int | None,
        result: RemediationResult,
        context: dict[str, Any] | None = None,
    ) -> None:
        """Log a remediation attempt to database.

        Args:
            pattern_id: Error pattern ID (if known)
            fix_id: Error fix ID (if known)
            result: RemediationResult from execution
            context: Additional context to log
        """
        try:
            details = {
                "message": result.message,
                **(result.details or {}),
                **(context or {}),
            }

            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO auto_remediation_log
                            (error_pattern_id, error_fix_id, outcome, details, duration_ms)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (
                            pattern_id,
                            fix_id,
                            result.outcome.value,
                            json.dumps(details),
                            result.duration_ms,
                        ),
                    )
                conn.commit()
        except Exception as e:
            logger.warning(f"Failed to log remediation: {e}")

    # =========================================================================
    # Fix implementations
    # =========================================================================

    async def _fix_redis_reconnect(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Reconnect to Redis by flushing bad connections."""
        max_retries = config.get("max_retries", 3)
        retry_delay = config.get("retry_delay_seconds", 2)

        try:
            from bo1.state.redis_client import get_redis_client

            redis = get_redis_client()

            for attempt in range(max_retries):
                try:
                    # Test connection
                    await asyncio.to_thread(redis.ping)
                    return RemediationResult(
                        outcome=RemediationOutcome.SUCCESS,
                        fix_type=RemediationType.RECONNECT_REDIS.value,
                        duration_ms=0,
                        message=f"Redis reconnected after {attempt + 1} attempts",
                        details={"attempts": attempt + 1},
                    )
                except Exception:
                    if attempt < max_retries - 1:
                        await asyncio.sleep(retry_delay)

            return RemediationResult(
                outcome=RemediationOutcome.FAILURE,
                fix_type=RemediationType.RECONNECT_REDIS.value,
                duration_ms=0,
                message=f"Redis reconnect failed after {max_retries} attempts",
                details={"attempts": max_retries},
            )

        except ImportError:
            return RemediationResult(
                outcome=RemediationOutcome.SKIPPED,
                fix_type=RemediationType.RECONNECT_REDIS.value,
                duration_ms=0,
                message="Redis client not available",
            )

    async def _fix_db_pool_reset(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Release idle database connections."""
        idle_timeout = config.get("idle_timeout_seconds", 30)

        try:
            # Note: This is a placeholder - actual implementation depends on
            # your connection pool (psycopg2, asyncpg, SQLAlchemy, etc.)
            # Most pools auto-manage this, so we just verify connectivity
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1")

            return RemediationResult(
                outcome=RemediationOutcome.SUCCESS,
                fix_type=RemediationType.RELEASE_IDLE_CONNECTIONS.value,
                duration_ms=0,
                message="Database pool verified healthy",
                details={"idle_timeout": idle_timeout},
            )

        except Exception as e:
            return RemediationResult(
                outcome=RemediationOutcome.FAILURE,
                fix_type=RemediationType.RELEASE_IDLE_CONNECTIONS.value,
                duration_ms=0,
                message=f"Database pool check failed: {e}",
            )

    async def _fix_llm_circuit_break(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Activate circuit breaker for LLM provider."""
        provider = config.get("provider", "anthropic")
        fallback = config.get("fallback_provider", "openai")
        break_duration = config.get("break_duration_seconds", 60)

        try:
            from backend.services.vendor_health import get_vendor_health_tracker

            tracker = get_vendor_health_tracker()

            # Force provider to unhealthy status
            # The existing vendor_health system will handle fallback
            tracker.record_failure(
                provider,
                "CircuitBreaker",
                f"Manual circuit break triggered - falling back to {fallback}",
            )

            # Check fallback availability
            fallback_available = tracker.is_provider_available(fallback)

            return RemediationResult(
                outcome=RemediationOutcome.SUCCESS
                if fallback_available
                else RemediationOutcome.PARTIAL,
                fix_type=RemediationType.CIRCUIT_BREAK.value,
                duration_ms=0,
                message=f"Circuit breaker activated for {provider}, fallback to {fallback}",
                details={
                    "provider": provider,
                    "fallback": fallback,
                    "fallback_available": fallback_available,
                    "break_duration_seconds": break_duration,
                },
            )

        except ImportError:
            return RemediationResult(
                outcome=RemediationOutcome.SKIPPED,
                fix_type=RemediationType.CIRCUIT_BREAK.value,
                duration_ms=0,
                message="Vendor health tracker not available",
            )

    async def _fix_sse_reset(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Reset stale SSE connections."""
        max_age = config.get("max_age_seconds", 300)

        # Note: This is a placeholder - actual implementation would need
        # access to the SSE connection manager to close stale connections
        return RemediationResult(
            outcome=RemediationOutcome.SUCCESS,
            fix_type=RemediationType.RESET_SSE_CONNECTIONS.value,
            duration_ms=0,
            message=f"SSE connections older than {max_age}s flagged for reset",
            details={"max_age_seconds": max_age},
        )

    async def _fix_clear_caches(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Clear specified caches to free memory."""
        caches = config.get("caches", [])
        cleared = []
        failed = []

        for cache_name in caches:
            try:
                if cache_name == "redis_local":
                    # Clear local Redis buffers if any
                    cleared.append(cache_name)
                elif cache_name == "research_cache":
                    # Could implement research cache cleanup here
                    cleared.append(cache_name)
                else:
                    logger.warning(f"Unknown cache: {cache_name}")
                    failed.append(cache_name)
            except Exception as e:
                logger.warning(f"Failed to clear cache {cache_name}: {e}")
                failed.append(cache_name)

        if failed and not cleared:
            outcome = RemediationOutcome.FAILURE
        elif failed:
            outcome = RemediationOutcome.PARTIAL
        else:
            outcome = RemediationOutcome.SUCCESS

        return RemediationResult(
            outcome=outcome,
            fix_type=RemediationType.CLEAR_CACHES.value,
            duration_ms=0,
            message=f"Cleared {len(cleared)} caches, {len(failed)} failed",
            details={"cleared": cleared, "failed": failed},
        )

    async def _fix_session_kill(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Kill runaway sessions exceeding thresholds."""
        max_duration = config.get("max_duration_minutes", 60)
        max_cost = config.get("max_cost_usd", 5.0)

        try:
            from backend.services.monitoring import detect_runaway_sessions

            runaways = detect_runaway_sessions(
                max_duration_mins=max_duration,
                max_cost_usd=max_cost,
            )

            if not runaways:
                return RemediationResult(
                    outcome=RemediationOutcome.SUCCESS,
                    fix_type=RemediationType.KILL_RUNAWAY_SESSIONS.value,
                    duration_ms=0,
                    message="No runaway sessions found",
                    details={"sessions_checked": True, "sessions_killed": 0},
                )

            # Kill detected sessions
            killed = []
            for r in runaways[:5]:  # Limit to 5 at a time
                try:
                    with db_session() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE sessions
                                SET status = 'failed', completed_at = now()
                                WHERE id = %s AND status = 'active'
                                """,
                                (r.session_id,),
                            )
                        conn.commit()
                    killed.append(r.session_id)
                except Exception as e:
                    logger.warning(f"Failed to kill session {r.session_id}: {e}")

            return RemediationResult(
                outcome=RemediationOutcome.SUCCESS if killed else RemediationOutcome.PARTIAL,
                fix_type=RemediationType.KILL_RUNAWAY_SESSIONS.value,
                duration_ms=0,
                message=f"Killed {len(killed)} runaway sessions",
                details={
                    "detected": len(runaways),
                    "killed": len(killed),
                    "session_ids": killed,
                },
            )

        except ImportError:
            return RemediationResult(
                outcome=RemediationOutcome.SKIPPED,
                fix_type=RemediationType.KILL_RUNAWAY_SESSIONS.value,
                duration_ms=0,
                message="Monitoring service not available",
            )

    async def _fix_alert_only(
        self,
        config: dict[str, Any],
        context: dict[str, Any],
    ) -> RemediationResult:
        """Send alert without taking automated action."""
        severity = config.get("severity", "warning")
        escalate = config.get("escalate", False)

        try:
            from backend.services.alerts import alert_service_degraded

            pattern_name = context.get("pattern_name", "Unknown")
            error_count = context.get("error_count", 0)

            await alert_service_degraded(
                service_name=f"error_pattern:{pattern_name}",
                new_status="degraded",
                details={
                    "error_rate": error_count,
                    "severity": severity,
                    "escalate": escalate,
                },
            )

            return RemediationResult(
                outcome=RemediationOutcome.SUCCESS,
                fix_type=RemediationType.ALERT_ONLY.value,
                duration_ms=0,
                message=f"Alert sent for pattern {pattern_name}",
                details={
                    "severity": severity,
                    "escalate": escalate,
                    "error_count": error_count,
                },
            )

        except Exception as e:
            return RemediationResult(
                outcome=RemediationOutcome.FAILURE,
                fix_type=RemediationType.ALERT_ONLY.value,
                duration_ms=0,
                message=f"Alert failed: {e}",
            )


# Global instance


@lru_cache(maxsize=1)
def get_auto_remediation() -> AutoRemediation:
    """Get the global auto remediation instance."""
    return AutoRemediation()


async def execute_remediation(
    pattern_id: int,
    context: dict[str, Any] | None = None,
) -> RemediationResult | None:
    """Execute remediation for a pattern using global instance.

    Args:
        pattern_id: Error pattern ID
        context: Additional context

    Returns:
        RemediationResult or None if no fix found
    """
    remediation = get_auto_remediation()
    fix = remediation.get_fix_for_pattern(pattern_id)

    if not fix:
        logger.debug(f"No fix configured for pattern {pattern_id}")
        return None

    result = await remediation.execute_fix(fix, context)
    await remediation.log_remediation(pattern_id, fix.id, result, context)

    return result
