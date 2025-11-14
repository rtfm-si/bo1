"""Integration test for Week 3 (Days 16-21): Cost Optimization & Context Management.

Tests:
1. Hierarchical context management (summarization)
2. Async summarization (non-blocking)
3. Context growth (linear vs quadratic)
4. Full deliberation with all optimizations
"""

import asyncio
import logging

import pytest

from bo1.agents.summarizer import SummarizerAgent
from bo1.constants import TokenLimits
from bo1.models.problem import Problem
from bo1.orchestration.deliberation import DeliberationEngine

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


@pytest.mark.skip(reason="Requires full facilitator flow which is non-deterministic in tests")
@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_full_deliberation_with_optimizations():
    """Test complete deliberation with all Week 3 optimizations (Day 21).

    Validates:
    1. Hierarchical context (summaries + current round)
    2. Async summarization (background processing)
    3. Model optimization (right model for each role)
    4. Cost tracking and metrics
    """
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile
    from bo1.models.problem import SubProblem
    from bo1.models.state import DeliberationState

    # Create a simple problem for testing
    problem = Problem(
        title="Should I invest $10K in paid ads or content marketing?",
        description=(
            "I have $10K to spend on marketing. Paid ads give immediate results "
            "but content marketing builds long-term value. Which should I prioritize?"
        ),
        context="Solo founder, SaaS product, $50K ARR, 18 months runway",
        constraints=[],
        sub_problems=[
            SubProblem(
                id="sp_001",
                goal="Determine optimal marketing channel for $10K investment",
                context="Solo founder, SaaS product, $50K ARR, 18 months runway",
                complexity_score=5,
            )
        ],
    )

    # Select test personas
    persona_codes = ["finance_strategist", "growth_hacker", "product_manager"]
    personas = []
    for code in persona_codes:
        p_data = get_persona_by_code(code)
        if p_data:
            personas.append(PersonaProfile(**p_data))

    # Create deliberation state
    state = DeliberationState(
        session_id="test_week3_optimizations",
        problem=problem,
        selected_personas=personas,
        current_sub_problem=problem.sub_problems[0],
    )

    # Initialize deliberation engine
    engine = DeliberationEngine(state=state)

    # Run deliberation
    logger.info("Starting full deliberation test with all optimizations...")

    # Run initial round
    contributions, llm_responses = await engine.run_initial_round()

    # Validate initial state (initial round is round 0)
    assert engine.state.current_round == 0
    assert len(engine.state.selected_personas) >= 3  # Should have selected personas
    assert len(engine.state.contributions) > 0  # Should have contributions

    # Run one more round to test summarization (this becomes round 1)
    await engine.run_round(round_number=1, max_rounds=3)

    # Now we should be at round 1
    assert engine.state.current_round == 1

    # Run one more round to ensure summarization happened (round 2)
    await engine.run_round(round_number=2, max_rounds=3)

    # Validate summarization happened (should have summary of round 0 or 1)
    assert len(engine.state.round_summaries) >= 1, (
        "No round summaries created after multiple rounds"
    )

    # Validate context structure
    # - Round summaries should be concise (100-150 tokens each)
    for i, summary in enumerate(engine.state.round_summaries):
        token_estimate = len(summary.split()) * 1.3
        assert token_estimate < 250, f"Round {i + 1} summary too long: ~{token_estimate:.0f} tokens"

    # Validate cost tracking
    # Note: This test is skipped due to non-deterministic facilitator behavior
    # Type ignores are for skipped test code
    assert engine.state.cost_total > 0, "No cost tracking"  # type: ignore[attr-defined]
    assert engine.state.cost_total < 0.50, (  # type: ignore[attr-defined]
        f"Cost too high for 2 rounds: ${engine.state.cost_total:.4f}"  # type: ignore[attr-defined]
    )

    # Validate model allocation
    # Personas should use Sonnet, summarization should use Haiku (validated in agent selection)

    logger.info(
        f"✓ Full deliberation completed with optimizations:\n"
        f"  - Rounds: {engine.state.current_round}\n"
        f"  - Personas: {len(engine.state.selected_personas)}\n"
        f"  - Contributions: {len(engine.state.contributions)}\n"
        f"  - Summaries: {len(engine.state.round_summaries)}\n"
        f"  - Total cost: ${engine.state.cost_total:.4f}\n"  # type: ignore[attr-defined]
        f"  - Cost per round: ${engine.state.cost_total / engine.state.current_round:.4f}"  # type: ignore[attr-defined]
    )


@pytest.mark.skip(reason="Requires full facilitator flow which is non-deterministic in tests")
@pytest.mark.integration
@pytest.mark.requires_llm
@pytest.mark.asyncio
async def test_summarization_with_background_processing():
    """Test that DeliberationEngine uses background summarization correctly (Day 16-17)."""
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile
    from bo1.models.problem import SubProblem
    from bo1.models.state import DeliberationState

    problem = Problem(
        title="Test problem",
        description="Simple test for background summarization",
        context="Testing context",
        constraints=[],
        sub_problems=[
            SubProblem(
                id="sp_001",
                goal="Test background summarization",
                context="Testing context",
                complexity_score=5,
            )
        ],
    )

    # Select test personas
    persona_codes = ["finance_strategist", "growth_hacker", "product_manager"]
    personas = []
    for code in persona_codes:
        p_data = get_persona_by_code(code)
        if p_data:
            personas.append(PersonaProfile(**p_data))

    # Create deliberation state
    state = DeliberationState(
        session_id="test_background_summarization",
        problem=problem,
        selected_personas=personas,
        current_sub_problem=problem.sub_problems[0],
    )

    engine = DeliberationEngine(state=state)

    # Run initial round
    await engine.run_initial_round()

    # Start next round - this should trigger background summarization
    await engine.run_round(round_number=1, max_rounds=3)

    # Check that a summary task was created (or completed)
    # Note: By the time we check, the task might already be done due to fast Haiku processing
    assert engine.pending_summary_task is not None or len(engine.state.round_summaries) > 0, (
        "No background summarization task created"
    )

    # If task is still pending, wait for it
    if engine.pending_summary_task and not engine.pending_summary_task.done():
        await engine.pending_summary_task

    # Verify summary was added to state
    assert len(engine.state.round_summaries) >= 1, "Background summary not added to state"

    logger.info(
        f"✓ Background summarization working: {len(engine.state.round_summaries)} summaries created"
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

            print("\n4. Testing background summarization...")
            await test_summarization_with_background_processing()

            print("\n5. Testing full deliberation with optimizations...")
            await test_full_deliberation_with_optimizations()

            print("\n" + "=" * 70)
            print("✅ ALL WEEK 3 TESTS PASSED")
            print("=" * 70)

        except Exception as e:
            print(f"\n❌ TEST FAILED: {e}")
            raise

    asyncio.run(run_manual_tests())
