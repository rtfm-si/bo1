"""Activities by date endpoint for heatmap tooltip detail."""

import logging
from datetime import date, datetime

from fastapi import APIRouter, Query

from backend.api.models import ActivityItem, DateActivitiesResponse, ErrorResponse
from backend.api.utils.db_helpers import execute_query
from backend.api.utils.errors import handle_api_errors
from backend.api.utils.openapi_security import SessionAuthDep

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/activities")


@router.get(
    "/by-date",
    response_model=DateActivitiesResponse,
    summary="Get activities for a specific date",
    description="Returns individual activity items for a given date, used by heatmap tooltips.",
    responses={
        200: {"description": "Activities retrieved"},
        401: {"description": "Not authenticated", "model": ErrorResponse},
    },
)
@handle_api_errors("get activities by date")
async def get_activities_by_date(
    user_data: SessionAuthDep,
    target_date: date = Query(..., alias="date", description="Date in YYYY-MM-DD format"),
) -> DateActivitiesResponse:
    """Get all activity items for a specific date."""
    user_id = user_data.get("user_id")
    date_str = target_date.isoformat()

    activities: list[ActivityItem] = []

    # Sessions created on this date
    session_rows = execute_query(
        """
        SELECT id, problem_statement, created_at
        FROM sessions
        WHERE user_id = %s AND DATE(created_at) = %s
        ORDER BY created_at
        """,
        (user_id, date_str),
        fetch="all",
    )
    for row in session_rows or []:
        activities.append(
            ActivityItem(
                id=str(row["id"]),
                type="session",
                title=row["problem_statement"][:100] if row["problem_statement"] else "Meeting",
                url=f"/meeting/{row['id']}",
                timestamp=row["created_at"].isoformat()
                if isinstance(row["created_at"], datetime)
                else None,
            )
        )

    # Actions completed on this date
    completed_rows = execute_query(
        """
        SELECT id, title, actual_end_date
        FROM actions
        WHERE user_id = %s
          AND status IN ('done', 'cancelled')
          AND DATE(actual_end_date) = %s
          AND deleted_at IS NULL
        ORDER BY actual_end_date
        """,
        (user_id, date_str),
        fetch="all",
    )
    for row in completed_rows or []:
        activities.append(
            ActivityItem(
                id=str(row["id"]),
                type="action_completed",
                title=row["title"] or "Action completed",
                url=f"/actions/{row['id']}",
            )
        )

    # Actions started on this date
    started_rows = execute_query(
        """
        SELECT id, title, actual_start_date
        FROM actions
        WHERE user_id = %s
          AND DATE(actual_start_date) = %s
          AND deleted_at IS NULL
        ORDER BY actual_start_date
        """,
        (user_id, date_str),
        fetch="all",
    )
    for row in started_rows or []:
        activities.append(
            ActivityItem(
                id=str(row["id"]),
                type="action_started",
                title=row["title"] or "Action started",
                url=f"/actions/{row['id']}",
            )
        )

    # Mentor sessions on this date
    mentor_rows = execute_query(
        """
        SELECT period, count
        FROM user_usage
        WHERE user_id = %s
          AND metric = 'mentor_chats'
          AND period = %s
        """,
        (user_id, date_str),
        fetch="all",
    )
    for row in mentor_rows or []:
        count = row["count"] if row["count"] else 1
        for i in range(count):
            activities.append(
                ActivityItem(
                    id=f"mentor-{date_str}-{i}",
                    type="mentor_session",
                    title="Advisor session",
                    url="/advisor",
                )
            )

    # Future planned starts
    planned_start_rows = execute_query(
        """
        SELECT id, title, COALESCE(target_start_date, estimated_start_date) AS start_date
        FROM actions
        WHERE user_id = %s
          AND DATE(COALESCE(target_start_date, estimated_start_date)) = %s
          AND actual_start_date IS NULL
          AND status NOT IN ('done', 'cancelled')
          AND deleted_at IS NULL
        ORDER BY title
        """,
        (user_id, date_str),
        fetch="all",
    )
    for row in planned_start_rows or []:
        activities.append(
            ActivityItem(
                id=str(row["id"]),
                type="planned_start",
                title=row["title"] or "Planned start",
                url=f"/actions/{row['id']}",
            )
        )

    # Future planned completions (due dates)
    planned_due_rows = execute_query(
        """
        SELECT id, title, COALESCE(target_end_date, estimated_end_date) AS due_date
        FROM actions
        WHERE user_id = %s
          AND DATE(COALESCE(target_end_date, estimated_end_date)) = %s
          AND status NOT IN ('done', 'cancelled')
          AND deleted_at IS NULL
        ORDER BY title
        """,
        (user_id, date_str),
        fetch="all",
    )
    for row in planned_due_rows or []:
        activities.append(
            ActivityItem(
                id=str(row["id"]),
                type="planned_due",
                title=row["title"] or "Due date",
                subtitle="Due",
                url=f"/actions/{row['id']}",
            )
        )

    logger.info(f"Found {len(activities)} activities for user {user_id} on {date_str}")

    return DateActivitiesResponse(
        date=date_str,
        activities=activities,
        total=len(activities),
    )
