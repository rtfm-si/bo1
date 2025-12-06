"""Contribution repository for contribution, recommendation, and related data operations.

Handles:
- Contribution CRUD operations
- Contribution embeddings (for semantic deduplication)
- Recommendations (expert recommendations)
- Sub-problem results
- Facilitator decisions
"""

import logging
from typing import Any

from psycopg2.extras import Json

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class ContributionRepository(BaseRepository):
    """Repository for contributions, recommendations, and facilitator decisions."""

    # =========================================================================
    # Contribution Operations
    # =========================================================================

    def save_contribution(
        self,
        session_id: str,
        persona_code: str,
        content: str,
        round_number: int,
        phase: str,
        cost: float = 0.0,
        tokens: int = 0,
        model: str = "unknown",
        embedding: list[float] | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Save a persona contribution to PostgreSQL.

        Args:
            session_id: Session identifier
            persona_code: Persona code (e.g., 'growth_hacker')
            content: Contribution text content
            round_number: Round number when contribution was made
            phase: Phase (initial_round, deliberation, moderator_intervention)
            cost: Cost in USD
            tokens: Token count
            model: Model used
            embedding: Optional embedding vector (1024 dimensions for Voyage AI)
            user_id: User ID (optional - will be fetched from session if not provided)

        Returns:
            Saved contribution record with id and created_at
        """
        # Validate required parameters
        self._validate_id(session_id, "session_id")
        self._validate_id(persona_code, "persona_code")
        self._validate_positive_int(round_number, "round_number")

        # Fetch user_id from session if not provided
        if user_id is None:
            with db_session() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
                    result = cur.fetchone()
                    if result:
                        user_id = result["user_id"]  # Dict access, not tuple
                    else:
                        logger.warning(
                            f"Session {session_id} not found, cannot fetch user_id for contribution"
                        )
                        user_id = "unknown"

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO contributions (
                        session_id, persona_code, content, round_number, phase,
                        cost, tokens, model, embedding, user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, persona_code, round_number, phase, created_at
                    """,
                    (
                        session_id,
                        persona_code,
                        content,
                        round_number,
                        phase,
                        cost,
                        tokens,
                        model,
                        embedding,
                        user_id,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    def save_contribution_embedding(self, contribution_id: str, embedding: list[float]) -> bool:
        """Update a contribution's embedding vector.

        This function is called after generating an embedding for semantic deduplication.
        Saves ~$0.0001 per contribution on repeat analysis.

        Args:
            contribution_id: Contribution record ID (UUID as string)
            embedding: Embedding vector (1024 dimensions for Voyage AI voyage-3)

        Returns:
            True if updated successfully, False otherwise

        Examples:
            >>> from bo1.llm.embeddings import generate_embedding
            >>> embedding = generate_embedding("We should focus on user experience", input_type="document")
            >>> contribution_repository.save_contribution_embedding("contrib_uuid", embedding)
            True
        """
        self._validate_id(contribution_id, "contribution_id")

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE contributions
                    SET embedding = %s
                    WHERE id = %s
                    """,
                    (embedding, contribution_id),
                )
                return bool(cur.rowcount and cur.rowcount > 0)

    def get_contribution_embedding(self, contribution_id: str) -> list[float] | None:
        """Get a contribution's embedding vector if it exists.

        Used by semantic deduplication to avoid regenerating embeddings.

        Args:
            contribution_id: Contribution record ID (UUID as string)

        Returns:
            Embedding vector if exists, None otherwise

        Examples:
            >>> embedding = contribution_repository.get_contribution_embedding("contrib_uuid")
            >>> if embedding:
            ...     print(f"Found cached embedding ({len(embedding)} dimensions)")
        """
        self._validate_id(contribution_id, "contribution_id")

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT embedding
                    FROM contributions
                    WHERE id = %s AND embedding IS NOT NULL
                    """,
                    (contribution_id,),
                )
                row = cur.fetchone()
                return row["embedding"] if row and row.get("embedding") else None

    # =========================================================================
    # Recommendation Operations
    # =========================================================================

    def save_recommendation(
        self,
        session_id: str,
        persona_code: str,
        recommendation: str,
        reasoning: str | None = None,
        confidence: float | None = None,
        conditions: list[str] | None = None,
        weight: float | None = None,
        sub_problem_index: int | None = None,
        persona_name: str | None = None,
    ) -> dict[str, Any]:
        """Save an expert recommendation to PostgreSQL.

        Args:
            session_id: Session identifier
            persona_code: Persona code
            recommendation: Free-form recommendation text
            reasoning: Reasoning behind recommendation
            confidence: Confidence score (0.0-1.0)
            conditions: List of conditions for the recommendation
            weight: Weight/importance of recommendation
            sub_problem_index: Sub-problem index (optional)
            persona_name: Display name of persona

        Returns:
            Saved recommendation record
        """
        self._validate_id(session_id, "session_id")
        self._validate_id(persona_code, "persona_code")

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO recommendations (
                        session_id, sub_problem_index, persona_code, persona_name,
                        recommendation, reasoning, confidence, conditions, weight
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, persona_code, created_at
                    """,
                    (
                        session_id,
                        sub_problem_index,
                        persona_code,
                        persona_name,
                        recommendation,
                        reasoning,
                        confidence,
                        Json(conditions) if conditions else None,
                        weight,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    # =========================================================================
    # Sub-Problem Result Operations
    # =========================================================================

    def save_sub_problem_result(
        self,
        session_id: str,
        sub_problem_index: int,
        goal: str,
        synthesis: str | None = None,
        expert_summaries: dict[str, str] | None = None,
        cost: float | None = None,
        duration_seconds: int | None = None,
        contribution_count: int | None = None,
    ) -> dict[str, Any]:
        """Save sub-problem result to PostgreSQL.

        Args:
            session_id: Session identifier
            sub_problem_index: Index of sub-problem
            goal: Sub-problem goal text
            synthesis: Synthesis text for this sub-problem
            expert_summaries: Dict of persona_code -> summary
            cost: Total cost for this sub-problem
            duration_seconds: Time taken
            contribution_count: Number of contributions

        Returns:
            Saved result record
        """
        self._validate_id(session_id, "session_id")
        self._validate_positive_int(sub_problem_index, "sub_problem_index")

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO sub_problem_results (
                        session_id, sub_problem_index, goal, synthesis,
                        expert_summaries, cost, duration_seconds, contribution_count
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, sub_problem_index) DO UPDATE
                    SET goal = EXCLUDED.goal,
                        synthesis = EXCLUDED.synthesis,
                        expert_summaries = EXCLUDED.expert_summaries,
                        cost = EXCLUDED.cost,
                        duration_seconds = EXCLUDED.duration_seconds,
                        contribution_count = EXCLUDED.contribution_count
                    RETURNING id, session_id, sub_problem_index, created_at
                    """,
                    (
                        session_id,
                        sub_problem_index,
                        goal,
                        synthesis,
                        Json(expert_summaries) if expert_summaries else None,
                        cost,
                        duration_seconds,
                        contribution_count,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}

    # =========================================================================
    # Facilitator Decision Operations
    # =========================================================================

    def save_facilitator_decision(
        self,
        session_id: str,
        round_number: int,
        action: str,
        reasoning: str | None = None,
        next_speaker: str | None = None,
        moderator_type: str | None = None,
        research_query: str | None = None,
        sub_problem_index: int | None = None,
        user_id: str | None = None,
    ) -> dict[str, Any]:
        """Save facilitator decision to PostgreSQL.

        Args:
            session_id: Session identifier
            round_number: Round when decision was made
            action: Decision action (continue, vote, moderator, research, clarify)
            reasoning: Reasoning behind decision
            next_speaker: Next persona to speak (if action=continue)
            moderator_type: Type of moderator intervention (if action=moderator)
            research_query: Research query (if action=research)
            sub_problem_index: Current sub-problem index
            user_id: User identifier (fetched from session if not provided)

        Returns:
            Saved decision record
        """
        self._validate_id(session_id, "session_id")
        self._validate_positive_int(round_number, "round_number")

        with db_session() as conn:
            with conn.cursor() as cur:
                # Fetch user_id from session if not provided
                if user_id is None:
                    cur.execute("SELECT user_id FROM sessions WHERE id = %s", (session_id,))
                    result = cur.fetchone()
                    if result:
                        user_id = result["user_id"]

                # user_id is required (NOT NULL constraint) - use fallback if still None
                if user_id is None:
                    # In MVP/dev mode, use test_user_1 as fallback
                    import os

                    if os.getenv("DEBUG", "").lower() == "true":
                        user_id = "test_user_1"
                        logger.warning(
                            f"Using fallback user_id 'test_user_1' for facilitator decision "
                            f"(session_id={session_id}). Session may not have user_id set."
                        )
                    else:
                        logger.error(
                            f"Cannot save facilitator decision: user_id is required but not found "
                            f"(session_id={session_id}). Skipping save."
                        )
                        return {}

                cur.execute(
                    """
                    INSERT INTO facilitator_decisions (
                        session_id, round_number, sub_problem_index, action,
                        reasoning, next_speaker, moderator_type, research_query, user_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, round_number, action, created_at
                    """,
                    (
                        session_id,
                        round_number,
                        sub_problem_index,
                        action,
                        reasoning,
                        next_speaker,
                        moderator_type,
                        research_query,
                        user_id,
                    ),
                )
                result = cur.fetchone()
                return dict(result) if result else {}


# Singleton instance
contribution_repository = ContributionRepository()
