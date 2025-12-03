"""Metrics calculation for deliberation quality and convergence.

Provides heuristic-based metrics for:
- Convergence: Agreement levels between participants
- Novelty: Introduction of new ideas
- Conflict: Disagreement and tension

Uses keyword analysis for v2 (can be upgraded to embeddings in future versions).
"""

import logging
from typing import Any

from bo1.models.state import ContributionMessage

logger = logging.getLogger(__name__)


class MetricsCalculator:
    """Calculate deliberation quality metrics.

    Provides methods to assess the health and progress of a deliberation
    using heuristic keyword analysis.
    """

    # Keywords for convergence detection
    AGREEMENT_KEYWORDS = [
        "agree",
        "yes",
        "correct",
        "exactly",
        "indeed",
        "aligned",
        "consensus",
        "support",
        "concur",
        "same",
        "similar",
    ]

    # Keywords for conflict detection
    DISAGREEMENT_KEYWORDS = [
        "disagree",
        "no",
        "wrong",
        "incorrect",
        "however",
        "but",
        "concern",
        "risk",
        "problem",
        "issue",
        "challenge",
    ]

    @staticmethod
    def calculate_round_metrics(
        contributions: list[ContributionMessage], round_number: int
    ) -> dict[str, Any]:
        """Calculate convergence and consensus metrics for current round.

        Uses heuristic-based analysis for v2 (can be upgraded to embeddings in v3).

        Args:
            contributions: All contributions so far
            round_number: Current round number

        Returns:
            Dictionary with metrics:
            - convergence: 0-1 (higher = more agreement)
            - novelty: 0-1 (higher = more new ideas)
            - conflict: 0-1 (higher = more disagreement)
            - should_stop: bool (recommendation to stop deliberation)
            - stop_reason: str or None (explanation if should_stop is True)

        Example:
            >>> metrics = MetricsCalculator.calculate_round_metrics(contributions, 3)
            >>> metrics["convergence"]
            0.72
            >>> metrics["should_stop"]
            False
        """
        if len(contributions) < 2:
            return {
                "convergence": 0.0,
                "novelty": 1.0,
                "conflict": 0.0,
                "should_stop": False,
                "stop_reason": None,
            }

        # Analyze recent contributions (last 2 rounds = ~6 contributions)
        recent_contributions = contributions[-6:]

        convergence = MetricsCalculator.calculate_convergence(recent_contributions)
        novelty = MetricsCalculator.calculate_novelty(recent_contributions)
        conflict = MetricsCalculator.calculate_conflict(recent_contributions)

        # Decide if deliberation should stop early
        should_stop = False
        stop_reason = None

        if convergence > 0.85 and novelty < 0.30 and round_number > 5:
            should_stop = True
            stop_reason = "High convergence + low novelty"

        if conflict > 0.80 and round_number > 10:
            should_stop = True
            stop_reason = "Deadlock detected"

        return {
            "convergence": convergence,
            "novelty": novelty,
            "conflict": conflict,
            "should_stop": should_stop,
            "stop_reason": stop_reason,
        }

    @staticmethod
    def calculate_convergence(contributions: list[ContributionMessage]) -> float:
        """Calculate convergence score (0-1, higher = more agreement).

        Uses keyword-based heuristic: count agreement vs. total words.

        Args:
            contributions: List of contributions to analyze

        Returns:
            Convergence score from 0 (no agreement) to 1 (full consensus)

        Example:
            >>> contribs = [ContributionMessage(..., content="I agree with this approach...")]
            >>> MetricsCalculator.calculate_convergence(contribs)
            0.43
        """
        if not contributions:
            return 0.0

        total_words = 0
        agreement_count = 0

        for contrib in contributions:
            words = contrib.content.lower().split()
            total_words += len(words)
            agreement_count += sum(
                1
                for word in words
                if any(kw in word for kw in MetricsCalculator.AGREEMENT_KEYWORDS)
            )

        if total_words == 0:
            return 0.0

        # Normalize to 0-1 range (assume 10% agreement words = full convergence)
        raw_score = agreement_count / total_words
        return min(raw_score * 10, 1.0)

    @staticmethod
    def calculate_novelty(contributions: list[ContributionMessage]) -> float:
        """Calculate novelty score (0-1, higher = more new ideas).

        Uses simple heuristic: check for unique vs. repeated key phrases.

        Args:
            contributions: List of contributions to analyze

        Returns:
            Novelty score from 0 (all repeated ideas) to 1 (all new ideas)

        Example:
            >>> contribs = [ContributionMessage(..., content="Consider market dynamics...")]
            >>> MetricsCalculator.calculate_novelty(contribs)
            0.81
        """
        if not contributions:
            return 1.0

        # Extract key phrases (3+ char words, lowercase, deduplicated per contribution)
        all_phrases: list[str] = []
        for contrib in contributions:
            words = [w.lower() for w in contrib.content.split() if len(w) > 3]
            unique_words_in_contrib = list(set(words))
            all_phrases.extend(unique_words_in_contrib)

        if not all_phrases:
            return 0.5

        unique_phrases = len(set(all_phrases))
        total_phrases = len(all_phrases)

        # Novelty = ratio of unique to total phrases
        return unique_phrases / total_phrases

    @staticmethod
    def calculate_conflict(contributions: list[ContributionMessage]) -> float:
        """Calculate conflict score (0-1, higher = more disagreement).

        Uses keyword-based heuristic: count disagreement vs. total words.

        Args:
            contributions: List of contributions to analyze

        Returns:
            Conflict score from 0 (no disagreement) to 1 (high conflict)

        Example:
            >>> contribs = [ContributionMessage(..., content="I disagree with this approach...")]
            >>> MetricsCalculator.calculate_conflict(contribs)
            0.37
        """
        if not contributions:
            return 0.0

        total_words = 0
        disagreement_count = 0

        for contrib in contributions:
            words = contrib.content.lower().split()
            total_words += len(words)
            disagreement_count += sum(
                1
                for word in words
                if any(kw in word for kw in MetricsCalculator.DISAGREEMENT_KEYWORDS)
            )

        if total_words == 0:
            return 0.0

        # Normalize to 0-1 range (assume 10% disagreement words = full conflict)
        raw_score = disagreement_count / total_words
        return min(raw_score * 10, 1.0)
