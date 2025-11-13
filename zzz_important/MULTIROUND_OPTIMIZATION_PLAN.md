# Multi-Round Deliberation Optimization Plan

**Created:** 2025-11-13
**Context:** Based on user feedback and CONSENSUS_BUILDING_RESEARCH.md alignment

---

## Problems Identified

1. **Slow facilitator decisions**: 25s per round, $0.027 per decision
2. **Long gaps between rounds**: Waiting for sequential operations
3. **Fixed moderator timing**: Need adaptive triggers based on discussion state
4. **No consensus visibility**: Metrics not exposed in logs
5. **Constant verbosity**: All rounds same length, causing drift and cost

---

## Solution 1: Use Haiku for Facilitator Decisions

### Current State
```
Facilitator (Sonnet 4.5):
- Decision time: 25.1s
- Cost: $0.027
- Task: Simple orchestration (continue/vote/research/moderator + speaker selection)
```

### Proposed Change
```python
# In bo1/agents/facilitator.py

def __init__(self, broker: PromptBroker | None = None, use_haiku: bool = True) -> None:
    """Initialize facilitator agent.

    Args:
        broker: LLM broker for making calls
        use_haiku: Use Haiku for fast, cheap decisions (default: True)
    """
    self.broker = broker or PromptBroker()
    self.model = "haiku-4.5" if use_haiku else "sonnet-4.5"

# Update call site
request = PromptRequest(
    system=system_prompt,
    user_message=user_message,
    temperature=1.0,
    max_tokens=800,  # Reduced from 2048 - facilitator doesn't need long responses
    phase="facilitator_decision",
    agent_type="facilitator",
    model=self.model,  # Use configured model
)
```

### Expected Impact
- **Speed**: 25s → 3-5s (5-8x faster)
- **Cost**: $0.027 → $0.001-0.002 (10-20x cheaper)
- **Quality**: Minimal impact - orchestration is simple task

---

## Solution 2: Adaptive Round Prompts (Loose → Strict)

### Research Alignment

From CONSENSUS_BUILDING_RESEARCH.md:
- **Early rounds (2-4)**: Divergent thinking, exploration
- **Middle rounds (5-7)**: Analysis, evidence gathering
- **Late rounds (8+)**: Convergent thinking, consensus

### Implementation

```python
# In bo1/prompts/reusable_prompts.py

def get_round_phase_config(round_number: int, max_rounds: int) -> dict:
    """Get configuration for current round phase.

    Returns:
        {
            "phase": "early" | "middle" | "late",
            "temperature": float,
            "max_tokens": int,
            "directive": str,
            "tone": str,
        }
    """
    progress = round_number / max_rounds

    if round_number <= 1:
        # Initial round
        return {
            "phase": "initial",
            "temperature": 1.0,
            "max_tokens": 2000,
            "directive": "Provide your complete perspective on this problem.",
            "tone": "exploratory",
        }
    elif progress <= 0.4:  # Early (rounds 2-4 of 10)
        return {
            "phase": "early",
            "temperature": 1.0,
            "max_tokens": 1500,
            "directive": "Explore different angles. What concerns or alternatives haven't been discussed?",
            "tone": "divergent",
        }
    elif progress <= 0.7:  # Middle (rounds 5-7 of 10)
        return {
            "phase": "middle",
            "temperature": 0.85,
            "max_tokens": 1200,
            "directive": "Build on the discussion with evidence and analysis. Address gaps or uncertainties.",
            "tone": "analytical",
        }
    else:  # Late (rounds 8+ of 10)
        return {
            "phase": "late",
            "temperature": 0.7,
            "max_tokens": 800,
            "directive": "Work toward consensus. Acknowledge tradeoffs and move toward a decision.",
            "tone": "convergent",
        }

# In bo1/orchestration/deliberation.py - update _call_persona_async

async def _call_persona_async(
    self,
    persona_profile: PersonaProfile,
    round_number: int,
    # ... other params
) -> tuple[ContributionMessage, LLMResponse]:
    """Call persona with adaptive round configuration."""

    # Get round phase config
    round_config = get_round_phase_config(round_number, self.state.max_rounds)

    # Add directive to prompt
    user_message = f"""{round_config["directive"]}

{problem_statement}

[Previous discussion context...]
"""

    request = PromptRequest(
        system=system_prompt,
        user_message=user_message,
        temperature=round_config["temperature"],
        max_tokens=round_config["max_tokens"],
        # ... other params
    )
```

### Expected Impact
- **Cost reduction**: 30-40% fewer tokens in late rounds
- **Speed improvement**: Faster responses in late rounds (800 tokens vs 2000)
- **Quality improvement**: Less drift (tighter prompts), better convergence

---

## Solution 3: Expose Consensus Metrics in Logs

### Metrics to Track

```python
# In bo1/orchestration/deliberation.py

async def run_round(self, round_number: int, max_rounds: int) -> ...:
    """Run round with metrics logging."""

    # After contribution
    if round_number > 1:
        # Calculate convergence metrics
        metrics = self._calculate_round_metrics(round_number)

        logger.info(f"[METRICS] Round {round_number}/{max_rounds}")
        logger.info(f"  Convergence: {metrics['convergence']:.2f} (target: >0.85)")
        logger.info(f"  Novelty: {metrics['novelty']:.2f} (target: <0.30 in late rounds)")
        logger.info(f"  Conflict: {metrics['conflict']:.2f} (0=consensus, 1=deadlock)")

        if metrics['should_stop']:
            logger.info(f"  🎯 Early stop recommended: {metrics['stop_reason']}")

def _calculate_round_metrics(self, round_number: int) -> dict:
    """Calculate convergence and consensus metrics."""
    recent_contributions = self.state.contributions[-6:]  # Last 2 rounds

    # Semantic convergence (0-1, higher = more similar)
    convergence = self._calculate_semantic_convergence(recent_contributions)

    # Novelty score (0-1, lower = more repetition)
    novelty = self._calculate_novelty(recent_contributions)

    # Conflict score (0-1, higher = more disagreement)
    conflict = self._calculate_conflict(recent_contributions)

    # Early stop decision
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
```

### Example Log Output
```
[METRICS] Round 5/7
  Convergence: 0.73 (target: >0.85)
  Novelty: 0.42 (target: <0.30 in late rounds)
  Conflict: 0.28 (0=consensus, 1=deadlock)

[METRICS] Round 6/7
  Convergence: 0.89 (target: >0.85)
  Novelty: 0.21 (target: <0.30 in late rounds)
  Conflict: 0.15 (0=consensus, 1=deadlock)
  🎯 Early stop recommended: High convergence + low novelty
```

---

## Solution 4: Adaptive Moderator Triggers

### Current Problem
Hard-coded: "Call contrarian at round 5" is inflexible

### Proposed Solution
Trigger moderators based on discussion state, not round number

```python
# In bo1/agents/facilitator.py

def _should_trigger_moderator(self, state: DeliberationState, round_number: int) -> dict | None:
    """Check if moderator intervention is needed.

    Returns:
        {
            "type": "contrarian" | "skeptic" | "optimist",
            "reason": str,
        } or None
    """
    recent = state.contributions[-6:]  # Last 2 rounds

    # Early rounds (1-4): Watch for premature consensus
    if round_number <= 4:
        if self._detect_premature_consensus(recent):
            return {
                "type": "contrarian",
                "reason": "Group converging too early without exploring alternatives",
            }

    # Middle rounds (5-7): Watch for unverified claims
    if 5 <= round_number <= 7:
        if self._detect_unverified_claims(recent):
            return {
                "type": "skeptic",
                "reason": "Claims made without evidence or verification",
            }

    # Late rounds (8+): Watch for negativity spiral
    if round_number >= 8:
        if self._detect_negativity_spiral(recent):
            return {
                "type": "optimist",
                "reason": "Discussion stuck in problems without exploring solutions",
            }

    # Any round: Watch for circular arguments
    if self._detect_circular_arguments(recent):
        return {
            "type": "contrarian",
            "reason": "Circular arguments detected, need fresh perspective",
        }

    return None

def _detect_premature_consensus(self, contributions: list) -> bool:
    """Detect if group is agreeing too quickly."""
    if len(contributions) < 4:
        return False

    # Check semantic similarity
    similarity = calculate_semantic_similarity(contributions)

    # If all contributions very similar in early rounds = red flag
    return similarity > 0.90

def _detect_unverified_claims(self, contributions: list) -> bool:
    """Detect claims without evidence."""
    # Simple heuristic: look for "should", "must", "will" without "because", "data shows", etc.
    claim_keywords = ["should", "must", "will definitely", "certainly"]
    evidence_keywords = ["because", "data shows", "research indicates", "according to"]

    for contrib in contributions:
        text = contrib.content.lower()
        has_claims = any(kw in text for kw in claim_keywords)
        has_evidence = any(kw in text for kw in evidence_keywords)

        if has_claims and not has_evidence:
            return True

    return False

def _detect_negativity_spiral(self, contributions: list) -> bool:
    """Detect if discussion stuck in problems."""
    negative_keywords = ["won't work", "impossible", "can't", "too risky", "fail"]
    positive_keywords = ["could", "might", "opportunity", "solution", "approach"]

    negative_count = sum(
        sum(kw in c.content.lower() for kw in negative_keywords)
        for c in contributions
    )
    positive_count = sum(
        sum(kw in c.content.lower() for kw in positive_keywords)
        for c in contributions
    )

    # If 3x more negative than positive = spiral
    return negative_count > 3 * positive_count if positive_count > 0 else negative_count > 5

def _detect_circular_arguments(self, contributions: list) -> bool:
    """Detect if same arguments repeating."""
    if len(contributions) < 4:
        return False

    # Extract key arguments from each contribution
    args = [extract_key_arguments(c.content) for c in contributions]

    # Check for repetition
    seen_args = set()
    repeat_count = 0

    for arg_list in args:
        for arg in arg_list:
            if arg in seen_args:
                repeat_count += 1
            seen_args.add(arg)

    # If >60% of arguments are repeats = circular
    total_args = sum(len(a) for a in args)
    return (repeat_count / total_args) > 0.6 if total_args > 0 else False
```

### Integration with Facilitator Decision

```python
# In decide_next_action method

async def decide_next_action(self, state, round_number, max_rounds):
    """Decide next action with adaptive moderator checking."""

    # Check if moderator should intervene BEFORE calling LLM
    moderator_trigger = self._should_trigger_moderator(state, round_number)

    if moderator_trigger:
        logger.info(f"🎭 Auto-triggering {moderator_trigger['type']} moderator")
        logger.info(f"   Reason: {moderator_trigger['reason']}")

        return FacilitatorDecision(
            action="moderator",
            reasoning=moderator_trigger['reason'],
            moderator_type=moderator_trigger['type'],
            moderator_focus=moderator_trigger['reason'],
        ), None  # Skip LLM call

    # Otherwise, call LLM for decision
    response = await self.broker.call(request)
    # ... rest of logic
```

---

## Solution 5: Research Triggers During Multi-Round

### Current State
Research option exists but not implemented

### Proposed Implementation

```python
# In bo1/agents/facilitator.py

def _check_research_needed(self, state: DeliberationState) -> dict | None:
    """Check if research/information is needed.

    Returns:
        {
            "query": str,
            "reason": str,
        } or None
    """
    recent = state.contributions[-3:]  # Last round

    # Look for questions or information gaps
    question_patterns = [
        "What is",
        "What are",
        "How much",
        "How many",
        "Do we know",
        "unclear",
        "uncertain",
        "need data",
        "need information",
    ]

    for contrib in recent:
        text = contrib.content
        for pattern in question_patterns:
            if pattern in text:
                # Extract the question/gap
                query = extract_research_query(text, pattern)

                return {
                    "query": query,
                    "reason": f"{contrib.persona_name} raised: {query}",
                }

    return None

# In decide_next_action
async def decide_next_action(self, state, round_number, max_rounds):
    """Decision with research checking."""

    # Check for research needs FIRST (fastest check)
    research_needed = self._check_research_needed(state)

    if research_needed:
        logger.info(f"🔍 Research needed: {research_needed['query']}")

        return FacilitatorDecision(
            action="research",
            reasoning=research_needed['reason'],
            research_query=research_needed['query'],
        ), None  # Skip LLM call

    # Then check moderator needs
    # Then call LLM if neither triggered
```

---

## Implementation Priority

### Phase 1: Quick Wins (This Week)
1. ✅ **Persona caching** - Already done
2. ✅ **Enhanced facilitator logging** - Already done
3. 🔨 **Haiku for facilitator** - 30 min implementation
4. 🔨 **Expose metrics in logs** - 1 hour implementation

### Phase 2: Adaptive System (Next Week)
5. 🔨 **Adaptive round prompts** - 2 hours implementation
6. 🔨 **Adaptive moderator triggers** - 3 hours implementation
7. 🔨 **Research triggers** - 2 hours implementation

### Phase 3: Testing & Tuning (Following Week)
8. Test on 20 deliberations
9. Tune thresholds (convergence, novelty, conflict)
10. Measure improvements

---

## Expected Results

### Current State (Round 2-7)
```
Round 2: Facilitator (25s, $0.027) → Persona speaks (57s, $0.040) = 82s total
Round 3: Facilitator (25s, $0.027) → Persona speaks (52s, $0.038) = 77s total
Round 4: Facilitator (25s, $0.027) → Persona speaks (55s, $0.041) = 80s total
Round 5: Facilitator (25s, $0.027) → Persona speaks (48s, $0.035) = 73s total

Total for 4 rounds: ~312s (5.2 min), ~$0.288
```

### After Optimizations
```
Round 2 (early): Facilitator (4s, $0.002) → Persona speaks (40s, $0.032) = 44s
Round 3 (early): Facilitator (4s, $0.002) → Persona speaks (38s, $0.030) = 42s
Round 4 (middle): Facilitator (4s, $0.002) → Persona speaks (32s, $0.024) = 36s
Round 5 (late): Facilitator (4s, $0.002) → Persona speaks (22s, $0.016) = 26s

Total for 4 rounds: ~148s (2.5 min), ~$0.120
```

### Improvements
- ⚡ **Speed**: 5.2 min → 2.5 min (53% faster)
- 💰 **Cost**: $0.288 → $0.120 (58% cheaper)
- 🎯 **Quality**: Better convergence, less drift
- 📊 **Visibility**: Metrics exposed in logs

---

## Monitoring & Success Criteria

### Metrics to Track
- Average time per round (target: <40s)
- Cost per deliberation (target: <$0.15)
- Early stop rate (target: >30% of deliberations stop before max rounds)
- Consensus level at completion (target: >70%)
- User feedback on deliberation quality

### Dashboard
```
=== Deliberation Performance ===
Total rounds: 5 / 7
Total time: 2m 28s
Total cost: $0.118

Convergence trajectory:
Round 1: 0.32 ━━━━░░░░░░
Round 2: 0.51 ━━━━━░░░░░
Round 3: 0.68 ━━━━━━━░░░
Round 4: 0.84 ━━━━━━━━░░
Round 5: 0.91 ━━━━━━━━━░ ✓ Consensus reached

Moderator interventions: 1 (contrarian at round 3)
Research calls: 0
Early stop: YES (2 rounds saved)
```

---

## Notes

1. **All changes backward compatible**: Can enable/disable optimizations via config
2. **A/B testing ready**: Can compare old vs new approach on same problems
3. **Research-aligned**: All optimizations match CONSENSUS_BUILDING_RESEARCH.md recommendations
4. **User control**: Exposed metrics allow user to see what's happening and tune thresholds

