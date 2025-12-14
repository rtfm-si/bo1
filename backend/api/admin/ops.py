"""Admin API endpoints for AI ops self-healing.

Provides:
- Error pattern management
- Auto-remediation history
- System health overview
"""

import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.api.middleware.admin import require_admin_any
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
async def list_error_patterns(
    error_type: str | None = None,
    enabled_only: bool = False,
    _user: dict = Depends(require_admin_any),
) -> ErrorPatternListResponse:
    """List all error patterns with stats.

    Args:
        error_type: Filter by error type
        enabled_only: Only return enabled patterns
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
                    fix_count=row["fix_count"],
                    last_remediation=row["last_remediation"],
                )
            )

        return ErrorPatternListResponse(patterns=patterns, total=len(patterns))

    except Exception as e:
        logger.error(f"Failed to list error patterns: {e}")
        raise HTTPException(status_code=500, detail="Failed to list error patterns") from None


@router.get("/remediations", response_model=RemediationHistoryResponse)
async def list_remediations(
    limit: int = 50,
    offset: int = 0,
    outcome: str | None = None,
    _user: dict = Depends(require_admin_any),
) -> RemediationHistoryResponse:
    """List recent auto-remediation history.

    Args:
        limit: Max entries to return (default 50)
        offset: Pagination offset
        outcome: Filter by outcome (success, failure, skipped, partial)
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
        logger.error(f"Failed to list remediations: {e}")
        raise HTTPException(status_code=500, detail="Failed to list remediations") from None


@router.post("/patterns", response_model=PatternCreateResponse)
async def create_pattern(
    request: CreatePatternRequest,
    _user: dict = Depends(require_admin_any),
) -> PatternCreateResponse:
    """Create a new error pattern.

    Note: This only creates the pattern - fixes must be added separately.
    """
    import re

    # Validate regex
    try:
        re.compile(request.pattern_regex)
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
                        request.pattern_name,
                        request.pattern_regex,
                        request.error_type,
                        request.severity,
                        request.description,
                        request.threshold_count,
                        request.threshold_window_minutes,
                        request.cooldown_minutes,
                    ),
                )
                pattern_id = cur.fetchone()["id"]
            conn.commit()

        return PatternCreateResponse(
            id=pattern_id,
            pattern_name=request.pattern_name,
            message="Pattern created successfully",
        )

    except Exception as e:
        if "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=409,
                detail=f"Pattern with name '{request.pattern_name}' already exists",
            ) from None
        logger.error(f"Failed to create pattern: {e}")
        raise HTTPException(status_code=500, detail="Failed to create pattern") from None


@router.patch("/patterns/{pattern_id}")
async def update_pattern(
    pattern_id: int,
    request: UpdatePatternRequest,
    _user: dict = Depends(require_admin_any),
) -> dict[str, str]:
    """Update an error pattern."""
    import re

    # Validate regex if provided
    if request.pattern_regex:
        try:
            re.compile(request.pattern_regex)
        except re.error as e:
            raise HTTPException(status_code=400, detail=f"Invalid regex: {e}") from None

    # Build update query dynamically
    updates = []
    params: list[Any] = []

    if request.pattern_regex is not None:
        updates.append("pattern_regex = %s")
        params.append(request.pattern_regex)

    if request.severity is not None:
        updates.append("severity = %s")
        params.append(request.severity)

    if request.description is not None:
        updates.append("description = %s")
        params.append(request.description)

    if request.enabled is not None:
        updates.append("enabled = %s")
        params.append(request.enabled)

    if request.threshold_count is not None:
        updates.append("threshold_count = %s")
        params.append(request.threshold_count)

    if request.threshold_window_minutes is not None:
        updates.append("threshold_window_minutes = %s")
        params.append(request.threshold_window_minutes)

    if request.cooldown_minutes is not None:
        updates.append("cooldown_minutes = %s")
        params.append(request.cooldown_minutes)

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
        logger.error(f"Failed to update pattern: {e}")
        raise HTTPException(status_code=500, detail="Failed to update pattern") from None


@router.get("/health", response_model=SystemHealthResponse)
async def get_health(
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
        logger.error(f"Health check failed: {e}")
        return SystemHealthResponse(
            checked_at=datetime.now(UTC),
            overall="unknown",
            components={"error": str(e)},
        )


@router.post("/check")
async def trigger_check(
    execute_fixes: bool = True,
    _user: dict = Depends(require_admin_any),
) -> dict[str, Any]:
    """Manually trigger an error pattern check.

    Args:
        execute_fixes: Whether to execute fixes (default True)

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
        logger.error(f"Manual check failed: {e}")
        raise HTTPException(status_code=500, detail=f"Check failed: {e}") from None
