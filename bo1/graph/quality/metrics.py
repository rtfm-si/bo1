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

import asyncio
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

        # P2 BATCH FIX: Run all metric calculations in PARALLEL using asyncio.gather
        # This reduces latency by 60-80% (from sequential 1000-2000ms to parallel ~400ms)
        if len(contributions) >= 3:
            # Build list of tasks based on contribution count thresholds
            recent_contributions = contributions[-6:]

            # Always run these with 3+ contributions
            convergence_task = self.calculate_convergence_score(contributions)
            exploration_task = self.calculate_exploration_score(
                contributions=recent_contributions,
                problem_statement=problem_statement,
                round_number=round_number,
            )
            focus_task = self.calculate_focus_score(
                contributions=recent_contributions,
                problem_statement=problem_statement,
            )

            # Only run novelty/conflict with 6+ contributions
            if len(contributions) >= 6:
                novelty_task = self.calculate_novelty_score(contributions)
                conflict_task = self.calculate_conflict_score(contributions)

                # Run ALL 5 metrics in parallel
                logger.info(f"Round {round_number}: Running 5 metrics in parallel (BATCH)")
                results = await asyncio.gather(
                    convergence_task,
                    novelty_task,
                    conflict_task,
                    exploration_task,
                    focus_task,
                    return_exceptions=True,
                )
                # Unpack results (asyncio.gather with return_exceptions returns list)
                convergence_result = results[0]
                novelty_result = results[1]
                conflict_result = results[2]
                exploration_result = results[3]
                focus_result = results[4]

                # Process novelty result
                if isinstance(novelty_result, BaseException):
                    logger.warning(f"Novelty score calculation failed: {novelty_result}")
                    metrics.novelty_score = 0.5
                else:
                    metrics.novelty_score = novelty_result
                    logger.info(f"Round {round_number}: Novelty: {novelty_result:.2f}")

                # Process conflict result
                if isinstance(conflict_result, BaseException):
                    logger.warning(f"Conflict score calculation failed: {conflict_result}")
                    metrics.conflict_score = 0.5
                else:
                    metrics.conflict_score = conflict_result
                    logger.info(f"Round {round_number}: Conflict: {conflict_result:.2f}")
            else:
                # Run only 3 metrics in parallel (not enough contributions for novelty/conflict)
                logger.info(f"Round {round_number}: Running 3 metrics in parallel (BATCH)")
                results_3 = await asyncio.gather(
                    convergence_task,
                    exploration_task,
                    focus_task,
                    return_exceptions=True,
                )
                convergence_result = results_3[0]
                exploration_result = results_3[1]
                focus_result = results_3[2]

                # Set fallback values for novelty/conflict
                if not hasattr(metrics, "novelty_score") or metrics.novelty_score is None:
                    metrics.novelty_score = 0.5
                if not hasattr(metrics, "conflict_score") or metrics.conflict_score is None:
                    metrics.conflict_score = 0.5

            # Process convergence result
            if isinstance(convergence_result, BaseException):
                logger.warning(f"Convergence score calculation failed: {convergence_result}")
                metrics.convergence_score = 0.0
            else:
                metrics.convergence_score = convergence_result
                logger.info(f"Round {round_number}: Convergence score: {convergence_result:.2f}")

            # Process exploration result (tuple with focus_prompts)
            if isinstance(exploration_result, BaseException):
                logger.warning(
                    f"Exploration score calculation failed: {exploration_result}", exc_info=True
                )
                metrics.exploration_score = 0.5
            else:
                exploration_score, aspect_coverage, focus_prompts, missing_aspects = (
                    exploration_result
                )
                metrics.exploration_score = exploration_score
                metrics.aspect_coverage = aspect_coverage
                # P2 FIX: Store focus prompts for next round - enables feedback loop!
                metrics.next_round_focus_prompts = focus_prompts
                metrics.missing_critical_aspects = missing_aspects
                logger.info(
                    f"Round {round_number}: Exploration score: {exploration_score:.2f}, "
                    f"missing: {missing_aspects}, focus_prompts: {len(focus_prompts)}"
                )

            # Process focus result
            if isinstance(focus_result, BaseException):
                logger.warning(f"Focus score calculation failed: {focus_result}", exc_info=True)
                metrics.focus_score = 0.8  # Fallback (assume on-topic)
            else:
                metrics.focus_score = focus_result
                logger.info(f"Round {round_number}: Focus score: {focus_result:.2f}")
        else:
            # Set fallback values for early rounds (< 3 contributions)
            if not hasattr(metrics, "exploration_score") or metrics.exploration_score is None:
                metrics.exploration_score = 0.0
            if not hasattr(metrics, "focus_score") or metrics.focus_score is None:
                metrics.focus_score = 1.0
            if not hasattr(metrics, "novelty_score") or metrics.novelty_score is None:
                metrics.novelty_score = 0.5
            if not hasattr(metrics, "conflict_score") or metrics.conflict_score is None:
                metrics.conflict_score = 0.5

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
    ) -> tuple[float, list[AspectCoverage], list[str], list[str]]:
        """Calculate exploration score (coverage of 8 critical aspects).

        P2 FIX: Now returns focus prompts for feedback loop to experts.

        Args:
            contributions: List of contribution messages
            problem_statement: The problem being deliberated
            round_number: Current round number

        Returns:
            Tuple of (exploration_score, aspect_coverage, focus_prompts, missing_aspects)
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


# ============================================================================
# Convergence Calculation Helpers (Moved from loop_prevention.py)
# ============================================================================


async def _calculate_convergence_score_semantic(contributions: list[Any]) -> float:
    """Calculate convergence score using semantic similarity (PREFERRED).

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to metrics.py.
    This is a quality metric calculation, not loop prevention logic.

    Uses Voyage AI embeddings to detect semantic repetition in contributions.
    This approach catches paraphrased content that keyword matching misses.

    Algorithm:
    1. Generate embeddings for recent contributions (last 6)
    2. Compare each contribution to all previous ones
    3. High similarity (>0.90) = likely repetition
    4. Return average repetition rate as convergence score

    Args:
        contributions: List of recent ContributionMessage objects

    Returns:
        Convergence score between 0.0 and 1.0
        - 1.0 = high convergence (lots of repetition)
        - 0.0 = no convergence (diverse contributions)
    """
    if len(contributions) < 3:
        return 0.0

    try:
        from bo1.llm.embeddings import cosine_similarity, generate_embedding

        # Extract content from contributions
        texts = []
        for contrib in contributions:
            content = contrib.content if hasattr(contrib, "content") else str(contrib)
            texts.append(content)

        # Generate embeddings for all contributions
        embeddings: list[list[float]] = []
        for text in texts:
            try:
                embedding = generate_embedding(text, input_type="document")
                embeddings.append(embedding)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}, falling back to keyword method")
                return _calculate_convergence_score_keyword(contributions)

        # Compare each contribution to all previous ones
        repetition_scores: list[float] = []
        for i in range(1, len(embeddings)):
            max_similarity = 0.0
            for j in range(i):
                # Cosine similarity between contribution i and j
                similarity = cosine_similarity(embeddings[i], embeddings[j])
                max_similarity = max(max_similarity, similarity)

            # Similarity thresholds:
            # >0.90 = likely exact repetition (score: 1.0)
            # 0.85-0.90 = paraphrased content (score: 0.7)
            # 0.80-0.85 = similar theme (score: 0.4)
            # <0.80 = new content (score: 0.0)
            if max_similarity > 0.90:
                repetition_scores.append(1.0)
            elif max_similarity > 0.85:
                repetition_scores.append(0.7)
            elif max_similarity > 0.80:
                repetition_scores.append(0.4)
            else:
                repetition_scores.append(0.0)

        # Convergence = average repetition rate
        convergence = sum(repetition_scores) / len(repetition_scores) if repetition_scores else 0.0

        logger.debug(
            f"Semantic convergence: {convergence:.2f} "
            f"(similarities: {[f'{s:.2f}' for s in repetition_scores]})"
        )

        return convergence

    except ImportError:
        logger.warning("voyageai not installed, falling back to keyword method")
        return _calculate_convergence_score_keyword(contributions)
    except Exception as e:
        logger.warning(
            f"Semantic convergence calculation failed: {e}, falling back to keyword method"
        )
        return _calculate_convergence_score_keyword(contributions)


def _calculate_convergence_score_keyword(contributions: list[Any]) -> float:
    """Calculate convergence score using keyword matching (FALLBACK).

    AUDIT FIX (Priority 4.3): Moved from loop_prevention.py to metrics.py.
    This is a quality metric calculation, not loop prevention logic.

    Uses keyword-based heuristic: count agreement vs. total words.
    Higher score = more convergence/agreement.

    This is a FALLBACK method when semantic similarity is unavailable.
    Keyword matching has high false negative rate (misses paraphrasing).

    Args:
        contributions: List of recent ContributionMessage objects

    Returns:
        Convergence score between 0.0 and 1.0
    """
    if not contributions:
        return 0.0

    # Agreement keywords that indicate convergence
    agreement_keywords = [
        "agree",
        "yes",
        "correct",
        "exactly",
        "support",
        "aligned",
        "consensus",
        "concur",
        "same",
        "similarly",
        "indeed",
        "right",
    ]

    # Count agreement keywords across all contributions
    total_words = 0
    agreement_count = 0

    for contrib in contributions:
        # Get content from ContributionMessage
        content = contrib.content.lower() if hasattr(contrib, "content") else str(contrib).lower()
        words = content.split()
        total_words += len(words)

        # Count agreement keywords
        for keyword in agreement_keywords:
            agreement_count += content.count(keyword)

    if total_words == 0:
        return 0.0

    # Calculate ratio and normalize to 0-1 scale
    # We expect ~1-2% agreement keywords for high convergence
    # So we scale: 2% agreement = 1.0 convergence
    raw_score = (agreement_count / total_words) * 50.0  # 2% * 50 = 1.0
    convergence = min(1.0, max(0.0, raw_score))

    logger.debug(f"Keyword convergence: {convergence:.2f} (fallback method)")

    return convergence
