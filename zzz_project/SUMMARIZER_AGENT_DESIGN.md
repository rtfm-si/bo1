# Summarizer Agent Design

## Purpose

The Summarizer is a background agent that compresses completed deliberation rounds into concise summaries for hierarchical context management. It enables cost-effective, high-quality deliberations by preventing quadratic context growth while maintaining memory of all rounds.

## Architecture

### Agent Type: Background / Asynchronous

- **Trigger**: After each round completes (5 persona contributions)
- **Execution**: Runs in background while next round proceeds
- **Model**: Haiku 4.5 (fast, cost-effective, good summarization)
- **Output**: 100-150 token summary of the round

### Integration Pattern

```
Round 1 completes
├─ Facilitator decides: "Continue to Round 2"
├─ 🔥 Summarizer starts (background): Summarize Round 1
└─ Round 2 starts immediately (doesn't wait)

Round 2 in progress...
└─ 🔥 Summarizer completes: Round 1 summary ready

Round 2 completes
├─ Facilitator decides: "Continue to Round 3"
├─ 🔥 Summarizer starts (background): Summarize Round 2
└─ Round 3 starts with context:
    - Round 1 summary (completed) ✓
    - Round 2 full detail (current)
    - Round 3 will get Round 2 summary next
```

### Non-Blocking Design

**Key Insight**: The summary of Round N is only needed AFTER Round N+1 completes.

- Round 1 summary not needed until Round 3 starts
- Round 2 summary not needed until Round 4 starts
- Always 1 round lag = always enough time for async completion

**Result**: Zero latency impact on deliberation flow

## Cost Analysis

### Haiku for Summarization (Recommended)

**Per Summary:**
- Input: 1,000 tokens × $0.80/MTok = $0.0008
- Output: 100 tokens × $4.00/MTok = $0.0004
- **Total**: $0.0012 per summary

**Per Deliberation (6 summaries):**
- Cost: $0.0072
- Time: ~1-2 seconds each (runs in background, no impact)

### Alternative: Sonnet for Summarization

**Per Deliberation (6 summaries):**
- Cost: $0.0270 (3.75× more expensive)
- Quality: Marginally better, but Haiku is sufficient for summarization

**Verdict**: Use Haiku unless quality testing shows issues

## Total Deliberation Cost

### With Hierarchical Summarization + Prompt Caching

| Component | Model | Cost |
|-----------|-------|------|
| 35 persona contributions | Sonnet + cache | $0.095 |
| 6 round summaries | Haiku | $0.007 |
| **Total** | | **$0.102** |

**vs Alternatives:**
- Haiku no cache: $0.140 (37% more expensive, worse quality)
- Sonnet no cache: $0.527 (416% more expensive)
- Sonnet full history: $0.115 (13% more expensive, cognitive overload risk)

## Implementation

### 1. Summarizer Agent Class

```python
# bo1/agents/summarizer.py

import anthropic
from bo1.prompts.summarizer_prompts import (
    SUMMARIZER_SYSTEM_PROMPT,
    compose_summarization_request
)

class SummarizerAgent:
    """
    Background agent for compressing deliberation rounds.

    Runs asynchronously to avoid blocking deliberation flow.
    """

    def __init__(self, anthropic_api_key: str):
        self.client = anthropic.Anthropic(api_key=anthropic_api_key)
        self.model = "claude-haiku-4-5-20250929"

    async def summarize_round(
        self,
        round_number: int,
        contributions: list[dict],
        problem_statement: str = None
    ) -> str:
        """
        Summarize a completed round into 100-150 tokens.

        Args:
            round_number: Which round (1-7)
            contributions: List of {'persona': str, 'content': str}
            problem_statement: Optional problem context

        Returns:
            Summary text (~100 tokens)
        """
        request = compose_summarization_request(
            round_number=round_number,
            contributions=contributions,
            problem_statement=problem_statement
        )

        response = self.client.messages.create(
            model=self.model,
            max_tokens=200,
            system=SUMMARIZER_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": request}
            ]
        )

        summary = response.content[0].text

        # Log for monitoring
        print(f"[Summarizer] Round {round_number} compressed: "
              f"{sum(len(c['content']) for c in contributions)} chars → "
              f"{len(summary)} chars")

        return summary
```

### 2. Orchestration Integration

```python
# bo1/orchestration/deliberation.py

import asyncio
from bo1.agents.summarizer import SummarizerAgent

class DeliberationState:
    round_summaries: list[str] = []
    current_round_contributions: list[dict] = []
    pending_summary_task: asyncio.Task = None
    round_number: int = 1

async def run_deliberation(problem: str, personas: list[str]):
    """Main deliberation loop with background summarization"""

    state = DeliberationState()
    summarizer = SummarizerAgent(api_key=ANTHROPIC_API_KEY)

    for round_num in range(1, 8):  # 7 rounds
        # Run the round
        for persona_code in personas:
            contribution = await persona_contributes(
                persona_code=persona_code,
                problem=problem,
                round_summaries=state.round_summaries,
                current_round_history=state.current_round_contributions
            )

            state.current_round_contributions.append({
                "persona": persona_code,
                "content": contribution
            })

        # Round complete - start summarization in background
        if round_num < 7:  # Don't summarize final round
            state.pending_summary_task = asyncio.create_task(
                summarizer.summarize_round(
                    round_number=round_num,
                    contributions=state.current_round_contributions,
                    problem_statement=problem if round_num == 1 else None
                )
            )

        # Check if previous round's summary is ready
        if state.pending_summary_task and round_num > 1:
            # Await the summary from PREVIOUS round
            # (e.g., in Round 3, get Round 1 summary)
            if len(state.round_summaries) < round_num - 1:
                prev_summary = await state.pending_summary_task
                state.round_summaries.append(prev_summary)

        # Facilitator decides next action
        decision = await facilitator_decides(state)

        if decision == "vote":
            break

        # Clear current round, move to next
        state.current_round_contributions = []
        state.round_number += 1

    # Ensure all pending summaries complete before voting
    if state.pending_summary_task:
        final_summary = await state.pending_summary_task
        state.round_summaries.append(final_summary)

    # Proceed to voting with all summaries available
    return await run_voting(state)
```

### 3. Simplified Orchestration (Alternative)

```python
# Simpler pattern: fire-and-forget with fallback

async def run_round_with_summary(state, personas):
    """Run round and start background summary"""

    # Execute round
    for persona in personas:
        contrib = await persona_contributes(...)
        state.current_round_contributions.append(contrib)

    # Start summary in background (fire-and-forget style)
    summary_task = asyncio.create_task(
        summarize_round(state.round_number, state.current_round_contributions)
    )

    # Store task to await later if needed
    state.summary_tasks[state.round_number] = summary_task

    # Move to next round immediately
    state.current_round_contributions = []
    state.round_number += 1

    return summary_task


async def get_round_summary(state, round_num: int) -> str:
    """
    Get summary for a round, waiting if necessary.

    In practice, this almost never blocks because we always have
    at least 1 round lag.
    """
    if round_num in state.round_summaries:
        # Already completed
        return state.round_summaries[round_num]

    if round_num in state.summary_tasks:
        # Await completion (usually already done)
        summary = await state.summary_tasks[round_num]
        state.round_summaries[round_num] = summary
        return summary

    # Shouldn't happen, but fallback
    return "[Summary not available]"
```

## Quality Assurance

### Summary Quality Metrics

Track these metrics to ensure summaries are effective:

1. **Compression Ratio**: Target 80-85% reduction
   - Input: ~1,000 tokens (5 contributions)
   - Output: ~100-150 tokens
   - Ratio: 85-90% compression

2. **Information Retention**: Sample evaluation
   - Can human reader understand key points from summary?
   - Are disagreements captured?
   - Are numbers/specifics preserved?

3. **Downstream Impact**: Persona quality in later rounds
   - Do personas reference earlier arguments correctly?
   - Do they avoid repeating points already made?
   - Do they build on earlier insights?

### Testing Strategy

```python
# Test summarization quality

async def test_summarizer():
    """Test summarizer on sample rounds"""

    summarizer = SummarizerAgent()

    # Test case: Round with clear disagreement
    contributions = [
        {"persona": "Finance", "content": "Too risky, cash flow impact..."},
        {"persona": "Growth", "content": "Worth the risk, CAC arbitrage..."},
        {"persona": "Product", "content": "Depends on timeline..."}
    ]

    summary = await summarizer.summarize_round(1, contributions)

    # Verify summary captures disagreement
    assert "risk" in summary.lower()
    assert len(summary.split()) < 150

    print(f"✓ Summary quality: {len(summary.split())} tokens")
```

## Monitoring

### Metrics to Track

```python
# Add to deliberation metrics

class SummarizationMetrics:
    summaries_generated: int = 0
    avg_summary_tokens: float = 0
    avg_compression_ratio: float = 0
    avg_generation_time: float = 0
    summaries_completed_before_needed: int = 0
    summaries_blocked_deliberation: int = 0  # Should be 0!

# Log in production
if summary_blocked_deliberation:
    logger.warning(
        f"[Summarizer] Round {round_num} summary not ready in time! "
        f"Deliberation blocked for {wait_time}ms"
    )
```

## Failure Handling

### Graceful Degradation

If summarization fails or times out:

1. **Option 1**: Use last N contributions instead of summary
   ```python
   if summary_failed:
       context = last_n_contributions(n=3)  # Fallback to sliding window
   ```

2. **Option 2**: Skip summary for that round
   ```python
   if summary_failed:
       state.round_summaries.append("[Round summary unavailable]")
       # Continue with available summaries
   ```

3. **Option 3**: Retry once with shorter prompt
   ```python
   try:
       summary = await summarizer.summarize_round(...)
   except Exception as e:
       logger.error(f"Summarization failed: {e}")
       summary = await summarizer.summarize_round_simple(...)  # Simplified prompt
   ```

## Future Enhancements

### Adaptive Summarization

Different summary strategies for different rounds:

- **Early rounds** (1-3): Longer summaries (150 tokens)
  - More exploration, want to capture diverse perspectives

- **Middle rounds** (4-5): Standard summaries (100 tokens)
  - Key arguments established, compress more

- **Late rounds** (6-7): Shorter summaries (75 tokens)
  - Focus on convergence, less new information

### Multi-Level Summarization

For very long deliberations (10+ rounds):

```
Round 1-5: Individual summaries (5 × 100 = 500 tokens)
  ↓
Meta-summary of Rounds 1-5 (200 tokens)
  ↓
Rounds 6-10: Individual summaries (5 × 100 = 500 tokens)
  ↓
Final context: Meta-summary + Round 10 detail (700 tokens total)
```

### Persona-Specific Summaries

Different personas might need different summary focus:

- **Finance**: Emphasize numbers, ROI, risks
- **Engineering**: Emphasize technical feasibility, timeline
- **Strategy**: Emphasize long-term implications

**Implementation**: Add persona_perspective parameter to summarizer

## References

- **Prompt Caching**: See PROMPT_ENGINEERING_FRAMEWORK.md
- **Consensus Building**: See CONSENSUS_BUILDING_RESEARCH.md
- **Cost Model**: See cost analysis in this document

---

**Status**: Design complete, ready for implementation
**Priority**: High (enables cost-effective Sonnet usage)
**Estimated Effort**: 2-3 days (agent class + orchestration integration + testing)
