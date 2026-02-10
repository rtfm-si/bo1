"""Repository for decision outcomes (Outcome Tracking).

Handles CRUD operations for decision_outcomes table with RLS.
"""

import logging
from typing import Any

from bo1.models.decision_outcome import DecisionOutcome
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class DecisionOutcomeRepository(BaseRepository):
    """Repository for decision outcome records."""

    def upsert(
        self,
        decision_id: str,
        user_id: str,
        outcome_status: str,
        outcome_notes: str | None = None,
        surprise_factor: int | None = None,
        lessons_learned: str | None = None,
        what_would_change: str | None = None,
    ) -> DecisionOutcome:
        """Upsert a decision outcome (one per decision).

        Uses INSERT ... ON CONFLICT (decision_id) DO UPDATE.
        """
        query = """
            INSERT INTO decision_outcomes (
                decision_id, user_id, outcome_status, outcome_notes,
                surprise_factor, lessons_learned, what_would_change
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (decision_id) DO UPDATE SET
                outcome_status = EXCLUDED.outcome_status,
                outcome_notes = EXCLUDED.outcome_notes,
                surprise_factor = EXCLUDED.surprise_factor,
                lessons_learned = EXCLUDED.lessons_learned,
                what_would_change = EXCLUDED.what_would_change,
                updated_at = NOW()
            RETURNING *
        """
        params = (
            decision_id,
            user_id,
            outcome_status,
            outcome_notes,
            surprise_factor,
            lessons_learned,
            what_would_change,
        )
        row = self._execute_returning(query, params, user_id=user_id)
        return DecisionOutcome.from_db_row(row)

    def get_by_decision(self, decision_id: str, user_id: str) -> DecisionOutcome | None:
        """Get outcome for a decision."""
        query = "SELECT * FROM decision_outcomes WHERE decision_id = %s"
        row = self._execute_one(query, (decision_id,), user_id=user_id)
        return DecisionOutcome.from_db_row(row) if row else None

    def list_by_user(self, user_id: str, limit: int = 50) -> list[DecisionOutcome]:
        """List outcomes for a user."""
        query = "SELECT * FROM decision_outcomes ORDER BY created_at DESC LIMIT %s"
        rows = self._execute_query(query, (limit,), user_id=user_id)
        return [DecisionOutcome.from_db_row(r) for r in rows]

    def list_pending_followups(self, user_id: str, age_days: int = 30) -> list[dict[str, Any]]:
        """Get decisions older than N days without outcomes.

        Returns dicts with decision + session info for the followup banner.
        """
        query = """
            SELECT
                ud.id AS decision_id,
                ud.session_id,
                ud.chosen_option_label,
                ud.created_at AS decision_date,
                EXTRACT(DAY FROM NOW() - ud.created_at)::int AS days_ago
            FROM user_decisions ud
            LEFT JOIN decision_outcomes do2 ON do2.decision_id = ud.id
            WHERE do2.id IS NULL
              AND ud.created_at < NOW() - make_interval(days => %s)
            ORDER BY ud.created_at ASC
            LIMIT 5
        """
        rows = self._execute_query(query, (age_days,), user_id=user_id)
        return rows


decision_outcome_repository = DecisionOutcomeRepository()
