"""Repository for user decisions (Decision Gate).

Handles CRUD operations for user_decisions table with RLS.
"""

import logging
from typing import Any

from bo1.models.user_decision import UserDecision
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class UserDecisionRepository(BaseRepository):
    """Repository for user decision records."""

    def upsert(
        self,
        session_id: str,
        user_id: str,
        chosen_option_id: str,
        chosen_option_label: str,
        chosen_option_description: str = "",
        rationale: dict[str, Any] | None = None,
        matrix_snapshot: dict[str, Any] | None = None,
        decision_source: str = "direct",
    ) -> UserDecision:
        """Upsert a user decision (one per session).

        Uses INSERT ... ON CONFLICT (session_id) DO UPDATE.
        """
        query = """
            INSERT INTO user_decisions (
                session_id, user_id, chosen_option_id, chosen_option_label,
                chosen_option_description, rationale, matrix_snapshot, decision_source
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                chosen_option_id = EXCLUDED.chosen_option_id,
                chosen_option_label = EXCLUDED.chosen_option_label,
                chosen_option_description = EXCLUDED.chosen_option_description,
                rationale = EXCLUDED.rationale,
                matrix_snapshot = EXCLUDED.matrix_snapshot,
                decision_source = EXCLUDED.decision_source,
                updated_at = NOW()
            RETURNING *
        """
        params = (
            session_id,
            user_id,
            chosen_option_id,
            chosen_option_label,
            chosen_option_description,
            self._to_json(rationale),
            self._to_json(matrix_snapshot),
            decision_source,
        )
        row = self._execute_returning(query, params, user_id=user_id)
        return UserDecision.from_db_row(row)

    def get_by_session(self, session_id: str, user_id: str) -> UserDecision | None:
        """Get decision for a session."""
        query = "SELECT * FROM user_decisions WHERE session_id = %s"
        row = self._execute_one(query, (session_id,), user_id=user_id)
        return UserDecision.from_db_row(row) if row else None

    def list_by_user(self, user_id: str, limit: int = 50) -> list[UserDecision]:
        """List decisions for a user."""
        query = "SELECT * FROM user_decisions ORDER BY created_at DESC LIMIT %s"
        rows = self._execute_query(query, (limit,), user_id=user_id)
        return [UserDecision.from_db_row(r) for r in rows]

    def list_with_outcomes(self, user_id: str, limit: int = 100) -> list[dict[str, Any]]:
        """List decisions LEFT JOINed with outcomes for pattern analysis."""
        query = """
            SELECT
                ud.id,
                ud.session_id,
                ud.chosen_option_id,
                ud.chosen_option_label,
                ud.decision_source,
                ud.rationale,
                ud.created_at,
                do2.outcome_status,
                do2.surprise_factor,
                do2.created_at AS outcome_date
            FROM user_decisions ud
            LEFT JOIN decision_outcomes do2 ON do2.decision_id = ud.id
            ORDER BY ud.created_at DESC
            LIMIT %s
        """
        return self._execute_query(query, (limit,), user_id=user_id)

    def delete(self, session_id: str, user_id: str) -> bool:
        """Delete a decision by session ID."""
        query = "DELETE FROM user_decisions WHERE session_id = %s"
        count = self._execute_count(query, (session_id,), user_id=user_id)
        return count > 0


user_decision_repository = UserDecisionRepository()
