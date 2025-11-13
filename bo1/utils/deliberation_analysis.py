"""Deliberation analysis utilities for detecting discussion patterns.

Provides reusable pattern detection methods to identify:
- Premature consensus
- Unverified claims
- Negativity spirals
- Circular arguments
- Research needs
"""

from bo1.constants import ThresholdValues
from bo1.models.state import ContributionMessage, DeliberationState


class DeliberationAnalyzer:
    """Utilities for analyzing deliberation quality and patterns.

    Consolidates detection methods used by facilitator to identify
    problematic patterns that may require intervention.
    """

    @staticmethod
    def detect_premature_consensus(contributions: list[ContributionMessage]) -> bool:
        """Detect if group is agreeing too quickly without exploration.

        Args:
            contributions: Recent contributions to analyze

        Returns:
            True if premature consensus detected

        Example:
            >>> analyzer = DeliberationAnalyzer()
            >>> recent = state.contributions[-6:]  # Last 2 rounds
            >>> if analyzer.detect_premature_consensus(recent):
            ...     trigger_contrarian_moderator()
        """
        if len(contributions) < 4:
            return False

        # Count agreement keywords
        agreement_keywords = ["agree", "yes", "correct", "exactly", "indeed", "aligned", "same"]
        total_words = 0
        agreement_count = 0

        for contrib in contributions:
            words = contrib.content.lower().split()
            total_words += len(words)
            agreement_count += sum(
                1 for word in words if any(kw in word for kw in agreement_keywords)
            )

        if total_words == 0:
            return False

        # If >15% agreement words in early rounds = premature consensus
        agreement_ratio = agreement_count / total_words
        return agreement_ratio > ThresholdValues.AGREEMENT_KEYWORDS_RATIO

    @staticmethod
    def detect_unverified_claims(contributions: list[ContributionMessage]) -> bool:
        """Detect claims made without supporting evidence.

        Args:
            contributions: Recent contributions to analyze

        Returns:
            True if unverified claims detected

        Example:
            >>> if analyzer.detect_unverified_claims(recent):
            ...     trigger_skeptic_moderator()
        """
        claim_keywords = ["should", "must", "will definitely", "certainly", "always", "never"]
        evidence_keywords = [
            "because",
            "data shows",
            "research indicates",
            "according to",
            "evidence",
            "study",
        ]

        for contrib in contributions:
            text = contrib.content.lower()
            has_claims = sum(1 for kw in claim_keywords if kw in text)
            has_evidence = sum(1 for kw in evidence_keywords if kw in text)

            # If 3+ claims but no evidence markers = red flag
            if has_claims >= 3 and has_evidence == 0:
                return True

        return False

    @staticmethod
    def detect_negativity_spiral(contributions: list[ContributionMessage]) -> bool:
        """Detect if discussion is stuck in problems without solutions.

        Args:
            contributions: Recent contributions to analyze

        Returns:
            True if negativity spiral detected

        Example:
            >>> if analyzer.detect_negativity_spiral(recent):
            ...     trigger_optimist_moderator()
        """
        negative_keywords = [
            "won't work",
            "impossible",
            "can't",
            "too risky",
            "fail",
            "problem",
            "issue",
        ]
        positive_keywords = [
            "could",
            "might",
            "opportunity",
            "solution",
            "approach",
            "possible",
            "potential",
        ]

        negative_count = 0
        positive_count = 0

        for contrib in contributions:
            text = contrib.content.lower()
            negative_count += sum(1 for kw in negative_keywords if kw in text)
            positive_count += sum(1 for kw in positive_keywords if kw in text)

        # If 3x more negative than positive = spiral
        if positive_count == 0:
            return negative_count > 5

        return negative_count > 3 * positive_count

    @staticmethod
    def detect_circular_arguments(contributions: list[ContributionMessage]) -> bool:
        """Detect if same arguments are repeating.

        Args:
            contributions: Recent contributions to analyze

        Returns:
            True if circular arguments detected

        Example:
            >>> if analyzer.detect_circular_arguments(recent):
            ...     trigger_contrarian_moderator()
        """
        if len(contributions) < 4:
            return False

        # Extract key phrases (4+ char words, deduplicated per contribution)
        all_phrases: list[str] = []
        for contrib in contributions:
            words = [w.lower() for w in contrib.content.split() if len(w) >= 4]
            unique_in_contrib = list(set(words))
            all_phrases.extend(unique_in_contrib)

        if not all_phrases:
            return False

        unique_phrases = len(set(all_phrases))
        total_phrases = len(all_phrases)

        # If <40% are unique = lots of repetition = circular
        return (unique_phrases / total_phrases) < 0.40

    @staticmethod
    def check_research_needed(state: DeliberationState) -> dict[str, str] | None:
        """Check if research or external information is needed.

        Args:
            state: Current deliberation state

        Returns:
            dict with "query" and "reason" if research needed, None otherwise

        Example:
            >>> research = analyzer.check_research_needed(state)
            >>> if research:
            ...     trigger_researcher(research['query'])
        """
        if len(state.contributions) < 2:
            return None

        recent = state.contributions[-3:]  # Last round

        # Look for questions or information gaps
        question_patterns = [
            "what is",
            "what are",
            "how much",
            "how many",
            "do we know",
            "unclear",
            "uncertain",
            "need data",
            "need information",
            "need research",
            "don't have data",
            "missing information",
        ]

        for contrib in recent:
            text = contrib.content.lower()
            for pattern in question_patterns:
                if pattern in text:
                    # Extract the sentence containing the pattern
                    sentences = text.split(".")
                    for sentence in sentences:
                        if pattern in sentence:
                            query = sentence.strip()[:200]  # Limit to 200 chars
                            return {
                                "query": query,
                                "reason": f"{contrib.persona_name} raised: {query}",
                            }

        return None
