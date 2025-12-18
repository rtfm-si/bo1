"""Action repository for action management operations.

Handles:
- Action CRUD operations
- Status updates and transitions
- Date management
- Dependency tracking
- Activity feed (action updates)
"""

import logging
from collections import deque
from datetime import date, datetime
from typing import Any, cast
from uuid import UUID

from backend.api.models import ActionVariance
from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository
from bo1.utils.timeline_parser import add_business_days, parse_timeline

logger = logging.getLogger(__name__)


class ActionRepository(BaseRepository):
    """Repository for action management operations."""

    # =========================================================================
    # Action CRUD
    # =========================================================================

    def create(
        self,
        user_id: str,
        source_session_id: str,
        title: str,
        description: str,
        what_and_how: list[str] | None = None,
        success_criteria: list[str] | None = None,
        kill_criteria: list[str] | None = None,
        status: str = "todo",
        priority: str = "medium",
        category: str = "implementation",
        timeline: str | None = None,
        estimated_duration_days: int | None = None,
        target_start_date: date | None = None,
        target_end_date: date | None = None,
        confidence: float = 0.0,
        source_section: str | None = None,
        sub_problem_index: int | None = None,
        sort_order: int = 0,
    ) -> dict[str, Any]:
        """Create a new action.

        Args:
            user_id: User who owns the action
            source_session_id: Session this action came from
            title: Short action title
            description: Full action description
            what_and_how: Steps to complete (optional)
            success_criteria: Success measures (optional)
            kill_criteria: Abandonment conditions (optional)
            status: Initial status (default: 'todo')
            priority: Priority level (default: 'medium')
            category: Action category (default: 'implementation')
            timeline: Human-readable timeline (optional)
            estimated_duration_days: Duration in business days (optional)
            target_start_date: User-set target start (optional)
            target_end_date: User-set target end (optional)
            confidence: AI confidence score (default: 0.0)
            source_section: Source synthesis section (optional)
            sub_problem_index: Sub-problem index (optional)
            sort_order: Sort order within status (default: 0)

        Returns:
            Created action record with all fields including generated ID
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO actions (
                        user_id, source_session_id, title, description,
                        what_and_how, success_criteria, kill_criteria,
                        status, priority, category,
                        timeline, estimated_duration_days,
                        target_start_date, target_end_date,
                        confidence, source_section, sub_problem_index,
                        sort_order
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, source_session_id, project_id, title, description,
                              what_and_how, success_criteria, kill_criteria,
                              status, priority, category,
                              timeline, estimated_duration_days,
                              target_start_date, target_end_date,
                              estimated_start_date, estimated_end_date,
                              actual_start_date, actual_end_date,
                              blocking_reason, blocked_at, auto_unblock,
                              replan_session_id, replan_requested_at, replanning_reason,
                              cancellation_reason, cancelled_at,
                              confidence, source_section, sub_problem_index,
                              sort_order, created_at, updated_at
                    """,
                    (
                        user_id,
                        source_session_id,
                        title,
                        description,
                        what_and_how or [],
                        success_criteria or [],
                        kill_criteria or [],
                        status,
                        priority,
                        category,
                        timeline,
                        estimated_duration_days,
                        target_start_date,
                        target_end_date,
                        confidence,
                        source_section,
                        sub_problem_index,
                        sort_order,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get(self, action_id: str | UUID) -> dict[str, Any] | None:
        """Get a single action by ID.

        Args:
            action_id: Action UUID

        Returns:
            Action record with all fields, or None if not found
        """
        return self._execute_one(
            """
            SELECT id, user_id, source_session_id, project_id, title, description,
                   what_and_how, success_criteria, kill_criteria,
                   status, priority, category,
                   timeline, estimated_duration_days,
                   target_start_date, target_end_date,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   blocking_reason, blocked_at, auto_unblock,
                   replan_session_id, replan_requested_at, replanning_reason,
                   cancellation_reason, cancelled_at,
                   confidence, source_section, sub_problem_index,
                   sort_order, created_at, updated_at
            FROM actions
            WHERE id = %s
            """,
            (str(action_id),),
        )

    def get_by_user(
        self,
        user_id: str,
        status_filter: str | None = None,
        project_id: str | None = None,
        session_id: str | None = None,
        tag_ids: list[str] | None = None,
        limit: int = 100,
        offset: int = 0,
        is_admin: bool = False,
    ) -> list[dict[str, Any]]:
        """Get all actions for a user with optional filtering.

        Args:
            user_id: User identifier
            status_filter: Filter by status (optional)
            project_id: Filter by project (optional)
            session_id: Filter by source session/meeting (optional)
            tag_ids: Filter by tags - actions must have ALL specified tags (optional)
            limit: Maximum actions to return (default: 100)
            offset: Number of actions to skip
            is_admin: If True, show actions from all sessions; otherwise only completed

        Returns:
            List of action records
        """
        query = """
            SELECT DISTINCT a.id, a.user_id, a.source_session_id, a.project_id, a.title, a.description,
                   a.what_and_how, a.success_criteria, a.kill_criteria,
                   a.status, a.priority, a.category,
                   a.timeline, a.estimated_duration_days,
                   a.target_start_date, a.target_end_date,
                   a.estimated_start_date, a.estimated_end_date,
                   a.actual_start_date, a.actual_end_date,
                   a.blocking_reason, a.blocked_at, a.auto_unblock,
                   a.replan_session_id, a.replan_requested_at, a.replanning_reason,
                   a.cancellation_reason, a.cancelled_at,
                   a.confidence, a.source_section, a.sub_problem_index,
                   a.sort_order, a.created_at, a.updated_at
            FROM actions a
            LEFT JOIN sessions s ON a.source_session_id = s.id
            WHERE a.user_id = %s
        """
        params: list[Any] = [user_id]

        # P1-007: Only show actions from completed or acknowledged-failed meetings
        # Actions from failed meetings become visible once user acknowledges the failure
        if not is_admin:
            query += """ AND (
                s.status = 'completed'
                OR s.id IS NULL
                OR (s.status = 'failed' AND s.failure_acknowledged_at IS NOT NULL)
            )"""

        # P1-005: Exclude soft-deleted actions for non-admin users
        if not is_admin:
            query += " AND a.deleted_at IS NULL"

        if status_filter:
            query += " AND a.status = %s"
            params.append(status_filter)

        if project_id:
            query += " AND a.project_id = %s"
            params.append(project_id)

        if session_id:
            query += " AND a.source_session_id = %s"
            params.append(session_id)

        if tag_ids:
            # Filter actions that have ALL specified tags (AND logic)
            query += """
                AND a.id IN (
                    SELECT at.action_id
                    FROM action_tags at
                    WHERE at.tag_id = ANY(%s)
                    GROUP BY at.action_id
                    HAVING COUNT(DISTINCT at.tag_id) = %s
                )
            """
            params.extend([tag_ids, len(tag_ids)])

        query += " ORDER BY a.sort_order ASC, a.created_at DESC LIMIT %s OFFSET %s"
        params.extend([limit, offset])

        return self._execute_query(query, tuple(params))

    def get_by_session(
        self,
        session_id: str,
        status_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get all actions for a session.

        Args:
            session_id: Session identifier
            status_filter: Filter by status (optional)

        Returns:
            List of action records
        """
        query = """
            SELECT id, user_id, source_session_id, project_id, title, description,
                   what_and_how, success_criteria, kill_criteria,
                   status, priority, category,
                   timeline, estimated_duration_days,
                   target_start_date, target_end_date,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   blocking_reason, blocked_at, auto_unblock,
                   replan_session_id, replan_requested_at, replanning_reason,
                   cancellation_reason, cancelled_at,
                   confidence, source_section, sub_problem_index,
                   sort_order, created_at, updated_at
            FROM actions
            WHERE source_session_id = %s
        """
        params: list[Any] = [session_id]

        if status_filter:
            query += " AND status = %s"
            params.append(status_filter)

        query += " ORDER BY sort_order ASC, created_at ASC"

        return self._execute_query(query, tuple(params))

    def update_status(
        self,
        action_id: str | UUID,
        status: str,
        user_id: str,
        blocking_reason: str | None = None,
        auto_unblock: bool = False,
        cancellation_reason: str | None = None,
        failure_reason_category: str | None = None,
        replan_suggested_at: datetime | None = None,
    ) -> bool:
        """Update action status.

        Args:
            action_id: Action UUID
            status: New status
            user_id: User making the update
            blocking_reason: Reason for blocking (if status is 'blocked')
            auto_unblock: Auto-unblock when dependencies complete
            cancellation_reason: Reason for cancellation (if status is 'cancelled')
            failure_reason_category: Category of failure (blocker/scope_creep/dependency/unknown)
            replan_suggested_at: When replanning suggestion was shown

        Returns:
            True if updated successfully
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get old status for audit
                cur.execute("SELECT status FROM actions WHERE id = %s", (str(action_id),))
                row = cur.fetchone()
                if not row:
                    return False
                old_status = row["status"]

                # Update action based on target status
                if status == "blocked":
                    cur.execute(
                        """
                        UPDATE actions
                        SET status = %s,
                            blocking_reason = %s,
                            blocked_at = NOW(),
                            auto_unblock = %s,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (status, blocking_reason, auto_unblock, str(action_id)),
                    )
                elif status == "cancelled":
                    cur.execute(
                        """
                        UPDATE actions
                        SET status = %s,
                            cancellation_reason = %s,
                            cancelled_at = NOW(),
                            failure_reason_category = %s,
                            replan_suggested_at = COALESCE(%s, NOW()),
                            blocking_reason = NULL,
                            blocked_at = NULL,
                            auto_unblock = false,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (
                            status,
                            cancellation_reason,
                            failure_reason_category,
                            replan_suggested_at,
                            str(action_id),
                        ),
                    )
                elif status in ("failed", "abandoned"):
                    # Terminal closure states - use closure_reason column
                    cur.execute(
                        """
                        UPDATE actions
                        SET status = %s,
                            closure_reason = %s,
                            cancelled_at = NOW(),
                            blocking_reason = NULL,
                            blocked_at = NULL,
                            auto_unblock = false,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (
                            status,
                            cancellation_reason,  # reuse cancellation_reason param for closure
                            str(action_id),
                        ),
                    )
                else:
                    # Clear blocking and cancellation fields when transitioning to other statuses
                    cur.execute(
                        """
                        UPDATE actions
                        SET status = %s,
                            blocking_reason = NULL,
                            blocked_at = NULL,
                            auto_unblock = false,
                            cancellation_reason = NULL,
                            cancelled_at = NULL,
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (status, str(action_id)),
                    )

                success = bool(cur.rowcount and cur.rowcount > 0)

                # Create audit record
                if success:
                    content = f"Status changed from {old_status} to {status}"
                    if status in ("cancelled", "failed", "abandoned") and cancellation_reason:
                        content += f": {cancellation_reason}"
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type,
                            content, old_status, new_status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(action_id),
                            user_id,
                            "status_change",
                            content,
                            old_status,
                            status,
                        ),
                    )

                return success

    def update_dates(
        self,
        action_id: str | UUID,
        user_id: str,
        target_start_date: date | None = None,
        target_end_date: date | None = None,
        estimated_start_date: date | None = None,
        estimated_end_date: date | None = None,
    ) -> bool:
        """Update action dates.

        Args:
            action_id: Action UUID
            user_id: User making the update
            target_start_date: User-set target start (optional)
            target_end_date: User-set target end (optional)
            estimated_start_date: Calculated start date (optional)
            estimated_end_date: Calculated end date (optional)

        Returns:
            True if updated successfully
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                update_fields = ["updated_at = NOW()"]
                params: list[Any] = []

                if target_start_date is not None:
                    update_fields.append("target_start_date = %s")
                    params.append(target_start_date)

                if target_end_date is not None:
                    update_fields.append("target_end_date = %s")
                    params.append(target_end_date)

                if estimated_start_date is not None:
                    update_fields.append("estimated_start_date = %s")
                    params.append(estimated_start_date)

                if estimated_end_date is not None:
                    update_fields.append("estimated_end_date = %s")
                    params.append(estimated_end_date)

                params.append(str(action_id))

                query = f"""
                    UPDATE actions
                    SET {", ".join(update_fields)}
                    WHERE id = %s
                """

                cur.execute(query, params)
                success = bool(cur.rowcount and cur.rowcount > 0)

                # Create audit record for significant date changes
                if success and (target_start_date or target_end_date):
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type,
                            content, date_field, new_date
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(action_id),
                            user_id,
                            "date_change",
                            "Target dates updated",
                            "target_dates",
                            target_start_date or target_end_date,
                        ),
                    )

                return success

    def start_action(self, action_id: str | UUID, user_id: str) -> bool:
        """Mark action as started (in_progress).

        Sets actual_start_date to current timestamp.

        Args:
            action_id: Action UUID
            user_id: User starting the action

        Returns:
            True if updated successfully
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET status = 'in_progress',
                        actual_start_date = NOW(),
                        updated_at = NOW()
                    WHERE id = %s AND status = 'todo'
                    """,
                    (str(action_id),),
                )
                success = bool(cur.rowcount and cur.rowcount > 0)

                if success:
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type, content
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (str(action_id), user_id, "progress", "Action started"),
                    )

                return success

    def complete_action(self, action_id: str | UUID, user_id: str) -> bool:
        """Mark action as completed.

        Sets actual_end_date to current timestamp and recalculates
        dependent action dates.

        Args:
            action_id: Action UUID
            user_id: User completing the action

        Returns:
            True if updated successfully
        """
        action_id_str = str(action_id)
        success = False

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE actions
                    SET status = 'done',
                        actual_end_date = NOW(),
                        updated_at = NOW()
                    WHERE id = %s AND status != 'done'
                    """,
                    (action_id_str,),
                )
                success = bool(cur.rowcount and cur.rowcount > 0)

                if success:
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type, content
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (action_id_str, user_id, "completion", "Action completed"),
                    )

        # After transaction commits, recalculate dates for dependent actions
        # Since this action now has an actual_end_date, dependents can update
        if success:
            self.recalculate_dates_cascade(action_id_str, user_id)

        return success

    def replan_action(
        self,
        action_id: str | UUID,
        user_id: str,
        new_steps: list[str] | None = None,
        new_target_date: date | None = None,
    ) -> dict[str, Any] | None:
        """Create a new action by replanning an existing failed/abandoned one.

        This method:
        1. Verifies the original action is in failed/abandoned status
        2. Creates a new action copying context from the original
        3. Links the new action to the original via replanned_from_id
        4. Marks the original action as 'replanned'

        Args:
            action_id: Original action UUID to replan
            user_id: User creating the replan
            new_steps: Optional new what_and_how steps (defaults to original)
            new_target_date: Optional new target end date

        Returns:
            New action record, or None if replan failed
        """
        action_id_str = str(action_id)

        # Get original action
        original = self.get(action_id_str)
        if not original:
            logger.warning(f"Replan failed: action {action_id_str} not found")
            return None

        # Verify ownership
        if original.get("user_id") != user_id:
            logger.warning(f"Replan failed: user {user_id} doesn't own action {action_id_str}")
            return None

        # Verify original is in a replannable state
        original_status = original.get("status", "")
        if original_status not in ("failed", "abandoned"):
            logger.warning(
                f"Replan failed: action {action_id_str} status '{original_status}' not replannable"
            )
            return None

        # Create new action with copied context
        new_action = None
        with db_session() as conn:
            with conn.cursor() as cur:
                # Create the new action
                cur.execute(
                    """
                    INSERT INTO actions (
                        user_id, source_session_id, project_id, title, description,
                        what_and_how, success_criteria, kill_criteria,
                        status, priority, category,
                        timeline, estimated_duration_days,
                        target_start_date, target_end_date,
                        confidence, source_section, sub_problem_index,
                        sort_order, replanned_from_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, source_session_id, project_id, title, description,
                              what_and_how, success_criteria, kill_criteria,
                              status, priority, category,
                              timeline, estimated_duration_days,
                              target_start_date, target_end_date,
                              estimated_start_date, estimated_end_date,
                              actual_start_date, actual_end_date,
                              replanned_from_id,
                              confidence, source_section, sub_problem_index,
                              sort_order, created_at, updated_at
                    """,
                    (
                        user_id,
                        original.get("source_session_id"),
                        original.get("project_id"),
                        original.get("title", ""),
                        original.get("description", ""),
                        new_steps or original.get("what_and_how", []),
                        original.get("success_criteria", []),
                        original.get("kill_criteria", []),
                        "todo",  # New action starts as todo
                        original.get("priority", "medium"),
                        original.get("category", "implementation"),
                        original.get("timeline"),
                        original.get("estimated_duration_days"),
                        date.today(),  # Start from today
                        new_target_date or original.get("target_end_date"),
                        original.get("confidence", 0.0),
                        original.get("source_section"),
                        original.get("sub_problem_index"),
                        original.get("sort_order", 0),
                        action_id_str,  # Link to original
                    ),
                )
                result = cur.fetchone()
                if result:
                    new_action = dict(result)

                    # Mark original as replanned
                    cur.execute(
                        """
                        UPDATE actions
                        SET status = 'replanned',
                            updated_at = NOW()
                        WHERE id = %s
                        """,
                        (action_id_str,),
                    )

                    # Create audit record for original
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type,
                            content, old_status, new_status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """,
                        (
                            action_id_str,
                            user_id,
                            "status_change",
                            f"Replanned to new action {new_action['id']}",
                            original_status,
                            "replanned",
                        ),
                    )

                    # Create audit record for new action
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type, content
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            str(new_action["id"]),
                            user_id,
                            "note",
                            f"Replanned from action {action_id_str}",
                        ),
                    )

        if new_action:
            logger.info(f"Created replanned action {new_action['id']} from {action_id_str}")

        return new_action

    def delete(self, action_id: str | UUID) -> bool:
        """Soft delete an action by setting deleted_at timestamp.

        Args:
            action_id: Action UUID

        Returns:
            True if soft deleted successfully
        """
        return (
            self._execute_count(
                "UPDATE actions SET deleted_at = NOW() WHERE id = %s AND deleted_at IS NULL",
                (str(action_id),),
            )
            > 0
        )

    def restore(self, action_id: str | UUID) -> bool:
        """Restore a soft-deleted action.

        Args:
            action_id: Action UUID

        Returns:
            True if restored successfully
        """
        return (
            self._execute_count(
                "UPDATE actions SET deleted_at = NULL WHERE id = %s AND deleted_at IS NOT NULL",
                (str(action_id),),
            )
            > 0
        )

    def hard_delete(self, action_id: str | UUID) -> bool:
        """Permanently delete an action (admin only).

        Args:
            action_id: Action UUID

        Returns:
            True if deleted successfully
        """
        return (
            self._execute_count(
                "DELETE FROM actions WHERE id = %s",
                (str(action_id),),
            )
            > 0
        )

    def soft_delete_by_session(self, session_id: str) -> int:
        """Soft delete all actions for a session (P1-006 cascade).

        Called when a meeting/session is soft-deleted.

        Args:
            session_id: Session UUID

        Returns:
            Number of actions soft-deleted
        """
        return self._execute_count(
            "UPDATE actions SET deleted_at = NOW() WHERE source_session_id = %s AND deleted_at IS NULL",
            (session_id,),
        )

    def restore_by_session(self, session_id: str) -> int:
        """Restore all soft-deleted actions for a session.

        Called when a meeting/session is restored (un-deleted).

        Args:
            session_id: Session UUID

        Returns:
            Number of actions restored
        """
        return self._execute_count(
            "UPDATE actions SET deleted_at = NULL WHERE source_session_id = %s AND deleted_at IS NOT NULL",
            (session_id,),
        )

    # =========================================================================
    # Action Updates (Activity Feed)
    # =========================================================================

    def add_update(
        self,
        action_id: str | UUID,
        user_id: str,
        update_type: str,
        content: str,
        progress_percent: int | None = None,
    ) -> dict[str, Any]:
        """Add an activity update for an action.

        Args:
            action_id: Action UUID
            user_id: User making the update
            update_type: Type of update (progress, blocker, note, etc.)
            content: Update content
            progress_percent: Progress percentage for progress updates (optional)

        Returns:
            Created update record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO action_updates (
                        action_id, user_id, update_type, content, progress_percent
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, action_id, user_id, update_type, content,
                              progress_percent, created_at
                    """,
                    (str(action_id), user_id, update_type, content, progress_percent),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_updates(self, action_id: str | UUID, limit: int = 50) -> list[dict[str, Any]]:
        """Get activity updates for an action.

        Args:
            action_id: Action UUID
            limit: Maximum updates to return (default: 50)

        Returns:
            List of update records, most recent first
        """
        return self._execute_query(
            """
            SELECT id, action_id, user_id, update_type, content,
                   old_status, new_status, old_date, new_date, date_field,
                   progress_percent, created_at
            FROM action_updates
            WHERE action_id = %s
            ORDER BY created_at DESC
            LIMIT %s
            """,
            (str(action_id), limit),
        )

    # =========================================================================
    # Dependency Management
    # =========================================================================

    # Valid status transitions (from_status -> allowed_to_statuses)
    VALID_TRANSITIONS = {
        "todo": {"in_progress", "blocked", "cancelled", "abandoned"},
        "blocked": {"todo", "in_progress", "cancelled", "failed", "abandoned"},
        "in_progress": {"todo", "blocked", "in_review", "done", "cancelled", "failed", "abandoned"},
        "in_review": {"in_progress", "done", "cancelled", "failed"},
        "done": set(),  # Terminal state
        "cancelled": set(),  # Terminal state
        "failed": {"replanned"},  # Can only transition to replanned (via replan action)
        "abandoned": {"replanned"},  # Can only transition to replanned (via replan action)
        "replanned": set(),  # Terminal state (action was cloned to new action)
    }

    def validate_status_transition(self, from_status: str, to_status: str) -> tuple[bool, str]:
        """Validate if a status transition is allowed.

        Args:
            from_status: Current action status
            to_status: Desired new status

        Returns:
            Tuple of (is_valid, error_message)
        """
        if from_status == to_status:
            return True, ""

        allowed = self.VALID_TRANSITIONS.get(from_status, set())
        if to_status not in allowed:
            if from_status in ("done", "cancelled", "replanned"):
                return False, f"Cannot change status of {from_status} actions"
            if from_status in ("failed", "abandoned") and to_status != "replanned":
                return False, f"Closed actions can only be replanned, not changed to '{to_status}'"
            return False, f"Invalid transition from '{from_status}' to '{to_status}'"
        return True, ""

    def add_dependency(
        self,
        action_id: str | UUID,
        depends_on_action_id: str | UUID,
        user_id: str,
        dependency_type: str = "finish_to_start",
        lag_days: int = 0,
    ) -> dict[str, Any] | None:
        """Add a dependency between two actions.

        Args:
            action_id: Action that has the dependency
            depends_on_action_id: Action that must complete first
            user_id: User making the change
            dependency_type: Type of dependency (finish_to_start, start_to_start, finish_to_finish)
            lag_days: Days of buffer between dependency completion and action start

        Returns:
            Created dependency record, or None if circular dependency detected
        """
        action_id_str = str(action_id)
        depends_on_str = str(depends_on_action_id)

        # Check for circular dependency
        if self._would_create_cycle(action_id_str, depends_on_str):
            logger.warning(f"Circular dependency detected: {action_id_str} -> {depends_on_str}")
            return None

        result_dict: dict[str, Any] | None = None

        with db_session() as conn:
            with conn.cursor() as cur:
                try:
                    cur.execute(
                        """
                        INSERT INTO action_dependencies (
                            action_id, depends_on_action_id, dependency_type, lag_days
                        )
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (action_id, depends_on_action_id) DO NOTHING
                        RETURNING action_id, depends_on_action_id, dependency_type, lag_days, created_at
                        """,
                        (action_id_str, depends_on_str, dependency_type, lag_days),
                    )
                    result = cur.fetchone()

                    if result:
                        # Check if we should auto-block the action
                        self._check_and_auto_block(action_id_str, user_id, conn)

                        # Create audit record
                        cur.execute(
                            """
                            INSERT INTO action_updates (
                                action_id, user_id, update_type, content
                            )
                            VALUES (%s, %s, %s, %s)
                            """,
                            (
                                action_id_str,
                                user_id,
                                "note",
                                f"Dependency added on action {depends_on_str}",
                            ),
                        )
                        result_dict = dict(result)
                except Exception as e:
                    logger.error(f"Failed to add dependency: {e}")
                    raise

        # Recalculate dates after transaction commits (outside with block)
        # This cascades date changes through the dependency chain
        if result_dict:
            self.recalculate_dates_cascade(action_id_str, user_id)

        return result_dict

    def remove_dependency(
        self,
        action_id: str | UUID,
        depends_on_action_id: str | UUID,
        user_id: str,
    ) -> bool:
        """Remove a dependency between two actions.

        Args:
            action_id: Action that has the dependency
            depends_on_action_id: Action being depended on
            user_id: User making the change

        Returns:
            True if removed successfully
        """
        action_id_str = str(action_id)
        depends_on_str = str(depends_on_action_id)

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    DELETE FROM action_dependencies
                    WHERE action_id = %s AND depends_on_action_id = %s
                    """,
                    (action_id_str, depends_on_str),
                )
                success = bool(cur.rowcount and cur.rowcount > 0)

                if success:
                    # Check if we should auto-unblock the action
                    self._check_and_auto_unblock(action_id_str, user_id, conn)

                    # Create audit record
                    cur.execute(
                        """
                        INSERT INTO action_updates (
                            action_id, user_id, update_type, content
                        )
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            action_id_str,
                            user_id,
                            "note",
                            f"Dependency on action {depends_on_str} removed",
                        ),
                    )

                return success

    def get_dependencies(self, action_id: str | UUID) -> list[dict[str, Any]]:
        """Get all dependencies for an action (what this action depends on).

        Args:
            action_id: Action UUID

        Returns:
            List of dependency records with dependent action details
        """
        return self._execute_query(
            """
            SELECT
                d.action_id,
                d.depends_on_action_id,
                d.dependency_type,
                d.lag_days,
                d.created_at,
                a.title as depends_on_title,
                a.status as depends_on_status
            FROM action_dependencies d
            JOIN actions a ON a.id = d.depends_on_action_id
            WHERE d.action_id = %s
            ORDER BY d.created_at ASC
            """,
            (str(action_id),),
        )

    def get_dependencies_batch(
        self,
        action_ids: list[str | UUID],
        include_transitive: bool = False,
        max_depth: int = 20,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get dependencies for multiple actions in a single query.

        Reduces N+1 queries to single query for batch dependency retrieval.

        Args:
            action_ids: List of action UUIDs
            include_transitive: If True, use recursive CTE to get full dependency tree
            max_depth: Maximum recursion depth to prevent cycles (default: 20)

        Returns:
            Dict mapping action_id -> list of dependency records
        """
        if not action_ids:
            return {}

        action_id_strs = [str(aid) for aid in action_ids]

        if include_transitive:
            # Use recursive CTE for transitive dependencies
            query = """
                WITH RECURSIVE dep_tree AS (
                    -- Base case: direct dependencies
                    SELECT
                        d.action_id,
                        d.depends_on_action_id,
                        d.dependency_type,
                        d.lag_days,
                        d.created_at,
                        1 as depth
                    FROM action_dependencies d
                    WHERE d.action_id = ANY(%s::uuid[])

                    UNION ALL

                    -- Recursive case: dependencies of dependencies
                    SELECT
                        dt.action_id,  -- Keep original action_id for grouping
                        d.depends_on_action_id,
                        d.dependency_type,
                        d.lag_days,
                        d.created_at,
                        dt.depth + 1 as depth
                    FROM action_dependencies d
                    JOIN dep_tree dt ON d.action_id = dt.depends_on_action_id
                    WHERE dt.depth < %s
                )
                SELECT DISTINCT ON (dt.action_id, dt.depends_on_action_id)
                    dt.action_id,
                    dt.depends_on_action_id,
                    dt.dependency_type,
                    dt.lag_days,
                    dt.created_at,
                    dt.depth,
                    a.title as depends_on_title,
                    a.status as depends_on_status
                FROM dep_tree dt
                JOIN actions a ON a.id = dt.depends_on_action_id
                ORDER BY dt.action_id, dt.depends_on_action_id, dt.depth
            """
            results = self._execute_query(query, (action_id_strs, max_depth))
        else:
            # Simple batch query for direct dependencies only
            query = """
                SELECT
                    d.action_id,
                    d.depends_on_action_id,
                    d.dependency_type,
                    d.lag_days,
                    d.created_at,
                    a.title as depends_on_title,
                    a.status as depends_on_status
                FROM action_dependencies d
                JOIN actions a ON a.id = d.depends_on_action_id
                WHERE d.action_id = ANY(%s::uuid[])
                ORDER BY d.action_id, d.created_at ASC
            """
            results = self._execute_query(query, (action_id_strs,))

        # Group by action_id
        deps_by_action: dict[str, list[dict[str, Any]]] = {aid: [] for aid in action_id_strs}
        for row in results:
            action_id = str(row["action_id"])
            if action_id in deps_by_action:
                deps_by_action[action_id].append(row)

        return deps_by_action

    def get_all_dependencies_for_user(
        self,
        user_id: str,
        include_completed: bool = False,
    ) -> dict[str, list[dict[str, Any]]]:
        """Get all dependencies for all actions belonging to a user.

        Single query fetching all dependencies indexed by action_id for O(1) lookup.

        Args:
            user_id: User identifier
            include_completed: If True, include deps for done/cancelled actions

        Returns:
            Dict mapping action_id -> list of dependency records
        """
        status_filter = "" if include_completed else "AND a_src.status NOT IN ('done', 'cancelled')"

        query = f"""
            SELECT
                d.action_id,
                d.depends_on_action_id,
                d.dependency_type,
                d.lag_days,
                d.created_at,
                a.title as depends_on_title,
                a.status as depends_on_status
            FROM action_dependencies d
            JOIN actions a ON a.id = d.depends_on_action_id
            JOIN actions a_src ON a_src.id = d.action_id
            WHERE a_src.user_id = %s
            {status_filter}
            ORDER BY d.action_id, d.created_at ASC
            LIMIT 10000
        """
        results = self._execute_query(query, (user_id,))

        # Group by action_id
        deps_by_action: dict[str, list[dict[str, Any]]] = {}
        for row in results:
            action_id = str(row["action_id"])
            if action_id not in deps_by_action:
                deps_by_action[action_id] = []
            deps_by_action[action_id].append(row)

        return deps_by_action

    def get_dependents(self, action_id: str | UUID) -> list[dict[str, Any]]:
        """Get all actions that depend on this action.

        Args:
            action_id: Action UUID

        Returns:
            List of dependency records with dependent action details
        """
        return self._execute_query(
            """
            SELECT
                d.action_id,
                d.depends_on_action_id,
                d.dependency_type,
                d.lag_days,
                d.created_at,
                a.title as dependent_title,
                a.status as dependent_status,
                a.auto_unblock
            FROM action_dependencies d
            JOIN actions a ON a.id = d.action_id
            WHERE d.depends_on_action_id = %s
            ORDER BY d.created_at ASC
            """,
            (str(action_id),),
        )

    def has_incomplete_dependencies(
        self, action_id: str | UUID
    ) -> tuple[bool, list[dict[str, Any]]]:
        """Check if action has incomplete dependencies.

        Args:
            action_id: Action UUID

        Returns:
            Tuple of (has_incomplete, list_of_incomplete_dependencies)
        """
        incomplete = self._execute_query(
            """
            SELECT
                d.depends_on_action_id,
                a.title,
                a.status
            FROM action_dependencies d
            JOIN actions a ON a.id = d.depends_on_action_id
            WHERE d.action_id = %s
            AND a.status NOT IN ('done', 'cancelled')
            """,
            (str(action_id),),
        )
        return len(incomplete) > 0, incomplete

    def _would_create_cycle(self, action_id: str, depends_on_id: str) -> bool:
        """Check if adding a dependency would create a circular reference.

        Uses BFS to traverse the dependency graph from depends_on_id
        to see if it can reach action_id.

        Args:
            action_id: The action getting the dependency
            depends_on_id: The action being depended on

        Returns:
            True if adding this dependency would create a cycle
        """
        if action_id == depends_on_id:
            return True

        # BFS from depends_on_id to see if we can reach action_id
        visited = set()
        queue = [depends_on_id]

        while queue:
            current = queue.pop(0)
            if current in visited:
                continue
            visited.add(current)

            # Get dependencies of current action
            deps = self._execute_query(
                """
                SELECT depends_on_action_id
                FROM action_dependencies
                WHERE action_id = %s
                """,
                (current,),
            )

            for dep in deps:
                dep_id = str(dep["depends_on_action_id"])
                if dep_id == action_id:
                    return True  # Found cycle
                if dep_id not in visited:
                    queue.append(dep_id)

        return False

    def _check_and_auto_block(self, action_id: str, user_id: str, conn: Any) -> bool:
        """Check if action should be auto-blocked due to incomplete dependencies.

        Args:
            action_id: Action UUID
            user_id: User ID for audit
            conn: Database connection (for transaction)

        Returns:
            True if action was blocked
        """
        with conn.cursor() as cur:
            # Get action status
            cur.execute(
                "SELECT status FROM actions WHERE id = %s",
                (action_id,),
            )
            row = cur.fetchone()
            if not row:
                return False

            current_status = row["status"]

            # Only auto-block if action is in todo status
            if current_status not in ("todo",):
                return False

            # Check for incomplete dependencies
            cur.execute(
                """
                SELECT a.id, a.title
                FROM action_dependencies d
                JOIN actions a ON a.id = d.depends_on_action_id
                WHERE d.action_id = %s
                AND a.status NOT IN ('done', 'cancelled')
                LIMIT 1
                """,
                (action_id,),
            )
            incomplete = cur.fetchone()

            if incomplete:
                # Block the action
                blocking_reason = f"Waiting for: {incomplete['title']}"
                cur.execute(
                    """
                    UPDATE actions
                    SET status = 'blocked',
                        blocking_reason = %s,
                        blocked_at = NOW(),
                        auto_unblock = true,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (blocking_reason, action_id),
                )

                # Create audit record
                cur.execute(
                    """
                    INSERT INTO action_updates (
                        action_id, user_id, update_type,
                        content, old_status, new_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        action_id,
                        user_id,
                        "status_change",
                        f"Auto-blocked: {blocking_reason}",
                        current_status,
                        "blocked",
                    ),
                )
                return True

        return False

    def _check_and_auto_unblock(self, action_id: str, user_id: str, conn: Any) -> bool:
        """Check if action should be auto-unblocked after dependency change.

        Args:
            action_id: Action UUID
            user_id: User ID for audit
            conn: Database connection (for transaction)

        Returns:
            True if action was unblocked
        """
        with conn.cursor() as cur:
            # Get action status and auto_unblock flag
            cur.execute(
                "SELECT status, auto_unblock FROM actions WHERE id = %s",
                (action_id,),
            )
            row = cur.fetchone()
            if not row:
                return False

            current_status = row["status"]
            auto_unblock = row["auto_unblock"]

            # Only auto-unblock if action is blocked and has auto_unblock enabled
            if current_status != "blocked" or not auto_unblock:
                return False

            # Check for incomplete dependencies
            cur.execute(
                """
                SELECT COUNT(*)
                FROM action_dependencies d
                JOIN actions a ON a.id = d.depends_on_action_id
                WHERE d.action_id = %s
                AND a.status NOT IN ('done', 'cancelled')
                """,
                (action_id,),
            )
            count_row = cur.fetchone()
            incomplete_count = count_row["count"] if count_row else 0

            if incomplete_count == 0:
                # Unblock the action
                cur.execute(
                    """
                    UPDATE actions
                    SET status = 'todo',
                        blocking_reason = NULL,
                        blocked_at = NULL,
                        auto_unblock = false,
                        updated_at = NOW()
                    WHERE id = %s
                    """,
                    (action_id,),
                )

                # Create audit record
                cur.execute(
                    """
                    INSERT INTO action_updates (
                        action_id, user_id, update_type,
                        content, old_status, new_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        action_id,
                        user_id,
                        "status_change",
                        "Auto-unblocked: all dependencies completed",
                        "blocked",
                        "todo",
                    ),
                )
                return True

        return False

    def auto_unblock_dependents(self, completed_action_id: str | UUID, user_id: str) -> list[str]:
        """Auto-unblock all actions that were waiting on this completed action.

        Called when an action is marked as done or cancelled.

        Args:
            completed_action_id: The action that was completed
            user_id: User ID for audit

        Returns:
            List of action IDs that were unblocked
        """
        unblocked_ids = []
        action_id_str = str(completed_action_id)

        # Get all actions that depend on this one and are blocked with auto_unblock
        dependents = self.get_dependents(action_id_str)

        for dep in dependents:
            if dep["dependent_status"] == "blocked" and dep["auto_unblock"]:
                dependent_id = str(dep["action_id"])

                # Check if all other dependencies are also complete
                has_incomplete, _ = self.has_incomplete_dependencies(dependent_id)

                if not has_incomplete:
                    # Unblock this action
                    with db_session() as conn:
                        with conn.cursor() as cur:
                            cur.execute(
                                """
                                UPDATE actions
                                SET status = 'todo',
                                    blocking_reason = NULL,
                                    blocked_at = NULL,
                                    auto_unblock = false,
                                    updated_at = NOW()
                                WHERE id = %s AND status = 'blocked'
                                """,
                                (dependent_id,),
                            )

                            if cur.rowcount and cur.rowcount > 0:
                                cur.execute(
                                    """
                                    INSERT INTO action_updates (
                                        action_id, user_id, update_type,
                                        content, old_status, new_status
                                    )
                                    VALUES (%s, %s, %s, %s, %s, %s)
                                    """,
                                    (
                                        dependent_id,
                                        user_id,
                                        "status_change",
                                        "Auto-unblocked: all dependencies completed",
                                        "blocked",
                                        "todo",
                                    ),
                                )
                                unblocked_ids.append(dependent_id)
                                logger.info(f"Auto-unblocked action {dependent_id}")

        return unblocked_ids

    def block_action(
        self,
        action_id: str | UUID,
        user_id: str,
        blocking_reason: str,
        auto_unblock: bool = False,
    ) -> bool:
        """Block an action with a reason.

        Args:
            action_id: Action UUID
            user_id: User blocking the action
            blocking_reason: Why the action is blocked
            auto_unblock: Whether to auto-unblock when dependencies complete

        Returns:
            True if blocked successfully
        """
        action = self.get(action_id)
        if not action:
            return False

        current_status = action.get("status", "")

        # Validate transition
        is_valid, error = self.validate_status_transition(current_status, "blocked")
        if not is_valid:
            logger.warning(f"Invalid block transition: {error}")
            return False

        return self.update_status(
            action_id=action_id,
            status="blocked",
            user_id=user_id,
            blocking_reason=blocking_reason,
            auto_unblock=auto_unblock,
        )

    def unblock_action(
        self,
        action_id: str | UUID,
        user_id: str,
        target_status: str = "todo",
    ) -> bool:
        """Unblock an action.

        Args:
            action_id: Action UUID
            user_id: User unblocking the action
            target_status: Status to transition to (default: 'todo')

        Returns:
            True if unblocked successfully
        """
        action = self.get(action_id)
        if not action:
            return False

        current_status = action.get("status", "")
        if current_status != "blocked":
            logger.warning(f"Cannot unblock action {action_id}: status is '{current_status}'")
            return False

        # Validate transition
        is_valid, error = self.validate_status_transition("blocked", target_status)
        if not is_valid:
            logger.warning(f"Invalid unblock transition: {error}")
            return False

        return self.update_status(
            action_id=action_id,
            status=target_status,
            user_id=user_id,
        )

    # =========================================================================
    # Date Calculations
    # =========================================================================

    def calculate_estimated_start_date(self, action_id: str | UUID) -> date | None:
        """Calculate the estimated start date based on dependencies.

        The estimated start date is the latest of:
        1. Today (can't start in the past)
        2. Target start date (if set)
        3. Max dependency end date + lag_days (for finish_to_start)

        Args:
            action_id: Action UUID

        Returns:
            Calculated estimated start date, or None if no dependencies
        """
        action = self.get(action_id)
        if not action:
            return None

        candidates: list[date] = [date.today()]

        # Consider target start date
        if action.get("target_start_date"):
            target = action["target_start_date"]
            if isinstance(target, date):
                candidates.append(target)

        # Get dependencies with their end dates
        deps = self._execute_query(
            """
            SELECT
                d.dependency_type,
                d.lag_days,
                a.status,
                a.actual_end_date::date as actual_end,
                a.estimated_end_date,
                a.actual_start_date::date as actual_start,
                a.estimated_start_date
            FROM action_dependencies d
            JOIN actions a ON a.id = d.depends_on_action_id
            WHERE d.action_id = %s
            """,
            (str(action_id),),
        )

        for dep in deps:
            dep_type = dep.get("dependency_type", "finish_to_start")
            lag_days = dep.get("lag_days", 0) or 0
            status = dep.get("status")

            if dep_type == "finish_to_start":
                # Action can start when dependency finishes
                if status in ("done", "cancelled"):
                    # Use actual end date if completed
                    end_date = dep.get("actual_end")
                else:
                    # Use estimated end date
                    end_date = dep.get("estimated_end_date")

                if end_date:
                    if isinstance(end_date, date):
                        # Add lag days (business days)
                        start_after = add_business_days(end_date, lag_days + 1)
                        candidates.append(start_after)

            elif dep_type == "start_to_start":
                # Action can start when dependency starts
                if status in ("in_progress", "in_review", "done", "cancelled"):
                    start_date = dep.get("actual_start")
                else:
                    start_date = dep.get("estimated_start_date")

                if start_date:
                    if isinstance(start_date, date):
                        start_after = add_business_days(start_date, lag_days)
                        candidates.append(start_after)

            # finish_to_finish doesn't affect start date

        return max(candidates) if candidates else date.today()

    def calculate_estimated_end_date(self, action_id: str | UUID) -> date | None:
        """Calculate the estimated end date based on start date and duration.

        Estimated end = estimated_start + duration (in business days)

        Args:
            action_id: Action UUID

        Returns:
            Calculated estimated end date, or None if insufficient data
        """
        action = self.get(action_id)
        if not action:
            return None

        # If target end date is set, use it
        target_end = action.get("target_end_date")
        if target_end and isinstance(target_end, date):
            return cast(date, target_end)

        # Get or calculate estimated start date
        estimated_start = action.get("estimated_start_date")
        if not estimated_start:
            estimated_start = self.calculate_estimated_start_date(action_id)
        if not estimated_start:
            return None

        # Get duration in business days
        duration = action.get("estimated_duration_days")
        if not duration:
            # Try to parse from timeline
            timeline = action.get("timeline")
            if timeline:
                duration = parse_timeline(timeline)

        if not duration:
            return None

        # Calculate end date (subtract 1 because start day counts)
        return add_business_days(estimated_start, duration - 1)

    def recalculate_action_dates(
        self,
        action_id: str | UUID,
        user_id: str,
    ) -> tuple[date | None, date | None]:
        """Recalculate and update estimated dates for a single action.

        Args:
            action_id: Action UUID
            user_id: User making the update

        Returns:
            Tuple of (estimated_start_date, estimated_end_date)
        """
        estimated_start = self.calculate_estimated_start_date(action_id)
        estimated_end = self.calculate_estimated_end_date(action_id)

        # Update the action with new dates
        self.update_dates(
            action_id=action_id,
            user_id=user_id,
            estimated_start_date=estimated_start,
            estimated_end_date=estimated_end,
        )

        return estimated_start, estimated_end

    def recalculate_dates_cascade(
        self,
        changed_action_id: str | UUID,
        user_id: str,
    ) -> list[str]:
        """Recalculate dates for an action and cascade to all dependents.

        When an action's dates change, all actions that depend on it
        (directly or indirectly) need their dates recalculated.

        Uses BFS to process actions in dependency order (shallow first).

        Args:
            changed_action_id: The action whose dates changed
            user_id: User making the update

        Returns:
            List of action IDs that were updated
        """
        updated_ids: list[str] = []
        action_id_str = str(changed_action_id)

        # First, recalculate the changed action itself
        self.recalculate_action_dates(action_id_str, user_id)
        updated_ids.append(action_id_str)

        # BFS through dependent actions
        visited: set[str] = {action_id_str}
        queue: deque[str] = deque([action_id_str])

        while queue:
            current_id = queue.popleft()

            # Get all actions that depend on current action
            dependents = self.get_dependents(current_id)

            for dep in dependents:
                dependent_id = str(dep["action_id"])
                if dependent_id in visited:
                    continue

                visited.add(dependent_id)

                # Recalculate dates for this dependent
                self.recalculate_action_dates(dependent_id, user_id)
                updated_ids.append(dependent_id)

                # Add to queue to process its dependents
                queue.append(dependent_id)

        logger.info(f"Date cascade updated {len(updated_ids)} actions")
        return updated_ids

    def recalculate_all_user_dates(self, user_id: str) -> int:
        """Recalculate dates for all actions belonging to a user.

        Useful for bulk recalculation after import or schema changes.

        Args:
            user_id: User identifier

        Returns:
            Number of actions updated
        """
        # Get all actions for user, ordered by dependencies (actions with no deps first)
        actions = self._execute_query(
            """
            SELECT a.id,
                   (SELECT COUNT(*) FROM action_dependencies d WHERE d.action_id = a.id) as dep_count
            FROM actions a
            WHERE a.user_id = %s
            AND a.status NOT IN ('done', 'cancelled')
            ORDER BY dep_count ASC
            """,
            (user_id,),
        )

        count = 0
        for action in actions:
            action_id = str(action["id"])
            self.recalculate_action_dates(action_id, user_id)
            count += 1

        logger.info(f"Recalculated dates for {count} actions")
        return count

    # =========================================================================
    # Progress Tracking
    # =========================================================================

    def update_progress(
        self,
        action_id: str | UUID,
        progress_type: str,
        progress_value: int | None = None,
        actual_start_date: str | None = None,
        actual_finish_date: str | None = None,
        estimated_effort_points: int | None = None,
    ) -> bool:
        """Update action progress tracking.

        Args:
            action_id: Action identifier
            progress_type: Type of progress tracking (percentage, points, status_only)
            progress_value: Progress value (0-100 for %, 0+ for points)
            actual_start_date: When work actually began (ISO format)
            actual_finish_date: When work completed (ISO format)
            estimated_effort_points: Estimated effort in story points

        Returns:
            True if update succeeded
        """
        action_id = str(action_id)

        # Parse dates if provided
        actual_start = None
        actual_finish = None
        if actual_start_date:
            try:
                actual_start = datetime.fromisoformat(actual_start_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid actual_start_date format: {actual_start_date}")
        if actual_finish_date:
            try:
                actual_finish = datetime.fromisoformat(actual_finish_date.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                logger.warning(f"Invalid actual_finish_date format: {actual_finish_date}")

        query = """
            UPDATE actions SET
                progress_type = %s,
                progress_value = %s,
                estimated_effort_points = %s,
                actual_start_date = COALESCE(%s, actual_start_date),
                actual_end_date = COALESCE(%s, actual_end_date),
                updated_at = now()
            WHERE id = %s
        """
        params = (
            progress_type,
            progress_value,
            estimated_effort_points,
            actual_start,
            actual_finish,
            action_id,
        )

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(query, params)
                return bool(cur.rowcount and cur.rowcount > 0)

    def calculate_variance(self, action_id: str | UUID) -> ActionVariance:
        """Calculate action schedule variance.

        Compares planned vs actual duration, returns risk_level (EARLY, ON_TIME, LATE).

        Args:
            action_id: Action identifier

        Returns:
            ActionVariance with schedule analysis
        """
        action_id = str(action_id)

        # Get action with dates
        action = self.get(action_id)
        if not action:
            logger.warning(f"Action not found: {action_id}")
            return ActionVariance(
                action_id=action_id,
                planned_duration_days=None,
                actual_duration_days=None,
                variance_days=None,
                risk_level="ON_TIME",
                progress_percent=None,
            )

        # Calculate planned duration
        # Use scheduled_start_date or created_at as plan start, target_end_date as plan end
        plan_start = action.get("scheduled_start_date") or action.get("created_at")
        plan_end = action.get("target_end_date")

        planned_days = None
        if plan_start and plan_end:
            if isinstance(plan_start, datetime):
                plan_start = plan_start.date()
            if isinstance(plan_end, datetime):
                plan_end = plan_end.date()
            planned_days = (plan_end - plan_start).days

        # Calculate actual duration
        actual_start = action.get("actual_start_date")
        actual_end = action.get("actual_end_date")

        actual_days = None
        if actual_start and actual_end:
            if isinstance(actual_start, datetime):
                actual_start = actual_start.date()
            if isinstance(actual_end, datetime):
                actual_end = actual_end.date()
            actual_days = (actual_end - actual_start).days

        # Calculate variance
        variance_days = None
        risk_level = "ON_TIME"

        if planned_days is not None and actual_days is not None:
            variance_days = actual_days - planned_days
            if variance_days < -1:  # Early by more than 1 day
                risk_level = "EARLY"
            elif variance_days > 1:  # Late by more than 1 day
                risk_level = "LATE"
            else:
                risk_level = "ON_TIME"

        # Get progress percent
        progress_percent = None
        if action.get("progress_type") == "percentage":
            progress_percent = action.get("progress_value")

        return ActionVariance(
            action_id=action_id,
            planned_duration_days=planned_days,
            actual_duration_days=actual_days,
            variance_days=variance_days,
            risk_level=risk_level,
            progress_percent=progress_percent,
        )


# Singleton instance for convenience
action_repository = ActionRepository()
