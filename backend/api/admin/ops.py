"""Admin API endpoints for AI ops self-healing.

Provides:
- Error pattern management
- Auto-remediation history
- System health overview
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ops", tags=["admin-ops"])


# =============================================================================
# Models
# =============================================================================


class ErrorPatternResponse(BaseModel):
    """Error pattern with stats."""

    id: int
    pattern_name: str
    pattern_regex: str
    error_type: str
    severity: str
    description: str | None
    enabled: bool
    threshold_count: int
    threshold_window_minutes: int
    cooldown_minutes: int
    created_at: datetime
    # Stats
    recent_matches: int = 0
    match_count: int = 0  # Total matches (persisted in DB)
    last_match_at: datetime | None = None
    fix_count: int = 0
    last_remediation: datetime | None = None


class ErrorPatternListResponse(BaseModel):
    """List of error patterns."""

    patterns: list[ErrorPatternResponse]
    total: int


class RemediationLogEntry(BaseModel):
    """Auto-remediation log entry."""

    id: int
    pattern_name: str | None
    fix_type: str | None
    triggered_at: datetime
    outcome: str
    details: dict[str, Any] | None
    duration_ms: int | None


class RemediationHistoryResponse(BaseModel):
    """List of remediation log entries."""

    entries: list[RemediationLogEntry]
    total: int


class SystemHealthResponse(BaseModel):
    """System health status."""

    checked_at: datetime
    overall: str
    components: dict[str, Any]
    recent_remediations: dict[str, int] = Field(default_factory=dict)


class CreatePatternRequest(BaseModel):
    """Request to create a new error pattern."""

    pattern_name: str = Field(..., min_length=1, max_length=100)
    pattern_regex: str = Field(..., min_length=1)
    error_type: str = Field(..., min_length=1, max_length=50)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")
    description: str | None = None
    threshold_count: int = Field(default=3, ge=1, le=100)
    threshold_window_minutes: int = Field(default=5, ge=1, le=60)
    cooldown_minutes: int = Field(default=5, ge=1, le=60)


class UpdatePatternRequest(BaseModel):
    """Request to update an error pattern."""

    pattern_regex: str | None = None
    severity: str | None = Field(default=None, pattern="^(low|medium|high|critical)$")
    description: str | None = None
    enabled: bool | None = None
    threshold_count: int | None = Field(default=None, ge=1, le=100)
    threshold_window_minutes: int | None = Field(default=None, ge=1, le=60)
    cooldown_minutes: int | None = Field(default=None, ge=1, le=60)


class PatternCreateResponse(BaseModel):
    """Response after creating a pattern."""

    id: int
    pattern_name: str
    message: str


# =============================================================================
# Endpoints
# =============================================================================


@router.get("/patterns", response_model=ErrorPatternListResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def list_error_patterns(
    request: Request,
    error_type: str | None = None,
    enabled_only: bool = False,
    _user: dict = Depends(require_admin_any),
) -> ErrorPatternListResponse:
    """List all error patterns with stats.

    Args:
        request: FastAPI request object
        error_type: Filter by error type
        enabled_only: Only return enabled patterns
        _user: Current authenticated admin user
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Build query with filters
                query = """
                    SELECT
                        ep.id, ep.pattern_name, ep.pattern_regex, ep.error_type,
                        ep.severity, ep.description, ep.enabled, ep.threshold_count,
                        ep.threshold_window_minutes, ep.cooldown_minutes, ep.created_at,
                        COALESCE(ep.match_count, 0) as match_count,
                        ep.last_match_at,
                        COUNT(DISTINCT ef.id) as fix_count,
                        (
                            SELECT MAX(triggered_at)
                            FROM auto_remediation_log arl
                            WHERE arl.error_pattern_id = ep.id
                        ) as last_remediation
                    FROM error_patterns ep
                    LEFT JOIN error_fixes ef ON ef.error_pattern_id = ep.id
                    WHERE 1=1
                """
                params: list[Any] = []

                if error_type:
                    query += " AND ep.error_type = %s"
                    params.append(error_type)

                if enabled_only:
                    query += " AND ep.enabled = true"

                query += " GROUP BY ep.id ORDER BY ep.id"

                cur.execute(query, params)
                rows = cur.fetchall()

        patterns = []
        for row in rows:
            patterns.append(
                ErrorPatternResponse(
                    id=row["id"],
                    pattern_name=row["pattern_name"],
                    pattern_regex=row["pattern_regex"],
                    error_type=row["error_type"],
                    severity=row["severity"],
                    description=row["description"],
                    enabled=row["enabled"],
                    threshold_count=row["threshold_count"],
                    threshold_window_minutes=row["threshold_window_minutes"],
                    cooldown_minutes=row["cooldown_minutes"],
                    created_at=row["created_at"],
                    match_count=row["match_count"],
                    last_match_at=row["last_match_at"],
                    fix_count=row["fix_count"],
                    last_remediation=row["last_remediation"],
                )
            )

        return ErrorPatternListResponse(patterns=patterns, total=len(patterns))

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to list error patterns: {e}",
            error_type=error_type,
            enabled_only=enabled_only,
        )
        raise HTTPException(status_code=500, detail="Failed to list error patterns") from None


@router.get("/remediations", response_model=RemediationHistoryResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def list_remediations(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    outcome: str | None = None,
    _user: dict = Depends(require_admin_any),
) -> RemediationHistoryResponse:
    """List recent auto-remediation history.

    Args:
        request: FastAPI request object
        limit: Max entries to return (default 50)
        offset: Pagination offset
        outcome: Filter by outcome (success, failure, skipped, partial)
        _user: Current authenticated admin user
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Count total
                count_query = "SELECT COUNT(*) FROM auto_remediation_log WHERE 1=1"
                count_params: list[Any] = []

                if outcome:
                    count_query += " AND outcome = %s"
                    count_params.append(outcome)

                cur.execute(count_query, count_params)
                total = cur.fetchone()["count"]

                # Fetch entries
                query = """
                    SELECT
                        arl.id, ep.pattern_name, ef.fix_type,
                        arl.triggered_at, arl.outcome, arl.details, arl.duration_ms
                    FROM auto_remediation_log arl
                    LEFT JOIN error_patterns ep ON ep.id = arl.error_pattern_id
                    LEFT JOIN error_fixes ef ON ef.id = arl.error_fix_id
                    WHERE 1=1
                """
                params: list[Any] = []

                if outcome:
                    query += " AND arl.outcome = %s"
                    params.append(outcome)

                query += " ORDER BY arl.triggered_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cur.execute(query, params)
                rows = cur.fetchall()

        entries = []
        for row in rows:
            entries.append(
                RemediationLogEntry(
                    id=row["id"],
                    pattern_name=row["pattern_name"],
                    fix_type=row["fix_type"],
                    triggered_at=row["triggered_at"],
                    outcome=row["outcome"],
                    details=row["details"],
                    duration_ms=row["duration_ms"],
                )
            )

        return RemediationHistoryResponse(entries=entries, total=total)

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to list remediations: {e}",
            limit=limit,
            offset=offset,
            outcome_filter=outcome,
        )
        raise HTTPException(status_code=500, detail="Failed to list remediations") from None


@router.post("/patterns", response_model=PatternCreateResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def create_pattern(
    request: Request,
    body: CreatePatternRequest,
    _user: dict = Depends(require_admin_any),
) -> PatternCreateResponse:
    """Create a new error pattern.

    Note: This only creates the pattern - fixes must be added separately.
    """
    import re

    # Validate regex
    try:
        re.compile(body.pattern_regex)
    except re.error as e:
        raise HTTPException(status_code=400, detail=f"Invalid regex: {e}") from None

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO error_patterns (
                        pattern_name, pattern_regex, error_type, severity,
                        description, threshold_count, threshold_window_minutes,
                        cooldown_minutes
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        body.pattern_name,
                        body.pattern_regex,
                        body.error_type,
                        body.severity,
                        body.description,
                        body.threshold_count,
                        body.threshold_window_minutes,
                        body.cooldown_minutes,
                    ),
                )
                pattern_id = cur.fetchone()["id"]
            conn.commit()

        return PatternCreateResponse(
            id=pattern_id,
            pattern_name=body.pattern_name,
            message="Pattern created successfully",
        )

    except Exception as e:
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Pattern with name '{body.pattern_name}' already exists",
            ) from None
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to create pattern: {e}",
            pattern_name=body.pattern_name,
            error_type=body.error_type,
        )
        raise HTTPException(status_code=500, detail="Failed to create pattern") from None


@router.patch("/patterns/{pattern_id}")
@limiter.limit(ADMIN_RATE_LIMIT)
async def update_pattern(
    request: Request,
    pattern_id: int,
    body: UpdatePatternRequest,
    _user: dict = Depends(require_admin_any),
) -> dict[str, str]:
    """Update an error pattern."""
    import re

    # Validate regex if provided
    if body.pattern_regex:
        try:
            re.compile(body.pattern_regex)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {e}") from None

    # Build update query dynamically
    updates = []
    params: list[Any] = []

    if body.pattern_regex is not None:
        updates.append("pattern_regex = %s")
        params.append(body.pattern_regex)

    if body.severity is not None:
        updates.append("severity = %s")
        params.append(body.severity)

    if body.description is not None:
        updates.append("description = %s")
        params.append(body.description)

    if body.enabled is not None:
        updates.append("enabled = %s")
        params.append(body.enabled)

    if body.threshold_count is not None:
        updates.append("threshold_count = %s")
        params.append(body.threshold_count)

    if body.threshold_window_minutes is not None:
        updates.append("threshold_window_minutes = %s")
        params.append(body.threshold_window_minutes)

    if body.cooldown_minutes is not None:
        updates.append("cooldown_minutes = %s")
        params.append(body.cooldown_minutes)

    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update")

    updates.append("updated_at = now()")
    params.append(pattern_id)

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE error_patterns
                    SET {", ".join(updates)}
                    WHERE id = %s
                    """,
                    params,
                )
                if cur.rowcount == 0:
                    raise HTTPException(status_code=404, detail="Pattern not found")
            conn.commit()

        return {"message": "Pattern updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to update pattern: {e}",
            pattern_id=pattern_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update pattern") from None


@router.get("/health", response_model=SystemHealthResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_health(
    request: Request,
    _user: dict = Depends(require_admin_any),
) -> SystemHealthResponse:
    """Get overall system health status.

    Checks connectivity to all critical services and
    summarizes recent remediation activity.
    """
    from backend.jobs.error_monitor import get_system_health

    try:
        health = await get_system_health()
        return SystemHealthResponse(
            checked_at=datetime.fromisoformat(health["checked_at"]),
            overall=health["overall"],
            components=health["components"],
            recent_remediations=health.get("recent_remediations", {}),
        )
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Health check failed: {e}",
        )
        return SystemHealthResponse(
            checked_at=datetime.now(UTC),
            overall="unknown",
            components={"error": str(e)},
        )


@router.post("/check")
@limiter.limit(ADMIN_RATE_LIMIT)
async def trigger_check(
    request: Request,
    execute_fixes: bool = True,
    _user: dict = Depends(require_admin_any),
) -> dict[str, Any]:
    """Manually trigger an error pattern check.

    Args:
        request: FastAPI request object
        execute_fixes: Whether to execute fixes (default True)
        _user: Current authenticated admin user

    Returns:
        Check results including detections and remediations
    """
    from backend.jobs.error_monitor import check_error_patterns

    try:
        result = await check_error_patterns(
            send_alerts=True,
            execute_fixes=execute_fixes,
        )
        return result
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Manual check failed: {e}",
            execute_fixes=execute_fixes,
        )
        raise HTTPException(status_code=500, detail=f"Check failed: {e}") from None


# =============================================================================
# Client & API Error Tracking
# =============================================================================


class ClientErrorItem(BaseModel):
    """Client-side error from frontend."""

    id: int
    url: str
    error: str
    stack: str | None = None
    component: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class ClientErrorListResponse(BaseModel):
    """List of client errors."""

    errors: list[ClientErrorItem]
    total: int
    limit: int
    offset: int


class ApiErrorItem(BaseModel):
    """API error (500, 429, 401, etc.)."""

    id: int
    status_code: int
    endpoint: str
    method: str
    error_message: str
    ip_address: str | None = None
    user_id: str | None = None
    created_at: datetime


class ApiErrorListResponse(BaseModel):
    """List of API errors."""

    errors: list[ApiErrorItem]
    total: int
    limit: int
    offset: int


class ErrorSummaryResponse(BaseModel):
    """Summary of errors for ops dashboard."""

    client_errors_24h: int
    api_errors_24h: int
    top_client_errors: list[dict]
    top_api_endpoints: list[dict]


@router.get("/client-errors", response_model=ClientErrorListResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def list_client_errors(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    hours: int = 24,
    _user: dict = Depends(require_admin_any),
) -> ClientErrorListResponse:
    """List recent client-side errors from frontend.

    Args:
        request: FastAPI request object
        limit: Max entries to return
        offset: Pagination offset
        hours: Lookback window in hours (default 24)
        _user: Current authenticated admin user
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Count total
                cur.execute(
                    """
                    SELECT COUNT(*) FROM audit_log
                    WHERE action = 'client_error'
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                    """,
                    (hours,),
                )
                total = cur.fetchone()["count"]

                # Fetch errors
                cur.execute(
                    """
                    SELECT id, resource_id AS url, details, ip_address, user_agent, timestamp AS created_at
                    FROM audit_log
                    WHERE action = 'client_error'
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                    """,
                    (hours, limit, offset),
                )
                rows = cur.fetchall()

        errors = []
        for row in rows:
            details = row["details"] or {}
            errors.append(
                ClientErrorItem(
                    id=row["id"],
                    url=row["url"] or "",
                    error=details.get("error", ""),
                    stack=details.get("stack"),
                    component=details.get("component"),
                    ip_address=row["ip_address"],
                    user_agent=row["user_agent"],
                    created_at=row["created_at"],
                )
            )

        return ClientErrorListResponse(errors=errors, total=total, limit=limit, offset=offset)

    except Exception as e:
        log_error(logger, ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to list client errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to list client errors") from None


@router.get("/api-errors", response_model=ApiErrorListResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def list_api_errors(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    hours: int = 24,
    status_code: int | None = None,
    _user: dict = Depends(require_admin_any),
) -> ApiErrorListResponse:
    """List recent API errors (500s, 429s, 401s).

    Args:
        request: FastAPI request object
        limit: Max entries to return
        offset: Pagination offset
        hours: Lookback window in hours (default 24)
        status_code: Filter by specific status code
        _user: Current authenticated admin user
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Count total
                count_query = """
                    SELECT COUNT(*) FROM audit_log
                    WHERE action = 'api_error'
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                """
                count_params: list[Any] = [hours]

                if status_code:
                    count_query += " AND (details->>'status_code')::int = %s"
                    count_params.append(status_code)

                cur.execute(count_query, count_params)
                total = cur.fetchone()["count"]

                # Fetch errors
                query = """
                    SELECT id, resource_id, details, ip_address, user_id, timestamp AS created_at
                    FROM audit_log
                    WHERE action = 'api_error'
                    AND timestamp >= NOW() - INTERVAL '%s hours'
                """
                params: list[Any] = [hours]

                if status_code:
                    query += " AND (details->>'status_code')::int = %s"
                    params.append(status_code)

                query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cur.execute(query, params)
                rows = cur.fetchall()

        errors = []
        for row in rows:
            details = row["details"] or {}
            errors.append(
                ApiErrorItem(
                    id=row["id"],
                    status_code=details.get("status_code", 500),
                    endpoint=details.get("endpoint", row["resource_id"] or ""),
                    method=details.get("method", "GET"),
                    error_message=details.get("error", ""),
                    ip_address=row["ip_address"],
                    user_id=row["user_id"],
                    created_at=row["created_at"],
                )
            )

        return ApiErrorListResponse(errors=errors, total=total, limit=limit, offset=offset)

    except Exception as e:
        log_error(logger, ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to list API errors: {e}")
        raise HTTPException(status_code=500, detail="Failed to list API errors") from None


@router.get("/error-summary", response_model=ErrorSummaryResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_error_summary(
    request: Request,
    _user: dict = Depends(require_admin_any),
) -> ErrorSummaryResponse:
    """Get summary of errors for ops dashboard.

    Returns counts and top errors from the last 24 hours.
    """
    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Count client errors
                cur.execute(
                    """
                    SELECT COUNT(*) FROM audit_log
                    WHERE action = 'client_error'
                    AND timestamp >= NOW() - INTERVAL '24 hours'
                    """
                )
                client_errors_24h = cur.fetchone()["count"]

                # Count API errors
                cur.execute(
                    """
                    SELECT COUNT(*) FROM audit_log
                    WHERE action = 'api_error'
                    AND timestamp >= NOW() - INTERVAL '24 hours'
                    """
                )
                api_errors_24h = cur.fetchone()["count"]

                # Top client errors by URL
                cur.execute(
                    """
                    SELECT resource_id AS url, COUNT(*) AS count
                    FROM audit_log
                    WHERE action = 'client_error'
                    AND timestamp >= NOW() - INTERVAL '24 hours'
                    GROUP BY resource_id
                    ORDER BY count DESC
                    LIMIT 5
                    """
                )
                top_client = [{"url": r["url"], "count": r["count"]} for r in cur.fetchall()]

                # Top API endpoints with errors
                cur.execute(
                    """
                    SELECT
                        details->>'endpoint' AS endpoint,
                        (details->>'status_code')::int AS status_code,
                        COUNT(*) AS count
                    FROM audit_log
                    WHERE action = 'api_error'
                    AND timestamp >= NOW() - INTERVAL '24 hours'
                    GROUP BY details->>'endpoint', details->>'status_code'
                    ORDER BY count DESC
                    LIMIT 5
                    """
                )
                top_api = [
                    {
                        "endpoint": r["endpoint"],
                        "status_code": r["status_code"],
                        "count": r["count"],
                    }
                    for r in cur.fetchall()
                ]

        return ErrorSummaryResponse(
            client_errors_24h=client_errors_24h,
            api_errors_24h=api_errors_24h,
            top_client_errors=top_client,
            top_api_endpoints=top_api,
        )

    except Exception as e:
        log_error(logger, ErrorCode.SERVICE_EXECUTION_ERROR, f"Failed to get error summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to get error summary") from None


# =============================================================================
# Performance Monitoring Endpoints
# =============================================================================


class MetricStatResponse(BaseModel):
    """Statistics for a single metric."""

    metric_name: str
    count: int
    avg: float
    min_val: float
    max_val: float
    p50: float
    p95: float
    p99: float
    window_minutes: int


class DegradationInfo(BaseModel):
    """Degradation info for a metric."""

    metric_name: str
    degradation_score: float
    current_avg: float
    baseline_avg: float
    ratio: float
    is_degraded: bool
    severity: str
    details: str


class PerformanceMetricsResponse(BaseModel):
    """Current performance metrics summary."""

    checked_at: datetime
    metrics: list[MetricStatResponse]


class PerformanceTrendsResponse(BaseModel):
    """24-hour performance trend data."""

    timestamp: datetime
    overall_health: str
    metrics: list[DegradationInfo]
    degraded_count: int
    critical_count: int


class ThresholdResponse(BaseModel):
    """Performance threshold configuration."""

    metric_name: str
    warn_value: float
    critical_value: float
    window_minutes: int
    enabled: bool
    description: str
    unit: str


class ThresholdListResponse(BaseModel):
    """List of all thresholds."""

    thresholds: list[ThresholdResponse]


class UpdateThresholdRequest(BaseModel):
    """Request to update a threshold."""

    warn_value: float | None = None
    critical_value: float | None = None
    window_minutes: int | None = None
    enabled: bool | None = None


@router.get("/performance-metrics", response_model=PerformanceMetricsResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_performance_metrics(
    request: Request,
    window_minutes: int = 30,
    _user: dict = Depends(require_admin_any),
) -> PerformanceMetricsResponse:
    """Get current performance metrics summary.

    Args:
        request: FastAPI request object
        window_minutes: Time window for stats (default 30)
        _user: Current authenticated admin user
    """
    from backend.services.performance_monitor import get_performance_monitor

    try:
        monitor = get_performance_monitor()

        # Metrics to check
        metric_names = [
            "api_response_time_ms",
            "llm_response_time_ms",
            "error_rate_percent",
            "queue_depth",
            "db_pool_usage_percent",
        ]

        metrics = []
        for name in metric_names:
            stats = monitor.get_metric_stats(name, window_minutes)
            if stats:
                metrics.append(
                    MetricStatResponse(
                        metric_name=stats.metric_name,
                        count=stats.count,
                        avg=stats.avg,
                        min_val=stats.min_val,
                        max_val=stats.max_val,
                        p50=stats.p50,
                        p95=stats.p95,
                        p99=stats.p99,
                        window_minutes=stats.window_minutes,
                    )
                )

        return PerformanceMetricsResponse(
            checked_at=datetime.now(UTC),
            metrics=metrics,
        )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get performance metrics: {e}",
        )
        raise HTTPException(status_code=500, detail="Failed to get performance metrics") from None


@router.get("/performance-trends", response_model=PerformanceTrendsResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_performance_trends(
    request: Request,
    _user: dict = Depends(require_admin_any),
) -> PerformanceTrendsResponse:
    """Get performance trend analysis with degradation detection.

    Args:
        request: FastAPI request object
        _user: Current authenticated admin user
    """
    from backend.services.performance_monitor import get_performance_monitor

    try:
        monitor = get_performance_monitor()
        trend = monitor.analyze_trends()

        metrics = []
        for _name, degradation in trend.metrics.items():
            metrics.append(
                DegradationInfo(
                    metric_name=degradation.metric_name,
                    degradation_score=degradation.degradation_score,
                    current_avg=degradation.current_avg,
                    baseline_avg=degradation.baseline_avg,
                    ratio=degradation.ratio,
                    is_degraded=degradation.is_degraded,
                    severity=degradation.severity,
                    details=degradation.details,
                )
            )

        return PerformanceTrendsResponse(
            timestamp=trend.timestamp,
            overall_health=trend.overall_health,
            metrics=metrics,
            degraded_count=trend.degraded_count,
            critical_count=trend.critical_count,
        )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get performance trends: {e}",
        )
        raise HTTPException(status_code=500, detail="Failed to get performance trends") from None


@router.get("/performance-thresholds", response_model=ThresholdListResponse)
@limiter.limit(ADMIN_RATE_LIMIT)
async def get_performance_thresholds(
    request: Request,
    _user: dict = Depends(require_admin_any),
) -> ThresholdListResponse:
    """Get all performance threshold configurations.

    Args:
        request: FastAPI request object
        _user: Current authenticated admin user
    """
    from backend.services.performance_thresholds import get_threshold_service

    try:
        service = get_threshold_service()
        thresholds = service.get_all_thresholds()

        return ThresholdListResponse(
            thresholds=[
                ThresholdResponse(
                    metric_name=t.metric_name,
                    warn_value=t.warn_value,
                    critical_value=t.critical_value,
                    window_minutes=t.window_minutes,
                    enabled=t.enabled,
                    description=t.description,
                    unit=t.unit,
                )
                for t in thresholds
            ]
        )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get performance thresholds: {e}",
        )
        raise HTTPException(
            status_code=500, detail="Failed to get performance thresholds"
        ) from None


@router.put("/performance-thresholds/{metric_name}")
@limiter.limit(ADMIN_RATE_LIMIT)
async def update_performance_threshold(
    request: Request,
    metric_name: str,
    body: UpdateThresholdRequest,
    _user: dict = Depends(require_admin_any),
) -> dict[str, str]:
    """Update a performance threshold configuration.

    Args:
        request: FastAPI request object
        metric_name: Name of the metric to update
        body: Threshold values to update
        _user: Current authenticated admin user
    """
    from backend.services.performance_thresholds import get_threshold_service

    try:
        service = get_threshold_service()
        result = service.update_threshold(
            metric_name=metric_name,
            warn_value=body.warn_value,
            critical_value=body.critical_value,
            window_minutes=body.window_minutes,
            enabled=body.enabled,
        )

        if result is None:
            raise HTTPException(status_code=500, detail="Failed to update threshold")

        return {"message": f"Threshold for {metric_name} updated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to update threshold: {e}",
            metric_name=metric_name,
        )
        raise HTTPException(status_code=500, detail="Failed to update threshold") from None
