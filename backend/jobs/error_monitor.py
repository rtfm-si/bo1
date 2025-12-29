"""Error monitoring background job for AI ops self-healing.

Periodically scans for error patterns and triggers auto-remediation.
Can be run as:
- Standalone script via cron
- Background task in FastAPI via APScheduler
"""

import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)

# Default monitoring interval (seconds)
DEFAULT_INTERVAL_SECONDS = 30

# Max errors to fetch per check
MAX_ERRORS_PER_CHECK = 100


async def fetch_recent_errors(limit: int = MAX_ERRORS_PER_CHECK) -> list[str]:
    """Fetch recent error logs from available sources.

    Attempts to fetch from (in order):
    1. Redis error buffer (fast, recent errors only)
    2. Loki logs (if configured)
    3. Database session_events (fallback)

    Args:
        limit: Max errors to fetch

    Returns:
        List of error message strings
    """
    errors: list[str] = []

    # Try Redis error buffer first
    try:
        from backend.api.dependencies import get_redis_manager

        redis_manager = get_redis_manager()
        if redis_manager.is_available and redis_manager.redis:
            # Check for error buffer key (populated by error handlers)
            raw_errors = redis_manager.redis.lrange("errors:recent", 0, limit - 1)
            errors.extend([e if isinstance(e, str) else e.decode() for e in raw_errors])
            if errors:
                logger.debug(f"Fetched {len(errors)} errors from Redis buffer")
                return errors
    except Exception as e:
        logger.debug(f"Redis error buffer unavailable: {e}")

    # Fallback: Check session_events for recent errors
    try:
        from bo1.state.database import db_session

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT data->>'error' as error_msg
                    FROM session_events
                    WHERE event_type = 'error'
                      AND created_at > now() - interval '5 minutes'
                      AND data->>'error' IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
                errors.extend([row[0] for row in rows if row[0]])

        if errors:
            logger.debug(f"Fetched {len(errors)} errors from session_events")
    except Exception as e:
        logger.debug(f"Session events query failed: {e}")

    # Also check audit_log for API errors (500s)
    try:
        from bo1.state.database import db_session

        remaining_limit = limit - len(errors)
        if remaining_limit > 0:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT details->>'error' as error_msg
                        FROM audit_log
                        WHERE action = 'api_error'
                          AND created_at > now() - interval '5 minutes'
                          AND details->>'error' IS NOT NULL
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (remaining_limit,),
                    )
                    rows = cur.fetchall()
                    api_errors = [row[0] for row in rows if row[0]]
                    errors.extend(api_errors)

            if api_errors:
                logger.debug(f"Fetched {len(api_errors)} errors from audit_log")
    except Exception as e:
        logger.debug(f"Audit log query failed: {e}")

    # Deduplicate errors by message (keep first occurrence)
    seen: set[str] = set()
    unique_errors: list[str] = []
    for error in errors:
        if error not in seen:
            seen.add(error)
            unique_errors.append(error)

    return unique_errors


async def check_performance_degradation(
    send_alerts: bool = True,
) -> dict[str, Any]:
    """Check for performance degradation across key metrics.

    Analyzes trends and sends alerts if degradation is detected.

    Args:
        send_alerts: Whether to send ntfy alerts for degradation

    Returns:
        Dict with performance analysis results
    """
    from backend.services.performance_monitor import get_performance_monitor
    from backend.services.performance_thresholds import get_threshold_service

    result: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "overall_health": "healthy",
        "metrics_checked": 0,
        "degraded_metrics": [],
        "critical_metrics": [],
    }

    try:
        monitor = get_performance_monitor()
        threshold_service = get_threshold_service()

        # Get trend analysis for all monitored metrics
        trend = monitor.analyze_trends()

        result["overall_health"] = trend.overall_health
        result["metrics_checked"] = len(trend.metrics)

        # Process each metric
        for metric_name, degradation in trend.metrics.items():
            if degradation.severity == "critical":
                result["critical_metrics"].append(
                    {
                        "metric": metric_name,
                        "current_avg": degradation.current_avg,
                        "baseline_avg": degradation.baseline_avg,
                        "ratio": degradation.ratio,
                        "score": degradation.degradation_score,
                        "details": degradation.details,
                    }
                )
            elif degradation.severity == "warn":
                result["degraded_metrics"].append(
                    {
                        "metric": metric_name,
                        "current_avg": degradation.current_avg,
                        "baseline_avg": degradation.baseline_avg,
                        "ratio": degradation.ratio,
                        "score": degradation.degradation_score,
                        "details": degradation.details,
                    }
                )

            # Also check absolute thresholds (not just trends)
            if degradation.current_avg > 0:
                stats = monitor.get_metric_stats(metric_name, 5)
                if stats and stats.count >= 5:
                    threshold_config = threshold_service.get_threshold(metric_name)
                    severity, exceeded = threshold_service.check_threshold(metric_name, stats.p95)

                    if exceeded and severity not in ["none"]:
                        logger.warning(
                            f"Threshold exceeded for {metric_name}: "
                            f"p95={stats.p95:.2f} > {threshold_config.warn_value} ({severity})"
                        )

        # Send alerts for degraded/critical metrics
        if send_alerts and (result["critical_metrics"] or result["degraded_metrics"]):
            await _send_performance_alert(result)

        logger.info(
            f"Performance check: health={result['overall_health']}, "
            f"degraded={len(result['degraded_metrics'])}, "
            f"critical={len(result['critical_metrics'])}"
        )

    except Exception as e:
        logger.error(f"Performance degradation check failed: {e}", exc_info=True)
        result["error"] = str(e)

    return result


async def _send_performance_alert(result: dict[str, Any]) -> None:
    """Send ntfy alert for performance degradation."""
    try:
        from backend.services.alerts import log_alert, send_ntfy_alert
        from bo1.config import get_settings

        severity = "critical" if result["critical_metrics"] else "warning"
        title = f"Performance Degradation: {result['overall_health'].upper()}"

        # Build message with degraded metrics
        lines = []
        for metric in result["critical_metrics"]:
            lines.append(f"🔴 {metric['metric']}: {metric['ratio']:.1f}x baseline")
        for metric in result["degraded_metrics"]:
            lines.append(f"🟡 {metric['metric']}: {metric['ratio']:.1f}x baseline")

        message = "\n".join(lines) if lines else "Performance degraded"

        topic = get_settings().ntfy_topic_alerts
        if topic:
            await send_ntfy_alert(
                topic=topic,
                title=title,
                message=message,
                priority="urgent" if severity == "critical" else "high",
                tags=["chart_with_downwards_trend", "warning"],
            )

        await log_alert(
            alert_type="performance_degradation",
            severity=severity,
            title=title,
            message=message,
            delivered=True,
            metadata={
                "overall_health": result["overall_health"],
                "degraded_count": len(result["degraded_metrics"]),
                "critical_count": len(result["critical_metrics"]),
            },
        )

    except Exception as e:
        logger.warning(f"Failed to send performance alert: {e}")


async def check_error_patterns(
    send_alerts: bool = True,
    execute_fixes: bool = True,
) -> dict[str, Any]:
    """Check for error patterns and optionally trigger remediation.

    Args:
        send_alerts: Whether to send ntfy alerts for detections
        execute_fixes: Whether to execute automated fixes

    Returns:
        Dict with detection results and remediation status
    """
    from backend.services.auto_remediation import execute_remediation
    from backend.services.error_detector import (
        detect_patterns,
        get_error_detector,
        should_trigger_remediation,
    )

    result: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "errors_scanned": 0,
        "patterns_matched": 0,
        "remediations_triggered": 0,
        "detections": [],
        "remediations": [],
        "performance": {},
    }

    try:
        # Fetch recent errors
        errors = await fetch_recent_errors()
        result["errors_scanned"] = len(errors)

        if not errors:
            logger.debug("No errors to scan")
            return result

        # Detect patterns
        detections = detect_patterns(errors, source="error_monitor")
        result["patterns_matched"] = len(detections)

        # Group by pattern for frequency check
        patterns_detected: dict[int, int] = {}
        for detection in detections:
            pattern_id = detection.pattern.id
            patterns_detected[pattern_id] = patterns_detected.get(pattern_id, 0) + 1
            result["detections"].append(
                {
                    "pattern_name": detection.pattern.pattern_name,
                    "error_type": detection.pattern.error_type,
                    "severity": detection.pattern.severity,
                    "matched_text": detection.matched_text[:200],
                }
            )

        # Check each pattern for remediation threshold
        detector = get_error_detector()
        for pattern_id, count in patterns_detected.items():
            if should_trigger_remediation(pattern_id):
                pattern = detector._patterns.get(pattern_id)
                if not pattern:
                    continue

                logger.info(
                    f"Triggering remediation for pattern {pattern.pattern_name} "
                    f"(count={count}, threshold={pattern.threshold_count})"
                )

                if execute_fixes:
                    remediation_result = await execute_remediation(
                        pattern_id,
                        context={
                            "pattern_name": pattern.pattern_name,
                            "error_count": count,
                            "trigger_source": "error_monitor",
                        },
                    )

                    if remediation_result:
                        result["remediations_triggered"] += 1
                        result["remediations"].append(
                            {
                                "pattern_name": pattern.pattern_name,
                                "fix_type": remediation_result.fix_type,
                                "outcome": remediation_result.outcome.value,
                                "message": remediation_result.message,
                                "duration_ms": remediation_result.duration_ms,
                            }
                        )

                        # Record remediation to reset cooldown
                        detector.record_remediation(pattern_id)

                        # Send alert if configured
                        if send_alerts:
                            await _send_remediation_alert(
                                pattern.pattern_name,
                                remediation_result,
                            )

        logger.info(
            f"Error check complete: {result['errors_scanned']} errors, "
            f"{result['patterns_matched']} matches, "
            f"{result['remediations_triggered']} remediations"
        )

        # Also check performance degradation
        try:
            perf_result = await check_performance_degradation(send_alerts=send_alerts)
            result["performance"] = perf_result
        except Exception as perf_e:
            logger.warning(f"Performance check failed (non-fatal): {perf_e}")
            result["performance"] = {"error": str(perf_e)}

    except Exception as e:
        logger.error(f"Error pattern check failed: {e}", exc_info=True)
        result["error"] = str(e)

    return result


async def _send_remediation_alert(
    pattern_name: str,
    result: Any,  # RemediationResult
) -> None:
    """Send ntfy alert for a remediation action."""
    try:
        from backend.services.alerts import log_alert, send_ntfy_alert

        title = f"Auto-Remediation: {pattern_name}"
        message = (
            f"Fix: {result.fix_type}\nOutcome: {result.outcome.value}\nMessage: {result.message}"
        )

        # Use alerts topic
        from bo1.config import get_settings

        topic = get_settings().ntfy_topic_alerts
        if topic:
            await send_ntfy_alert(
                topic=topic,
                title=title,
                message=message,
                priority="default" if result.outcome.value == "success" else "high",
                tags=["wrench", "robot"],
            )

        await log_alert(
            alert_type="auto_remediation",
            severity="info" if result.outcome.value == "success" else "warning",
            title=title,
            message=message,
            delivered=True,
            metadata={
                "pattern_name": pattern_name,
                "fix_type": result.fix_type,
                "outcome": result.outcome.value,
            },
        )

    except Exception as e:
        logger.warning(f"Failed to send remediation alert: {e}")


async def get_system_health() -> dict[str, Any]:
    """Get overall system health status.

    Aggregates health from multiple sources:
    - Redis connectivity
    - Postgres connectivity
    - LLM provider status
    - Recent error patterns

    Returns:
        Dict with health status for each component
    """
    health: dict[str, Any] = {
        "checked_at": datetime.now(UTC).isoformat(),
        "overall": "healthy",
        "components": {},
    }

    # Check Redis
    try:
        from backend.api.dependencies import get_redis_manager

        redis_manager = get_redis_manager()
        if redis_manager.is_available and redis_manager.redis:
            redis_manager.redis.ping()
            health["components"]["redis"] = {"status": "healthy"}
        else:
            health["components"]["redis"] = {"status": "unhealthy", "error": "Redis unavailable"}
            health["overall"] = "degraded"
    except Exception as e:
        health["components"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health["overall"] = "degraded"

    # Check Postgres
    try:
        from bo1.state.database import db_session

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
        health["components"]["postgres"] = {"status": "healthy"}
    except Exception as e:
        health["components"]["postgres"] = {"status": "unhealthy", "error": str(e)}
        health["overall"] = "degraded"

    # Check LLM providers
    try:
        from backend.services.vendor_health import get_all_provider_status

        providers = get_all_provider_status()
        health["components"]["llm_providers"] = providers

        # Check if any provider is unhealthy
        for _provider, status in providers.items():
            if status.get("status") == "unhealthy":
                health["overall"] = "degraded"
                break
    except Exception as e:
        health["components"]["llm_providers"] = {"error": str(e)}

    # Get recent remediation stats
    try:
        from bo1.state.database import db_session

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT outcome, COUNT(*) as count
                    FROM auto_remediation_log
                    WHERE triggered_at > now() - interval '1 hour'
                    GROUP BY outcome
                    """
                )
                rows = cur.fetchall()
                health["recent_remediations"] = {row[0]: row[1] for row in rows}
    except Exception as e:
        logger.debug(f"Failed to get recent remediations: {e}")

    # Determine overall status
    if any(
        c.get("status") == "unhealthy" for c in health["components"].values() if isinstance(c, dict)
    ):
        health["overall"] = "unhealthy"

    return health


def run_check_sync(
    send_alerts: bool = True,
    execute_fixes: bool = True,
) -> dict[str, Any]:
    """Synchronous wrapper for check_error_patterns.

    For use in schedulers that don't support async.
    """
    return asyncio.run(
        check_error_patterns(
            send_alerts=send_alerts,
            execute_fixes=execute_fixes,
        )
    )


if __name__ == "__main__":
    # CLI entry point for cron jobs or manual runs
    import argparse

    parser = argparse.ArgumentParser(description="Check for error patterns")
    parser.add_argument(
        "--no-alerts",
        action="store_true",
        help="Don't send ntfy alerts",
    )
    parser.add_argument(
        "--no-fixes",
        action="store_true",
        help="Don't execute automated fixes (detection only)",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Just show system health status",
    )
    args = parser.parse_args()

    if args.health:
        import json

        health = asyncio.run(get_system_health())
        print(json.dumps(health, indent=2))
    else:
        result = run_check_sync(
            send_alerts=not args.no_alerts,
            execute_fixes=not args.no_fixes,
        )
        print(f"Check result: {result}")
