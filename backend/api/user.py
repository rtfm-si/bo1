"""User GDPR endpoints for data export, account deletion, and consent.

Provides:
- POST /api/v1/user/gdpr-consent - Record GDPR consent
- GET /api/v1/user/export - Export user data (Art. 15)
- DELETE /api/v1/user/delete - Delete user account (Art. 17)
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.api.middleware.auth import get_current_user
from backend.api.models import (
    VALID_KANBAN_STATUSES,
    ApplyPromoCodeRequest,
    ErrorResponse,
    KanbanColumn,
    KanbanColumnsResponse,
    KanbanColumnsUpdate,
    UserPromotion,
)
from backend.services.audit import (
    get_recent_deletion_request,
    get_recent_export_request,
    log_gdpr_event,
)
from backend.services.gdpr import GDPRError, collect_user_data, delete_user_data
from backend.services.promotion_service import PromoValidationError, validate_and_apply_code
from backend.services.usage_tracking import get_all_usage, get_effective_tier
from bo1.constants import TierFeatureFlags, TierLimits
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])


# Data retention models
class RetentionSettingResponse(BaseModel):
    """Response for retention setting endpoint."""

    data_retention_days: int = Field(
        ..., description="Data retention period in days (-1=forever, 365-1095)"
    )


class RetentionSettingUpdate(BaseModel):
    """Request body for updating retention setting.

    Valid values:
    - -1: Forever (data kept until account deletion)
    - 365-1095: 1 to 3 years
    """

    days: int = Field(..., description="Data retention period (-1=forever, 365-1095 days)")

    @classmethod
    def validate_days(cls, v: int) -> int:
        """Validate retention days: -1 (forever) or 365-1095 (1-3 years)."""
        if v == -1:
            return v
        if v < 365:
            raise ValueError(
                "Retention period must be at least 365 days (1 year) or -1 for forever"
            )
        if v > 1095:
            raise ValueError(
                "Retention period cannot exceed 1095 days (3 years). Use -1 for forever."
            )
        return v

    def model_post_init(self, _context: object) -> None:
        """Validate days after initialization."""
        self.days = self.validate_days(self.days)


def _get_client_ip(request: Request) -> str | None:
    """Extract client IP from request headers."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return None


@router.post(
    "/gdpr-consent",
    summary="Record GDPR consent",
    description="Record user's GDPR consent timestamp. Called after OAuth signup.",
    responses={
        200: {"description": "Consent recorded"},
        500: {"description": "Failed to record consent", "model": ErrorResponse},
    },
)
async def record_gdpr_consent(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Record GDPR consent timestamp for user."""
    user_id = user["user_id"]
    client_ip = _get_client_ip(request)

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET gdpr_consent_at = NOW(),
                        updated_at = NOW()
                    WHERE id = %s AND gdpr_consent_at IS NULL
                    """,
                    (user_id,),
                )
                updated = cur.rowcount > 0

        if updated:
            # Log the consent event
            log_gdpr_event(
                user_id=user_id,
                action="consent_given",
                ip_address=client_ip,
            )
            logger.info(f"GDPR consent recorded for user {user_id}")

        return {
            "status": "ok",
            "consent_recorded": updated,
        }

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to record GDPR consent for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to record consent") from e


@router.get(
    "/export",
    summary="Export user data (GDPR Art. 15)",
    description="""
    Export all user data as JSON file. Rate limited to 1 request per 24 hours.

    Includes:
    - User profile
    - Business context
    - Sessions (meetings)
    - Actions
    - Datasets (metadata only)
    - Projects
    - GDPR audit log
    """,
    responses={
        200: {"description": "JSON file with all user data"},
        429: {"description": "Rate limit exceeded (1 per 24h)", "model": ErrorResponse},
        500: {"description": "Export failed", "model": ErrorResponse},
    },
)
async def export_user_data(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> Response:
    """Export all user data as downloadable JSON."""
    user_id = user["user_id"]
    client_ip = _get_client_ip(request)

    # Rate limit: 1 export per 24 hours
    recent = get_recent_export_request(user_id, window_hours=24)
    if recent:
        last_export = recent["created_at"]
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Rate limit exceeded",
                "message": "You can only request data export once every 24 hours.",
                "last_export": last_export.isoformat() if last_export else None,
            },
        )

    # Log the export request
    log_gdpr_event(
        user_id=user_id,
        action="export_requested",
        ip_address=client_ip,
    )

    try:
        # Collect all user data
        data = collect_user_data(user_id)

        # Log completion
        log_gdpr_event(
            user_id=user_id,
            action="export_completed",
            details={"record_count": sum(len(v) for v in data.values() if isinstance(v, list))},
            ip_address=client_ip,
        )

        # Return as downloadable JSON file
        filename = f"boardof_one_export_{user_id[:8]}_{datetime.now(UTC).strftime('%Y%m%d')}.json"
        content = json.dumps(data, indent=2, default=str)

        return Response(
            content=content,
            media_type="application/json",
            headers={
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Cache-Control": "no-store",
            },
        )

    except GDPRError as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"GDPR export failed for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.delete(
    "/delete",
    summary="Delete user account (GDPR Art. 17)",
    description="""
    Permanently delete user account and anonymize associated data.

    **WARNING**: This action is irreversible.

    What happens:
    - User profile: Deleted
    - Business context: Deleted
    - Sessions: Anonymized (user_id removed, problem statement hashed)
    - Actions: Anonymized (user_id removed, titles cleared)
    - Datasets: Deleted (including files from storage)
    - Projects: Deleted

    Rate limited to 1 request per 24 hours.
    """,
    responses={
        200: {"description": "Account deleted successfully"},
        429: {"description": "Rate limit exceeded", "model": ErrorResponse},
        500: {"description": "Deletion failed", "model": ErrorResponse},
    },
)
async def delete_user_account(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Delete user account and anonymize data."""
    user_id = user["user_id"]
    client_ip = _get_client_ip(request)

    # Check for recent deletion request (prevent accidental double-deletion)
    recent = get_recent_deletion_request(user_id, window_hours=24)
    if recent:
        if recent["action"] == "deletion_completed":
            raise HTTPException(
                status_code=410,
                detail={
                    "error": "Account already deleted",
                    "message": "This account has already been deleted.",
                },
            )
        raise HTTPException(
            status_code=429,
            detail={
                "error": "Deletion pending",
                "message": "A deletion request is already in progress.",
            },
        )

    # Log the deletion request
    log_gdpr_event(
        user_id=user_id,
        action="deletion_requested",
        ip_address=client_ip,
    )

    try:
        # Perform deletion
        summary = delete_user_data(user_id)

        # Log completion
        log_gdpr_event(
            user_id=user_id,
            action="deletion_completed",
            details=summary,
            ip_address=client_ip,
        )

        # Delete SuperTokens session (logout)
        try:
            from supertokens_python.recipe.session.asyncio import revoke_all_sessions_for_user

            await revoke_all_sessions_for_user(user_id)
        except Exception as e:
            logger.warning(f"Failed to revoke SuperTokens sessions: {e}")

        return {
            "status": "deleted",
            "message": "Your account and data have been deleted.",
            "summary": {
                "sessions_anonymized": summary.get("sessions_anonymized", 0),
                "actions_anonymized": summary.get("actions_anonymized", 0),
                "datasets_deleted": summary.get("datasets_deleted", 0),
            },
        }

    except GDPRError as e:
        # Log failure
        log_gdpr_event(
            user_id=user_id,
            action="deletion_failed",
            details={"error": str(e)},
            ip_address=client_ip,
        )
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"GDPR deletion failed for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get(
    "/retention",
    summary="Get data retention setting",
    description="Get the user's configured data retention period in days.",
    response_model=RetentionSettingResponse,
    responses={
        200: {"description": "Current retention setting"},
        500: {"description": "Failed to get setting", "model": ErrorResponse},
    },
)
async def get_retention_setting(
    user: dict[str, Any] = Depends(get_current_user),
) -> RetentionSettingResponse:
    """Get user's data retention period setting."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT data_retention_days FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                # Handle potential NULL from users created before migration
                retention_days = row["data_retention_days"]
                if retention_days is None:
                    retention_days = 730  # Default fallback (2 years)

                return RetentionSettingResponse(data_retention_days=retention_days)

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get retention setting for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get setting") from e


@router.patch(
    "/retention",
    summary="Update data retention setting",
    description="""
    Update the user's data retention period.

    Valid values:
    - -1: Forever (data kept until account deletion)
    - 365-1095: 1 to 3 years

    Note: Changing to a shorter period does not immediately delete data.
    The scheduled cleanup job will remove data past the new retention period
    during its next run. Users with "Forever" retention (-1) are skipped by
    the cleanup job entirely.
    """,
    response_model=RetentionSettingResponse,
    responses={
        200: {"description": "Retention setting updated"},
        422: {"description": "Invalid retention period (must be -1 or 365-1095 days)"},
        500: {"description": "Failed to update setting", "model": ErrorResponse},
    },
)
async def update_retention_setting(
    body: RetentionSettingUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> RetentionSettingResponse:
    """Update user's data retention period setting."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET data_retention_days = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING data_retention_days
                    """,
                    (body.days, user_id),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(f"Updated retention setting for {user_id}: {body.days} days")
                return RetentionSettingResponse(data_retention_days=row["data_retention_days"])

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to update retention setting for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update setting") from e


# Meeting preferences models
class PreferencesResponse(BaseModel):
    """Response for user preferences endpoint."""

    skip_clarification: bool = Field(
        default=False, description="Skip pre-meeting clarifying questions by default"
    )
    default_reminder_frequency_days: int = Field(
        default=3, description="Default reminder frequency for new actions (1-14 days)"
    )


class PreferencesUpdate(BaseModel):
    """Request body for updating user preferences."""

    skip_clarification: bool | None = Field(
        default=None, description="Skip pre-meeting clarifying questions by default"
    )
    default_reminder_frequency_days: int | None = Field(
        default=None,
        ge=1,
        le=14,
        description="Default reminder frequency for new actions (1-14 days)",
    )


@router.get(
    "/preferences",
    summary="Get user preferences",
    description="Get the user's meeting and workflow preferences.",
    response_model=PreferencesResponse,
    responses={
        200: {"description": "Current preferences"},
        500: {"description": "Failed to get preferences", "model": ErrorResponse},
    },
)
async def get_preferences(
    user: dict[str, Any] = Depends(get_current_user),
) -> PreferencesResponse:
    """Get user's meeting preferences."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT skip_clarification, default_reminder_frequency_days FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                return PreferencesResponse(
                    skip_clarification=row.get("skip_clarification", False) or False,
                    default_reminder_frequency_days=row.get("default_reminder_frequency_days") or 3,
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get preferences for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get preferences") from e


@router.patch(
    "/preferences",
    summary="Update user preferences",
    description="""
    Update user's meeting and workflow preferences.

    Available preferences:
    - skip_clarification: Skip pre-meeting clarifying questions by default.
      When enabled, meetings start directly without asking context questions.
      You can still provide context via your business profile.
    """,
    response_model=PreferencesResponse,
    responses={
        200: {"description": "Preferences updated"},
        500: {"description": "Failed to update preferences", "model": ErrorResponse},
    },
)
async def update_preferences(
    body: PreferencesUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> PreferencesResponse:
    """Update user's meeting preferences."""
    user_id = user["user_id"]

    # Build dynamic update query
    updates = []
    params: list[Any] = []

    if body.skip_clarification is not None:
        updates.append("skip_clarification = %s")
        params.append(body.skip_clarification)

    if body.default_reminder_frequency_days is not None:
        # Clamp to valid range
        freq = max(1, min(14, body.default_reminder_frequency_days))
        updates.append("default_reminder_frequency_days = %s")
        params.append(freq)

    if not updates:
        # No changes requested, return current values
        return await get_preferences(user)

    params.append(user_id)

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE users
                    SET {", ".join(updates)}, updated_at = NOW()
                    WHERE id = %s
                    RETURNING skip_clarification, default_reminder_frequency_days
                    """,
                    params,
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(
                    f"Updated preferences for {user_id}: skip_clarification={row.get('skip_clarification')}, "
                    f"default_reminder_frequency_days={row.get('default_reminder_frequency_days')}"
                )
                return PreferencesResponse(
                    skip_clarification=row.get("skip_clarification", False) or False,
                    default_reminder_frequency_days=row.get("default_reminder_frequency_days") or 3,
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to update preferences for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update preferences") from e


# Gantt color preference models
class GanttColorPreferenceResponse(BaseModel):
    """Response for Gantt color preference endpoint."""

    gantt_color_strategy: str = Field(
        ...,
        description="Gantt chart color coding strategy (BY_STATUS, BY_PROJECT, BY_PRIORITY, HYBRID)",
    )


class GanttColorPreferenceUpdate(BaseModel):
    """Request body for updating Gantt color preference."""

    gantt_color_strategy: str = Field(
        ...,
        pattern="^(BY_STATUS|BY_PROJECT|BY_PRIORITY|HYBRID)$",
        description="Gantt chart color coding strategy",
    )


@router.get(
    "/preferences/gantt-colors",
    summary="Get Gantt color preference",
    description="Get the user's preferred Gantt chart color coding strategy.",
    response_model=GanttColorPreferenceResponse,
    responses={
        200: {"description": "Current Gantt color preference"},
        500: {"description": "Failed to get preference", "model": ErrorResponse},
    },
)
async def get_gantt_color_preference(
    user: dict[str, Any] = Depends(get_current_user),
) -> GanttColorPreferenceResponse:
    """Get user's Gantt color preference."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT gantt_color_strategy FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                return GanttColorPreferenceResponse(
                    gantt_color_strategy=row.get("gantt_color_strategy", "BY_STATUS") or "BY_STATUS"
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get Gantt color preference for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get preference") from e


@router.patch(
    "/preferences/gantt-colors",
    summary="Update Gantt color preference",
    description="""
    Update user's preferred Gantt chart color coding strategy.

    Available strategies:
    - BY_STATUS: Color actions by their status (not started, in progress, blocked, on hold, complete, cancelled)
    - BY_PROJECT: Color actions by their assigned project
    - BY_PRIORITY: Color actions by their priority (low, medium, high)
    - HYBRID: Combine status (primary) and project (accent stripe) coloring
    """,
    response_model=GanttColorPreferenceResponse,
    responses={
        200: {"description": "Preference updated"},
        400: {"description": "Invalid strategy", "model": ErrorResponse},
        500: {"description": "Failed to update preference", "model": ErrorResponse},
    },
)
async def update_gantt_color_preference(
    body: GanttColorPreferenceUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> GanttColorPreferenceResponse:
    """Update user's Gantt color preference."""
    user_id = user["user_id"]
    strategy = body.gantt_color_strategy

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET gantt_color_strategy = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING gantt_color_strategy
                    """,
                    (strategy, user_id),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(f"Updated Gantt color strategy for {user_id}: {strategy}")
                return GanttColorPreferenceResponse(
                    gantt_color_strategy=row["gantt_color_strategy"]
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to update Gantt color preference for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update preference") from e


# =============================================================================
# Kanban Column Preferences
# =============================================================================

# Default columns for new users
DEFAULT_KANBAN_COLUMNS = [
    KanbanColumn(id="todo", title="To Do"),
    KanbanColumn(id="in_progress", title="In Progress"),
    KanbanColumn(id="done", title="Done"),
]


def _validate_kanban_columns(columns: list[KanbanColumn]) -> None:
    """Validate kanban column configuration.

    Raises HTTPException if validation fails.
    """
    # Check for unique IDs
    ids = [col.id for col in columns]
    if len(ids) != len(set(ids)):
        raise HTTPException(status_code=400, detail="Column IDs must be unique")

    # Check all IDs are valid ActionStatus values
    for col_id in ids:
        if col_id not in VALID_KANBAN_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid column ID '{col_id}'. Must be a valid action status.",
            )


@router.get(
    "/preferences/kanban-columns",
    summary="Get kanban columns preference",
    description="Get the user's kanban column configuration.",
    response_model=KanbanColumnsResponse,
    responses={
        200: {"description": "Current kanban columns"},
        500: {"description": "Failed to get preference", "model": ErrorResponse},
    },
)
async def get_kanban_columns(
    user: dict[str, Any] = Depends(get_current_user),
) -> KanbanColumnsResponse:
    """Get user's kanban column configuration."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT kanban_columns FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                # Return stored columns or defaults
                stored = row.get("kanban_columns")
                if stored:
                    columns = [KanbanColumn(**col) for col in stored]
                else:
                    columns = DEFAULT_KANBAN_COLUMNS

                return KanbanColumnsResponse(columns=columns)

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get kanban columns for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get preference") from e


@router.patch(
    "/preferences/kanban-columns",
    summary="Update kanban columns preference",
    description="""
    Update user's kanban column configuration.

    Rules:
    - 1-8 columns allowed
    - Column IDs must be valid action statuses (todo, in_progress, blocked, in_review, done, cancelled, failed, abandoned, replanned)
    - Column IDs must be unique
    - Titles must be 1-50 characters
    - Optional hex color (e.g., #FF5733)
    """,
    response_model=KanbanColumnsResponse,
    responses={
        200: {"description": "Columns updated"},
        400: {"description": "Invalid configuration", "model": ErrorResponse},
        500: {"description": "Failed to update preference", "model": ErrorResponse},
    },
)
async def update_kanban_columns(
    body: KanbanColumnsUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> KanbanColumnsResponse:
    """Update user's kanban column configuration."""
    user_id = user["user_id"]

    # Validate columns
    _validate_kanban_columns(body.columns)

    try:
        import json

        columns_json = json.dumps([col.model_dump() for col in body.columns])

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET kanban_columns = %s, updated_at = NOW()
                    WHERE id = %s
                    RETURNING kanban_columns
                    """,
                    (columns_json, user_id),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(f"Updated kanban columns for {user_id}: {len(body.columns)} columns")
                return KanbanColumnsResponse(columns=body.columns)

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to update kanban columns for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update preference") from e


# =============================================================================
# Usage & Limits
# =============================================================================


class UsageMetricResponse(BaseModel):
    """Single metric usage details."""

    metric: str = Field(..., description="Metric name")
    current: int = Field(..., description="Current usage count")
    limit: int = Field(..., description="Limit (-1 = unlimited)")
    remaining: int = Field(..., description="Remaining quota (-1 = unlimited)")
    reset_at: str | None = Field(None, description="When usage resets (ISO 8601)")


class UsageResponse(BaseModel):
    """User's current usage across all metrics."""

    tier: str = Field(..., description="User's subscription tier")
    effective_tier: str = Field(..., description="Effective tier (may differ if override active)")
    metrics: list[UsageMetricResponse] = Field(..., description="Usage per metric")
    features: dict[str, bool] = Field(..., description="Feature flags for tier")


@router.get(
    "/usage",
    summary="Get user usage",
    description="Get current usage across all metrics (meetings, datasets, mentor chats).",
    response_model=UsageResponse,
    responses={
        200: {"description": "Usage retrieved successfully"},
        401: {"description": "Authentication required", "model": ErrorResponse},
        500: {"description": "Failed to get usage", "model": ErrorResponse},
    },
)
async def get_usage(
    user: dict[str, Any] = Depends(get_current_user),
) -> UsageResponse:
    """Get user's current usage and limits."""
    user_id = user["user_id"]
    base_tier = user.get("subscription_tier", "free")

    try:
        # Get effective tier (considering overrides)
        effective_tier = get_effective_tier(user_id, base_tier)

        # Get usage for all metrics
        all_usage = get_all_usage(user_id, effective_tier)

        # Format metrics
        metrics = []
        for metric_name, result in all_usage.items():
            metrics.append(
                UsageMetricResponse(
                    metric=metric_name,
                    current=result.current,
                    limit=result.limit,
                    remaining=result.remaining,
                    reset_at=result.reset_at.isoformat() if result.reset_at else None,
                )
            )

        # Get feature flags
        features = TierFeatureFlags.get_features(effective_tier)

        return UsageResponse(
            tier=base_tier,
            effective_tier=effective_tier,
            metrics=metrics,
            features=features,
        )

    except Exception as e:
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get usage for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get usage") from e


class TierLimitsResponse(BaseModel):
    """Tier limits information."""

    tier: str = Field(..., description="Tier name")
    limits: dict[str, int] = Field(..., description="Limits per metric")
    features: dict[str, bool] = Field(..., description="Feature flags")


@router.get(
    "/tier-info",
    summary="Get tier information",
    description="Get limits and features for user's current tier.",
    response_model=TierLimitsResponse,
    responses={
        200: {"description": "Tier info retrieved successfully"},
        401: {"description": "Authentication required", "model": ErrorResponse},
    },
)
async def get_tier_info(
    user: dict[str, Any] = Depends(get_current_user),
) -> TierLimitsResponse:
    """Get user's tier limits and features."""
    user_id = user["user_id"]
    base_tier = user.get("subscription_tier", "free")
    effective_tier = get_effective_tier(user_id, base_tier)

    return TierLimitsResponse(
        tier=effective_tier,
        limits=TierLimits.get_limits(effective_tier),
        features=TierFeatureFlags.get_features(effective_tier),
    )


# =============================================================================
# Promotions
# =============================================================================


@router.post(
    "/promo-code",
    response_model=UserPromotion,
    summary="Apply promo code",
    description="""
    Apply a promo code to your account.

    Validation checks:
    - Code must exist and be active
    - Code must not be expired
    - Code must not have reached maximum uses
    - You cannot apply the same code twice
    """,
    responses={
        200: {"description": "Promo code applied successfully"},
        404: {"description": "Promo code not found", "model": ErrorResponse},
        409: {"description": "Code already applied", "model": ErrorResponse},
        410: {"description": "Code expired or at max uses", "model": ErrorResponse},
        422: {"description": "Invalid promo code format", "model": ErrorResponse},
    },
)
async def apply_promo_code(
    body: ApplyPromoCodeRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> UserPromotion:
    """Apply a promo code to user's account."""
    user_id = user["user_id"]

    try:
        result = validate_and_apply_code(user_id, body.code)
        logger.info(f"User {user_id} applied promo code {body.code}")

        # Convert to Pydantic model
        from backend.api.models import Promotion

        return UserPromotion(
            id=result["id"],
            promotion=Promotion(**result["promotion"]),
            applied_at=result["applied_at"],
            deliberations_remaining=result["deliberations_remaining"],
            discount_applied=result["discount_applied"],
            status=result["status"],
        )

    except PromoValidationError as e:
        if e.code == "not_found":
            raise HTTPException(status_code=404, detail=e.message) from e
        elif e.code == "already_applied":
            raise HTTPException(
                status_code=409,
                detail={
                    "error": "Already applied",
                    "message": e.message,
                },
            ) from e
        elif e.code in ("expired", "inactive", "max_uses_reached"):
            raise HTTPException(
                status_code=410,
                detail={
                    "error": e.code,
                    "message": e.message,
                },
            ) from e
        else:
            raise HTTPException(status_code=400, detail=e.message) from e


# =============================================================================
# Cost Calculator Defaults
# =============================================================================


class CostCalculatorDefaults(BaseModel):
    """User defaults for meeting cost calculator widget."""

    avg_hourly_rate: int = Field(
        default=75,
        ge=10,
        le=1000,
        description="Average hourly rate per participant ($)",
    )
    typical_participants: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Typical number of meeting participants",
    )
    typical_duration_mins: int = Field(
        default=60,
        ge=15,
        le=480,
        description="Typical meeting duration in minutes",
    )
    typical_prep_mins: int = Field(
        default=30,
        ge=0,
        le=240,
        description="Typical preparation time per participant in minutes",
    )


@router.get(
    "/cost-calculator-defaults",
    summary="Get cost calculator defaults",
    description="Get the user's saved defaults for the meeting cost calculator widget.",
    response_model=CostCalculatorDefaults,
    responses={
        200: {"description": "Cost calculator defaults"},
        500: {"description": "Failed to get defaults", "model": ErrorResponse},
    },
)
async def get_cost_calculator_defaults(
    user: dict[str, Any] = Depends(get_current_user),
) -> CostCalculatorDefaults:
    """Get user's cost calculator defaults."""
    from bo1.state.repositories.user_repository import user_repository

    user_id = user["user_id"]

    try:
        defaults = user_repository.get_cost_calculator_defaults(user_id)
        return CostCalculatorDefaults(**defaults)

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get cost calculator defaults for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get defaults") from e


@router.patch(
    "/cost-calculator-defaults",
    summary="Update cost calculator defaults",
    description="""
    Update the user's defaults for the meeting cost calculator widget.

    These defaults are used to pre-populate the calculator when estimating
    traditional meeting costs vs Bo1 meeting costs.

    Constraints:
    - avg_hourly_rate: $10-1000
    - typical_participants: 1-20
    - typical_duration_mins: 15-480 (8 hours max)
    - typical_prep_mins: 0-240 (4 hours max)
    """,
    response_model=CostCalculatorDefaults,
    responses={
        200: {"description": "Defaults updated"},
        422: {"description": "Invalid values", "model": ErrorResponse},
        500: {"description": "Failed to update defaults", "model": ErrorResponse},
    },
)
async def update_cost_calculator_defaults(
    body: CostCalculatorDefaults,
    user: dict[str, Any] = Depends(get_current_user),
) -> CostCalculatorDefaults:
    """Update user's cost calculator defaults."""
    from bo1.state.repositories.user_repository import user_repository

    user_id = user["user_id"]

    try:
        defaults = user_repository.update_cost_calculator_defaults(
            user_id,
            {
                "avg_hourly_rate": body.avg_hourly_rate,
                "typical_participants": body.typical_participants,
                "typical_duration_mins": body.typical_duration_mins,
                "typical_prep_mins": body.typical_prep_mins,
            },
        )
        logger.info(f"Updated cost calculator defaults for {user_id}")
        return CostCalculatorDefaults(**defaults)

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to update cost calculator defaults for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update defaults") from e


# =============================================================================
# Value Metrics Endpoints
# =============================================================================


class ValueMetricResponse(BaseModel):
    """A single value metric with trend information."""

    name: str = Field(..., description="Field name (e.g., 'revenue')")
    label: str = Field(..., description="Human-readable label (e.g., 'Revenue')")
    current_value: str | float | int | None = Field(None, description="Current display value")
    previous_value: str | float | int | None = Field(None, description="Previous value")
    change_percent: float | None = Field(None, description="Percentage change")
    trend_direction: str = Field("stable", description="Trend: improving/worsening/stable")
    metric_type: str = Field("neutral", description="higher_is_better/lower_is_better/neutral")
    last_updated: datetime | None = Field(None, description="When metric was last updated")
    is_positive_change: bool | None = Field(None, description="True if change is good")


class ValueMetricsResponse(BaseModel):
    """Response for value metrics endpoint."""

    metrics: list[ValueMetricResponse] = Field(
        default_factory=list, description="List of value metrics"
    )
    has_context: bool = Field(False, description="Whether user has business context")
    has_history: bool = Field(False, description="Whether metrics have historical data")


@router.get(
    "/value-metrics",
    summary="Get user's key value metrics with trends",
    description="""
    Get the user's key business metrics from their context with trend indicators.

    Returns up to 5 key metrics (revenue, customers, growth, etc.) along with:
    - Current and previous values
    - Percentage change
    - Trend direction (improving/worsening/stable)
    - Color coding guidance (is_positive_change)

    **Use Cases:**
    - Dashboard value metrics panel
    - Show business health at a glance
    - Track metric improvements over time

    **Empty State:**
    If `has_context` is false, display a prompt to set up business context.
    If `has_history` is false, trends will show as "insufficient_data".
    """,
    response_model=ValueMetricsResponse,
    responses={
        200: {
            "description": "Value metrics retrieved successfully",
            "content": {
                "application/json": {
                    "examples": {
                        "with_metrics": {
                            "summary": "User with metrics",
                            "value": {
                                "metrics": [
                                    {
                                        "name": "revenue",
                                        "label": "Revenue",
                                        "current_value": "$50K",
                                        "previous_value": "$45K",
                                        "change_percent": 11.1,
                                        "trend_direction": "improving",
                                        "metric_type": "higher_is_better",
                                        "is_positive_change": True,
                                    }
                                ],
                                "has_context": True,
                                "has_history": True,
                            },
                        },
                        "no_context": {
                            "summary": "User without context",
                            "value": {
                                "metrics": [],
                                "has_context": False,
                                "has_history": False,
                            },
                        },
                    }
                }
            },
        },
    },
)
async def get_value_metrics(
    user: dict[str, Any] = Depends(get_current_user),
) -> ValueMetricsResponse:
    """Get user's key business metrics with trend information."""
    from backend.services.value_metrics import extract_value_metrics
    from bo1.state.repositories import user_repository

    user_id = user["user_id"]

    try:
        # Load user's business context
        context_data = user_repository.get_context(user_id)

        # Extract value metrics
        result = extract_value_metrics(context_data, max_metrics=5)

        # Convert to response model
        metrics = [
            ValueMetricResponse(
                name=m.name,
                label=m.label,
                current_value=m.current_value,
                previous_value=m.previous_value,
                change_percent=m.change_percent,
                trend_direction=m.trend_direction,
                metric_type=m.metric_type,
                last_updated=m.last_updated,
                is_positive_change=m.is_positive_change,
            )
            for m in result.metrics
        ]

        return ValueMetricsResponse(
            metrics=metrics,
            has_context=result.has_context,
            has_history=result.has_history,
        )

    except Exception as e:
        # Log but return empty metrics instead of 500 - graceful degradation
        log_error(
            logger,
            ErrorCode.SERVICE_EXECUTION_ERROR,
            f"Failed to get value metrics for {user_id}: {e}",
            user_id=user_id,
        )
        return ValueMetricsResponse(metrics=[], has_context=False, has_history=False)


# =============================================================================
# Data Retention Reminder Settings
# =============================================================================


class RetentionReminderSettingsResponse(BaseModel):
    """Response for retention reminder settings endpoint."""

    deletion_reminder_suppressed: bool = Field(
        ..., description="Whether deletion reminder emails are suppressed"
    )
    last_deletion_reminder_sent_at: datetime | None = Field(
        None, description="When last reminder was sent"
    )


@router.get(
    "/retention-reminder/settings",
    summary="Get retention reminder settings",
    description="Get the user's retention reminder email preferences.",
    response_model=RetentionReminderSettingsResponse,
    responses={
        200: {"description": "Current settings"},
        500: {"description": "Failed to get settings", "model": ErrorResponse},
    },
)
async def get_retention_reminder_settings(
    user: dict[str, Any] = Depends(get_current_user),
) -> RetentionReminderSettingsResponse:
    """Get user's retention reminder email settings."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT deletion_reminder_suppressed, last_deletion_reminder_sent_at
                    FROM users WHERE id = %s
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                return RetentionReminderSettingsResponse(
                    deletion_reminder_suppressed=row.get("deletion_reminder_suppressed", False)
                    or False,
                    last_deletion_reminder_sent_at=row.get("last_deletion_reminder_sent_at"),
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to get retention reminder settings for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to get settings") from e


@router.post(
    "/retention-reminder/suppress",
    summary="Suppress retention reminder emails",
    description="""
    Suppress future data retention reminder emails.

    Users can turn off reminder emails about upcoming data deletion.
    This does not affect the actual data retention policy - data will
    still be deleted according to the configured retention period.
    """,
    response_model=RetentionReminderSettingsResponse,
    responses={
        200: {"description": "Reminders suppressed"},
        500: {"description": "Failed to update setting", "model": ErrorResponse},
    },
)
async def suppress_retention_reminders(
    request: Request,
    user: dict[str, Any] = Depends(get_current_user),
) -> RetentionReminderSettingsResponse:
    """Suppress retention reminder emails for the user."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET deletion_reminder_suppressed = true, updated_at = NOW()
                    WHERE id = %s
                    RETURNING deletion_reminder_suppressed, last_deletion_reminder_sent_at
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(f"User {user_id} suppressed retention reminders")
                return RetentionReminderSettingsResponse(
                    deletion_reminder_suppressed=True,
                    last_deletion_reminder_sent_at=row.get("last_deletion_reminder_sent_at"),
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to suppress retention reminders for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update setting") from e


@router.post(
    "/retention-reminder/enable",
    summary="Enable retention reminder emails",
    description="Re-enable data retention reminder emails after suppressing them.",
    response_model=RetentionReminderSettingsResponse,
    responses={
        200: {"description": "Reminders enabled"},
        500: {"description": "Failed to update setting", "model": ErrorResponse},
    },
)
async def enable_retention_reminders(
    user: dict[str, Any] = Depends(get_current_user),
) -> RetentionReminderSettingsResponse:
    """Re-enable retention reminder emails for the user."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE users
                    SET deletion_reminder_suppressed = false, updated_at = NOW()
                    WHERE id = %s
                    RETURNING deletion_reminder_suppressed, last_deletion_reminder_sent_at
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(f"User {user_id} enabled retention reminders")
                return RetentionReminderSettingsResponse(
                    deletion_reminder_suppressed=False,
                    last_deletion_reminder_sent_at=row.get("last_deletion_reminder_sent_at"),
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to enable retention reminders for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to update setting") from e


@router.post(
    "/retention-reminder/acknowledge",
    summary="Acknowledge retention reminder",
    description="""
    Acknowledge the retention reminder (user understands data will be deleted).

    This resets the reminder timer without changing any settings.
    The user won't receive another reminder for the minimum interval period.
    """,
    response_model=RetentionReminderSettingsResponse,
    responses={
        200: {"description": "Reminder acknowledged"},
        500: {"description": "Failed to acknowledge", "model": ErrorResponse},
    },
)
async def acknowledge_retention_reminder(
    user: dict[str, Any] = Depends(get_current_user),
) -> RetentionReminderSettingsResponse:
    """Acknowledge retention reminder (resets reminder timer)."""
    user_id = user["user_id"]

    try:
        with db_session() as conn:
            with conn.cursor() as cur:
                # Just update the last sent timestamp to delay next reminder
                cur.execute(
                    """
                    UPDATE users
                    SET last_deletion_reminder_sent_at = NOW(), updated_at = NOW()
                    WHERE id = %s
                    RETURNING deletion_reminder_suppressed, last_deletion_reminder_sent_at
                    """,
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(f"User {user_id} acknowledged retention reminder")
                return RetentionReminderSettingsResponse(
                    deletion_reminder_suppressed=row.get("deletion_reminder_suppressed", False)
                    or False,
                    last_deletion_reminder_sent_at=row.get("last_deletion_reminder_sent_at"),
                )

    except HTTPException:
        raise
    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_WRITE_ERROR,
            f"Failed to acknowledge retention reminder for {user_id}: {e}",
            user_id=user_id,
        )
        raise HTTPException(status_code=500, detail="Failed to acknowledge") from e
