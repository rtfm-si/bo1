"""Admin API endpoints for extended KPIs.

Provides:
- GET /api/admin/extended-kpis - Get extended KPI metrics
"""

from fastapi import APIRouter, Depends, Request

from backend.api.admin.models import (
    ActionStats,
    DataAnalysisStats,
    ExperimentMetricsResponse,
    ExperimentVariantStats,
    ExtendedKPIsResponse,
    MeetingStats,
    MentorSessionStats,
    ProjectStats,
)
from backend.api.middleware.admin import require_admin_any
from backend.api.middleware.rate_limit import ADMIN_RATE_LIMIT, limiter
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
                    COUNT(*) FILTER (WHERE status = 'archived') AS archived,
                    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted
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
                deleted=row["deleted"],
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
                    COUNT(*) FILTER (WHERE status = 'cancelled') AS cancelled,
                    COUNT(*) FILTER (WHERE deleted_at IS NOT NULL) AS deleted
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
                deleted=row["deleted"],
            )


def get_meeting_stats() -> MeetingStats:
    """Get meeting/session statistics grouped by status."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS total_meetings,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'created'), 0) AS created,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'running'), 0) AS running,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'completed'), 0) AS completed,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'failed'), 0) AS failed,
                    COALESCE(COUNT(*) FILTER (WHERE status = 'killed'), 0) AS killed,
                    0 AS deleted,  -- sessions don't support soft-delete
                    COALESCE(COUNT(*) FILTER (WHERE created_at::date = CURRENT_DATE), 0) AS today,
                    COALESCE(COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '7 days'), 0) AS week,
                    COALESCE(COUNT(*) FILTER (WHERE created_at >= CURRENT_DATE - INTERVAL '30 days'), 0) AS month
                FROM sessions
                """
            )
            row = cur.fetchone()
            return MeetingStats(
                total_meetings=row["total_meetings"],
                created=row["created"],
                running=row["running"],
                completed=row["completed"],
                failed=row["failed"],
                killed=row["killed"],
                deleted=row["deleted"],
                meetings_today=row["today"],
                meetings_this_week=row["week"],
                meetings_this_month=row["month"],
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
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get extended KPIs")
async def get_extended_kpis(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> ExtendedKPIsResponse:
    """Get extended KPI metrics (admin only)."""
    logger.info("Admin: Fetching extended KPIs")

    return ExtendedKPIsResponse(
        mentor_sessions=get_mentor_session_stats(),
        data_analyses=get_data_analysis_stats(),
        projects=get_project_stats(),
        actions=get_action_stats(),
        meetings=get_meeting_stats(),
    )


def get_persona_count_experiment_metrics() -> list[ExperimentVariantStats]:
    """Get metrics for persona count A/B experiment (3 vs 5 personas)."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    persona_count_variant AS variant,
                    COUNT(*) AS session_count,
                    COUNT(*) FILTER (WHERE status = 'completed') AS completed_count,
                    AVG(total_cost) FILTER (WHERE status = 'completed') AS avg_cost,
                    AVG(EXTRACT(EPOCH FROM (updated_at - created_at)))
                        FILTER (WHERE status = 'completed') AS avg_duration_seconds,
                    AVG(round_number) FILTER (WHERE status = 'completed') AS avg_rounds,
                    AVG(expert_count) FILTER (WHERE status = 'completed') AS avg_persona_count
                FROM sessions
                WHERE persona_count_variant IS NOT NULL
                GROUP BY persona_count_variant
                ORDER BY persona_count_variant
                """
            )
            rows = cur.fetchall()

            variants = []
            for row in rows:
                session_count = row["session_count"]
                completed_count = row["completed_count"]
                completion_rate = (
                    (completed_count / session_count * 100) if session_count > 0 else 0
                )

                variants.append(
                    ExperimentVariantStats(
                        variant=row["variant"],
                        session_count=session_count,
                        completed_count=completed_count,
                        avg_cost=round(row["avg_cost"], 4) if row["avg_cost"] else None,
                        avg_duration_seconds=(
                            round(row["avg_duration_seconds"], 1)
                            if row["avg_duration_seconds"]
                            else None
                        ),
                        avg_rounds=round(row["avg_rounds"], 1) if row["avg_rounds"] else None,
                        avg_persona_count=(
                            round(row["avg_persona_count"], 1) if row["avg_persona_count"] else None
                        ),
                        completion_rate=round(completion_rate, 1),
                    )
                )
            return variants


@router.get(
    "/experiments/persona-count",
    response_model=ExperimentMetricsResponse,
    summary="Get persona count A/B experiment metrics",
    description="""
    Get metrics for the persona count A/B experiment (3 vs 5 personas).

    Returns:
    - Session counts per variant
    - Average cost per session
    - Average duration and rounds
    - Completion rates
    """,
    responses={
        200: {"description": "Experiment metrics retrieved successfully"},
        500: {"description": "Internal server error", "model": ErrorResponse},
    },
)
@limiter.limit(ADMIN_RATE_LIMIT)
@handle_api_errors("get experiment metrics")
async def get_persona_count_experiment(
    request: Request,
    _admin: str = Depends(require_admin_any),
) -> ExperimentMetricsResponse:
    """Get persona count A/B experiment metrics (admin only)."""
    from datetime import UTC, datetime

    logger.info("Admin: Fetching persona count experiment metrics")

    variants = get_persona_count_experiment_metrics()
    total_sessions = sum(v.session_count for v in variants)

    # Get experiment period (first and last session with variant)
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    MIN(created_at) AS period_start,
                    MAX(created_at) AS period_end
                FROM sessions
                WHERE persona_count_variant IS NOT NULL
                """
            )
            row = cur.fetchone()
            period_start = (
                row["period_start"].isoformat()
                if row["period_start"]
                else datetime.now(UTC).isoformat()
            )
            period_end = (
                row["period_end"].isoformat()
                if row["period_end"]
                else datetime.now(UTC).isoformat()
            )

    return ExperimentMetricsResponse(
        experiment_name="persona_count",
        variants=variants,
        total_sessions=total_sessions,
        period_start=period_start,
        period_end=period_end,
    )
