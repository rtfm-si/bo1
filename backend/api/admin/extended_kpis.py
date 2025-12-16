"""Admin API endpoints for extended KPIs.

Provides:
- GET /api/admin/extended-kpis - Get extended KPI metrics
"""

from fastapi import APIRouter, Depends

from backend.api.admin.models import (
    ActionStats,
    DataAnalysisStats,
    ExtendedKPIsResponse,
    MentorSessionStats,
    ProjectStats,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.models import ErrorResponse
from backend.api.utils.errors import handle_api_errors
from bo1.state.database import db_session
from bo1.utils.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="", tags=["Admin - Extended KPIs"])


def get_mentor_session_stats() -> MentorSessionStats:
    """Get mentor session statistics from user_usage table."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COALESCE(SUM(count), 0) AS total_sessions,
                    COALESCE(SUM(CASE WHEN created_at::date = CURRENT_DATE THEN count ELSE 0 END), 0) AS today,
                    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '7 days' THEN count ELSE 0 END), 0) AS week,
                    COALESCE(SUM(CASE WHEN created_at >= CURRENT_DATE - INTERVAL '30 days' THEN count ELSE 0 END), 0) AS month
                FROM user_usage
                WHERE metric = 'mentor_chats'
                """
            )
            row = cur.fetchone()
            return MentorSessionStats(
                total_sessions=row["total_sessions"],
                sessions_today=row["today"],
                sessions_this_week=row["week"],
                sessions_this_month=row["month"],
            )


def get_data_analysis_stats() -> DataAnalysisStats:
    """Get dataset analysis statistics from dataset_analyses table."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_analyses,
                    COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE) AS today,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days') AS week,
                    COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days') AS month
                FROM dataset_analyses
                """
            )
            row = cur.fetchone()
            return DataAnalysisStats(
                total_analyses=row["total_analyses"],
                analyses_today=row["today"],
                analyses_this_week=row["week"],
                analyses_this_month=row["month"],
            )


def get_project_stats() -> ProjectStats:
    """Get project statistics grouped by status."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_projects,
                    COUNT(*) FILTER (WHERE status = 'active') AS active,
                    COUNT(*) FILTER (WHERE status = 'paused') AS paused,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'archived') AS archived
                FROM projects
                """
            )
            row = cur.fetchone()
            return ProjectStats(
                total_projects=row["total_projects"],
                active=row["active"],
                paused=row["paused"],
                completed=row["completed"],
                archived=row["archived"],
            )


def get_action_stats() -> ActionStats:
    """Get action statistics grouped by status."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_actions,
                    COUNT(*) FILTER (WHERE status = 'pending') AS pending,
                    COUNT(*) FILTER (WHERE status = 'in_progress') AS in_progress,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed,
                    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled
                FROM actions
                """
            )
            row = cur.fetchone()
            return ActionStats(
                total_actions=row["total_actions"],
                pending=row["pending"],
                in_progress=row["in_progress"],
                completed=row["completed"],
                cancelled=row["cancelled"],
            )


@router.get(
    "/extended-kpis",
    response_model=ExtendedKPIsResponse,
    summary="Get extended KPIs",
    description="""
    Get extended KPI metrics for the admin dashboard.

    Returns:
    - Mentor session stats (total, today, week, month)
    - Dataset analysis stats (total, today, week, month)
    - Project stats by status (active, paused, completed, archived)
    - Action stats by status (pending, in_progress, completed, cancelled)
    """,
    responses={
        200: {"description": "Extended KPIs retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@handle_api_errors("get extended KPIs")
async def get_extended_kpis(
    _admin: str = Depends(require_admin_any),
) -> ExtendedKPIsResponse:
    """Get extended KPI metrics (admin only)."""
    logger.info("Admin: Fetching extended KPIs")

    return ExtendedKPIsResponse(
        mentor_sessions=get_mentor_session_stats(),
        data_analyses=get_data_analysis_stats(),
        projects=get_project_stats(),
        actions=get_action_stats(),
    )
