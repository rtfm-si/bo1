# Board of One: UX Design Principles & IP Protection

**Last Updated**: 2025-01-16 (Week 6 Planning)

---

## Executive Summary

Board of One's competitive advantage lies in proprietary deliberation mechanics (balancer logic, persona weighting, convergence algorithms). **We protect this IP through UX design**, not just code secrecy. Users see polished outputs (expert insights, synthesis), never orchestration mechanics.

**Key Principle**: "Show the magic, hide the machinery."

---

## 1. Positioning Strategy

### What We Sell (Outcomes, Not Mechanisms)

**DO SAY**:
- "Research-inspired advisory intelligence"
- "Proprietary deliberation model"
- "Multi-perspective decision support"
- "We help you think better, not just faster"
- Specific outcomes: "Reduce decision regret by 40%", "Identify blind spots in <15 minutes"

**NEVER SAY**:
- "Multi-agent LLM system"
- "Persona voting algorithm"
- "Our moderator triggers when X happens..."
- Technical architecture details (LangGraph, Claude API, Redis)

### Authority Through Opacity

**Positioning Language**:
- "Cutting-edge AI" → ✅ (but be specific: "ensemble reasoning", "iterative refinement")
- "Research-backed" → ✅ (but cite: "Based on deliberative democracy research", "Inspired by expert panel methodologies")
- "Proprietary model" → ✅ (opaque, authoritative)
- "Our system evaluates..." → ✅ (abstract, no implementation)

**Forbidden Phrases**:
- "5 personas debate your problem"
- "We use Claude Sonnet 4.5"
- "If convergence < 0.85, moderator intervenes"
- Any mention of: weighting, balancers, decomposition heuristics, round limits

### Marketing Message Framework

**Primary Message**:
> "Board of One gives solo founders clarity and confidence for complex decisions. In 5-15 minutes, you'll get structured insights from diverse expert perspectives—without the cost or time of hiring advisors."

**Secondary Messages**:
- Outcomes: "Make better decisions, faster"
- Process: "Like having a board meeting with yourself"
- Authority: "Research-inspired deliberation technology"
- Trust: "Transparent reasoning, not black-box answers"

**Never Lead With**:
- Technology stack
- Implementation details
- How many personas or rounds
- Cost per deliberation

---

## 2. Two-Layer UX Architecture

### Visible Layer (Safe to Show Users)

**What Users See**:
1. **Expert Persona Messages** (polished, final only)
   - Persona name, expertise, avatar
   - Final contribution text (NOT intermediate reasoning)
   - Confidence level: "High", "Medium", "Low" (NOT numeric scores)
2. **Facilitator Summaries**
   - "Where advisors align: ..."
   - "Where advisors diverge: ..."
   - "Key tensions to resolve: ..."
   - NEVER: "Moderator activated", "Balancer adjusted weights"
3. **Insight Flags**
   - Risk notes: "⚠️ Execution capacity constraint identified"
   - Opportunity notes: "💡 Quick-win strategy available"
   - NOT: How insights were detected or scored
4. **Final Synthesis**
   - Executive summary
   - Action plan with priorities
   - Risk assessment
   - NOT: How synthesis was generated
5. **Progress Indicators**
   - Visible micro-stages: "Framing problem" → "Gathering perspectives" → "Aligning insights"
   - Stage transitions (animated)
   - NOT: Graph node names, round numbers, convergence scores

### Hidden Layer (IP Protection - Never Show)

**What Users NEVER See**:
1. **Persona Weighting/Scoring**
   - Initial weights, dynamic adjustments
   - Confidence scores (numeric)
   - Influence calculations
2. **Balancer Activations**
   - When balancer triggered
   - What balancer adjusted
   - Balancer reasoning
3. **Moderator Interventions**
   - Moderator messages
   - Why moderator intervened
   - Moderator strategies
4. **Debate Mechanics**
   - Round numbers ("Round 3 of 10")
   - Convergence scores (0.0-1.0)
   - Novelty metrics
   - Problem drift detection
5. **Decomposition Logic**
   - Why problem was split into N sub-problems
   - Heuristics applied (complexity, independence, etc.)
   - Atomic vs. composite decisions
6. **Reasoning Chains**
   - Internal thinking (chain-of-thought)
   - Intermediate outputs
   - Model self-critique
7. **Graph Execution**
   - Node names ("decompose_node", "facilitator_decide")
   - Edge routing decisions
   - Checkpoint saves
   - Loop prevention triggers
8. **Internal Timestamps/Counters**
   - Step counts
   - Token usage (end users)
   - Cache hit rates
   - LLM latency

### Admin Exception (Debug Mode)

**Admin Dashboard ONLY**:
- Full system visibility (all hidden layer elements)
- Raw state inspector (JSON)
- Graph execution timeline
- Internal metrics dashboard
- Debug export for support tickets

**Access Control**:
- Requires `role="admin"` (database field)
- Never exposed via end-user API
- Separate admin routes (`/admin/*`)

---

## 3. Progressive Disclosure UX (Solving "Blank Screen Problem")

### The Problem

**User Experience Failure**:
- Deliberations take 5-15 minutes
- Users see: Blank screen or static spinner for 10 minutes
- Users think: "Is it broken? Should I refresh?"
- Users abandon: 40% churn on first session

### The Solution: Micro-Stages + Staggered Reveals

**Principle**: People don't mind waiting if they feel progress. People abandon if they feel confusion.

#### Micro-Stages (Visible Narrative)

Map graph nodes → user-friendly stages:

| Graph Node(s) | Visible Stage | Duration | What User Sees |
|---------------|---------------|----------|----------------|
| `decompose` | "Framing problem" | 30s | "Breaking your question into focus areas..." |
| `select_personas` | "Gathering perspectives" | 20s | "Assembling expert advisory panel..." |
| `initial_round` | "Gathering perspectives" | 60s | Advisor typing indicators → contributions appear |
| `facilitator_decide` + `persona_contribute` | "Analyzing tensions" | 45s | "Advisors refining positions..." |
| `check_convergence` + `vote` | "Aligning insights" | 30s | "Synthesizing recommendations..." |
| `synthesize` | "Preparing recommendations" | 45s | "Drafting final report..." |

**Implementation**:
- Never show raw node names
- Always show estimated duration + progress bar
- Transition animations between stages
- Update at least every 30 seconds

#### Staggered Advisor Reveals (Not Bulk Dump)

**Bad UX**: 5 advisors contribute in parallel → all appear at once after 5 seconds (bulk dump)

**Good UX**: 5 advisors appear one-by-one as they complete, with minimum spacing to maintain activity

**Natural Pacing Strategy**:
1. Execute all expert calls in parallel (fastest execution ~5s total for Haiku)
2. Stream contributions as they complete using `asyncio.as_completed()`
3. If multiple complete simultaneously, space reveals 3-5s apart (configurable)
4. Natural variance in LLM response times creates organic stagger (3-8s range)

**Example Timeline** (5 experts, Haiku ~5s avg):
```
0s: All 5 calls start in parallel
4s: Maria completes (fast) → emit immediately
5s: Zara completes → emit immediately (1s natural gap)
7s: Tariq completes → emit immediately (2s natural gap)
8s: Chen + Aria both complete → emit Chen, delay Aria 3s
11s: Aria emitted (3s minimum spacing)
```

**Result**: User sees activity every 1-3 seconds (no bulk dump, no artificial 45-90s delays)

**Benefits**:
- ✅ No fake delays (honest UX)
- ✅ Maintains parallel execution (fastest possible)
- ✅ Prevents bulk dumps (smooth reveal)
- ✅ Configurable pacing (`min_spacing` parameter)
- ✅ Natural feel (variance creates organic rhythm)

#### Early Partial Outputs

**Show Immediately** (don't wait for full deliberation):
1. **Problem Decomposition** (after `decompose_node`):
   ```
   "We've broken this into 3 focus areas:
   1. Customer acquisition cost analysis
   2. Channel fit for target market
   3. Execution capacity constraints"
   ```
2. **Advisory Panel** (after `select_personas`):
   ```
   "Your Advisory Board:
   - Maria Chen (Finance & Metrics)
   - Zara Okafor (Growth Marketing)
   - Tariq Hassan (Business Strategy)"
   ```
3. **Facilitator Reflections** (after each round):
   ```
   "Early signals show optimism around paid channels, but risk alignment forming around execution capacity."
   ```

#### Live Insight Flags (Emerging Patterns)

**During deliberation**, show real-time insights:
- "💡 Quick-win opportunity identified: Paid ads for validation phase"
- "⚠️ Risk emerging: Execution bandwidth constraints"
- "🔄 Advisors refining: CAC target assumptions"

**Implementation**:
- Simple keyword extraction (no LLM needed)
- Emit `insight_emerging` SSE event
- Display as animated pills above contribution feed

#### Background Mode (Optional)

**For users who don't want to watch**:
- Toggle: "We'll ping you when ready (5-10 min)"
- Close SSE connection (save server resources)
- Send browser notification when complete
- Optional: Email notification (user preference)

**User Flow**:
1. User submits problem
2. Deliberation starts → micro-stages begin
3. User clicks "Continue in Background"
4. User closes tab or switches to other work
5. 8 minutes later: Browser notification fires
6. User returns to see full results

---

## 4. Concrete Things to Hide (IP Protection Checklist)

### Never Expose to End Users

**Mechanics**:
- [ ] Persona weighting formulas
- [ ] Balancer activation triggers
- [ ] Moderator intervention logic
- [ ] Convergence score thresholds (0.85, etc.)
- [ ] Round number limits (10 max, etc.)
- [ ] Decomposition heuristics (complexity scoring)
- [ ] Problem drift detection thresholds
- [ ] Vote aggregation algorithms

**Internal State**:
- [ ] Graph node names ("decompose_node", "persona_contribute")
- [ ] Round numbers ("Round 3 of 10") → use "Refining insights..." narrative
- [ ] Convergence scores (numeric) → use "Nearing consensus..." if needed
- [ ] Persona confidence scores (0.0-1.0) → use "High/Medium/Low"
- [ ] Token usage or cost (end users don't see)
- [ ] Cache hit rates
- [ ] Internal timestamps (elapsed time OK, step counts NO)

**Reasoning**:
- [ ] Chain-of-thought (even collapsed)
- [ ] Intermediate reasoning steps
- [ ] Model self-critique
- [ ] Facilitator internal planning

**Graph Execution**:
- [ ] Node execution order
- [ ] Edge routing decisions
- [ ] Checkpoint save events
- [ ] Loop prevention triggers
- [ ] Recursion limits

### Admin Dashboard Exceptions

**Full visibility available for debugging**:
- ✅ Raw state JSON
- ✅ All graph nodes + transitions
- ✅ Persona weights + confidence scores
- ✅ Moderator/balancer logs
- ✅ Convergence metrics
- ✅ Token usage + cost
- ✅ Reasoning chains

**Access Control**:
- Requires `role="admin"` in database
- Separate admin routes (`/admin/debug/sessions/{id}`)
- Never exposed via end-user API

---

## 5. Marketing Language Guidelines (Week 14 Launch)

### Landing Page Copy

**Hero Section**:
- Headline: "Think Better. Decide Faster. Lead with Confidence."
- Subheadline: "Board of One gives solo founders the clarity of a full advisory board—in 15 minutes, not 15 meetings."

**How It Works** (3-step):
1. "Share Your Decision" → User submits problem
2. "Expert Perspectives Assemble" → System deliberates (show micro-stages, NOT graph)
3. "Get Actionable Insights" → Synthesis report delivered

**Social Proof**:
- "Reduced decision regret by 40% for 200+ founders"
- "Identified blind spots in <15 minutes"
- "Like having a CFO, CMO, and strategist on speed dial"

### FAQs (Address "How Does It Work?")

**Question**: "How does Board of One generate insights?"

**Bad Answer**: "We use 5 AI personas that debate your problem across multiple rounds using Claude Sonnet 4.5."

**Good Answer**: "Board of One uses a proprietary deliberation model that simulates expert panel discussions. Our research-inspired approach surfaces diverse perspectives, identifies blind spots, and synthesizes actionable recommendations—all in 5-15 minutes."

**Question**: "Is this just ChatGPT for business decisions?"

**Bad Answer**: "No, we use multi-agent orchestration with LangGraph and prompt engineering."

**Good Answer**: "No. ChatGPT gives you one answer fast. Board of One gives you multiple expert perspectives that challenge each other, then synthesizes a balanced recommendation. It's the difference between asking one friend vs. convening a board meeting."

### Trust Signals (Not Technical Details)

**DO emphasize**:
- "Research-backed methodology"
- "Thousands of deliberations completed"
- "Trusted by YC founders" (if true)
- Specific outcomes: "Avg. decision confidence +35%"

**DON'T emphasize**:
- "Powered by Claude Sonnet 4.5"
- "Uses LangGraph for orchestration"
- "5 personas with dynamic weighting"

---

## 6. Event Filtering Reference

### End-User SSE Events (ALLOWED)

```typescript
const userFacingEvents = [
  "session_started",
  "stage_transition",        // "framing_problem" → "gathering_perspectives"
  "advisor_typing",          // Maria is thinking...
  "advisor_complete",        // Maria's contribution ready
  "facilitator_summary",     // Where advisors align/diverge
  "insight_emerging",        // Risk/opportunity flags
  "synthesis_ready",         // Final report ready
  "session_complete",
  "error",                   // User-facing errors only
];
```

### Internal Events (BLOCKED from end users)

```typescript
const internalEvents = [
  "decompose_node_start",
  "decompose_node_end",
  "select_personas_node_start",
  "facilitator_decide_node_start",
  "persona_contribute_node_start",
  "moderator_intervene",         // IP: Moderator logic
  "balancer_activate",           // IP: Balancer logic
  "convergence_check",           // IP: Convergence algorithm
  "weighting_updated",           // IP: Persona weighting
  "checkpoint_saved",            // Internal state management
  "loop_prevention_triggered",   // Internal safety
  "cost_updated",                // Internal cost tracking (end users see final cost only)
];
```

### Admin-Only Events (DEBUG mode)

```typescript
const adminOnlyEvents = [
  ...internalEvents,             // All internal events
  "graph_state_snapshot",        // Full state at each step
  "llm_call_metadata",           // Model, tokens, latency, cost
  "cache_hit",                   // Prompt caching stats
  "redis_checkpoint_saved",      // Checkpoint details
  "reasoning_chain",             // Chain-of-thought outputs
];
```

---

## 7. Success Metrics (Week 14)

### UX Metrics

- [ ] **Session completion rate**: >85% (vs. <60% with blank screens)
- [ ] **Avg. time to first engagement**: <10 seconds (show decomposition immediately)
- [ ] **Background mode adoption**: 30-40% of users
- [ ] **User feedback**: "Never felt lost" >90%

### IP Protection Metrics

- [ ] **Internal event leaks**: 0 (audit daily in admin dashboard)
- [ ] **Support tickets asking "How does it work?"**: <5% (opaque positioning works)
- [ ] **Competitor reverse-engineering attempts**: Detectable via honeypot endpoints (future)

### Positioning Metrics

- [ ] **Landing page conversion**: >5% (vs. <2% with technical language)
- [ ] **User quotes mentioning outcomes**: >80% ("clarity", "confidence", "blind spots")
- [ ] **User quotes mentioning tech**: <10% ("AI", "personas", "algorithm")

---

**END OF DOCUMENT**
