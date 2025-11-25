"""Advanced meeting quality metrics.

This module provides functions to calculate:
- Exploration Score: Coverage of 8 critical decision aspects (NEW)
- Focus Score: Continuous on-topic ratio (ENHANCED from drift detection)
- Meeting Completeness Index: Composite quality metric (NEW)
- Novelty Score: Measures whether experts are generating new insights vs rehashing old ideas
- Conflict Score: Measures level of disagreement/debate between experts
- Drift Detection: Tracks when discussion veers off-topic from the original problem
"""

import logging
from typing import Any

from bo1.llm.embeddings import cosine_similarity, generate_embedding

logger = logging.getLogger(__name__)


# ============================================================================
# Exploration Score (NEW - LLM-based)
# ============================================================================


async def calculate_exploration_score_llm(
    contributions: list[Any],
    problem_statement: str,
    round_number: int = 1,
) -> tuple[float, list[Any]]:
    """Calculate exploration score using LLM-based Judge Agent.

    This is the PREFERRED method for exploration scoring as it uses LLM to
    understand the depth of discussion, not just keyword matching.

    Algorithm:
    1. Call Judge Agent to analyze contributions
    2. Get aspect coverage assessments (none/shallow/deep)
    3. Map: none=0.0, shallow=0.5, deep=1.0
    4. Return average across 8 aspects

    Args:
        contributions: List of ContributionMessage objects
        problem_statement: Problem being deliberated
        round_number: Current round number

    Returns:
        Tuple of (exploration_score, aspect_coverage_list)
        - exploration_score: 0.0-1.0 (0.6+ required to end, 0.7+ = well explored)
        - aspect_coverage: List of AspectCoverage objects with details

    Example:
        >>> score, coverage = await calculate_exploration_score_llm(
        ...     contributions, problem="Should we expand to EU?"
        ... )
        >>> print(f"Exploration: {score:.2f}")
        >>> missing = [a.name for a in coverage if a.level == "none"]
        >>> print(f"Missing: {missing}")
    """
    try:
        # Import here to avoid circular dependency
        from bo1.agents.judge import judge_round

        # Use Judge Agent to assess aspect coverage
        judge_output = await judge_round(
            contributions=contributions,
            problem_statement=problem_statement,
            round_number=round_number,
        )

        # Extract exploration score and coverage from judge output
        exploration_score = judge_output.exploration_score
        aspect_coverage = judge_output.aspect_coverage

        logger.info(
            f"LLM exploration score: {exploration_score:.2f} "
            f"(deep: {sum(1 for a in aspect_coverage if a.level == 'deep')}/8, "
            f"shallow: {sum(1 for a in aspect_coverage if a.level == 'shallow')}/8)"
        )

        return exploration_score, aspect_coverage

    except Exception as e:
        logger.warning(f"LLM exploration calculation failed: {e}, falling back to heuristic")
        return calculate_exploration_score_heuristic(contributions, problem_statement)


def calculate_exploration_score_heuristic(
    contributions: list[Any],
    problem_statement: str,
) -> tuple[float, list[Any]]:
    """Calculate exploration score using keyword heuristic (FALLBACK).

    This is less accurate than LLM but provides a reasonable fallback when
    LLM calls fail or budget is exceeded.

    Algorithm:
    1. Extract text from contributions
    2. For each aspect, count keyword matches
    3. 3+ matches = deep, 1-2 = shallow, 0 = none
    4. Average across aspects

    Args:
        contributions: List of ContributionMessage objects
        problem_statement: Problem being deliberated

    Returns:
        Tuple of (exploration_score, aspect_coverage_list)
    """
    from bo1.graph.meeting_config import CRITICAL_ASPECTS
    from bo1.models.state import AspectCoverage

    logger.info("Using heuristic exploration score (fallback)")

    # Combine all contribution text
    all_text = " ".join([getattr(c, "content", str(c)).lower() for c in contributions])

    # Keyword patterns for each aspect
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
            level = "deep"
            score = 1.0
            notes = f"Found {matches} keyword matches (heuristic)"
        elif matches >= 1:
            level = "shallow"
            score = 0.5
            notes = f"Found {matches} keyword matches (heuristic)"
        else:
            level = "none"
            score = 0.0
            notes = "Not mentioned (heuristic)"

        aspect_coverage.append(AspectCoverage(name=aspect, level=level, notes=notes))
        scores.append(score)

    exploration_score = sum(scores) / len(scores) if scores else 0.0

    logger.info(f"Heuristic exploration score: {exploration_score:.2f}")

    return exploration_score, aspect_coverage


# ============================================================================
# Focus Score (ENHANCED from drift detection)
# ============================================================================


async def calculate_focus_score(
    contributions: list[Any],
    problem_statement: str,
) -> float:
    """Calculate focus score using semantic similarity (ENHANCED).

    This replaces the binary drift detection with a continuous 0-1 score
    that measures how on-topic each contribution is.

    Algorithm:
    1. For each contribution, calculate semantic similarity to problem
    2. Classify: >0.80 = core (1.0), 0.60-0.80 = context (0.5), <0.60 = off_topic (0.0)
    3. Return: (core_count + 0.5 * context_count) / total_count

    Args:
        contributions: List of ContributionMessage objects
        problem_statement: Problem being deliberated

    Returns:
        Focus score 0.0-1.0
        - >0.80 = excellent focus (mostly core contributions)
        - 0.60-0.80 = moderate focus (some context)
        - <0.60 = poor focus (drifting off topic)

    Example:
        >>> focus = await calculate_focus_score(contributions, problem="Pricing strategy")
        >>> if focus < 0.60:
        ...     print("Deliberation is drifting off topic")
    """
    if not contributions:
        return 1.0  # Empty contributions = no drift

    try:
        # Generate embedding for problem statement
        problem_embedding = generate_embedding(problem_statement, input_type="document")

        # Classify each contribution
        core_count = 0
        context_count = 0
        off_topic_count = 0

        for contrib in contributions:
            content = getattr(contrib, "content", str(contrib))

            # Generate embedding for contribution
            contrib_embedding = generate_embedding(content, input_type="document")

            # Calculate similarity
            similarity = cosine_similarity(problem_embedding, contrib_embedding)

            # Classify based on similarity thresholds
            if similarity > 0.80:
                core_count += 1
            elif similarity > 0.60:
                context_count += 1
            else:
                off_topic_count += 1

        total = core_count + context_count + off_topic_count
        if total == 0:
            return 1.0

        # Focus score: core + 0.5*context weighted by total
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
    """Calculate focus score using keyword matching (FALLBACK).

    Args:
        contributions: List of ContributionMessage objects
        problem_statement: Problem being deliberated

    Returns:
        Focus score 0.0-1.0 (heuristic estimate)
    """
    if not contributions:
        return 1.0

    # Extract key terms from problem (simple tokenization)
    problem_terms = set(problem_statement.lower().split())
    problem_terms = {t for t in problem_terms if len(t) > 4}  # Filter short words

    if not problem_terms:
        return 0.8  # Assume on-topic if we can't extract terms

    # Calculate overlap for each contribution
    on_topic_count = 0

    for contrib in contributions:
        content = getattr(contrib, "content", str(contrib)).lower()
        content_terms = set(content.split())

        # Calculate term overlap
        overlap = len(problem_terms & content_terms) / len(problem_terms)

        if overlap > 0.2:  # At least 20% overlap = on-topic
            on_topic_count += 1

    focus_score = on_topic_count / len(contributions) if contributions else 1.0

    logger.info(f"Heuristic focus score: {focus_score:.2f}")

    return focus_score


# ============================================================================
# Meeting Completeness Index (NEW)
# ============================================================================


def calculate_meeting_completeness_index(
    exploration_score: float,
    convergence_score: float,
    focus_score: float,
    novelty_score_recent: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Calculate Meeting Completeness Index.

    This is the composite quality metric that combines all dimensions:
    meeting_index = wE * exploration + wC * convergence + wF * focus + wN * (1 - novelty_recent)

    Where:
    - exploration_score = coverage of 8 critical aspects
    - convergence_score = agreement level
    - focus_score = on-topic ratio
    - novelty_score_recent = recent novelty (1 - novelty = lack of novelty bonus)
    - wE, wC, wF, wN = weights (must sum to 1.0)

    Args:
        exploration_score: 0-1 (0.6+ required to end)
        convergence_score: 0-1 (semantic agreement)
        focus_score: 0-1 (on-topic ratio)
        novelty_score_recent: 0-1 (recent novelty, 0 = repetitive)
        weights: Optional custom weights dict. Default: balanced config

    Returns:
        Meeting completeness index 0-1
        - 0.7+ = high quality, can recommend ending
        - 0.5-0.7 = moderate quality
        - <0.5 = low quality, needs more exploration

    Example:
        >>> completeness = calculate_meeting_completeness_index(
        ...     exploration_score=0.68,
        ...     convergence_score=0.72,
        ...     focus_score=0.81,
        ...     novelty_score_recent=0.42
        ... )
        >>> print(f"Meeting quality: {completeness:.0%}")
        Meeting quality: 64%
    """
    # Default weights (balanced config)
    if weights is None:
        weights = {"exploration": 0.35, "convergence": 0.35, "focus": 0.20, "low_novelty": 0.10}

    # Validate weights sum to 1.0
    total_weight = sum(weights.values())
    if not (0.99 <= total_weight <= 1.01):
        logger.warning(f"Weights sum to {total_weight}, normalizing...")
        # Normalize
        weights = {k: v / total_weight for k, v in weights.items()}

    # Calculate composite index
    # Note: (1 - novelty_score_recent) = lack of novelty bonus (low novelty = good for ending)
    meeting_index = (
        weights["exploration"] * exploration_score
        + weights["convergence"] * convergence_score
        + weights["focus"] * focus_score
        + weights["low_novelty"] * (1.0 - novelty_score_recent)
    )

    # Ensure in range [0, 1]
    meeting_index = max(0.0, min(1.0, meeting_index))

    logger.info(
        f"Meeting Completeness Index: {meeting_index:.2f} "
        f"(E={exploration_score:.2f}, C={convergence_score:.2f}, "
        f"F={focus_score:.2f}, N={novelty_score_recent:.2f})"
    )

    return meeting_index


# ============================================================================
# Existing Functions (Novelty, Conflict, Drift Detection)
# ============================================================================


def calculate_novelty_score_semantic(contributions: list[dict[str, Any]]) -> float:
    """Calculate novelty score using semantic embeddings.

    For each recent contribution:
    1. Generate embedding using Voyage AI
    2. Compare to all previous contributions
    3. Novelty = 1 - (max similarity to any previous contribution)
    4. Return average novelty across recent contributions

    High similarity to past = low novelty
    Low similarity to past = high novelty

    Args:
        contributions: List of contribution dicts with 'content' field

    Returns:
        Float between 0.0-1.0 representing novelty score
        Returns 0.0 if embeddings fail or insufficient contributions
    """
    if len(contributions) < 2:
        return 0.0

    try:
        # Generate embeddings for all contributions
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

        # Calculate novelty for recent contributions
        novelty_scores = []
        recent_count = min(6, len(contributions))

        for i in range(len(embeddings) - recent_count, len(embeddings)):
            current_embedding = embeddings[i]

            # Compare to all previous embeddings
            max_similarity = 0.0
            for j in range(i):
                similarity = cosine_similarity(current_embedding, embeddings[j])
                max_similarity = max(max_similarity, similarity)

            # Novelty = 1 - max_similarity
            novelty = 1.0 - max_similarity if max_similarity > 0 else 1.0
            novelty_scores.append(novelty)

        # Return average novelty
        if novelty_scores:
            avg_novelty = sum(novelty_scores) / len(novelty_scores)
            logger.info(f"Calculated novelty score: {avg_novelty:.3f}")
            return avg_novelty

        return 0.0

    except Exception as e:
        logger.error(f"Error calculating novelty score: {e}")
        return 0.0


def calculate_conflict_score(contributions: list[dict[str, Any]]) -> float:
    """Calculate conflict score based on disagreement vs agreement keywords.

    Detects:
    - Disagreement keywords: "disagree", "however", "but", "wrong", "incorrect", "alternative"
    - Agreement keywords: "agree", "exactly", "correct", "yes", "support"

    Conflict score = (disagreement_count - agreement_count) / total_words
    Normalized to 0-1 range

    High conflict = healthy debate
    Low conflict = consensus or lack of engagement

    Args:
        contributions: List of contribution dicts with 'content' field

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

    disagreement_count = 0
    agreement_count = 0
    total_words = 0

    # Get last 6 contributions for conflict analysis
    recent = contributions[-6:] if len(contributions) > 6 else contributions

    for contribution in recent:
        content = contribution.get("content", "").lower()
        words = content.split()
        total_words += len(words)

        # Count disagreement keywords
        for word in words:
            # Remove punctuation for matching
            clean_word = word.strip(".,!?;:")
            if clean_word in disagreement_keywords:
                disagreement_count += 1
            elif clean_word in agreement_keywords:
                agreement_count += 1

    if total_words == 0:
        return 0.0

    # Calculate raw score
    raw_score = (disagreement_count - agreement_count) / total_words

    # Normalize to 0-1 range
    # Typical range: -0.02 to +0.02 (2% of words are agreement/disagreement)
    # Map: -0.02 → 0.0, 0 → 0.5, +0.02 → 1.0
    normalized = (raw_score + 0.02) / 0.04
    conflict_score = max(0.0, min(1.0, normalized))

    logger.info(
        f"Calculated conflict score: {conflict_score:.3f} "
        f"(disagreement: {disagreement_count}, agreement: {agreement_count}, "
        f"total_words: {total_words})"
    )

    return conflict_score


def detect_contribution_drift(contribution: str, problem_statement: str) -> bool:
    """Detect if a contribution has drifted off-topic from the problem.

    Algorithm:
    1. Generate embeddings for contribution and problem statement
    2. Calculate cosine similarity
    3. If similarity < 0.60 → drift detected (off-topic)

    Args:
        contribution: The contribution text to check
        problem_statement: The original problem statement

    Returns:
        True if drift detected (off-topic), False otherwise
    """
    if not contribution or not problem_statement:
        return False

    try:
        # Generate embeddings
        contribution_embedding = generate_embedding(contribution, input_type="document")
        problem_embedding = generate_embedding(problem_statement, input_type="document")

        # Calculate similarity
        similarity = cosine_similarity(contribution_embedding, problem_embedding)

        # Drift threshold: 0.60
        drift_detected = similarity < 0.60

        if drift_detected:
            logger.warning(f"Drift detected: similarity {similarity:.3f} below threshold 0.60")
        else:
            logger.debug(f"No drift: similarity {similarity:.3f}")

        return drift_detected

    except Exception as e:
        logger.error(f"Error detecting drift: {e}")
        return False
