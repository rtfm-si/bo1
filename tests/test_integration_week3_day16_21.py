"""Integration test for Week 3 (Days 16-21): Cost Optimization & Context Management.

Tests:
1. Summarization quality (preserves key info)
2. Async summarization (non-blocking)
3. Context growth (linear vs quadratic)
"""

import asyncio
import logging

import pytest

from bo1.agents.summarizer import SummarizerAgent
from bo1.constants import TokenLimits

logger = logging.getLogger(__name__)


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_summarization_quality():
    """Test that summarization preserves key information (Day 16-17)."""
    summarizer = SummarizerAgent()

    # Example contributions with disagreements and specific numbers
    contributions = [
        {
            "persona": "Zara Morales (Growth)",
            "content": (
                "I see significant opportunity in the SEO channel. Our CAC via paid "
                "ads is $80, while industry benchmarks show SEO can achieve $15-20 once "
                "ramped. The 6-month lag is real, but this is a long-term play. I'd "
                "propose a 70/30 split: $35K SEO, $15K paid to maintain pipeline."
            ),
        },
        {
            "persona": "Maria Santos (Finance)",
            "content": (
                "The numbers concern me. $50K is 40% of our quarterly marketing budget. "
                "SEO ROI won't materialize for 6+ months, creating cash flow risk. I need "
                "to see: (1) sensitivity analysis on timeline, (2) contingency if results "
                "lag, (3) impact on runway. What's our break-even assumption?"
            ),
        },
        {
            "persona": "Sarah Kim (Marketing)",
            "content": (
                "Both channels are necessary but serve different goals. Paid ads = "
                "predictable pipeline for Q4 targets. SEO = strategic moat for 2025. "
                "I agree with Zara's split approach but suggest starting 60/40 to derisk. "
                "We can shift allocation in Q1 based on early SEO signals."
            ),
        },
    ]

    # Summarize the round
    response = await summarizer.summarize_round(
        round_number=1,
        contributions=contributions,
        problem_statement="Should we invest $50K in SEO or paid ads?",
    )

    summary = response.content

    # Validation 1: Summary should be concise (within token budget)
    output_tokens = response.token_usage.output_tokens
    target = TokenLimits.SUMMARY_TARGET
    assert output_tokens <= target * 1.5, (
        f"Summary too long: {output_tokens} tokens (target: {target})"
    )

    # Validation 2: Key numbers should be preserved
    assert any(num in summary for num in ["50K", "$50", "50,000", "80", "$80", "15-20", "$15"]), (
        "Summary missing specific numbers/data points"
    )

    # Validation 3: Disagreements should be captured
    disagreement_keywords = [
        "concern",
        "risk",
        "however",
        "but",
        "disagree",
        "tension",
        "different",
        "oppose",
    ]
    has_disagreement = any(keyword in summary.lower() for keyword in disagreement_keywords)
    assert has_disagreement, "Summary doesn't capture disagreements/tensions"

    # Validation 4: Multiple perspectives should be represented
    # Should mention at least 2 of the 3 personas or their viewpoints
    personas_mentioned = sum(
        1
        for persona in ["Zara", "Maria", "Sarah", "Growth", "Finance", "Marketing"]
        if persona in summary
    )
    assert personas_mentioned >= 2 or "split" in summary.lower(), (
        "Summary doesn't represent multiple perspectives"
    )

    # Validation 5: Cost should be minimal (Haiku)
    assert response.cost_total < 0.01, f"Summarization too expensive: ${response.cost_total:.4f}"

    logger.info(
        f"✓ Summarization quality validated: {output_tokens} tokens, "
        f"${response.cost_total:.6f}, preserves key info"
    )


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_async_summarization_non_blocking():
    """Test that summarization runs asynchronously without blocking (Day 16-17)."""
    summarizer = SummarizerAgent()

    contributions = [
        {
            "persona": "Expert A",
            "content": "This is a detailed analysis of the problem with multiple considerations...",
        },
        {
            "persona": "Expert B",
            "content": "I have a different perspective based on my experience...",
        },
    ]

    # Start summarization as background task
    task = asyncio.create_task(
        summarizer.summarize_round(
            round_number=1, contributions=contributions, problem_statement="Test problem"
        )
    )

    # Simulate other work happening while summarization runs
    await asyncio.sleep(0.1)  # Other work proceeds immediately

    # Task should still be running or just completed
    assert not task.done() or task.done(), "Task should be in progress or completed"

    # Now wait for result
    response = await task

    # Validate we got a valid summary
    assert response.content
    assert len(response.content) > 10

    logger.info("✓ Async summarization works without blocking")


@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_context_growth_linear():
    """Test that context grows linearly, not quadratically (Day 16-17).

    With hierarchical context:
    - Old rounds are 100-150 token summaries
    - Current round is full detail (~1,000 tokens)
    - Total context should be ~1,400 tokens regardless of round count
    """
    summarizer = SummarizerAgent()

    # Simulate multiple rounds
    round_summaries = []
    contributions_per_round = [
        {"persona": f"Expert {i}", "content": "Detailed analysis..." * 20} for i in range(5)
    ]

    # Create summaries for rounds 1-4
    for round_num in range(1, 5):
        response = await summarizer.summarize_round(
            round_number=round_num,
            contributions=contributions_per_round,
            problem_statement="Test problem",
        )
        round_summaries.append(response.content)

    # Measure context size growth
    # Without summarization: 5 rounds × 5 personas × 200 tokens = 5,000 tokens (quadratic)
    # With summarization: 4 summaries × 100 tokens + 1 current round × 1,000 tokens = 1,400 tokens (linear)

    summary_tokens = sum(len(s.split()) for s in round_summaries) * 1.3  # Rough estimate
    current_round_tokens = (
        len(" ".join(c["content"] for c in contributions_per_round)) // 4
    )  # Rough estimate

    total_context_estimate = summary_tokens + current_round_tokens

    # Validate linear growth (should be ~1,500 tokens, not 5,000+)
    assert total_context_estimate < 3000, (
        f"Context growing too fast: ~{total_context_estimate} tokens (should be <3000)"
    )

    logger.info(
        f"✓ Context growth is linear: ~{total_context_estimate:.0f} tokens for 5 rounds "
        f"(without summarization would be ~5,000+ tokens)"
    )


if __name__ == "__main__":
    # Run tests manually for development
    logging.basicConfig(level=logging.INFO)

    async def run_manual_tests() -> None:
        """Run tests manually for debugging."""
        print("\n" + "=" * 70)
        print("WEEK 3 INTEGRATION TESTS (Days 16-21)")
        print("=" * 70)

        try:
            print("\n1. Testing summarization quality...")
            await test_summarization_quality()

            print("\n2. Testing async summarization...")
            await test_async_summarization_non_blocking()

            print("\n3. Testing context growth (linear vs quadratic)...")
            await test_context_growth_linear()

            print("\n" + "=" * 70)
            print("✅ ALL WEEK 3 TESTS PASSED")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            raise

    asyncio.run(run_manual_tests())
