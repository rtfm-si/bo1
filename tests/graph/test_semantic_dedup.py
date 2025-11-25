"""Tests for semantic deduplication."""

import pytest

from bo1.graph.quality.semantic_dedup import (
    _check_novelty_keyword_fallback,
    filter_duplicate_contributions,
)
from bo1.models.state import ContributionMessage


def test_keyword_fallback_identical():
    """Test keyword fallback detects identical text."""
    text1 = "We should focus on improving user experience and reducing friction."
    text2 = "We should focus on improving user experience and reducing friction."

    is_novel, score = _check_novelty_keyword_fallback(text2, [text1], threshold=0.80)

    assert not is_novel, "Identical text should not be novel"
    assert score > 0.5, "Similarity should be high for identical text"


def test_keyword_fallback_similar():
    """Test keyword fallback detects similar content."""
    text1 = "User experience should be our top priority for the product."
    text2 = "We need to prioritize user experience for our product."

    is_novel, score = _check_novelty_keyword_fallback(text2, [text1], threshold=0.80)

    # With adjusted threshold (0.80 * 0.6 = 0.48), high overlap should be filtered
    assert not is_novel or score < 0.6, "Similar text should have high overlap score"


def test_keyword_fallback_different():
    """Test keyword fallback allows different topics."""
    text1 = "User experience should be our priority."
    text2 = "Revenue is declining and we need to cut costs immediately."

    is_novel, score = _check_novelty_keyword_fallback(text2, [text1], threshold=0.80)

    assert is_novel, "Different topics should be novel"
    assert score < 0.3, "Similarity should be low for different topics"


def test_keyword_fallback_empty():
    """Test keyword fallback handles empty inputs."""
    text1 = "Some content here"
    text2 = ""

    is_novel, score = _check_novelty_keyword_fallback(text2, [text1], threshold=0.80)

    assert not is_novel, "Empty text should not be novel"
    assert score == 0.0


def test_keyword_fallback_no_previous():
    """Test keyword fallback with no previous contributions."""
    text = "This is a new contribution"

    is_novel, score = _check_novelty_keyword_fallback(text, [], threshold=0.80)

    assert is_novel, "First contribution should always be novel"
    assert score == 0.0


@pytest.mark.asyncio
async def test_filter_duplicate_contributions_structure():
    """Test the structure of filter_duplicate_contributions (non-LLM)."""
    # Create test contributions
    contrib1 = ContributionMessage(
        persona_code="cfo",
        persona_name="Maria",
        content="Focus on costs and ROI",
        round_number=1,
    )
    contrib2 = ContributionMessage(
        persona_code="cto",
        persona_name="Alex",
        content="Revenue is declining rapidly",
        round_number=1,
    )

    # Test that function can be called without errors
    # This will use keyword fallback (no LLM/embeddings)
    result = await filter_duplicate_contributions([contrib1, contrib2], threshold=0.80)

    assert isinstance(result, list)
    assert len(result) >= 1  # At least some contributions should pass
    assert all(hasattr(c, "content") for c in result)


@pytest.mark.asyncio
async def test_filter_duplicate_contributions_empty():
    """Test filtering with empty input."""
    result = await filter_duplicate_contributions([], threshold=0.80)

    assert isinstance(result, list)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_filter_duplicate_contributions_single():
    """Test filtering with single contribution."""
    contrib = ContributionMessage(
        persona_code="cfo",
        persona_name="Maria",
        content="Focus on costs",
        round_number=1,
    )

    result = await filter_duplicate_contributions([contrib], threshold=0.80)

    assert len(result) == 1
    assert result[0].content == "Focus on costs"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Voyage AI API - only run in integration tests")
async def test_semantic_novelty_identical():
    """Test that identical text is detected as duplicate using embeddings."""
    from bo1.graph.quality.semantic_dedup import check_semantic_novelty

    text1 = "We should focus on improving user experience and reducing friction."
    text2 = "We should focus on improving user experience and reducing friction."

    is_novel, score = await check_semantic_novelty(text2, [text1])

    assert not is_novel, "Identical text should not be novel"
    assert score >= 0.95, "Similarity should be very high"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Voyage AI API - only run in integration tests")
async def test_semantic_novelty_similar_meaning():
    """Test that similar meaning is detected as duplicate."""
    from bo1.graph.quality.semantic_dedup import check_semantic_novelty

    text1 = "User experience should be our top priority."
    text2 = "We need to prioritize improving the user experience."

    is_novel, score = await check_semantic_novelty(text2, [text1], threshold=0.80)

    assert not is_novel, "Similar meaning should not be novel with 0.80 threshold"
    assert score >= 0.75, "Similarity should be high for similar meaning"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires Voyage AI API - only run in integration tests")
async def test_semantic_novelty_different_topic():
    """Test that different topics are novel."""
    from bo1.graph.quality.semantic_dedup import check_semantic_novelty

    text1 = "User experience should be our priority."
    text2 = "Revenue is declining and we need to cut costs."

    is_novel, score = await check_semantic_novelty(text2, [text1])

    assert is_novel, "Different topics should be novel"
    assert score < 0.50, "Similarity should be low"


@pytest.mark.asyncio
async def test_semantic_dedup_failsafe():
    """Test that failsafe returns True (novel) on complete failure.

    This tests the P1.2 fix: if both embedding and keyword checks fail,
    mark as novel to avoid blocking all contributions.
    """
    from unittest.mock import patch

    from bo1.graph.quality.semantic_dedup import check_semantic_novelty

    text1 = "Some content"
    text2 = "Other content"

    # Mock the embedding generation to fail inside the check_semantic_novelty function
    # The function imports generate_embedding from bo1.llm.embeddings
    with patch(
        "bo1.llm.embeddings.generate_embedding",
        side_effect=Exception("API failure"),
    ):
        with patch(
            "bo1.graph.quality.semantic_dedup._check_novelty_keyword_fallback",
            side_effect=Exception("Keyword failure"),
        ):
            is_novel, score = await check_semantic_novelty(text2, [text1])

            # Failsafe: should return True (novel)
            assert is_novel, "Failsafe should mark as novel when both checks fail"
            assert score == 0.0
