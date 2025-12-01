"""Quality metrics calculator for deliberation rounds.

AUDIT FIX (Priority 4.3): Extracted from loop_prevention.py check_convergence_node.
This module provides focused, testable quality metric calculations.

Calculates:
- Convergence score (semantic similarity)
- Novelty score (uniqueness of contributions)
- Conflict score (disagreement level)
- Exploration score (coverage of 8 critical aspects)
- Focus score (on-topic ratio)
- Meeting completeness index (composite metric)
"""

import logging
from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.models.state import AspectCoverage, DeliberationMetrics

logger = logging.getLogger(__name__)


class QualityMetricsCalculator:
    """Calculates deliberation quality metrics.

    AUDIT FIX (Priority 4.3): Extracted from check_convergence_node monolith.
    Each metric calculation is isolated for testability and maintainability.
    """

    async def calculate_all(
        self,
        state: DeliberationGraphState,
        problem_statement: str,
    ) -> DeliberationMetrics:
        """Calculate all quality metrics for current state.

        Args:
            state: Current deliberation state
            problem_statement: The problem being deliberated

        Returns:
            DeliberationMetrics with all scores populated
        """
        contributions = state.get("contributions", [])
        round_number = state.get("round_number", 1)
        metrics = state.get("metrics")

        # Ensure metrics object exists
        if not metrics:
            logger.warning(f"Round {round_number}: Metrics object missing, creating new one")
            metrics = DeliberationMetrics()
        elif isinstance(metrics, dict):
            # Convert dict back to Pydantic model (happens after checkpoint restoration)
            logger.info(
                f"Round {round_number}: Converting metrics dict to DeliberationMetrics model"
            )
            metrics = DeliberationMetrics(**metrics)

        # Calculate convergence
        if len(contributions) >= 3:
            convergence_score = await self.calculate_convergence_score(contributions)
            metrics.convergence_score = convergence_score
            logger.info(f"Round {round_number}: Convergence score: {convergence_score:.2f}")

        # Calculate novelty and conflict (require at least 6 contributions)
        if len(contributions) >= 6:
            novelty_score = await self.calculate_novelty_score(contributions)
            conflict_score = await self.calculate_conflict_score(contributions)
            metrics.novelty_score = novelty_score
            metrics.conflict_score = conflict_score
            logger.info(
                f"Round {round_number}: Novelty: {novelty_score:.2f}, Conflict: {conflict_score:.2f}"
            )
        else:
            # Set neutral fallback values
            if not hasattr(metrics, "novelty_score") or metrics.novelty_score is None:
                metrics.novelty_score = 0.5
            if not hasattr(metrics, "conflict_score") or metrics.conflict_score is None:
                metrics.conflict_score = 0.5

        # Calculate exploration and focus (require at least 3 contributions)
        if len(contributions) >= 3:
            try:
                exploration_score, aspect_coverage = await self.calculate_exploration_score(
                    contributions=contributions[-6:],  # Recent contributions
                    problem_statement=problem_statement,
                    round_number=round_number,
                )
                metrics.exploration_score = exploration_score
                metrics.aspect_coverage = aspect_coverage
                logger.info(f"Round {round_number}: Exploration score: {exploration_score:.2f}")
            except Exception as e:
                logger.warning(f"Exploration score calculation failed: {e}", exc_info=True)
                metrics.exploration_score = 0.5  # Fallback

            try:
                focus_score = await self.calculate_focus_score(
                    contributions=contributions[-6:],
                    problem_statement=problem_statement,
                )
                metrics.focus_score = focus_score
                logger.info(f"Round {round_number}: Focus score: {focus_score:.2f}")
            except Exception as e:
                logger.warning(f"Focus score calculation failed: {e}", exc_info=True)
                metrics.focus_score = 0.8  # Fallback (assume on-topic)
        else:
            # Set fallback values for early rounds
            if not hasattr(metrics, "exploration_score") or metrics.exploration_score is None:
                metrics.exploration_score = 0.0
            if not hasattr(metrics, "focus_score") or metrics.focus_score is None:
                metrics.focus_score = 1.0

        # Calculate meeting completeness index (composite metric)
        if len(contributions) >= 3:
            from bo1.graph.meeting_config import get_meeting_config

            config = get_meeting_config(dict(state))

            try:
                meeting_completeness = self.calculate_meeting_completeness_index(
                    exploration_score=metrics.exploration_score or 0.0,
                    convergence_score=metrics.convergence_score or 0.0,
                    focus_score=metrics.focus_score or 0.0,
                    novelty_score=metrics.novelty_score or 0.5,
                    weights=config.weights,
                )
                metrics.meeting_completeness_index = meeting_completeness
                logger.info(
                    f"Round {round_number}: Meeting completeness: {meeting_completeness:.2f}"
                )
            except Exception as e:
                logger.warning(f"Completeness index calculation failed: {e}", exc_info=True)
                metrics.meeting_completeness_index = 0.5  # Fallback
        else:
            if (
                not hasattr(metrics, "meeting_completeness_index")
                or metrics.meeting_completeness_index is None
            ):
                metrics.meeting_completeness_index = 0.0

        return metrics

    async def calculate_convergence_score(self, contributions: list[Any]) -> float:
        """Calculate convergence score using semantic similarity.

        Args:
            contributions: List of contribution messages

        Returns:
            Convergence score (0.0 to 1.0)
        """
        from bo1.graph.safety.loop_prevention import _calculate_convergence_score_semantic

        # Use last 6 contributions or all if fewer available
        recent_contributions = contributions[-6:] if len(contributions) >= 6 else contributions
        return await _calculate_convergence_score_semantic(recent_contributions)

    async def calculate_novelty_score(self, contributions: list[Any]) -> float:
        """Calculate novelty score (uniqueness of recent contributions).

        Args:
            contributions: List of contribution messages

        Returns:
            Novelty score (0.0 to 1.0)
        """
        from bo1.graph.quality_metrics import calculate_novelty_score_semantic

        # Convert contributions to dict format
        contrib_dicts = []
        for contrib in contributions:
            if hasattr(contrib, "content"):
                contrib_dicts.append({"content": contrib.content})
            else:
                contrib_dicts.append({"content": str(contrib)})

        return calculate_novelty_score_semantic(contrib_dicts[-6:])

    async def calculate_conflict_score(self, contributions: list[Any]) -> float:
        """Calculate conflict score (disagreement vs agreement).

        Args:
            contributions: List of contribution messages

        Returns:
            Conflict score (0.0 to 1.0)
        """
        from bo1.graph.quality_metrics import calculate_conflict_score

        # Convert contributions to dict format
        contrib_dicts = []
        for contrib in contributions:
            if hasattr(contrib, "content"):
                contrib_dicts.append({"content": contrib.content})
            else:
                contrib_dicts.append({"content": str(contrib)})

        return calculate_conflict_score(contrib_dicts[-6:])

    async def calculate_exploration_score(
        self,
        contributions: list[Any],
        problem_statement: str,
        round_number: int,
    ) -> tuple[float, list[AspectCoverage]]:
        """Calculate exploration score (coverage of 8 critical aspects).

        Args:
            contributions: List of contribution messages
            problem_statement: The problem being deliberated
            round_number: Current round number

        Returns:
            Tuple of (exploration_score, aspect_coverage)
        """
        from bo1.graph.quality_metrics import calculate_exploration_score_llm

        return await calculate_exploration_score_llm(
            contributions=contributions,
            problem_statement=problem_statement,
            round_number=round_number,
        )

    async def calculate_focus_score(
        self,
        contributions: list[Any],
        problem_statement: str,
    ) -> float:
        """Calculate focus score (on-topic ratio).

        Args:
            contributions: List of contribution messages
            problem_statement: The problem being deliberated

        Returns:
            Focus score (0.0 to 1.0)
        """
        from bo1.graph.quality_metrics import calculate_focus_score

        return await calculate_focus_score(
            contributions=contributions,
            problem_statement=problem_statement,
        )

    def calculate_meeting_completeness_index(
        self,
        exploration_score: float,
        convergence_score: float,
        focus_score: float,
        novelty_score: float,
        weights: dict[str, float],
    ) -> float:
        """Calculate meeting completeness index (composite metric).

        Args:
            exploration_score: Coverage of 8 critical aspects (0-1)
            convergence_score: Agreement level (0-1)
            focus_score: On-topic ratio (0-1)
            novelty_score: Uniqueness of recent contributions (0-1)
            weights: Weight configuration from meeting config

        Returns:
            Meeting completeness index (0.0 to 1.0)
        """
        from bo1.graph.quality_metrics import calculate_meeting_completeness_index

        return calculate_meeting_completeness_index(
            exploration_score=exploration_score,
            convergence_score=convergence_score,
            focus_score=focus_score,
            novelty_score_recent=novelty_score,
            weights=weights,
        )
