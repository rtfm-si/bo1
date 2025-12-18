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

CLEANUP: Consolidated from quality_metrics.py - all functions now in single module.
"""

import asyncio
import logging
from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.llm.embeddings import cosine_similarity, generate_embedding
from bo1.models.state import AspectCoverage, DeliberationMetrics

logger = logging.getLogger(__name__)


# ============================================================================
# Exploration Score (LLM-based)
# ============================================================================


async def calculate_exploration_score_llm(
    contributions: list[Any],
    problem_statement: str,
    round_number: int = 1,
) -> tuple[float, list[Any], list[str], list[str]]:
    """Calculate exploration score using LLM-based Judge Agent.

    This is the PREFERRED method for exploration scoring as it uses LLM to
    understand the depth of discussion, not just keyword matching.

    Args:
        contributions: List of ContributionMessage objects
        problem_statement: Problem being deliberated
        round_number: Current round number

    Returns:
        Tuple of (exploration_score, aspect_coverage_list, focus_prompts, missing_aspects)
    """
    try:
        from bo1.agents.judge import judge_round

        judge_output = await judge_round(
            contributions=contributions,
            problem_statement=problem_statement,
            round_number=round_number,
        )

        exploration_score = judge_output.exploration_score
        aspect_coverage = judge_output.aspect_coverage
        focus_prompts = judge_output.next_round_focus_prompts
        missing_aspects = judge_output.missing_critical_aspects

        logger.info(
            f"LLM exploration score: {exploration_score:.2f} "
            f"(deep: {sum(1 for a in aspect_coverage if a.level == 'deep')}/8, "
            f"shallow: {sum(1 for a in aspect_coverage if a.level == 'shallow')}/8, "
            f"missing: {missing_aspects}, focus_prompts: {len(focus_prompts)})"
        )

        return exploration_score, aspect_coverage, focus_prompts, missing_aspects

    except Exception as e:
        logger.warning(f"LLM exploration calculation failed: {e}, falling back to heuristic")
        score, coverage = calculate_exploration_score_heuristic(contributions, problem_statement)
        missing = [a.name for a in coverage if a.level in ("none", "shallow")]
        return score, coverage, [], missing


def calculate_exploration_score_heuristic(
    contributions: list[Any],
    problem_statement: str,
) -> tuple[float, list[Any]]:
    """Calculate exploration score using keyword heuristic (FALLBACK)."""
    from bo1.graph.meeting_config import CRITICAL_ASPECTS

    logger.info("Using heuristic exploration score (fallback)")

    all_text = " ".join([getattr(c, "content", str(c)).lower() for c in contributions])

    aspect_keywords = {
        "problem_clarity": ["problem is", "we need to", "goal is", "objective is", "trying to"],
        "objectives": ["success", "target", "metric", "achieve", "goal", "outcome"],
        "options_alternatives": [
            "option",
            "alternative",
            "could also",
            "instead",
            "or we could",
            "another approach",
        ],
        "key_assumptions": ["assume", "assumption", "if", "provided that", "given that", "presume"],
        "risks_failure_modes": [
            "risk",
            "fail",
            "could go wrong",
            "danger",
            "threat",
            "concern",
            "downside",
        ],
        "constraints": ["budget", "time", "resource", "limitation", "can't", "cannot", "limited"],
        "stakeholders_impact": [
            "stakeholder",
            "customer",
            "team",
            "user",
            "affect",
            "impact",
            "people",
        ],
        "dependencies_unknowns": [
            "depend",
            "unknown",
            "unclear",
            "need to know",
            "blocker",
            "requires",
        ],
    }

    aspect_coverage = []
    scores = []

    for aspect in CRITICAL_ASPECTS:
        keywords = aspect_keywords.get(aspect, [])
        matches = sum(1 for keyword in keywords if keyword in all_text)

        if matches >= 3:
            level, score, notes = "deep", 1.0, f"Found {matches} keyword matches (heuristic)"
        elif matches >= 1:
            level, score, notes = "shallow", 0.5, f"Found {matches} keyword matches (heuristic)"
        else:
            level, score, notes = "none", 0.0, "Not mentioned (heuristic)"

        aspect_coverage.append(AspectCoverage(name=aspect, level=level, notes=notes))
        scores.append(score)

    exploration_score = sum(scores) / len(scores) if scores else 0.0
    logger.info(f"Heuristic exploration score: {exploration_score:.2f}")

    return exploration_score, aspect_coverage


# ============================================================================
# Focus Score
# ============================================================================


async def calculate_focus_score(
    contributions: list[Any],
    problem_statement: str,
) -> float:
    """Calculate focus score using semantic similarity.

    Returns:
        Focus score 0.0-1.0 (>0.80 = excellent, 0.60-0.80 = moderate, <0.60 = poor)
    """
    if not contributions:
        return 1.0

    try:
        problem_embedding = generate_embedding(problem_statement, input_type="document")

        core_count = context_count = off_topic_count = 0

        for contrib in contributions:
            content = getattr(contrib, "content", str(contrib))
            contrib_embedding = generate_embedding(content, input_type="document")
            similarity = cosine_similarity(problem_embedding, contrib_embedding)

            if similarity > 0.80:
                core_count += 1
            elif similarity > 0.60:
                context_count += 1
            else:
                off_topic_count += 1

        total = core_count + context_count + off_topic_count
        if total == 0:
            return 1.0

        focus_score = (core_count + 0.5 * context_count) / total

        logger.info(
            f"Focus score: {focus_score:.2f} "
            f"(core: {core_count}, context: {context_count}, off_topic: {off_topic_count})"
        )

        return focus_score

    except Exception as e:
        logger.warning(f"Semantic focus calculation failed: {e}, falling back to heuristic")
        return calculate_focus_score_heuristic(contributions, problem_statement)


def calculate_focus_score_heuristic(
    contributions: list[Any],
    problem_statement: str,
) -> float:
    """Calculate focus score using keyword matching (FALLBACK)."""
    if not contributions:
        return 1.0

    problem_terms = set(problem_statement.lower().split())
    problem_terms = {t for t in problem_terms if len(t) > 4}

    if not problem_terms:
        return 0.8

    on_topic_count = 0
    for contrib in contributions:
        content = getattr(contrib, "content", str(contrib)).lower()
        content_terms = set(content.split())
        overlap = len(problem_terms & content_terms) / len(problem_terms)
        if overlap > 0.2:
            on_topic_count += 1

    focus_score = on_topic_count / len(contributions) if contributions else 1.0
    logger.info(f"Heuristic focus score: {focus_score:.2f}")

    return focus_score


# ============================================================================
# Meeting Completeness Index
# ============================================================================


def calculate_meeting_completeness_index(
    exploration_score: float,
    convergence_score: float,
    focus_score: float,
    novelty_score_recent: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate Meeting Completeness Index (composite quality metric).

    meeting_index = wE * exploration + wC * convergence + wF * focus + wN * (1 - novelty_recent)
    """
    if weights is None:
        weights = {"exploration": 0.35, "convergence": 0.35, "focus": 0.20, "low_novelty": 0.10}

    total_weight = sum(weights.values())
    if not (0.99 <= total_weight <= 1.01):
        logger.warning(f"Weights sum to {total_weight}, normalizing...")
        weights = {k: v / total_weight for k, v in weights.items()}

    meeting_index = (
        weights["exploration"] * exploration_score
        + weights["convergence"] * convergence_score
        + weights["focus"] * focus_score
        + weights["low_novelty"] * (1.0 - novelty_score_recent)
    )

    meeting_index = max(0.0, min(1.0, meeting_index))

    logger.info(
        f"Meeting Completeness Index: {meeting_index:.2f} "
        f"(E={exploration_score:.2f}, C={convergence_score:.2f}, "
        f"F={focus_score:.2f}, N={novelty_score_recent:.2f})"
    )

    return meeting_index


# ============================================================================
# Novelty Score
# ============================================================================


def calculate_novelty_score_semantic(contributions: list[dict[str, Any]]) -> float:
    """Calculate novelty score using semantic embeddings.

    High similarity to past = low novelty; Low similarity to past = high novelty.

    Returns:
        Float between 0.0-1.0 representing novelty score
    """
    if len(contributions) < 2:
        return 0.0

    try:
        texts = [c.get("content", "") for c in contributions]
        embeddings = []

        for text in texts:
            if not text:
                continue
            try:
                embedding = generate_embedding(text, input_type="document")
                embeddings.append(embedding)
            except Exception as e:
                logger.warning(f"Failed to generate embedding: {e}")
                continue

        if len(embeddings) < 2:
            logger.warning("Not enough embeddings generated for novelty calculation")
            return 0.0

        novelty_scores = []
        recent_count = min(6, len(contributions))

        for i in range(len(embeddings) - recent_count, len(embeddings)):
            current_embedding = embeddings[i]
            max_similarity = 0.0
            for j in range(i):
                similarity = cosine_similarity(current_embedding, embeddings[j])
                max_similarity = max(max_similarity, similarity)

            novelty = 1.0 - max_similarity if max_similarity > 0 else 1.0
            novelty_scores.append(novelty)

        if novelty_scores:
            avg_novelty = sum(novelty_scores) / len(novelty_scores)
            logger.info(f"Calculated novelty score: {avg_novelty:.3f}")
            return avg_novelty

        return 0.0

    except Exception as e:
        logger.error(f"Error calculating novelty score: {e}")
        return 0.0


# ============================================================================
# Conflict Score
# ============================================================================


def calculate_conflict_score(contributions: list[dict[str, Any]]) -> float:
    """Calculate conflict score based on disagreement vs agreement keywords.

    High conflict = healthy debate; Low conflict = consensus or lack of engagement.

    Returns:
        Float between 0.0-1.0 representing conflict score
    """
    if not contributions:
        return 0.0

    disagreement_keywords = {
        "disagree",
        "however",
        "but",
        "wrong",
        "incorrect",
        "alternative",
        "unfortunately",
        "concern",
        "issue",
        "problem",
        "challenge",
        "risk",
        "different",
        "oppose",
        "contrary",
        "doubt",
        "question",
    }

    agreement_keywords = {
        "agree",
        "exactly",
        "correct",
        "yes",
        "support",
        "absolutely",
        "indeed",
        "definitely",
        "certainly",
        "perfect",
        "right",
        "good",
    }

    disagreement_count = agreement_count = total_words = 0

    recent = contributions[-6:] if len(contributions) > 6 else contributions

    for contribution in recent:
        content = contribution.get("content", "").lower()
        words = content.split()
        total_words += len(words)

        for word in words:
            clean_word = word.strip(".,!?;:")
            if clean_word in disagreement_keywords:
                disagreement_count += 1
            elif clean_word in agreement_keywords:
                agreement_count += 1

    if total_words == 0:
        return 0.0

    raw_score = (disagreement_count - agreement_count) / total_words
    normalized = (raw_score + 0.02) / 0.04
    conflict_score = max(0.0, min(1.0, normalized))

    logger.info(
        f"Calculated conflict score: {conflict_score:.3f} "
        f"(disagreement: {disagreement_count}, agreement: {agreement_count}, "
        f"total_words: {total_words})"
    )

    return conflict_score


# ============================================================================
# Drift Detection
# ============================================================================


def detect_contribution_drift(contribution: str, problem_statement: str) -> bool:
    """Detect if a contribution has drifted off-topic from the problem.

    Returns:
        True if drift detected (off-topic), False otherwise
    """
    if not contribution or not problem_statement:
        return False

    try:
        contribution_embedding = generate_embedding(contribution, input_type="document")
        problem_embedding = generate_embedding(problem_statement, input_type="document")

        similarity = cosine_similarity(contribution_embedding, problem_embedding)
        drift_detected = similarity < 0.60

        if drift_detected:
            logger.warning(f"Drift detected: similarity {similarity:.3f} below threshold 0.60")
        else:
            logger.debug(f"No drift: similarity {similarity:.3f}")

        return drift_detected

    except Exception as e:
        logger.error(f"Error detecting drift: {e}")
        return False


# ============================================================================
# QualityMetricsCalculator Class
# ============================================================================


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
            focus_task = self.calculate_focus_score_async(
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
                meeting_completeness = self.calculate_meeting_completeness_index_method(
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
        return await calculate_exploration_score_llm(
            contributions=contributions,
            problem_statement=problem_statement,
            round_number=round_number,
        )

    async def calculate_focus_score_async(
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
        return await calculate_focus_score(
            contributions=contributions,
            problem_statement=problem_statement,
        )

    def calculate_meeting_completeness_index_method(
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
