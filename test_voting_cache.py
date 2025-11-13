#!/usr/bin/env python3
"""Test script to verify voting cache optimization works correctly."""

import asyncio
import logging

from bo1.llm.broker import PromptBroker
from bo1.models.problem import Problem
from bo1.models.state import DeliberationState
from bo1.orchestration.voting import collect_votes

# Configure logging to see cache hits
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


async def test_voting_cache_optimization():
    """Test that voting uses sequential-then-parallel pattern for cache hits."""
    print("=" * 70)
    print("VOTING CACHE OPTIMIZATION TEST")
    print("=" * 70)
    print()

    # Create mock state with 5 personas
    import uuid

    state = DeliberationState(
        session_id=str(uuid.uuid4()),
        problem=Problem(
            title="Test Decision",
            description="Should we invest $50K in marketing?",
            context="Early-stage SaaS, $100K ARR",
        ),
    )

    # Add 5 personas (using actual persona codes from our data)
    from bo1.data import get_persona_by_code
    from bo1.models.persona import PersonaProfile

    persona_codes = [
        "growth_hacker",
        "finance_strategist",
        "risk_officer",
        "wellness_advisor",
        "corporate_strategist",
    ]  # 5 diverse personas
    persona_dicts = [get_persona_by_code(code) for code in persona_codes]
    state.selected_personas = [PersonaProfile(**p) for p in persona_dicts if p is not None]

    # Add substantial mock contributions to exceed 1024 token threshold
    # Real deliberations have 3-5 rounds with 3-5 personas each (~3000+ tokens)
    from bo1.models.state import ContributionMessage, ContributionType

    # Simulate 3 rounds of discussion with substantial contributions
    mock_contributions = [
        ContributionMessage(
            persona_code="growth_hacker",
            persona_name="Zara Morales",
            content="""I've analyzed the marketing investment decision from a growth perspective.
            The $50K investment represents a significant commitment for an early-stage SaaS at $100K ARR.

            **Channel Analysis:**
            - SEO: Long-term asset building, 6-12 month ROI horizon, compounds over time
            - Paid Ads: Immediate results, controllable spend, direct attribution, but stops when budget ends

            **Risk Assessment:**
            For a company at your stage, I recommend a hybrid approach: 60% SEO ($30K), 40% paid ads ($20K).
            SEO investment builds long-term foundation while paid ads provide immediate feedback loop.

            **Growth Metrics to Track:**
            - CAC payback period (target: <6 months)
            - Organic traffic growth (target: 30% MoM)
            - Conversion rate optimization (target: 3-5%)
            - Customer LTV (target: >3x CAC)

            The key is treating this as a learning investment, not just customer acquisition.""",
            contribution_type=ContributionType.INITIAL,
            round_number=1,
        ),
        ContributionMessage(
            persona_code="finance_strategist",
            persona_name="Maria Santos",
            content="""From a financial planning perspective, this $50K investment is 50% of your current ARR.

            **Financial Viability Check:**
            - Cash runway impact: How many months of runway does this consume?
            - Expected CAC: What's the target customer acquisition cost?
            - LTV assumptions: What's the baseline customer lifetime value?
            - Break-even timeline: When do you need these customers to be cash-flow positive?

            **Budget Allocation Recommendations:**
            I agree with Zara's hybrid approach, but would add strict financial guardrails:
            1. Monthly budget caps with go/no-go decision points
            2. CAC ceiling of $500 (based on $100K ARR suggesting ~20 customers)
            3. Required 90-day payback period
            4. Reserve $10K ($20% of budget) for optimization and pivots

            **Risk Mitigation:**
            Consider phasing: Start with $20K pilot (SEO foundation + paid testing),
            evaluate after 60 days, then deploy remaining $30K based on validated metrics.""",
            contribution_type=ContributionType.RESPONSE,
            round_number=2,
        ),
        ContributionMessage(
            persona_code="risk_officer",
            persona_name="Ahmad Hassan",
            content="""As a risk officer, I need to highlight several critical risk factors:

            **Market Risk:**
            - Economic downturn could reduce conversion rates
            - Competition may drive up acquisition costs mid-campaign
            - Algorithm changes (Google, Meta) could invalidate paid strategies

            **Execution Risk:**
            - Do you have in-house expertise for SEO and paid ads?
            - Agency costs could consume 30-40% of budget
            - Poor execution could waste entire investment with minimal learnings

            **Financial Risk:**
            - 50% of ARR is aggressive for an experimental investment
            - If customers don't convert or churn quickly, you've burned runway
            - Opportunity cost: Could this $50K be better spent on product development?

            **Risk Mitigation Recommendations:**
            1. Require weekly performance reviews with kill-switch authority
            2. Set hard CAC ceiling and pause spending if exceeded
            3. Diversify channels (not just SEO vs Paid, but within Paid: multiple platforms)
            4. Build internal expertise before scaling spend
            5. Secure customer testimonials/case studies before major ad spend

            **My Vote Leans Conditional:** Proceed only if you have:
            - 12+ months runway post-investment
            - Clear ICP with validated willingness to pay
            - Internal or trusted agency expertise
            - Documented product-market fit metrics""",
            contribution_type=ContributionType.RESPONSE,
            round_number=3,
        ),
    ]
    state.contributions = mock_contributions

    # Create broker
    broker = PromptBroker()

    print(f"Testing with {len(state.selected_personas)} personas:")
    for p in state.selected_personas:
        print(f"  - {p.name} ({p.code})")
    print()

    print("Expected behavior:")
    print("  1. First vote (creates cache)")
    print("  2. Remaining 4 votes in parallel (hit cache)")
    print()
    print("Watch for cache_read_tokens in the logs below:")
    print("=" * 70)
    print()

    # Collect votes
    votes, llm_responses = await collect_votes(state, broker)

    print()
    print("=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"Votes collected: {len(votes)}/{len(state.selected_personas)}")
    print()

    # Analyze cache performance
    if llm_responses:
        print("Token usage per vote:")
        print()

        total_cost = 0
        total_cache_read = 0
        total_cache_creation = 0

        for i, response in enumerate(llm_responses, 1):
            usage = response.token_usage
            cache_read = usage.cache_read_tokens
            cache_creation = usage.cache_creation_tokens
            cost = usage.calculate_cost("sonnet")

            total_cost += cost
            total_cache_read += cache_read
            total_cache_creation += cache_creation

            cache_status = "🎯 CACHE HIT" if cache_read > 0 else "📝 CACHE CREATION"
            print(f"Vote {i}: {cache_status}")
            print(f"  Input:          {usage.input_tokens:,}")
            print(f"  Cache creation: {cache_creation:,}")
            print(f"  Cache read:     {cache_read:,}")
            print(f"  Output:         {usage.output_tokens:,}")
            print(f"  Cost:           ${cost:.6f}")
            print()

        print("=" * 70)
        print("TOTALS")
        print("=" * 70)
        print(f"Total cache creation: {total_cache_creation:,} tokens")
        print(f"Total cache reads:    {total_cache_read:,} tokens")
        print(f"Total cost:           ${total_cost:.4f}")
        print()

        # Calculate savings vs Haiku
        # Assume same token counts but Haiku pricing
        haiku_cost = (total_cache_read * 1.00 / 1_000_000) + (
            total_cache_creation * 1.00 / 1_000_000
        )
        haiku_cost += sum(r.token_usage.output_tokens for r in llm_responses) * 5.00 / 1_000_000

        if haiku_cost > 0:
            savings = haiku_cost - total_cost
            savings_pct = (savings / haiku_cost) * 100
            print(f"Haiku (estimated):    ${haiku_cost:.4f}")
            print(f"Savings:              ${savings:.4f} ({savings_pct:.1f}% reduction)")
            print()

        # Validate expected behavior
        print("=" * 70)
        print("VALIDATION")
        print("=" * 70)

        if total_cache_creation > 0:
            print("✅ Cache creation detected (first vote)")
        else:
            print("❌ No cache creation detected")

        if total_cache_read > 0:
            print(f"✅ Cache hits detected ({total_cache_read:,} tokens)")
        else:
            print("❌ No cache hits detected")

        cache_hit_ratio = (
            total_cache_read / (total_cache_creation + total_cache_read)
            if (total_cache_creation + total_cache_read) > 0
            else 0
        )
        expected_ratio = 4 / 5  # 1 creation, 4 hits out of 5 total

        print(f"\nCache hit ratio: {cache_hit_ratio:.1%} (expected ~{expected_ratio:.1%})")

        if cache_hit_ratio >= expected_ratio - 0.05:  # Allow 5% tolerance
            print("✅ Sequential-then-parallel pattern working correctly")
            return True
        else:
            print("⚠️ Cache hit ratio lower than expected")
            return False
    else:
        print("❌ No LLM responses received")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_voting_cache_optimization())
    print()
    print("=" * 70)
    print("TEST", "PASSED ✅" if success else "FAILED ❌")
    print("=" * 70)
    exit(0 if success else 1)
