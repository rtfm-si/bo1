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
from backend.api.models import ErrorResponse
from backend.services.audit import (
    get_recent_deletion_request,
    get_recent_export_request,
    log_gdpr_event,
)
from backend.services.gdpr import GDPRError, collect_user_data, delete_user_data
from backend.services.usage_tracking import get_all_usage, get_effective_tier
from bo1.constants import TierFeatureFlags, TierLimits
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/user", tags=["user"])


# Data retention models
class RetentionSettingResponse(BaseModel):
    """Response for retention setting endpoint."""

    data_retention_days: int = Field(
        ..., ge=365, le=3650, description="Data retention period in days (1-10 years)"
    )


class RetentionSettingUpdate(BaseModel):
    """Request body for updating retention setting."""

    days: int = Field(..., ge=365, le=3650, description="Data retention period (365-3650 days)")


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
        logger.error(f"Failed to record GDPR consent for {user_id}: {e}")
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
        logger.error(f"GDPR export failed for {user_id}: {e}")
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
        logger.error(f"GDPR deletion failed for {user_id}: {e}")
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
                    retention_days = 365  # Default fallback

                return RetentionSettingResponse(data_retention_days=retention_days)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get retention setting for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to get setting") from e


@router.patch(
    "/retention",
    summary="Update data retention setting",
    description="""
    Update the user's data retention period.

    Valid range: 365-3650 days (1 year to 10 years).

    - Minimum 1 year ensures data is available for annual reviews
    - Maximum 10 years for enterprise compliance needs

    Note: Changing to a shorter period does not immediately delete data.
    The scheduled cleanup job will remove data past the new retention period
    during its next run.
    """,
    response_model=RetentionSettingResponse,
    responses={
        200: {"description": "Retention setting updated"},
        422: {"description": "Invalid retention period (must be 365-3650 days)"},
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
        logger.error(f"Failed to update retention setting for {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to update setting") from e


# Meeting preferences models
class PreferencesResponse(BaseModel):
    """Response for user preferences endpoint."""

    skip_clarification: bool = Field(
        default=False, description="Skip pre-meeting clarifying questions by default"
    )


class PreferencesUpdate(BaseModel):
    """Request body for updating user preferences."""

    skip_clarification: bool | None = Field(
        default=None, description="Skip pre-meeting clarifying questions by default"
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
                    "SELECT skip_clarification FROM users WHERE id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                return PreferencesResponse(
                    skip_clarification=row.get("skip_clarification", False) or False
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get preferences for {user_id}: {e}")
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
                    RETURNING skip_clarification
                    """,
                    params,
                )
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="User not found")

                logger.info(
                    f"Updated preferences for {user_id}: skip_clarification={row.get('skip_clarification')}"
                )
                return PreferencesResponse(
                    skip_clarification=row.get("skip_clarification", False) or False
                )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update preferences for {user_id}: {e}")
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
        logger.error(f"Failed to get Gantt color preference for {user_id}: {e}")
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
        logger.error(f"Failed to update Gantt color preference for {user_id}: {e}")
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
        logger.error(f"Failed to get usage for {user_id}: {e}")
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
