"""Session repository for session and related data operations.

Handles:
- Session CRUD operations
- Session events
- Session tasks
- Session synthesis
- Session clarifications
"""

import logging
from typing import Any

from psycopg2.extras import Json

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class SessionRepository(BaseRepository):
    """Repository for session and related data (events, tasks, synthesis)."""

    # =========================================================================
    # Session CRUD
    # =========================================================================

    def create(
        self,
        session_id: str,
        user_id: str,
        problem_statement: str,
        problem_context: dict[str, Any] | None = None,
        status: str = "created",
    ) -> dict[str, Any]:
        """Save a new session to PostgreSQL.

        Args:
            session_id: Session identifier (e.g., bo1_uuid)
            user_id: User who created the session
            problem_statement: Original problem statement
            problem_context: Additional context as dict (optional)
            status: Initial status (default: 'created')

        Returns:
            Saved session record with timestamps
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sessions (
                        id, user_id, problem_statement, problem_context, status
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE
                    SET user_id = EXCLUDED.user_id,
                        problem_statement = EXCLUDED.problem_statement,
                        problem_context = EXCLUDED.problem_context,
                        status = EXCLUDED.status,
                        updated_at = NOW()
                    RETURNING id, user_id, problem_statement, problem_context, status,
                              phase, total_cost, round_number, created_at, updated_at
                    """,
                    (
                        session_id,
                        user_id,
                        problem_statement,
                        Json(problem_context) if problem_context else None,
                        status,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get(self, session_id: str) -> dict[str, Any] | None:
        """Get a single session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session record with all fields, or None if not found
        """
        return self._execute_one(
            """
            SELECT id, user_id, problem_statement, problem_context, status,
                   phase, total_cost, round_number, created_at, updated_at,
                   synthesis_text, final_recommendation
            FROM sessions
            WHERE id = %s
            """,
            (session_id,),
        )

    def update_status(
        self,
        session_id: str,
        status: str,
        phase: str | None = None,
        total_cost: float | None = None,
        round_number: int | None = None,
        synthesis_text: str | None = None,
        final_recommendation: str | None = None,
    ) -> bool:
        """Update session status and optional fields.

        Args:
            session_id: Session identifier
            status: New status (e.g., 'running', 'completed', 'failed', 'killed')
            phase: Current deliberation phase (optional)
            total_cost: Total cost in USD (optional)
            round_number: Current round number (optional)
            synthesis_text: Final synthesis text (optional)
            final_recommendation: Final recommendation (optional)

        Returns:
            True if updated successfully, False otherwise
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Build dynamic UPDATE query based on provided fields
                update_fields = ["status = %s", "updated_at = NOW()"]
                params: list[Any] = [status]

                if phase is not None:
                    update_fields.append("phase = %s")
                    params.append(phase)

                if total_cost is not None:
                    update_fields.append("total_cost = %s")
                    params.append(total_cost)

                if round_number is not None:
                    update_fields.append("round_number = %s")
                    params.append(round_number)

                if synthesis_text is not None:
                    update_fields.append("synthesis_text = %s")
                    params.append(synthesis_text)

                if final_recommendation is not None:
                    update_fields.append("final_recommendation = %s")
                    params.append(final_recommendation)

                params.append(session_id)

                # Safe: update_fields contains only controlled column names
                query = f"""
                    UPDATE sessions
                    SET {", ".join(update_fields)}
                    WHERE id = %s
                """  # noqa: S608

                cur.execute(query, params)
                return bool(cur.rowcount and cur.rowcount > 0)

    def update_phase(self, session_id: str, phase: str) -> bool:
        """Update just the session phase (lightweight update for progress tracking).

        Args:
            session_id: Session identifier
            phase: New phase name

        Returns:
            True if updated successfully, False otherwise
        """
        return (
            self._execute_count(
                """
            UPDATE sessions
            SET phase = %s, updated_at = NOW()
            WHERE id = %s
            """,
                (phase, session_id),
            )
            > 0
        )

    def list_by_user(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0,
        status_filter: str | None = None,
        include_deleted: bool = False,
    ) -> list[dict[str, Any]]:
        """List sessions for a user with pagination and summary counts.

        Args:
            user_id: User identifier
            limit: Maximum sessions to return (default: 50)
            offset: Number of sessions to skip
            status_filter: Filter by status (optional)
            include_deleted: Include deleted sessions

        Returns:
            List of session records with expert_count, contribution_count, task_count, focus_area_count
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                query = """
                    SELECT s.id, s.user_id, s.problem_statement, s.problem_context, s.status,
                           s.phase, s.total_cost, s.round_number, s.created_at, s.updated_at,
                           s.synthesis_text, s.final_recommendation,
                           (SELECT COUNT(*)::int FROM session_events se
                            WHERE se.session_id = s.id AND se.event_type = 'persona_selected') as expert_count,
                           (SELECT COUNT(*)::int FROM session_events se
                            WHERE se.session_id = s.id AND se.event_type = 'contribution') as contribution_count,
                           (SELECT st.total_tasks FROM session_tasks st
                            WHERE st.session_id = s.id) as task_count,
                           (SELECT COUNT(*)::int FROM session_events se
                            WHERE se.session_id = s.id AND se.event_type = 'subproblem_started') as focus_area_count
                    FROM sessions s
                    WHERE s.user_id = %s
                """
                params: list[Any] = [user_id]

                if not include_deleted:
                    query += " AND s.status != 'deleted'"

                if status_filter:
                    query += " AND s.status = %s"
                    params.append(status_filter)

                query += " ORDER BY s.created_at DESC LIMIT %s OFFSET %s"
                params.extend([limit, offset])

                cur.execute(query, params)
                return [dict(row) for row in cur.fetchall()]

    def get_metadata(self, session_id: str) -> dict[str, Any] | None:
        """Get session metadata in Redis-compatible format.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dict or None if not found
        """
        try:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT id, user_id, problem_statement, problem_context,
                               status, phase, created_at, updated_at
                        FROM sessions
                        WHERE id = %s
                        """,
                        (session_id,),
                    )
                    row = cur.fetchone()
                    if not row:
                        return None

                    row_dict = dict(row)
                    return {
                        "status": row_dict["status"],
                        "phase": row_dict["phase"],
                        "user_id": row_dict["user_id"],
                        "created_at": row_dict["created_at"].isoformat(),
                        "updated_at": row_dict["updated_at"].isoformat(),
                        "problem_statement": row_dict["problem_statement"],
                        "problem_context": row_dict["problem_context"] or {},
                    }
        except Exception as e:
            logger.error(f"Failed to get session metadata for {session_id}: {e}")
            return None

    # =========================================================================
    # Session Events
    # =========================================================================

    def save_event(
        self,
        session_id: str,
        event_type: str,
        sequence: int,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        """Save a session event to PostgreSQL.

        Args:
            session_id: Session identifier
            event_type: Event type (e.g., 'contribution', 'synthesis_complete')
            sequence: Event sequence number
            data: Event payload

        Returns:
            Saved event record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO session_events (
                        session_id, event_type, sequence, data, user_id
                    )
                    VALUES (%s, %s, %s, %s, (
                        SELECT user_id FROM sessions WHERE id = %s
                    ))
                    ON CONFLICT (session_id, sequence, created_at) DO NOTHING
                    RETURNING id, session_id, event_type, sequence, created_at
                    """,
                    (session_id, event_type, sequence, Json(data), session_id),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_events(self, session_id: str) -> list[dict[str, Any]]:
        """Get all events for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of event records ordered by sequence
        """
        return self._execute_query(
            """
            SELECT id, session_id, event_type, sequence, data, created_at
            FROM session_events
            WHERE session_id = %s
            ORDER BY sequence ASC
            """,
            (session_id,),
        )

    # =========================================================================
    # Session Tasks
    # =========================================================================

    @staticmethod
    def _extract_task_id_references(
        dependencies: list[str], current_sub_problem_index: int | None = None
    ) -> tuple[list[str], list[tuple[int, str]]]:
        """Extract task_N and spN_task_M references from dependency strings.

        Parses dependency strings like:
        - "task_1" (same sub-problem)
        - "Pricing research complete (task_1)"
        - "sp0_task_2" (cross-sub-problem: sub-problem 0, task 2)
        - "sp2_task_1, sp1_task_3" (multiple cross-sub-problem)

        Args:
            dependencies: List of dependency strings from extracted task
            current_sub_problem_index: Index of current sub-problem (for context)

        Returns:
            Tuple of:
            - List of local task IDs (e.g., ["task_1", "task_2"])
            - List of cross-sub-problem refs as (sp_index, task_id) tuples
        """
        import re

        local_task_ids: list[str] = []
        cross_sp_refs: list[tuple[int, str]] = []

        # Pattern for local task references: task_N
        local_pattern = r"\b(task_\d+)\b"
        # Pattern for cross-sub-problem references: spN_task_M
        cross_pattern = r"\bsp(\d+)_task_(\d+)\b"

        for dep in dependencies:
            # Extract cross-sub-problem references first
            cross_matches = re.findall(cross_pattern, dep, re.IGNORECASE)
            for sp_idx_str, task_num in cross_matches:
                sp_idx = int(sp_idx_str)
                task_id = f"task_{task_num}"
                ref = (sp_idx, task_id)
                if ref not in cross_sp_refs:
                    cross_sp_refs.append(ref)

            # Extract local task references (excluding cross-sp ones)
            # Remove cross-sp patterns first to avoid double-matching
            dep_cleaned = re.sub(cross_pattern, "", dep, flags=re.IGNORECASE)
            local_matches = re.findall(local_pattern, dep_cleaned, re.IGNORECASE)
            for match in local_matches:
                task_id = match.lower()  # Normalize to lowercase
                if task_id not in local_task_ids:
                    local_task_ids.append(task_id)

        return local_task_ids, cross_sp_refs

    def save_tasks(
        self,
        session_id: str,
        tasks: list[dict[str, Any]],
        total_tasks: int,
        extraction_confidence: float,
        synthesis_sections_analyzed: list[str],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Save extracted tasks to actions table and session_tasks metadata.

        Args:
            session_id: Session identifier
            tasks: List of ExtractedTask dictionaries
            total_tasks: Total number of tasks
            extraction_confidence: Confidence score (0.0-1.0)
            synthesis_sections_analyzed: List of analyzed sections
            user_id: User identifier (optional)

        Returns:
            Saved task record with metadata
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Get user_id from session if not provided
                if not user_id:
                    cur.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
                    row = cur.fetchone()
                    if row:
                        user_id = row["user_id"]
                    else:
                        raise ValueError(f"Session not found: {session_id}")

                # Save metadata to session_tasks (for extraction_confidence tracking)
                cur.execute(
                    """
                    INSERT INTO session_tasks (
                        session_id, user_id, tasks, total_tasks, extraction_confidence,
                        synthesis_sections_analyzed
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id) DO UPDATE
                    SET tasks = EXCLUDED.tasks,
                        total_tasks = EXCLUDED.total_tasks,
                        extraction_confidence = EXCLUDED.extraction_confidence,
                        synthesis_sections_analyzed = EXCLUDED.synthesis_sections_analyzed,
                        extracted_at = NOW()
                    RETURNING id, session_id, total_tasks, extraction_confidence, extracted_at
                    """,
                    (
                        session_id,
                        user_id,
                        Json(tasks),
                        total_tasks,
                        extraction_confidence,
                        synthesis_sections_analyzed,
                    ),
                )
                result = cur.fetchone()

                # Save each task to actions table and track task_id -> action_id mapping
                # Key format: "sp{index}_{task_id}" for cross-sp lookups
                task_id_to_action_id: dict[str, str] = {}
                tasks_with_local_deps: list[
                    tuple[str, list[str], int | None]
                ] = []  # (action_id, local_deps, sp_idx)
                tasks_with_cross_deps: list[
                    tuple[str, list[tuple[int, str]]]
                ] = []  # (action_id, cross_sp_deps)

                for idx, task in enumerate(tasks):
                    sp_index = task.get("sub_problem_index")

                    cur.execute(
                        """
                        INSERT INTO actions (
                            user_id, source_session_id, title, description,
                            what_and_how, success_criteria, kill_criteria,
                            status, priority, category,
                            timeline, estimated_duration_days,
                            confidence, source_section, sub_problem_index,
                            sort_order
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT DO NOTHING
                        RETURNING id
                        """,
                        (
                            user_id,
                            session_id,
                            task.get("title", ""),
                            task.get("description", ""),
                            task.get("what_and_how", []),
                            task.get("success_criteria", []),
                            task.get("kill_criteria", []),
                            "todo",  # Initial status
                            task.get("priority", "medium"),
                            task.get("category", "implementation"),
                            task.get("timeline"),
                            task.get("estimated_duration_days"),
                            task.get("confidence", 0.0),
                            task.get("source_section"),
                            sp_index,
                            idx,  # Use array index as sort_order
                        ),
                    )
                    action_row = cur.fetchone()
                    if action_row:
                        action_id = str(action_row["id"])
                        task_id = task.get("id", f"task_{idx + 1}")

                        # Store both local and cross-sp lookup keys
                        task_id_to_action_id[task_id] = action_id
                        if sp_index is not None:
                            # Also store with sp prefix for cross-sp lookups
                            cross_key = f"sp{sp_index}_{task_id}"
                            task_id_to_action_id[cross_key] = action_id

                        # Parse dependencies for both local and cross-sp references
                        deps = task.get("dependencies", [])
                        local_deps, cross_sp_deps = self._extract_task_id_references(deps, sp_index)

                        if local_deps:
                            tasks_with_local_deps.append((action_id, local_deps, sp_index))
                        if cross_sp_deps:
                            tasks_with_cross_deps.append((action_id, cross_sp_deps))

                # Create action_dependencies for local (same sub-problem) dependencies
                for action_id, local_dep_task_ids, _sp_index in tasks_with_local_deps:
                    for dep_task_id in local_dep_task_ids:
                        depends_on_action_id = task_id_to_action_id.get(dep_task_id)
                        if depends_on_action_id and depends_on_action_id != action_id:
                            cur.execute(
                                """
                                INSERT INTO action_dependencies (
                                    action_id, depends_on_action_id, dependency_type, lag_days
                                )
                                VALUES (%s, %s, 'finish_to_start', 0)
                                ON CONFLICT DO NOTHING
                                """,
                                (action_id, depends_on_action_id),
                            )
                            logger.debug(
                                f"Created local dependency: {action_id} -> {depends_on_action_id}"
                            )

                # Create action_dependencies for cross-sub-problem dependencies
                for action_id, cross_sp_deps in tasks_with_cross_deps:
                    for sp_idx, task_id in cross_sp_deps:
                        # Look up by cross-sp key format
                        cross_key = f"sp{sp_idx}_{task_id}"
                        depends_on_action_id = task_id_to_action_id.get(cross_key)
                        if depends_on_action_id and depends_on_action_id != action_id:
                            cur.execute(
                                """
                                INSERT INTO action_dependencies (
                                    action_id, depends_on_action_id, dependency_type, lag_days
                                )
                                VALUES (%s, %s, 'finish_to_start', 0)
                                ON CONFLICT DO NOTHING
                                """,
                                (action_id, depends_on_action_id),
                            )
                            logger.info(
                                f"Created cross-sub-problem dependency: action {action_id} "
                                f"depends on sp{sp_idx}_{task_id} (action {depends_on_action_id})"
                            )
                        else:
                            logger.warning(
                                f"Cross-sub-problem dependency not resolved: {cross_key} "
                                f"(action may be from different session or not yet extracted)"
                            )

                return dict(result) if result else {}

    def get_tasks(self, session_id: str) -> dict[str, Any] | None:
        """Get extracted tasks for a session.

        Args:
            session_id: Session identifier

        Returns:
            Task record with tasks array, or None if not found
        """
        return self._execute_one(
            """
            SELECT id, session_id, tasks, total_tasks, extraction_confidence,
                   synthesis_sections_analyzed, extracted_at, task_statuses
            FROM session_tasks
            WHERE session_id = %s
            """,
            (session_id,),
        )

    def update_task_status(
        self,
        session_id: str,
        task_id: str,
        status: str,
    ) -> bool:
        """Update the status of a single task.

        Args:
            session_id: Session identifier
            task_id: Task ID (e.g., "task_1")
            status: New status ("todo", "doing", "done")

        Returns:
            True if updated successfully, False otherwise
        """
        if status not in ("todo", "doing", "done"):
            raise ValueError(f"Invalid task status: {status}")

        return (
            self._execute_count(
                """
                UPDATE session_tasks
                SET task_statuses = task_statuses || %s::jsonb
                WHERE session_id = %s
                """,
                (Json({task_id: status}), session_id),
            )
            > 0
        )

    def get_user_tasks(
        self,
        user_id: str,
        status_filter: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Get all tasks across all sessions for a user.

        Args:
            user_id: User identifier
            status_filter: Filter by status ("todo", "doing", "done") - optional
            limit: Maximum number of sessions to return
            offset: Number of sessions to skip

        Returns:
            List of session task records with session metadata
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT st.session_id, st.tasks, st.task_statuses, st.extracted_at,
                           s.problem_statement, s.status as session_status, s.created_at
                    FROM session_tasks st
                    JOIN sessions s ON st.session_id = s.id
                    WHERE s.user_id = %s AND s.status != 'deleted'
                    ORDER BY st.extracted_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (user_id, limit, offset),
                )
                return [dict(row) for row in cur.fetchall()]

    # =========================================================================
    # Session Synthesis
    # =========================================================================

    def save_synthesis(self, session_id: str, synthesis_text: str) -> bool:
        """Save synthesis text to sessions table.

        Args:
            session_id: Session identifier
            synthesis_text: Final synthesis text

        Returns:
            True if saved successfully
        """
        return (
            self._execute_count(
                """
            UPDATE sessions
            SET synthesis_text = %s, updated_at = NOW()
            WHERE id = %s
            """,
                (synthesis_text, session_id),
            )
            > 0
        )

    def get_synthesis(self, session_id: str) -> str | None:
        """Get synthesis text for a session.

        Args:
            session_id: Session identifier

        Returns:
            Synthesis text or None if not found
        """
        result = self._execute_one(
            """
            SELECT synthesis_text
            FROM sessions
            WHERE id = %s
            """,
            (session_id,),
        )
        return result["synthesis_text"] if result else None


# Singleton instance for convenience
session_repository = SessionRepository()
