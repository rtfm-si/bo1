"""Admin alert endpoints.

Provides admin-only endpoints for:
- Alert history (list sent alerts with filtering)
- Alert settings (view current thresholds)

All endpoints require admin authentication.
"""

import logging

from fastapi import APIRouter, Depends, Query

from backend.api.admin.models import (
    AlertHistoryItem,
    AlertHistoryResponse,
    AlertSettingsResponse,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from bo1.constants import SecurityAlerts

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["admin"])


@router.get(
    "/history",
    response_model=AlertHistoryResponse,
    summary="Get alert history (admin only)",
    description="Get paginated list of sent alerts with optional type filter.",
    responses={
        200: {"description": "Alert history retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("get alert history")
async def get_alert_history(
    alert_type: str | None = Query(None, description="Filter by alert type"),
    limit: int = Query(50, ge=1, le=100, description="Max records to return"),
    offset: int = Query(0, ge=0, description="Records to skip"),
) -> AlertHistoryResponse:
    """Get paginated alert history."""
    from bo1.state.database import db_session

    # Get total count
    with db_session() as conn:
        with conn.cursor() as cur:
            if alert_type:
                cur.execute(
                    "SELECT COUNT(*) as cnt FROM alert_history WHERE alert_type = %s",
                    (alert_type,),
                )
            else:
                cur.execute("SELECT COUNT(*) as cnt FROM alert_history")
            total = cur.fetchone()["cnt"]

    # Get paginated records
    with db_session() as conn:
        with conn.cursor() as cur:
            if alert_type:
                cur.execute(
                    """
                    SELECT id, alert_type, severity, title, message, metadata, delivered,
                           created_at, updated_at
                    FROM alert_history
                    WHERE alert_type = %s
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (alert_type, limit, offset),
                )
            else:
                cur.execute(
                    """
                    SELECT id, alert_type, severity, title, message, metadata, delivered,
                           created_at, updated_at
                    FROM alert_history
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
            rows = cur.fetchall()

    alerts = [
        AlertHistoryItem(
            id=row["id"],
            alert_type=row["alert_type"],
            severity=row["severity"],
            title=row["title"],
            message=row["message"],
            metadata=row["metadata"],
            delivered=row["delivered"],
            created_at=row["created_at"].isoformat() if row["created_at"] else "",
            updated_at=row["updated_at"].isoformat() if row["updated_at"] else None,
        )
        for row in rows
    ]

    return AlertHistoryResponse(
        total=total,
        alerts=alerts,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/settings",
    response_model=AlertSettingsResponse,
    summary="Get alert settings (admin only)",
    description="Get current alert threshold settings from constants.",
    responses={
        200: {"description": "Alert settings retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("get alert settings")
async def get_alert_settings() -> AlertSettingsResponse:
    """Get current alert threshold settings."""
    return AlertSettingsResponse(
        auth_failure_threshold=SecurityAlerts.AUTH_FAILURE_THRESHOLD,
        auth_failure_window_minutes=SecurityAlerts.AUTH_FAILURE_WINDOW_MINUTES,
        rate_limit_threshold=SecurityAlerts.RATE_LIMIT_THRESHOLD,
        rate_limit_window_minutes=SecurityAlerts.RATE_LIMIT_WINDOW_MINUTES,
        lockout_threshold=SecurityAlerts.LOCKOUT_THRESHOLD,
    )


@router.get(
    "/types",
    response_model=list[str],
    summary="Get alert types (admin only)",
    description="Get list of distinct alert types from history.",
    responses={
        200: {"description": "Alert types retrieved successfully"},
        403: {"description": "Admin access required", "model": ErrorResponse},
    },
    dependencies=[Depends(require_admin_any)],
)
@handle_api_errors("get alert types")
async def get_alert_types() -> list[str]:
    """Get distinct alert types for filtering."""
    from bo1.state.database import db_session

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT alert_type FROM alert_history ORDER BY alert_type")
            rows = cur.fetchall()
            return [row["alert_type"] for row in rows]
