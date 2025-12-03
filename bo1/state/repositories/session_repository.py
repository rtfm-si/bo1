"""Session repository for session and related data operations.

Handles:
- Session CRUD operations
- Session events
- Session tasks
- Session synthesis
- Session clarifications
"""

import logging
from datetime import datetime
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

    def save_tasks(
        self,
        session_id: str,
        tasks: list[dict[str, Any]],
        total_tasks: int,
        extraction_confidence: float,
        synthesis_sections_analyzed: list[str],
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Save extracted tasks to PostgreSQL.

        Args:
            session_id: Session identifier
            tasks: List of ExtractedTask dictionaries
            total_tasks: Total number of tasks
            extraction_confidence: Confidence score (0.0-1.0)
            synthesis_sections_analyzed: List of analyzed sections
            user_id: User identifier (optional)

        Returns:
            Saved task record
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
                   synthesis_sections_analyzed, extracted_at
            FROM session_tasks
            WHERE session_id = %s
            """,
            (session_id,),
        )

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

    # =========================================================================
    # Session Clarifications
    # =========================================================================

    def save_clarification(
        self,
        session_id: str,
        question: str,
        asked_by_persona: str | None = None,
        priority: str | None = None,
        reason: str | None = None,
        answer: str | None = None,
        answered_at: datetime | None = None,
        asked_at_round: int | None = None,
    ) -> dict[str, Any]:
        """Save a clarification question from an expert.

        Args:
            session_id: Session identifier
            question: The clarification question
            asked_by_persona: Persona code who asked
            priority: CRITICAL or NICE_TO_HAVE
            reason: Why this question is important
            answer: User's answer
            answered_at: When answer was provided
            asked_at_round: Round number when asked

        Returns:
            Saved clarification record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO session_clarifications (
                        session_id, question, asked_by_persona, priority,
                        reason, answer, answered_at, asked_at_round
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, question, asked_by_persona, priority,
                              reason, answer, answered_at, asked_at_round, created_at
                    """,
                    (
                        session_id,
                        question,
                        asked_by_persona,
                        priority,
                        reason,
                        answer,
                        answered_at,
                        asked_at_round,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def get_clarifications(self, session_id: str) -> list[dict[str, Any]]:
        """Get all clarifications for a session.

        Args:
            session_id: Session identifier

        Returns:
            List of clarification records
        """
        return self._execute_query(
            """
            SELECT id, session_id, question, asked_by_persona, priority,
                   reason, answer, answered_at, asked_at_round, created_at
            FROM session_clarifications
            WHERE session_id = %s
            ORDER BY created_at ASC
            """,
            (session_id,),
        )


# Singleton instance for convenience
session_repository = SessionRepository()
