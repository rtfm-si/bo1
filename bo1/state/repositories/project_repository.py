"""Project repository for project management operations.

Handles:
- Project CRUD operations
- Project-action relationships
- Progress calculation
- Session linking
- Status management
"""

import logging
from datetime import date
from typing import Any
from uuid import UUID

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


# Valid status transitions for projects
VALID_PROJECT_TRANSITIONS: dict[str, list[str]] = {
    "active": ["paused", "completed", "archived"],
    "paused": ["active", "archived"],
    "completed": ["active", "archived"],  # Can reopen if needed
    "archived": [],  # Terminal state
}


class ProjectRepository(BaseRepository):
    """Repository for project management operations."""

    # =========================================================================
    # Project CRUD
    # =========================================================================

    def create(
        self,
        user_id: str,
        name: str,
        description: str | None = None,
        status: str = "active",
        target_start_date: date | None = None,
        target_end_date: date | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any]:
        """Create a new project.

        Args:
            user_id: User who owns the project
            name: Project name
            description: Project description (optional)
            status: Initial status (default: 'active')
            target_start_date: User-set target start (optional)
            target_end_date: User-set target end (optional)
            color: Hex color for visualization (optional)
            icon: Emoji or icon name (optional)

        Returns:
            Created project record with all fields including generated ID
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO projects (
                        user_id, name, description, status,
                        target_start_date, target_end_date,
                        color, icon
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, user_id, name, description, status,
                              target_start_date, target_end_date,
                              estimated_start_date, estimated_end_date,
                              actual_start_date, actual_end_date,
                              progress_percent, total_actions, completed_actions,
                              color, icon, created_at, updated_at
                    """,
                    (
                        user_id,
                        name,
                        description,
                        status,
                        target_start_date,
                        target_end_date,
                        color,
                        icon,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get(self, project_id: str | UUID) -> dict[str, Any] | None:
        """Get a single project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project record with all fields, or None if not found
        """
        return self._execute_one(
            """
            SELECT id, user_id, name, description, status,
                   target_start_date, target_end_date,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   progress_percent, total_actions, completed_actions,
                   color, icon, created_at, updated_at
            FROM projects
            WHERE id = %s
            """,
            (str(project_id),),
        )

    def get_by_user(
        self,
        user_id: str,
        status: str | None = None,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Get all projects for a user with optional filtering and pagination.

        Args:
            user_id: User ID to get projects for
            status: Filter by status (optional)
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (total_count, page_results)
        """
        where_clauses = ["user_id = %s"]
        params: list[Any] = [user_id]

        if status:
            where_clauses.append("status = %s")
            params.append(status)

        where_sql = " AND ".join(where_clauses)

        count_query = f"""
            SELECT COUNT(*) as count
            FROM projects
            WHERE {where_sql}
        """

        data_query = f"""
            SELECT id, user_id, name, description, status,
                   target_start_date, target_end_date,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   progress_percent, total_actions, completed_actions,
                   color, icon, created_at, updated_at
            FROM projects
            WHERE {where_sql}
            ORDER BY updated_at DESC
            LIMIT %s OFFSET %s
        """

        return self._execute_paginated(count_query, data_query, params, page, per_page)

    def update(
        self,
        project_id: str | UUID,
        name: str | None = None,
        description: str | None = None,
        target_start_date: date | None = None,
        target_end_date: date | None = None,
        color: str | None = None,
        icon: str | None = None,
    ) -> dict[str, Any] | None:
        """Update a project's basic fields.

        Args:
            project_id: Project UUID
            name: New name (optional)
            description: New description (optional)
            target_start_date: New target start (optional)
            target_end_date: New target end (optional)
            color: New color (optional)
            icon: New icon (optional)

        Returns:
            Updated project record, or None if not found
        """
        updates = []
        params: list[Any] = []

        if name is not None:
            updates.append("name = %s")
            params.append(name)
        if description is not None:
            updates.append("description = %s")
            params.append(description)
        if target_start_date is not None:
            updates.append("target_start_date = %s")
            params.append(target_start_date)
        if target_end_date is not None:
            updates.append("target_end_date = %s")
            params.append(target_end_date)
        if color is not None:
            updates.append("color = %s")
            params.append(color)
        if icon is not None:
            updates.append("icon = %s")
            params.append(icon)

        if not updates:
            return self.get(project_id)

        updates.append("updated_at = NOW()")
        params.append(str(project_id))

        query = f"""
            UPDATE projects
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, user_id, name, description, status,
                      target_start_date, target_end_date,
                      estimated_start_date, estimated_end_date,
                      actual_start_date, actual_end_date,
                      progress_percent, total_actions, completed_actions,
                      color, icon, created_at, updated_at
        """

        return self._execute_one(query, tuple(params))

    def delete(self, project_id: str | UUID, user_id: str) -> bool:
        """Delete a project (soft delete via archive status).

        Args:
            project_id: Project UUID
            user_id: User ID (for verification)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        count = self._execute_count(
            """
            UPDATE projects
            SET status = 'archived', updated_at = NOW()
            WHERE id = %s AND user_id = %s
            """,
            (str(project_id), user_id),
        )
        return count > 0

    def hard_delete(self, project_id: str | UUID, user_id: str) -> bool:
        """Permanently delete a project.

        Args:
            project_id: Project UUID
            user_id: User ID (for verification)

        Returns:
            True if deleted, False if not found or unauthorized
        """
        count = self._execute_count(
            """
            DELETE FROM projects
            WHERE id = %s AND user_id = %s
            """,
            (str(project_id), user_id),
        )
        return count > 0

    # =========================================================================
    # Status Management
    # =========================================================================

    def validate_status_transition(self, current_status: str, new_status: str) -> tuple[bool, str]:
        """Validate if a status transition is allowed.

        Args:
            current_status: Current project status
            new_status: Desired new status

        Returns:
            Tuple of (is_valid, error_message)
        """
        if current_status == new_status:
            return True, ""

        allowed = VALID_PROJECT_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            return False, (
                f"Cannot transition from '{current_status}' to '{new_status}'. "
                f"Allowed transitions: {allowed or 'none (terminal state)'}"
            )

        return True, ""

    def update_status(
        self, project_id: str | UUID, new_status: str, user_id: str
    ) -> dict[str, Any] | None:
        """Update a project's status with validation.

        Args:
            project_id: Project UUID
            new_status: New status value
            user_id: User ID (for verification)

        Returns:
            Updated project record, or None if not found/invalid

        Raises:
            ValueError: If transition is not allowed
        """
        project = self.get(project_id)
        if not project or project["user_id"] != user_id:
            return None

        current_status = project["status"]
        is_valid, error = self.validate_status_transition(current_status, new_status)
        if not is_valid:
            raise ValueError(error)

        # Handle completion logic
        extra_updates = ""
        if new_status == "completed" and not project["actual_end_date"]:
            extra_updates = ", actual_end_date = NOW()"

        return self._execute_one(
            f"""
            UPDATE projects
            SET status = %s, updated_at = NOW(){extra_updates}
            WHERE id = %s AND user_id = %s
            RETURNING id, user_id, name, description, status,
                      target_start_date, target_end_date,
                      estimated_start_date, estimated_end_date,
                      actual_start_date, actual_end_date,
                      progress_percent, total_actions, completed_actions,
                      color, icon, created_at, updated_at
            """,
            (new_status, str(project_id), user_id),
        )

    # =========================================================================
    # Progress Calculation
    # =========================================================================

    def recalculate_progress(self, project_id: str | UUID) -> dict[str, Any] | None:
        """Recalculate project progress from its actions.

        Updates:
        - progress_percent: % of done actions
        - total_actions: count of all actions
        - completed_actions: count of done/cancelled actions
        - estimated_start_date: min of action estimated_start_dates
        - estimated_end_date: max of action estimated_end_dates

        Args:
            project_id: Project UUID

        Returns:
            Updated project record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get action statistics
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total,
                        COUNT(*) FILTER (WHERE status IN ('done', 'cancelled')) as completed,
                        MIN(estimated_start_date) as est_start,
                        MAX(estimated_end_date) as est_end,
                        MIN(actual_start_date) as first_start
                    FROM actions
                    WHERE project_id = %s
                    """,
                    (str(project_id),),
                )
                stats = cur.fetchone()

                total = stats["total"] or 0
                completed = stats["completed"] or 0
                progress = int((completed / total * 100) if total > 0 else 0)
                est_start = stats["est_start"]
                est_end = stats["est_end"]
                first_start = stats["first_start"]

                # Update project
                cur.execute(
                    """
                    UPDATE projects
                    SET total_actions = %s,
                        completed_actions = %s,
                        progress_percent = %s,
                        estimated_start_date = %s,
                        estimated_end_date = %s,
                        actual_start_date = COALESCE(actual_start_date, %s),
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, user_id, name, description, status,
                              target_start_date, target_end_date,
                              estimated_start_date, estimated_end_date,
                              actual_start_date, actual_end_date,
                              progress_percent, total_actions, completed_actions,
                              color, icon, created_at, updated_at
                    """,
                    (total, completed, progress, est_start, est_end, first_start, str(project_id)),
                )
                result = cur.fetchone()

                # Auto-complete project if all actions done
                if result and total > 0 and completed == total:
                    if result["status"] == "active":
                        cur.execute(
                            """
                            UPDATE projects
                            SET status = 'completed',
                                actual_end_date = NOW(),
                                updated_at = NOW()
                            WHERE id = %s
                            RETURNING id, user_id, name, description, status,
                                      target_start_date, target_end_date,
                                      estimated_start_date, estimated_end_date,
                                      actual_start_date, actual_end_date,
                                      progress_percent, total_actions, completed_actions,
                                      color, icon, created_at, updated_at
                            """,
                            (str(project_id),),
                        )
                        result = cur.fetchone()

                return dict(result) if result else None

    # =========================================================================
    # Project-Action Relationships
    # =========================================================================

    def get_actions(
        self,
        project_id: str | UUID,
        status: str | None = None,
        page: int = 1,
        per_page: int = 50,
    ) -> tuple[int, list[dict[str, Any]]]:
        """Get all actions for a project.

        Args:
            project_id: Project UUID
            status: Filter by action status (optional)
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (total_count, page_results)
        """
        where_clauses = ["project_id = %s"]
        params: list[Any] = [str(project_id)]

        if status:
            where_clauses.append("status = %s")
            params.append(status)

        where_sql = " AND ".join(where_clauses)

        count_query = f"""
            SELECT COUNT(*) as count
            FROM actions
            WHERE {where_sql}
        """

        data_query = f"""
            SELECT id, user_id, source_session_id, project_id, title, description,
                   what_and_how, success_criteria, kill_criteria,
                   status, priority, category,
                   timeline, estimated_duration_days,
                   target_start_date, target_end_date,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   blocking_reason, blocked_at, auto_unblock,
                   confidence, source_section, sub_problem_index,
                   sort_order, created_at, updated_at
            FROM actions
            WHERE {where_sql}
            ORDER BY sort_order, estimated_start_date NULLS LAST, created_at
            LIMIT %s OFFSET %s
        """

        return self._execute_paginated(count_query, data_query, params, page, per_page)

    def assign_action(self, action_id: str | UUID, project_id: str | UUID, user_id: str) -> bool:
        """Assign an action to a project.

        Args:
            action_id: Action UUID
            project_id: Project UUID
            user_id: User ID (for verification)

        Returns:
            True if assigned, False if not found or unauthorized
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Verify action belongs to user
                cur.execute(
                    "SELECT user_id FROM actions WHERE id = %s",
                    (str(action_id),),
                )
                action = cur.fetchone()
                if not action or action["user_id"] != user_id:
                    return False

                # Verify project belongs to user
                cur.execute(
                    "SELECT user_id FROM projects WHERE id = %s",
                    (str(project_id),),
                )
                project = cur.fetchone()
                if not project or project["user_id"] != user_id:
                    return False

                # Assign action to project
                cur.execute(
                    """
                    UPDATE actions
                    SET project_id = %s, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (str(project_id), str(action_id)),
                )

        # Recalculate project progress
        self.recalculate_progress(project_id)
        return True

    def unassign_action(self, action_id: str | UUID, user_id: str) -> bool:
        """Remove an action from its project.

        Args:
            action_id: Action UUID
            user_id: User ID (for verification)

        Returns:
            True if unassigned, False if not found or unauthorized
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get current project_id
                cur.execute(
                    "SELECT user_id, project_id FROM actions WHERE id = %s",
                    (str(action_id),),
                )
                action = cur.fetchone()
                if not action or action["user_id"] != user_id:
                    return False

                old_project_id = action["project_id"]

                # Remove from project
                cur.execute(
                    """
                    UPDATE actions
                    SET project_id = NULL, updated_at = NOW()
                    WHERE id = %s
                    """,
                    (str(action_id),),
                )

        # Recalculate old project's progress
        if old_project_id:
            self.recalculate_progress(old_project_id)
        return True

    def get_unassigned_actions(
        self, user_id: str, page: int = 1, per_page: int = 50
    ) -> tuple[int, list[dict[str, Any]]]:
        """Get all actions without a project.

        Args:
            user_id: User ID
            page: Page number (1-indexed)
            per_page: Items per page

        Returns:
            Tuple of (total_count, page_results)
        """
        count_query = """
            SELECT COUNT(*) as count
            FROM actions
            WHERE user_id = %s AND project_id IS NULL
        """

        data_query = """
            SELECT id, user_id, source_session_id, project_id, title, description,
                   what_and_how, success_criteria, kill_criteria,
                   status, priority, category,
                   timeline, estimated_duration_days,
                   target_start_date, target_end_date,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   blocking_reason, blocked_at, auto_unblock,
                   confidence, source_section, sub_problem_index,
                   sort_order, created_at, updated_at
            FROM actions
            WHERE user_id = %s AND project_id IS NULL
            ORDER BY created_at DESC
            LIMIT %s OFFSET %s
        """

        return self._execute_paginated(count_query, data_query, [user_id], page, per_page)

    # =========================================================================
    # Session Linking
    # =========================================================================

    def link_session(
        self,
        project_id: str | UUID,
        session_id: str,
        relationship: str = "discusses",
    ) -> dict[str, Any] | None:
        """Link a session to a project.

        Args:
            project_id: Project UUID
            session_id: Session ID
            relationship: Type of link (discusses, created_from, replanning)

        Returns:
            Created link record, or None if already exists
        """
        return self._execute_one(
            """
            INSERT INTO session_projects (project_id, session_id, relationship)
            VALUES (%s, %s, %s)
            ON CONFLICT (session_id, project_id) DO UPDATE
            SET relationship = EXCLUDED.relationship
            RETURNING session_id, project_id, relationship, created_at
            """,
            (str(project_id), session_id, relationship),
        )

    def unlink_session(self, project_id: str | UUID, session_id: str) -> bool:
        """Remove a session-project link.

        Args:
            project_id: Project UUID
            session_id: Session ID

        Returns:
            True if unlinked, False if link not found
        """
        count = self._execute_count(
            """
            DELETE FROM session_projects
            WHERE project_id = %s AND session_id = %s
            """,
            (str(project_id), session_id),
        )
        return count > 0

    def get_sessions(self, project_id: str | UUID) -> list[dict[str, Any]]:
        """Get all sessions linked to a project.

        Args:
            project_id: Project UUID

        Returns:
            List of session links with session details
        """
        return self._execute_query(
            """
            SELECT sp.session_id, sp.project_id, sp.relationship, sp.created_at,
                   s.problem_statement, s.status as session_status, s.created_at as session_created_at
            FROM session_projects sp
            JOIN sessions s ON s.id = sp.session_id
            WHERE sp.project_id = %s
            ORDER BY sp.created_at DESC
            """,
            (str(project_id),),
        )

    def get_projects_for_session(self, session_id: str) -> list[dict[str, Any]]:
        """Get all projects linked to a session.

        Args:
            session_id: Session ID

        Returns:
            List of project links with project details
        """
        return self._execute_query(
            """
            SELECT sp.session_id, sp.project_id, sp.relationship, sp.created_at,
                   p.name, p.status, p.progress_percent
            FROM session_projects sp
            JOIN projects p ON p.id = sp.project_id
            WHERE sp.session_id = %s
            ORDER BY sp.created_at DESC
            """,
            (session_id,),
        )

    # =========================================================================
    # Gantt Data
    # =========================================================================

    def get_gantt_data(self, project_id: str | UUID) -> dict[str, Any]:
        """Get Gantt chart data for a project.

        Args:
            project_id: Project UUID

        Returns:
            Dictionary with project info, actions, and dependencies
        """
        project = self.get(project_id)
        if not project:
            return {}

        # Get all actions
        actions = self._execute_query(
            """
            SELECT id, title, status, priority,
                   estimated_start_date, estimated_end_date,
                   actual_start_date, actual_end_date,
                   progress_percent, blocking_reason
            FROM actions
            WHERE project_id = %s
            ORDER BY estimated_start_date NULLS LAST, sort_order
            """,
            (str(project_id),),
        )

        # Get all dependencies between project actions
        action_ids = [str(a["id"]) for a in actions]
        dependencies = []
        if action_ids:
            dependencies = self._execute_query(
                """
                SELECT ad.action_id, ad.depends_on_action_id, ad.dependency_type, ad.lag_days
                FROM action_dependencies ad
                WHERE ad.action_id = ANY(%s) AND ad.depends_on_action_id = ANY(%s)
                """,
                (action_ids, action_ids),
            )

        return {
            "project": {
                "id": str(project["id"]),
                "name": project["name"],
                "status": project["status"],
                "estimated_start_date": self._to_iso_string_or_none(
                    project["estimated_start_date"]
                ),
                "estimated_end_date": self._to_iso_string_or_none(project["estimated_end_date"]),
                "progress_percent": project["progress_percent"],
                "color": project["color"],
            },
            "actions": [
                {
                    "id": str(a["id"]),
                    "title": a["title"],
                    "status": a["status"],
                    "priority": a["priority"],
                    "estimated_start_date": self._to_iso_string_or_none(a["estimated_start_date"]),
                    "estimated_end_date": self._to_iso_string_or_none(a["estimated_end_date"]),
                    "actual_start_date": self._to_iso_string_or_none(a["actual_start_date"]),
                    "actual_end_date": self._to_iso_string_or_none(a["actual_end_date"]),
                    "blocking_reason": a["blocking_reason"],
                }
                for a in actions
            ],
            "dependencies": [
                {
                    "from": str(d["depends_on_action_id"]),
                    "to": str(d["action_id"]),
                    "type": d["dependency_type"],
                    "lag_days": d["lag_days"],
                }
                for d in dependencies
            ],
        }


# Singleton instance
project_repository = ProjectRepository()
