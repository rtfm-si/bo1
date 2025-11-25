"""Semantic deduplication for contribution filtering.

This module prevents experts from repeating similar points by using
Voyage AI embeddings to detect semantic similarity between contributions.

Key Features:
- Real-time deduplication during parallel round execution
- Configurable similarity threshold (default: 0.80)
- Detailed logging of filtered contributions
- Fallback to keyword-based matching if embeddings fail

Architecture:
- Uses Voyage AI voyage-3 model (1024 dimensions)
- Cosine similarity for comparison
- Threshold: 0.80 = very similar, likely repetition
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Default similarity threshold for considering contributions duplicate
# 0.80 = very similar content (likely paraphrasing)
# 0.90 = nearly identical (exact repetition)
# 0.70 = similar theme but different details
DEFAULT_SIMILARITY_THRESHOLD = 0.80


async def check_semantic_novelty(
    new_contribution: str,
    previous_contributions: list[str],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> tuple[bool, float]:
    """Check if contribution is semantically novel using Voyage AI.

    This function compares a new contribution against all previous contributions
    using semantic embeddings to detect repetition or paraphrasing.

    Args:
        new_contribution: The new contribution text to check
        previous_contributions: List of previous contribution texts to compare against
        threshold: Similarity threshold (0.0-1.0). Above this = not novel.
                  Default: 0.80 (very similar = likely repetition)

    Returns:
        Tuple of (is_novel: bool, max_similarity_score: float)
        - is_novel: True if contribution is novel (all similarities below threshold)
        - max_similarity_score: Highest similarity score found

    Example:
        >>> is_novel, score = await check_semantic_novelty(
        ...     "We should focus on user experience",
        ...     ["User experience is our top priority", "Sales are declining"]
        ... )
        >>> print(f"Novel: {is_novel}, Max similarity: {score:.2f}")
        Novel: False, Max similarity: 0.85
    """
    if not new_contribution or not new_contribution.strip():
        logger.warning("Empty new contribution, marking as not novel")
        return False, 0.0

    if not previous_contributions:
        # No previous contributions, always novel
        return True, 0.0

    try:
        from bo1.llm.embeddings import cosine_similarity, generate_embedding

        # Generate embedding for new contribution
        new_embedding = generate_embedding(new_contribution, input_type="document")

        # Compare against all previous contributions
        max_similarity = 0.0

        for prev_contrib in previous_contributions:
            if not prev_contrib or not prev_contrib.strip():
                continue

            try:
                # Generate embedding for previous contribution
                prev_embedding = generate_embedding(prev_contrib, input_type="document")

                # Calculate cosine similarity
                similarity = cosine_similarity(new_embedding, prev_embedding)

                # Track maximum
                max_similarity = max(max_similarity, similarity)

                # Early exit if we find high similarity
                if similarity > threshold:
                    logger.info(
                        f"Semantic deduplication: High similarity detected "
                        f"(score: {similarity:.3f} > threshold: {threshold:.3f})"
                    )
                    logger.debug(
                        f"New: '{new_contribution[:50]}...' ≈ Previous: '{prev_contrib[:50]}...'"
                    )
                    return False, similarity

            except Exception as e:
                logger.warning(
                    f"Failed to generate embedding for previous contribution: {e}. "
                    "Skipping comparison."
                )
                continue

        # All comparisons below threshold = novel
        is_novel = max_similarity <= threshold
        logger.debug(
            f"Semantic novelty check: {'NOVEL' if is_novel else 'DUPLICATE'} "
            f"(max similarity: {max_similarity:.3f}, threshold: {threshold:.3f})"
        )

        return is_novel, max_similarity

    except ImportError:
        logger.warning("voyageai not installed, falling back to keyword-based deduplication")
        return _check_novelty_keyword_fallback(new_contribution, previous_contributions, threshold)

    except Exception as e:
        logger.error(f"Semantic novelty check failed: {e}. Falling back to keyword method.")
        return _check_novelty_keyword_fallback(new_contribution, previous_contributions, threshold)


def _check_novelty_keyword_fallback(
    new_contribution: str,
    previous_contributions: list[str],
    threshold: float,
) -> tuple[bool, float]:
    """Fallback keyword-based novelty check.

    Uses keyword overlap as a simple proxy for semantic similarity when
    embeddings are unavailable.

    Args:
        new_contribution: The new contribution text
        previous_contributions: List of previous contribution texts
        threshold: Similarity threshold (converted to keyword overlap ratio)

    Returns:
        Tuple of (is_novel: bool, max_overlap_score: float)
    """
    # Extract keywords (simple tokenization, lowercase, remove punctuation)
    import re

    def extract_keywords(text: str) -> set[str]:
        """Extract keyword set from text."""
        # Remove punctuation, lowercase, split
        words = re.findall(r"\b\w+\b", text.lower())
        # Filter stopwords (simple list)
        stopwords = {
            "a",
            "an",
            "the",
            "is",
            "are",
            "was",
            "were",
            "be",
            "been",
            "being",
            "have",
            "has",
            "had",
            "do",
            "does",
            "did",
            "will",
            "would",
            "should",
            "could",
            "may",
            "might",
            "must",
            "can",
            "of",
            "to",
            "in",
            "for",
            "on",
            "with",
            "at",
            "by",
            "from",
            "and",
            "or",
            "but",
            "not",
            "as",
            "if",
            "this",
            "that",
            "these",
            "those",
            "it",
            "its",
            "they",
            "them",
            "their",
            "we",
            "us",
            "our",
        }
        keywords = {w for w in words if w not in stopwords and len(w) > 2}
        return keywords

    new_keywords = extract_keywords(new_contribution)

    if not new_keywords:
        return False, 0.0  # Empty keywords = not novel

    max_overlap = 0.0

    for prev_contrib in previous_contributions:
        prev_keywords = extract_keywords(prev_contrib)

        if not prev_keywords:
            continue

        # Calculate Jaccard similarity (keyword overlap)
        intersection = new_keywords & prev_keywords
        union = new_keywords | prev_keywords

        if union:
            overlap_score = len(intersection) / len(union)
            max_overlap = max(max_overlap, overlap_score)

    # Convert threshold (designed for cosine similarity 0-1)
    # to Jaccard similarity (also 0-1, but different scale)
    # Jaccard tends to be lower, so we adjust threshold down
    adjusted_threshold = threshold * 0.6  # Empirical adjustment

    is_novel = max_overlap <= adjusted_threshold

    logger.debug(
        f"Keyword fallback novelty check: {'NOVEL' if is_novel else 'DUPLICATE'} "
        f"(max overlap: {max_overlap:.3f}, adjusted threshold: {adjusted_threshold:.3f})"
    )

    return is_novel, max_overlap


async def filter_duplicate_contributions(
    contributions: list[Any],
    threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
) -> list[Any]:
    """Filter duplicate contributions using semantic similarity.

    This function processes a list of contribution objects and removes
    those that are semantically similar to previous ones in the list.

    Args:
        contributions: List of ContributionMessage objects
        threshold: Similarity threshold for deduplication (default: 0.80)

    Returns:
        Filtered list of contributions with duplicates removed

    Example:
        >>> contributions = [
        ...     ContributionMessage(content="Focus on user experience", ...),
        ...     ContributionMessage(content="UX should be our priority", ...),  # Duplicate
        ...     ContributionMessage(content="Revenue is declining", ...),
        ... ]
        >>> filtered = await filter_duplicate_contributions(contributions)
        >>> len(filtered)  # Returns 2 (second contribution filtered)
        2
    """
    if not contributions:
        return []

    filtered = []
    previous_texts: list[str] = []

    for contrib in contributions:
        # Extract content from contribution
        contrib_text = contrib.content if hasattr(contrib, "content") else str(contrib)

        # Check novelty against all previous contributions
        is_novel, similarity = await check_semantic_novelty(
            contrib_text, previous_texts, threshold=threshold
        )

        if is_novel:
            # Novel contribution - keep it
            filtered.append(contrib)
            previous_texts.append(contrib_text)
        else:
            # Duplicate - filter it out
            persona_name = getattr(contrib, "persona_name", "Unknown")
            logger.info(
                f"Filtered duplicate contribution from {persona_name} "
                f"(similarity: {similarity:.3f}, threshold: {threshold:.3f})"
            )
            logger.debug(f"Filtered content: '{contrib_text[:100]}...'")

    filtered_count = len(contributions) - len(filtered)
    if filtered_count > 0:
        logger.info(
            f"Semantic deduplication: {filtered_count} of {len(contributions)} "
            f"contributions filtered ({filtered_count / len(contributions):.0%})"
        )

    return filtered
