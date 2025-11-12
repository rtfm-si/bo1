# Board of One (bo1) - Product Requirements Document

## 1. Vision & Overview

**Board of One** is a console-based AI system that helps users solve complex problems through structured decomposition, multi-perspective debate, and collaborative synthesis. By simulating a board of domain experts, the system transforms vague or overwhelming challenges into actionable recommendations.

### Core Concept

When faced with a complex decision or problem, most people lack access to a diverse group of experts who can debate options, challenge assumptions, and arrive at well-reasoned solutions. Board of One democratizes this advisory board experience through AI.

### Key Principles

- **User Sovereignty**: The end user is the ONLY person who can perform and take/accept actions. The system provides recommendations, NOT directives. All outputs are advisory.
- **Decomposition First**: Break complex problems into manageable, sequential, or non-sequential sub-problems
- **Diverse Perspectives**: Multiple expert personas with different viewpoints and expertise
- **Structured Debate**: Facilitated discussion prevents groupthink and surfaces trade-offs
- **Democratic Decision**: Voting ensures balanced consideration of options, weighted by reversibility
- **Synthesized Output**: Clear, actionable recommendations with rationale
- **Reversibility Awareness**: One-way door decisions (irreversible) require higher consensus than two-way door decisions (reversible)
- **Guardrails & Safety**: System includes prompts with guardrails to prevent harmful recommendations and ensure responsible advice

---

## 2. User Stories

### Primary Use Cases

**As a user facing a complex decision, I want to:**

- Input my problem in natural language without needing to structure it
- Understand how my problem breaks down into smaller, manageable pieces
- Hear diverse expert perspectives on each aspect of my problem
- See experts debate and challenge each other's assumptions
- Receive a clear, actionable recommendation based on expert consensus

**Example Scenarios (Solopreneur Focus):**

1. **Product Direction Choice**:
   "I have $50K saved and 12 months runway. Should I build a B2B SaaS dashboard tool, a consumer mobile app for habit tracking, or a freelance marketplace for technical writers?"

   **Context:**

   - Resources: $50K, 12 months, solo developer with design skills
   - Success criteria: $5K MRR by month 9, product-market fit signals by month 6
   - Constraints: No technical co-founder, limited marketing budget ($5K), previous startup failed
   - Skills: Full-stack dev, decent at design, weak at sales/marketing

   **Sub-problems:**

   - Market opportunity sizing: Which has fastest path to $5K MRR?
   - Solo-founder feasibility: Which can one person realistically build and sell?
   - Competitive landscape: Where do I have unfair advantage or differentiation?
   - Go-to-market fit: Which aligns with my weak marketing skills?
   - Financial burn rate: Which option optimizes runway vs. development time?
   - Pivot potential: If this fails, which provides most learnings/assets for next attempt?

2. **Pricing Strategy Decision**:
   "I have 500 users on my free plan. Should I introduce a $29/month tier, a $99/month tier with premium features, usage-based pricing at $0.10/unit, or keep free and monetize through partnerships?"

   **Context:**

   - Resources: Solo founder, 500 free users, 15% weekly active, built-in analytics
   - Success criteria: Convert 5% to paid within 3 months, maintain 80%+ free user retention
   - Constraints: 2 competitors doing freemium at $20/mo and $50/mo, users are small businesses
   - Current situation: Running out of money in 4 months, users love product but haven't asked to pay

   **Sub-problems:**

   - Value perception: What are users actually willing to pay for?
   - Competitive positioning: How to price against established competitors?
   - Conversion psychology: Which model has highest free-to-paid conversion?
   - Revenue modeling: Which hits $5K MRR fastest with current user base?
   - Churn risk: Which pricing model least likely to alienate free users?
   - Implementation complexity: Which can be built/tested fastest with limited resources?

3. **Growth Channel Prioritization**:
   "I have a working product with 50 paying customers ($3K MRR). Should I focus on content marketing (SEO blog), paid ads (Google/Meta), partnership channel (integrate with Shopify), cold outbound sales, or building a free tool/PLG motion?"

   **Context:**

   - Resources: $3K MRR, $2K/mo personal expenses, 20 hours/week (still have part-time job)
   - Success criteria: Get to $10K MRR in 6 months to go full-time
   - Constraints: Not a natural writer, hate cold calling, limited ad budget ($500/mo)
   - Current situation: 50 customers came from Reddit posts and word-of-mouth, no repeatable channel

   **Sub-problems:**

   - Channel-skill fit: Which plays to my strengths and available time?
   - ROI timeline: Which channel shows results within 6-month window?
   - Scalability potential: Which can grow beyond my personal time investment?
   - Customer acquisition cost: Which can acquire customers profitably with $500/mo budget?
   - Competitive moats: Which builds defensible advantage vs. competitors?
   - Learning value: If I fail to hit $10K, which teaches most valuable skills?

4. **Technical Debt vs Feature Development**:
   "My app works but has scaling issues, security concerns, and legacy code. Should I spend 3 months refactoring the codebase, ship 2-3 new features customers are requesting, migrate to a more scalable architecture, or hire a contractor to do the refactor while I focus on features?"

   **Context:**

   - Resources: 200 paying customers, $15K MRR, $8K/mo profit, solo technical founder
   - Success criteria: Reach $30K MRR by end of year without major outages
   - Constraints: Current code slows down feature development by ~40%, 2 competitors shipping fast
   - Technical situation: PostgreSQL hitting limits, monolith needs microservices, no test coverage

   **Sub-problems:**

   - Risk assessment: What's probability and impact of major outage if we don't refactor?
   - Growth inhibitors: Is tech debt or lack of features the bigger blocker to $30K MRR?
   - Contractor feasibility: Can someone else refactor without me, or too complex/risky?
   - Customer retention: Will customers churn without new features in 3 months?
   - Competitive dynamics: How much runway before competitors make us irrelevant?
   - Hybrid approach: Can we incrementally refactor while shipping features, or all-or-nothing?

5. **Niche Pivot Decision**:
   "My project management tool has 100 customers across various industries. Should I pivot to serve only law firms (20 customers, willing to pay 3x), double down on current horizontal approach, or pivot to agencies (30 customers, fastest growing segment)?"

   **Context:**

   - Resources: $12K MRR, 2 years in, burnt out from feature requests in all directions
   - Success criteria: Reach $25K MRR in 12 months, reduce feature complexity, improve retention (currently 70%)
   - Constraints: Solo founder, limited development capacity, competitors in every vertical
   - Customer data: Law firms pay $200/mo (vs $80 avg), agencies growing 30% MoM, horizontal churn is 30%

   **Sub-problems:**

   - Market size validation: Is law firm niche big enough to reach $25K MRR?
   - Product-market fit: Which segment has strongest fit vs. needs customization?
   - Churn impact: Will losing horizontal customers during pivot hurt revenue?
   - Development focus: Which direction reduces feature sprawl and complexity?
   - Competitive advantage: Where can I build moat vs. generalist competitors?
   - Personal sustainability: Which keeps me motivated vs. burnt out?

6. **Co-founder vs Solo Decision**:
   "I've been solo for 18 months, at $8K MRR but plateaued. Should I bring on a co-founder (have 2 candidates: sales expert wants 30% equity, technical person wants 25%), hire a part-time salesperson ($3K/mo + commission), or stay solo and focus on product-led growth?"

   **Context:**

   - Resources: $8K MRR, $5K/mo profit, strong product, weak at sales/marketing
   - Success criteria: Break through plateau to $20K MRR, sustainable growth, maintain control
   - Constraints: Giving up equity is scary, cash flow tight for hiring, working 60hr weeks
   - Candidates: Sales co-founder has industry network but no startup experience; technical co-founder reduces my load but doesn't solve growth problem

   **Sub-problems:**

   - Bottleneck diagnosis: Is sales/marketing the real blocker, or product/positioning?
   - Equity vs cash: What's true value of 25-30% equity vs. hiring costs over 2 years?
   - Co-founder fit: Are these candidates committed or just interested?
   - Control vs growth: How much equity/control am I willing to trade for growth?
   - Alternative solutions: Can I solve growth without co-founder or hire?
   - Reversibility: Which decision is hardest to undo if wrong?

---

## 3. Core Features

### 3.1 Problem Intake

- **Natural Language Input**: User describes problem conversationally
- **Clarification Round**: System asks 0-3 clarifying questions to understand context
- **Problem Statement**: System generates clear problem statement for user confirmation

### 3.2 Problem Decomposition

- **Automatic Breakdown**: System decomposes problem into 1-5 sub-problems
  - 1 sub-problem: Atomic problem (same as original, no decomposition needed)
  - 2-3 sub-problems: Simple to moderate complexity
  - 4 sub-problems: Complex problem, thorough analysis
  - 5 sub-problems: Maximum allowed, highly complex
  - If >5 identified: Group into 3-5 meta-problems for recursive decomposition
- **Sub-Problem Framing**: Each sub-problem defines GOAL and CONTEXT, not pre-determined options
  - Goal: What decision/question needs resolving
  - Context: Constraints, resources, success criteria
  - Options: Emerge from expert debate (NOT defined at decomposition)
  - Example: "Identify optimal growth channel given constraints" vs. "Choose between A, B, or C"
- **Dependency Mapping**: Identifies sequential vs. parallel sub-problems
- **Complexity Scoring**: Each sub-problem assigned complexity score (1-10) by Decomposer LLM
  - Score 1-3 (Simple): Binary choice, low ambiguity, single domain
  - Score 4-6 (Moderate): Multiple factors, some ambiguity, 2-3 domains
  - Score 7-10 (Complex): Many factors, high ambiguity, 3+ domains, one-way door
  - Determines max debate rounds: Simple (5), Moderate (7), Complex (10)
- **User Review**: User can modify, merge, or add sub-problems
- **Success Criteria**: Each sub-problem has clear evaluation criteria
- **Depth Management**: Complex sub-problems get more detailed framing rather than creating excessive sub-problems

### 3.3 Expert Board Assembly

- **Dynamic Roster**: System selects 3-5 expert personas based on problem domain
- **Diverse Perspectives**: Ensures mix of optimist/pessimist, risk-taker/conservative, specialist/generalist
- **Persona Profiles**: Each expert has background, expertise, and decision-making style
- **User Override**: User can request specific expert types or remove personas (v2 feature)

### 3.4 Facilitated Debate (Per Sub-Problem)

- **Opening Statements**: Each expert shares initial perspective (1-2 short paragraphs)
- **Debate Rounds**: Adaptive (complexity-based, with early stopping)
  - **Minimum**: 1 round (opening statements only, if immediate consensus)
  - **Typical**: 3-7 rounds (most common range)
  - **Maximum**: Complexity-based hard cap
    - Simple (complexity 1-3): 5 rounds max
    - Moderate (complexity 4-6): 7 rounds max
    - Complex (complexity 7-10): 10 rounds max
    - **Hard cap**: 15 rounds (prevents cognitive overload)
  - **Early Stop**: System stops when consensus reached or diminishing returns detected
  - **Research-backed**: Most value comes from rounds 3-5; gains minimal after round 7-10
- **Round Structure**:
  - Round 1: Initial positions and reasoning
  - Round 2+: Responses, challenges, counterarguments
  - Final round: Refined positions, concessions, consensus-building
- **Facilitator Role**:
  - Keeps discussion on track
  - Highlights disagreements
  - Asks probing questions
  - Ensures all voices heard
  - Triggers early stop when convergence detected
  - Summarizes key points

### 3.5 Voting Mechanism

- **Option Formulation Timing**: Options are formulated AFTER debate, not before
  - **Research-backed**: Prevents anchoring bias, encourages divergent thinking
  - **Discovery over prescription**: Better solutions may emerge during debate
  - **If user provides specific options**: Treated as context, but experts can challenge or suggest alternatives
- **Options Presented**: Facilitator distills 2-4 distinct options from debate
  - Options represent actual positions that emerged from expert discussion
  - Each option includes: Clear description, Pros, Cons, "Best if" conditions
  - Typically 2-4 options (fewer = weak exploration, more = decision paralysis)
- **Expert Votes**: Each expert votes for one option with brief rationale
- **Vote Transparency**: User sees how each expert voted and why
- **Weighted Consideration**: Not pure majority - considers strength of arguments, confidence levels, and reversibility

### 3.6 Synthesis & Recommendation

- **Per Sub-Problem**: Facilitator synthesizes voted option with caveats
- **Final Integration**: Combines all sub-problem recommendations into coherent whole
- **Trade-offs Highlighted**: Explicitly states what's gained and sacrificed
- **Implementation Path**: Sequential steps for acting on recommendation
- **Confidence Level**: System indicates confidence in recommendation (low/medium/high)

---

## 4. System Flow

```
1. PROBLEM INTAKE
   ├─ User inputs problem
   ├─ System asks clarifying questions (only critically blocking questions)
   ├─ System generates problem statement
   └─ User confirms/edits

2. DECOMPOSITION
   ├─ System breaks into sub-problems (1-5 sub-problems)
   ├─ Identifies dependencies (sequential vs parallel)
   ├─ Assigns complexity score to each (1-10 scale)
   └─ Finalizes structure

3. BOARD ASSEMBLY
   ├─ System analyzes problem domain and requirements
   ├─ Compares candidate personas (expertise, perspective, diversity)
   ├─ Selects 2-6 expert personas for balanced board
   └─ Ensures diversity: risk tolerance, time horizon, approach style

4. FOR EACH SUB-PROBLEM (in dependency order):
   │
   ├─── 4.1 INITIALIZE SUB-PROBLEM DELIBERATION
   │    ├─ Facilitator frames sub-problem with clear goal
   │    ├─ Calculate adaptive round limits based on complexity:
   │    │  • Simple (complexity 1-3): 3-5 rounds max
   │    │  • Moderate (complexity 4-6): 5-7 rounds max
   │    │  • Complex (complexity 7-10): 7-10 rounds max
   │    ├─ Initialize convergence tracking metrics:
   │    │  • Semantic similarity baseline
   │    │  • Novelty score threshold
   │    │  • Conflict score monitoring
   │    └─ Show problem statement in all prompts (prevent drift)
   │
   ├─── 4.2 DEBATE LOOP (Adaptive rounds with early stopping)
   │    │
   │    ├── Phase 1: OPENING ROUND (Required, ~1-2 min)
   │    │   ├─ Each expert gives opening statement (100-150 words)
   │    │   ├─ Focus: Initial position, key concerns, questions
   │    │   ├─ Experts consider: "What would other experts think?"
   │    │   └─ Metrics: HIGH novelty expected, LOW convergence
   │    │
   │    ├── Phase 2: EARLY DEBATE - Divergent Thinking (Rounds 2-4, ~2-3 min)
   │    │   │
   │    │   ├─ FACILITATOR ORCHESTRATION (per round):
   │    │   │  ├─ Polls experts: Who wants to speak?
   │    │   │  ├─ Selection rules:
   │    │   │  │  • Never same expert twice in a row
   │    │   │  │  • Prioritize experts with new material insights
   │    │   │  │  • Directly invite silent experts if needed
   │    │   │  ├─ Checks for premature consensus:
   │    │   │  │  • If agreement >80% before round 3 → Devils advocate
   │    │   │  │  • If overly positive → Contrarian intervention
   │    │   │  │  • If overly pessimistic → Optimist intervention
   │    │   │  └─ Round summary: Key disagreements, open questions
   │    │   │
   │    │   ├─ EXPERT CONTRIBUTIONS (fluid, opt-in):
   │    │   │  ├─ Experts speak ONLY if material value to add:
   │    │   │  │  • New evidence or perspective
   │    │   │  │  • Challenge to another's position
   │    │   │  │  • Answer to open question
   │    │   │  ├─ Experts can request RESEARCH (v1: limited):
   │    │   │  │  • Expert mentions need in statement: "I'd need research on X"
   │    │   │  │  • Facilitator detects request via LLM parsing
   │    │   │  │  • Researcher agent called asynchronously
   │    │   │  │  • v1 Source: LLM built-in knowledge (no external search)
   │    │   │  │  • Findings presented in NEXT round
   │    │   │  │  • v1 Limit: Max 2 research requests per sub-problem
   │    │   │  │  • v2 Enhancement: Web search, database queries
   │    │   │  └─ Must respond to others' arguments (no monologues)
   │    │   │
   │    │   └─ QUALITY CONTROLS (continuous monitoring):
   │    │       ├─ Problem drift detection:
   │    │       │  • Check relevance to sub-problem goal (score 0-10)
   │    │       │  • If score <6 → Facilitator redirects discussion
   │    │       ├─ Novelty tracking:
   │    │       │  • Calculate semantic novelty vs. past contributions
   │    │       │  • Flag if novelty <0.3 (repetition warning)
   │    │       └─ No repetition: Prevent rehashing same arguments
   │    │
   │    ├── Phase 3: MIDDLE DEBATE - Analysis & Evidence (Rounds 5-7, ~2-4 min)
   │    │   ├─ Deep dive into contentious points
   │    │   ├─ Research requests more common
   │    │   ├─ Facilitator asks probing questions
   │    │   ├─ Experts challenge assumptions with evidence
   │    │   └─ Metrics: Research calls peak, conflict may increase
   │    │
   │    ├── Phase 4: LATE DEBATE - Convergent Thinking (Rounds 8-10, ~1-2 min)
   │    │   ├─ Experts refine positions based on discussion
   │    │   ├─ Identify areas of consensus
   │    │   ├─ Address remaining objections
   │    │   ├─ Facilitator synthesizes common ground
   │    │   └─ Metrics: DECREASING novelty, INCREASING convergence
   │    │
   │    └── ADAPTIVE STOPPING CRITERIA (checked each round):
   │        │
   │        ├─ EARLY STOP - Consensus Reached:
   │        │  • Semantic convergence >0.85 (experts aligning)
   │        │  • Novelty score <0.3 (no new arguments)
   │        │  • Conflict score <0.2 (low disagreement)
   │        │  • Minimum 5 rounds completed
   │        │  → ACTION: Skip to voting
   │        │
   │        ├─ EARLY STOP - Diminishing Returns:
   │        │  • Marginal utility <0.3 for 2 consecutive rounds
   │        │  • No new insights being generated
   │        │  • Argument repetition rate >60%
   │        │  → ACTION: Move to voting
   │        │
   │        ├─ INTERVENTION - Deadlock Detected:
   │        │  • Conflict score >0.8 for 5+ rounds
   │        │  • Circular refutation pattern detected
   │        │  • Polarization: 40-60% split persisting
   │        │  → ACTION: Facilitator breaks deadlock or force vote
   │        │
   │        ├─ HARD LIMITS (safety nets):
   │        │  • Max rounds reached (complexity-based)
   │        │  • Time limit exceeded (3-5 min per sub-problem)
   │        │  • Cost threshold exceeded
   │        │  → ACTION: Force transition to voting
   │        │
   │        └─ CONTINUE DELIBERATION:
   │           • Healthy debate (conflict 0.2-0.8)
   │           • Novel contributions emerging
   │           • Convergence not yet reached
   │           → ACTION: Next round
   │
   ├─── 4.3 VOTING & CONFIDENCE CALIBRATION
   │    │
   │    ├─ OPTION FORMULATION:
   │    │  ├─ Facilitator distills 2-4 distinct options from debate
   │    │  ├─ For each option:
   │    │  │  • Clear description
   │    │  │  • Pros (2-3 key advantages)
   │    │  │  • Cons (2-3 key disadvantages)
   │    │  │  • Best if: Conditions where optimal
   │    │  └─ Options represent meaningful choice (not trivial variants)
   │    │
   │    ├─ INITIAL VOTING:
   │    │  ├─ Each expert votes for one option
   │    │  ├─ Provides rationale (50-100 words)
   │    │  ├─ States confidence level (0-1 scale)
   │    │  └─ All votes collected in parallel
   │    │
   │    ├─ CONFIDENCE CALIBRATION (always performed, 30-60 seconds):
   │    │  ├─ Show all votes to all experts (after initial voting)
   │    │  ├─ Each expert reconsiders confidence (parallel execution):
   │    │  │  • If outlier vote → Lower confidence
   │    │  │  • If majority agrees → Maintain/increase confidence
   │    │  │  • If unique expertise → Maintain confidence
   │    │  │  • Prompt: "Given the group's votes, reconsider your confidence"
   │    │  ├─ Experts update confidence scores (may stay same)
   │    │  ├─ Final aggregation uses calibrated confidence
   │    │  └─ Research: 15-25% improvement in calibration accuracy
   │    │
   │    │  v1: Always run (minimal cost, high quality gain)
   │    │  Display both pre/post calibration in transcript (optional detail)
   │    │
   │    └─ VOTE AGGREGATION (automatic mechanism selection):
   │       │
   │       ├─ STEP 1: Assess Decision Reversibility (via Facilitator):
   │       │  • One-way door: Large financial commitment, legal agreement, hiring/firing
   │       │  • Two-way door: Experiments, pilots, iterative changes, feature decisions
   │       │
   │       ├─ STEP 2: Select Voting Mechanism:
   │       │  │
   │       │  ├─ IF one-way door:
   │       │  │  → Use UNANIMOUS or SUPERMAJORITY (≥75%)
   │       │  │  → Require strong consensus for irreversible decisions
   │       │  │  → If not achieved: recommendation is "need more analysis" or "defer"
   │       │  │
   │       │  ├─ ELSE IF two-way door AND low confidence spread:
   │       │  │  → Use SIMPLE MAJORITY (>50%) - most common
   │       │  │
   │       │  ├─ ELSE IF two-way door AND high confidence spread:
   │       │  │  → Use CONFIDENCE-WEIGHTED voting
   │       │  │  → Weight high-confidence experts more heavily
   │       │  │
   │       │  └─ DEFAULT: SIMPLE MAJORITY (>50%)
   │       │
   │       ├─ STEP 3: Calculate Results:
   │       │  • Simple majority: Count votes (most common)
   │       │  • Confidence-weighted: Weight by calibrated confidence scores
   │       │  • Consensus level: Calculate agreement percentage
   │       │  • Identify dissenting opinions for synthesis
   │       │
   │       └─ STEP 4: Present Result With Context:
   │          • Show which mechanism was used and why
   │          • Example: "Using unanimous voting because this is irreversible (one-way door)"
   │          • Show vote distribution regardless of mechanism
   │
   │          v1 Implementation: Default to SIMPLE MAJORITY for all decisions
   │          v2 Enhancement: Add reversibility auto-detection
   │
   │          Research Finding: Most LLM multi-agent systems use only dictatorial
   │          or plurality voting (lack of diversity). System should adapt voting
   │          mechanism to decision stakes and context.
   │
   ├─── 4.4 SUB-PROBLEM SYNTHESIS & COMMITMENT
   │    │
   │    ├─ SYNTHESIZE RECOMMENDATION:
   │    │  ├─ Consider vote distribution + argument strength
   │    │  ├─ Refer back to original sub-problem goal
   │    │  ├─ Acknowledge dissenting views respectfully
   │    │  ├─ Explain reasoning for recommendation
   │    │  ├─ State confidence level in recommendation
   │    │  └─ Highlight caveats and conditions
   │    │
   │    ├─ COMMITMENT PROTOCOL (conditional "disagree and commit"):
   │    │  │
   │    │  ├─ TRIGGER CONDITIONS (generate statement if ANY):
   │    │  │  • Vote split ≥30% (e.g., 4 vote A, 2 vote B = 33% dissent)
   │    │  │  • Average confidence <0.65 (indicates uncertainty)
   │    │  │  • One-way door decision WITH dissenting votes
   │    │  │  • Explicit strong objection in expert rationale
   │    │  │
   │    │  ├─ IF TRIGGERED, Facilitator generates:
   │    │  │  • "The board has decided: [DECISION]"
   │    │  │  • "We acknowledge [Expert X] and [Expert Y] had reservations about [concern]"
   │    │  │  • "Despite this dissent, we commit to [DECISION] because: [rationale]"
   │    │  │  • "This decision is FINAL for this sub-problem. We disagree and commit."
   │    │  │
   │    │  ├─ IF NOT TRIGGERED (strong consensus):
   │    │  │  • Simple statement: "The board recommends [DECISION] with high confidence (0.85)."
   │    │  │  • Skip "disagree and commit" framing
   │    │  │
   │    │  └─ PURPOSE:
   │    │     • Prevents endless relitigating
   │    │     • Acknowledges dissent respectfully
   │    │     • Forces forward progress despite imperfect consensus
   │    │
   │    └─ DELIBERATION QUALITY REPORT:
   │       ├─ Efficiency metrics:
   │       │  • Rounds used vs. max allowed
   │       │  • Time elapsed
   │       │  • Early stop triggered? (convergence/utility)
   │       ├─ Quality metrics:
   │       │  • Final consensus level (%)
   │       │  • Average confidence score
   │       │  • Problem drift score (0 = on-topic)
   │       │  • Research requests utilized
   │       └─ Interventions:
   │          • Facilitator interventions (devils advocate, etc.)
   │          • Deadlocks resolved
   │          • Moderator redirects

5. FINAL RECOMMENDATION (Cross-Sub-Problem Integration)
   ├─ Integrate all sub-problem solutions into coherent plan
   ├─ Check for conflicts between sub-problem recommendations
   ├─ Highlight key trade-offs across entire problem
   ├─ Provide sequential implementation roadmap
   ├─ State overall confidence level
   └─ Include "disagree and commit" framing if needed
```

---

## 4.5 Key System Design Principles (Research-Backed)

### 4.5.1 Preventing Debate Death Spirals

**Multi-Layered Safety Net:**

1. **Hard Limits**: Iteration caps (complexity-based), time limits (3-5 min), cost thresholds
2. **Adaptive Stopping**: Semantic convergence, novelty tracking, marginal utility
3. **Structural Interventions**: Facilitator moderation, devils advocate, deadlock breaking
4. **Quality Monitoring**: Problem drift detection, repetition flagging, cognitive overload prevention
5. **Kill Switch**: Manual kill switch override

**Research Finding**: ~0.8% of debates suffer from problem drift, ~0.5% benefit from extended rounds beyond 7-10. Most gains occur in first 3-5 rounds.

### 4.5.2 Convergence Measurement

**Semantic Similarity Tracking**:

- Calculate embedding-based similarity of recent contributions
- High similarity (>0.85) late in debate = convergence/consensus
- Low similarity (<0.5) late in debate = divergence/deadlock

**Novelty Scoring**:

- Each contribution scored against all previous (0-1)
- High novelty (>0.6) early = healthy exploration
- Low novelty (<0.3) late = consensus or repetition
- Low novelty early = groupthink risk

**Conflict Scoring**:

- Macro conflict: Opinion distribution across all experts (0-1)
- Micro conflict: Pairwise disagreement detection
- Low conflict (<0.2) = consensus emerging
- High conflict (>0.8) = deadlock risk

### 4.5.3 Facilitator Intervention Strategy

**Phase-Adaptive Interventions**:

- **Early rounds (1-4)**: Encourage divergence, trigger contrarian if premature consensus
- **Middle rounds (5-7)**: Challenge unverified claims, request evidence, probe assumptions
- **Late rounds (8-10)**: Encourage convergence, synthesize common ground, address holdouts

**Conflict Resolution**:

- Circular arguments → Find common ground, reframe question
- Information gaps → Trigger research requests
- Values disagreements → Acknowledge trade-offs explicitly

**Society of Mind Insight** (key research finding):

- Divergent thinking (disagreement) is valuable EARLY but can hinder performance LATE
- Early debate should encourage multiple perspectives, challenge assumptions
- Late debate should encourage synthesis, convergence, resolution
- Balance needed: Too much divergence late = "irrelevant information that complicates decision-making"

**Stanford Simulacra Insight** (key research finding):

- Pure LLM agents are "excessively polite and cooperative"
- Default to agreement, avoid conflict, suppress dissent
- System MUST explicitly inject disagreement via contrarian/skeptic moderators
- Otherwise: Groupthink, premature consensus, unexplored alternatives

### 4.5.4 Problem Drift Prevention

**Continuous Relevance Checking**:

- Every contribution evaluated against sub-problem goal (0-10)
- Score <6 triggers facilitator redirect
- Problem statement shown in every prompt context
- Facilitator checks relevance every 3-5 rounds

**Research Finding**: Problem drift is #1 cause of diminishing returns in multi-agent debates.

### 4.5.5 Optimal Round Counts

**Complexity-Based Allocation**:

- Simple problems (1-3): 3-5 rounds sufficient
- Moderate problems (4-6): 5-7 rounds optimal
- Complex problems (7-10): 7-10 rounds justified
- Hard cap: 15 rounds (cognitive overload risk)

**Research Finding**: Diminishing returns typically occur after round 7-10. Extended debates (>15 rounds) cause cognitive overload where agents lose track of conversation history.

### 4.5.6 Disagree and Commit

**Forcing Progress Without Perfect Consensus**:

- Acknowledge that perfect agreement is rare
- Use voting to force decision at appropriate stopping point
- Create explicit commitment statement post-vote
- Lock decision to prevent endless reconsideration
- Frame dissent as healthy, commitment as necessary

**Research Finding**: Pure LLM agents default to excessive politeness and cooperation. Need explicit mechanisms to surface disagreement AND to move forward despite it

### 4.5.7 Entropy-Based Monitoring

**Tracking Debate Diversity Over Time**:

- Calculate token entropy of contributions (Shannon entropy)
- High entropy early = diverse perspectives (healthy exploration)
- Decreasing entropy late = convergence (healthy synthesis)
- Increasing entropy late = problem drift or circular arguments (red flag)

**Research Finding**: Entropy metrics predict when debates are productive vs. going in circles. High entropy should naturally decrease as consensus emerges.

### 4.5.8 Cognitive Overload Prevention

**Managing Conversation History**:

- **Symptom**: Agents repeat arguments, contradict themselves, ask answered questions
- **Prevention**:
  - Context window management: Summarize early rounds, keep recent detail
  - Explicit memory aids: Show "key arguments so far" in each prompt
  - Hard iteration cap at 15 rounds (cognitive overload risk beyond this)

**Research Finding**: Extended debates (>15 rounds) cause agents to lose track of conversation history, degrading response quality.

**Implementation Strategy**:

- Early debate (<10 rounds): Show full transcript
- Late debate (>10 rounds): Summarize early, detail recent + key arguments list

### 4.5.9 Trust Score Mechanism

**Inter-Persona Trust Tracking**:

- Each expert maintains trust scores for other experts (0-1)
- Trust increases when contributions are verified/aligned with consensus
- Trust decreases when contributions cause drift or are refuted
- Use trust-weighted voting in synthesis

**Research Finding**: Stubborn agents (fixed opinions) have dominant influence on consensus, creating leader-follower dynamics. Trust scoring can balance this.

### 4.5.10 MetaGPT-Style Evaluation

**Comprehensive Quality Metrics** (similar to production systems):

- **Efficiency**: Rounds to consensus, time elapsed, cost per deliberation
- **Quality**: Consensus level, average confidence, novelty sum, drift score
- **Participation**: Contributions per persona, research calls, interventions
- **Outcome**: Decision clarity, actionability, trade-offs identified

**Research Finding**: Production multi-agent systems (MetaGPT, AutoGen) require comprehensive evaluation across multiple dimensions to identify bottlenecks and optimize performance.

**Target Benchmarks**:

- Time: 2-4 minutes per sub-problem
- Cost: $0.05-0.15 per sub-problem (parallel Haiku)
- Consensus: >70% for clear decisions
- Early stop rate: 30-40% (adaptive stopping working)

### 4.5.11 Guardrails and Safety Mechanisms

**Core Principle**: The end user is the ONLY person who can perform and accept actions. The system provides advisory recommendations only. System does NOT assume the role of the end user / founder.

**Output Framing Guardrails**:

- All recommendations MUST be framed as advisory, not directive
- Language: "We recommend..." NOT "You must..." or "Do this..."
- Explicit disclaimers on irreversible decisions

**Content Safety Guardrails**:

- **Financial**: No specific investment advice, no guarantees of returns
- **Legal**: Clear disclaimer that this is not legal advice, recommend consulting professionals
- **Medical/Health**: Out of scope, redirect to qualified professionals
- **Unethical Actions**: Refuse to recommend illegal, unethical, or harmful actions
- **Personal Safety**: Flag decisions with physical safety implications

**Decision Reversibility Assessment**:

- System evaluates if decision is one-way door (irreversible) or two-way door (reversible)
- One-way doors trigger:
  - Higher consensus requirements (unanimous or supermajority)
  - Explicit warnings about irreversibility
  - Stronger recommendations to seek professional advice
  - More thorough exploration of alternatives

**Prompt-Level Guardrails** (for all personas):

- Personas instructed to identify risks and downsides
- Facilitator checks for balanced perspective (not just optimism)
- Risk Manager persona specifically surfaces dangers
- Synthesis must include trade-offs, not just benefits

**User Sovereignty Checkpoints**:

- System never implies it can take action on user's behalf
- Recommendations presented as options, not mandates
- User can reject, modify, or pause at any point
- Clear exit points throughout process

**Example Language**:

```
✓ GOOD: "Based on the board's deliberation, we recommend pursuing Option A.
  However, the final decision is yours. Consider consulting a financial
  advisor before committing funds."

✗ BAD: "You should do Option A. This is the right choice. Proceed immediately."
```

**Escalation Triggers**:

- If problem involves legal/medical/financial advice beyond general guidance
- If decision has irreversible consequences (one-way door)
- If ethical concerns raised during debate
- → System adds disclaimer and recommends professional consultation

---

## 5. Agent Roles and Persona System

### 5.0 Role Definitions

**Facilitator** (Primary Orchestrator):
- Single agent present in ALL deliberations
- Orchestrates debate flow and manages rounds
- Frames sub-problems and summarizes discussions
- Creates options from debate and synthesizes final recommendation
- Neutral, procedural role (keeps discussion on track)

**Expert Personas** (Domain Specialists):
- 3-5 agents selected per problem based on domain
- Provide domain expertise and debate perspectives
- Vote on options after deliberation
- Examples: Technical Architect, Financial Analyst, Risk Manager

**Moderator Personas** (Conditional Interventions):
- Special personas injected conditionally to improve debate quality
- NOT always present (triggered only when needed)
- Three types:
  - **Contrarian**: Triggers when premature consensus detected (early rounds)
  - **Skeptic**: Triggers when unverified claims made (middle rounds)
  - **Optimist**: Triggers when excessive negativity/deadlock (late rounds)
- Purpose: Prevent groupthink, surface hidden risks, break deadlocks

**Researcher** (Evidence Gatherer):
- Triggered when experts request research
- Gathers evidence from knowledge sources
- Presents findings back to deliberation
- Not a voting member

**Summary:**
- Facilitator = always present, orchestrates
- Expert Personas = always present (3-5), debate and vote
- Moderator Personas = conditional (0-3), improve quality
- Researcher = on-demand, provides evidence

### 5.1 Persona Attributes

Each expert has:

- **Name & Title**: e.g., "Dr. Sarah Chen, Behavioral Economist"
- **Background**: 2-3 sentences of relevant experience
- **Expertise Domain**: Primary area of knowledge
- **Decision-Making Style**:
  - Risk tolerance (conservative → aggressive)
  - Time horizon (short-term → long-term)
  - Perspective (optimistic → pessimistic)
  - Approach (analytical → intuitive)
- **Typical Concerns**: What they typically focus on

### 5.2 Persona Selection Logic

- **Domain Matching**: Select experts relevant to problem domain
- **Perspective Diversity**: Ensure mix of viewpoints
- **Complementary Skills**: Cover different aspects (technical, business, human, financial)
- **Optimal Size**:
  - **3 experts**: Simple problems, single domain (e.g., technical-only decision)
  - **4 experts**: Moderate problems, 2-3 domains (e.g., technical + business)
  - **5 experts**: Complex problems, 3+ domains (e.g., technical + business + financial + risk)
  - **2 experts**: Rare edge case for binary decisions (e.g., "Should I do X or not?")
  - **6 experts**: Rare edge case for highly complex/multidisciplinary problems

**Selection algorithm (v1):**
1. Identify domains needed (technical, financial, market, operations, risk, human)
2. Map to expert personas from pool
3. Ensure diversity in risk tolerance, time horizon, optimism/pessimism
4. Select 3-5 experts (aim for 4 as default)
5. If >5 needed, prioritize most critical domains

**Research finding:** 3-5 agents optimal for multi-agent debate. Too few (1-2) = groupthink risk. Too many (>6) = diminishing returns + increased cost.

### 5.3 Sample Persona Pool

- **Technical Architect**: Systems thinking, scalability, technical debt
- **Financial Analyst**: ROI, cost-benefit, financial risk
- **User Advocate**: Customer needs, usability, adoption
- **Risk Manager**: Downside scenarios, mitigation, contingency
- **Growth Strategist**: Market opportunity, competitive advantage
- **Operations Expert**: Feasibility, execution, resource constraints
- **Behavioral Psychologist**: Human factors, motivation, change management
- **Data Scientist**: Evidence-based, metrics, measurement

---

## 6. Console Interface Design

### 6.1 Interaction Model

**Text-based, progressive disclosure:**

```
> Welcome to Board of One

> What problem or decision would you like help with?
[User input]

> Thank you. I have a few clarifying questions:
> 1. [Question]
[User answer]

> Based on our discussion, here's how I understand your problem:
> [Problem statement]
> Is this accurate? (yes/edit)

> I've broken this into 4 sub-problems:
> 1. [Sub-problem 1] (foundational)
> 2. [Sub-problem 2] (depends on #1)
> 3. [Sub-problem 3] (parallel to #2)
> 4. [Sub-problem 4] (synthesis)
> Continue? (yes/modify)

> I've assembled a board of 4 experts:
> 1. [Expert name, title, perspective]
> 2. [Expert name, title, perspective]
> 3. [Expert name, title, perspective]
> 4. [Expert name, title, perspective]
> Ready to begin? (yes/modify/view-profiles)

> === SUB-PROBLEM 1: [Title] ===
>
> [FACILITATOR]: Let's discuss [sub-problem]. I'll ask each expert for their opening thoughts.
>
> [EXPERT 1 NAME]: [Opening statement]
>
> [EXPERT 2 NAME]: [Opening statement]
> ...
>
> Continue to debate? (yes/skip-to-vote)
```

### 6.2 Display Conventions

- **Clear Speaker Labels**: [FACILITATOR], [EXPERT NAME]
- **Section Breaks**: === SECTION === for major transitions
- **Progress Indicators**: "Sub-problem 2 of 4"
- **User Choice Points**: Explicit (yes/no/modify) prompts
- **Collapsible Detail**: Option to see full debate or summary
- **Color Coding** (if terminal supports):
  - Facilitator: Blue
  - Experts: Yellow/Green
  - User prompts: White
  - Warnings/caveats: Red

### 6.3 Pacing Controls

- **Skip Options**: Skip to vote, skip to final recommendation
- **Pause/Resume**: OUT OF SCOPE for v1
  - v1: Sessions must complete in single sitting (5-15 min typical)
  - v2: Add pause/resume with state serialization
- **Verbosity Levels**:
  - Concise: Key points only
  - Standard: Full debate (default)
  - Detailed: Include expert reasoning, facilitator notes

---

## 7. Debate Mechanics

### 7.1 Debate Structure (Per Sub-Problem)

**Round 1: Opening Positions (2-3 min)**

- Each expert states position in 100-150 words
- Focus: What they believe, why

**Round 2: Challenge & Response (3-4 min)**

- Experts respond to others' points
- Facilitator highlights key disagreements
- Focus: Where do perspectives differ?

**Round 3: Convergence (2-3 min)**

- Experts refine positions based on discussion
- Identify areas of consensus
- Focus: What can we agree on? What remains contentious?

### 7.2 Facilitator Interventions

- **Redirect**: If discussion goes off-topic
- **Challenge**: If groupthink emerges
- **Clarify**: If positions are unclear
- **Summarize**: At end of each round
- **Balance**: Ensure quieter experts speak

### 7.3 Quality Controls

- **No Repetition**: Experts don't repeat points already made
- **Substantive Engagement**: Must respond to others' arguments
- **Evidence-Based**: Claims should reference reasoning/data
- **No Personal Attacks**: Focus on ideas, not personas

---

## 8. Voting & Decision Making

### 8.1 Option Formulation

After debate, facilitator distills 2-4 distinct options:

- **Option A**: [Clear description]
  - Pros: [2-3 key advantages]
  - Cons: [2-3 key disadvantages]
  - Best if: [Conditions where this is optimal]

### 8.2 Voting Process

Each expert casts vote:

```
[EXPERT NAME] votes for: Option B
Rationale: [50-100 word explanation]
Confidence: Medium/High/Low
```

### 8.3 Synthesis Logic

Facilitator considers:

1. **Vote Distribution**: Which option(s) received most support?
2. **Argument Strength**: Were some rationales more compelling?
3. **Confidence Levels**: How certain were the experts?
4. **Risk Factors**: What could go wrong with each option?
5. **User Context**: Refers back to original problem framing

**Output**: Recommended option with clear explanation of why

---

## 9. Success Metrics

### 9.1 Quality Indicators

- **Recommendation Clarity**: User understands what to do next
- **Perspective Diversity**: Multiple viewpoints represented in debate
- **Decision Confidence**: User feels more confident in their choice
- **Trade-off Visibility**: User understands what they're giving up
- **Actionability**: Recommendation includes concrete next steps

### 9.2 User Satisfaction

- Would user use Board of One again?
- Did recommendation differ from user's initial intuition?
- Did user learn something new from the debate?
- Time to useful recommendation (target: 5-15 min)

### 9.3 System Performance

- **Decomposition Quality**: Are sub-problems well-scoped?
- **Expert Relevance**: Were the right personas selected?
- **Debate Substance**: Did experts engage meaningfully or superficially?
- **Consensus Achievement**: Did voting produce clear winner or stalemate?

---

## 10. Out of Scope (v1)

**Explicitly NOT included in initial version:**

- Visual UI / web interface
- User accounts or persistence
- Real-time expert persona customization
- Integration with external data sources
- Learning from previous sessions
- Expert persona memory across sessions
- File upload/attachment support
- Voice interface
- Mobile app

---

## 11. Technical Considerations (High-Level)

### 11.1 Core Components

1. **Problem Analyzer**: Decomposes problems, identifies dependencies
2. **Persona Engine**: Selects and embodies expert personas
3. **Debate Orchestrator**: Manages conversation flow, ensures quality
4. **Facilitator Agent**: Guides discussion, synthesizes
5. **Vote Processor**: Tabulates and interprets votes
6. **Recommendation Generator**: Final synthesis

### 11.2 Data Structures

- **Problem**: Original text, clarifications, final statement
- **Sub-Problems**: List with dependencies, success criteria
- **Expert Roster**: Personas with attributes
- **Debate Transcript**: Structured log of all statements
- **Votes**: Expert, option, rationale, confidence
- **Recommendation**: Final output with reasoning

### 11.3 Session Management

- Each session is self-contained
- Session can be paused and resumed
- Transcript can be exported as markdown
- No persistent storage across sessions (v1)

---

## 12. Example Session Flow

```
> Welcome to Board of One (bo1)
> I'll help you solve complex problems through expert debate and synthesis.

> What problem or decision would you like help with?
> Should I rewrite my application in Rust or stick with Python?

> Thanks. A few clarifying questions:
> 1. What's your current pain point with Python?
> Performance is becoming an issue as we scale

> 2. How large is your team and what's their experience?
> 3 developers, all strong in Python, none know Rust

> 3. What's your timeline for this decision?
> Need to decide in next 2 months

> Based on our discussion, here's your problem:
> "Decide whether to rewrite a scaling Python application in Rust,
>  considering performance needs, team capabilities, and a 2-month timeline."
>
> Continue? (yes/edit)
> yes

> I've broken this into 4 sub-problems:
> 1. Performance Analysis (foundational)
>    - How much performance gain would Rust provide?
>    - Are there Python optimization alternatives?
>
> 2. Team Capability Assessment (parallel to #1)
>    - What's the learning curve for Rust?
>    - Cost of reduced productivity during transition?
>
> 3. Migration Strategy (depends on #1 and #2)
>    - Full rewrite vs. gradual migration?
>    - Which components to prioritize?
>
> 4. Risk Evaluation (depends on #3)
>    - What could go wrong?
>    - Mitigation strategies?
>
> Continue? (yes/modify)
> yes

> I've assembled a board of 4 experts:
>
> 1. Dr. Maya Patel - Performance Engineering Lead
>    Conservative, data-driven, focuses on measurable improvements
>
> 2. Alex Chen - Engineering Manager
>    Pragmatic, team-focused, balances technical and human factors
>
> 3. Jordan Kim - Systems Architect
>    Optimistic about new tech, long-term thinking, modernization advocate
>
> 4. Sam Rodriguez - Risk & Operations
>    Cautious, execution-focused, highlights practical constraints
>
> Ready to begin? (yes/modify/view-profiles)
> yes

> === SUB-PROBLEM 1 of 4: Performance Analysis ===
>
> [FACILITATOR]: Let's start with the core question: How much performance
> improvement would Rust realistically provide, and are there alternatives?
> Each expert, please share your opening thoughts.
>
> [DR. MAYA PATEL]: Before considering Rust, we need hard data. I'd want to
> profile the Python application to identify actual bottlenecks. Often, 90%
> of performance issues come from 10% of the code - database queries,
> inefficient algorithms, or poor caching. We might achieve significant gains
> by optimizing Python code, adding PyPy JIT compilation, or rewriting just
> the hot paths in Cython or even Rust through FFI, without a full rewrite.
>
> [ALEX CHEN]: Maya makes a great point about profiling, but I want to add
> the human factor. Even if Rust could give us 10x performance, if it takes
> 6 months to rewrite and our team is unproductive during that time, we've
> lost significant value. We should also consider: what performance do we
> actually NEED? Sometimes "good enough and maintainable" beats "theoretically
> optimal but complex."
>
> [JORDAN KIM]: I see this differently. This isn't just about solving today's
> performance problem - it's about positioning for the next 5 years. Rust
> offers memory safety, fearless concurrency, and performance. Yes, there's
> a learning curve, but investing in Rust skills now could pay dividends
> across multiple projects. The question isn't "can we optimize Python" but
> "what's our long-term technical foundation?"
>
> [SAM RODRIGUEZ]: I'm concerned about the 2-month timeline. That's extremely
> tight for a language migration. We need to be realistic: learning Rust,
> rewriting code, testing, and deploying is easily a 6-12 month effort for
> a team new to the language. If performance is truly urgent, we need faster
> solutions - vertical scaling, caching, database optimization, or hybrid
> approaches like Maya suggested.
>
> Continue to Round 2? (yes/skip-to-vote)
> yes

[... debate continues through rounds 2 and 3 ...]

> [FACILITATOR]: Based on our discussion, I see 3 distinct options:
>
> Option A: Optimize Python First
> - Profile and fix bottlenecks in current codebase
> - Add caching, database optimization
> - Potentially use PyPy or Cython for hot paths
> Pros: Fast, low risk, team stays productive
> Cons: May hit Python's performance ceiling eventually
> Best if: Performance needs are modest, timeline is tight
>
> Option B: Hybrid Approach (Python + Rust FFI)
> - Keep Python for most code
> - Rewrite critical paths in Rust, call via FFI
> - Gradual team learning
> Pros: Performance gains where needed, lower risk than full rewrite
> Cons: Added complexity, FFI overhead, two languages to maintain
> Best if: Specific bottlenecks identified, team wants to learn Rust
>
> Option C: Full Rust Rewrite
> - Complete migration to Rust
> - Modern foundation for future
> Pros: Maximum performance, memory safety, long-term benefits
> Cons: High cost, long timeline, productivity hit
> Best if: Timeline is flexible, performance is critical, strategic investment
>
> Experts, please vote:

[... voting occurs ...]

> === RECOMMENDATION: Sub-Problem 1 ===
>
> I recommend Option A (Optimize Python First) with Option B (Hybrid) as
> a follow-up if needed. Here's why:
>
> Your 2-month timeline is incompatible with a Rust migration. Three experts
> (Maya, Alex, Sam) agreed that profiling and optimizing Python first is
> the pragmatic choice. This buys you time to:
> 1. Get immediate performance improvements
> 2. Measure actual vs. theoretical bottlenecks
> 3. Evaluate if Python optimization is sufficient
> 4. If not, identify specific components for Rust rewriting
>
> Jordan's long-term perspective is valid, but given constraints, a phased
> approach is lower risk.
>
> Confidence: High
>
> Continue to Sub-Problem 2? (yes/pause/skip-to-final)

[... process continues for remaining sub-problems ...]

> === FINAL RECOMMENDATION ===
>
> After debating 4 sub-problems with your expert board, here's the synthesis:
>
> RECOMMENDATION: Optimize Python now, evaluate Rust in 6 months
>
> SEQUENTIAL STEPS:
> 1. [Weeks 1-2] Profile application, identify top 5 bottlenecks
> 2. [Weeks 3-4] Implement Python optimizations (caching, DB queries, algorithms)
> 3. [Weeks 5-6] Measure results, determine if sufficient
> 4. [Weeks 7-8] If insufficient, pilot Rust FFI for #1 bottleneck
> 5. [Month 6] Evaluate: Continue Python, Hybrid, or plan full migration
>
> KEY TRADE-OFFS:
> ✓ Lower risk, faster results
> ✓ Team stays productive
> ✓ Data-driven decision making
> ✗ May not achieve maximum theoretical performance
> ✗ Defers long-term language decision
>
> CONFIDENCE: High
>
> This recommendation balances your immediate timeline constraints with
> long-term flexibility. You're not ruling out Rust, but you're not betting
> the farm on it without data.
>
> Would you like the full transcript? (yes/no)
```

---

## 13. Future Enhancements (Post-v1)

### Phase 2

- Web interface
- Persistent sessions and history
- Export recommendations to various formats

### Phase 3

- Custom expert personas (user-defined)
- Expert learning from feedback
- Problem templates for common scenarios
- Integration with task managers

### Phase 4

- Expert marketplace (community-created personas)

---

## 14. Design Decisions

### 14.1 LLM Architecture: Multiple Instances

**Decision**: Use separate LLM instances for each persona, facilitator, and researcher.

**Rationale**:
- Better role separation and consistency
- Higher parallel processing capability
- More authentic debate dynamics
- Aligns with research best practices (MetaGPT, AutoGen)

**Trade-offs**:
- Slightly higher cost vs. single instance
- Better quality and performance justify cost

### 14.2 Debate Length: Progress Indicators

**Decision**: Show real-time progress metrics to manage user expectations.

**Implementation**:
- Display progress toward max iterations: "Round 5/15 (33%)"
- Show convergence metrics in real-time
- Stream quality indicators (novelty score, conflict level)
- Let adaptive stopping work naturally

**Rationale**:
- Users tolerate longer debates when they see progress
- Transparency builds trust in the process
- Early stop becomes visible feature, not hidden behavior

### 14.3 Vote Ties: Present Honestly

**Decision**: When experts are evenly split, present findings as-is with pros/cons for each option.

**Implementation**:
- Synthesis acknowledges split: "The board was evenly split (3-3)"
- Include all dissenting opinions in final recommendation
- Use confidence scores as tiebreaker when appropriate
- Present trade-offs clearly for user to make final call

**Rationale**:
- Honest representation better than forced consensus
- User sovereignty means user makes final decision anyway
- Split votes often indicate genuine trade-offs worth preserving

### 14.4 Sub-Problem Limits: Adaptive Decomposition

**Decision**: ALWAYS decompose into at least 1 sub-problem. Handle complexity through recursive decomposition.

**Implementation**:

```
EVERY problem is decomposed into sub-problems (minimum 1, maximum 5):

If problem is simple/atomic (1 sub-problem):
  → Decompose into single sub-problem (same as original)
  → Use standard deliberation flow
  → Example: "Should I name my startup FooBar or BarFoo?"
    → Sub-problem 1: "Choose optimal name between FooBar and BarFoo"

If problem yields 2-5 sub-problems:
  → Standard flow (optimal range)
  → This is the most common case

If problem yields >5 sub-problems:
  → Group related sub-problems into 3-5 "meta-problems"
  → Each meta-problem can be further decomposed recursively
  → Sequential: Solve meta-problem 1, then decompose if needed
  → Example: "Product Strategy" meta-problem → 3 sub-problems in next level
```

**Rationale**:
- **Single unified flow**: No special cases, no branching logic
- **Simpler architecture**: Same deliberation process for all problems
- **Consistent user experience**: Always see decomposition step
- **Prevents cognitive overload**: Top level capped at 5 sub-problems
- **Recursive approach**: Handles arbitrary complexity via meta-problems
- **Aligns with research**: Optimal decision decomposition patterns

### 14.5 User Intervention: Round Checkpoints

**Decision**: User can intervene at end of each round via checkpoint prompts.

**Round Definition:**

A "round" is a complete cycle where:
1. Facilitator frames the current state of discussion
2. Each expert who has something material to contribute speaks once
3. Facilitator summarizes key points and disagreements

**Round structure:**
- Round 1 (Opening): All experts speak (required)
- Round 2+: Only experts with new material speak (opt-in)
- Round ends when: Facilitator determines no expert has new material, OR all active experts have spoken

**User intervention checkpoint:**
- Occurs at END of each round (after facilitator summary)
- User sees: "Round 3 complete. Continue? (yes/skip-to-vote/intervene)"
- If user selects "intervene", their input becomes part of Round 4 context

**Console Implementation Example:**

```
Round 1:
  - Facilitator: Frames sub-problem
  - Expert A: Opening statement (100 words)
  - Expert B: Opening statement (100 words)
  - Expert C: Opening statement (100 words)
  - Facilitator: Summary of key disagreements
  → User checkpoint: Continue? (yes/skip-to-vote/intervene)

Round 2 (if continue):
  - Facilitator: "Expert B raised concern about X. Expert C suggested Y. Let's explore."
  - Expert B: Responds to Expert C (80 words)
  - Expert A: Adds new perspective (80 words)
  - Expert C: (Opts to skip - nothing new to add)
  - Facilitator: Summary
  → User checkpoint: Continue? (yes/skip-to-vote/intervene)

Round 3 (if intervene):
  - User: "What about option Z that you haven't considered?"
  - Facilitator: "The user raises an interesting point about option Z. Experts, please respond."
  - Expert A: Responds to user's suggestion
  - Expert B: Responds to user's suggestion
  - Expert C: Responds to user's suggestion
  - Facilitator: Summary incorporating user input
  → User checkpoint: Continue?
```

**Note:** This differs from "iteration" in code, which may count individual expert statements.
A "round" from user perspective = complete discussion cycle.

**Rationale**:
- Balances user control with debate flow
- Prevents interrupting mid-argument
- Natural checkpoints already exist (end of round)
- Simpler implementation than real-time intervention
- User can course-correct if debate drifts

**Future Enhancement**: Real-time intervention during debate (post-v1)

### 14.6 Quality Thresholds: Research-Based Mitigation

**Decision**: Quality is ensured through comprehensive monitoring rather than simple thresholds.

**Implementation** (covered in section 4.5):
- Problem drift detection (relevance scoring 0-10, flag <6)
- Novelty tracking (semantic similarity, flag <0.3 late in debate)
- Facilitator interventions (contrarian, skeptic, optimist)
- Cognitive overload prevention (max 15 rounds)
- Deadlock detection (conflict score >0.8 for 5+ rounds)

**Rationale**:
- No single metric captures "quality"
- Multi-dimensional monitoring more effective
- Research-backed thresholds (see CONSENSUS_BUILDING_RESEARCH.md)
- Adaptive system responds to quality issues dynamically

### 14.7 Recommendation Disclaimers: Deferred to UI Phase

**Decision**: No legal disclaimers for console v1 (personal use only).

**v1 (Console)**:
- Advisory language in all recommendations ("We recommend...")
- User sovereignty maintained (never directive)
- No legal disclaimers needed (single user, non-commercial)

**Future (Public UI)**:
- Standard disclaimers for financial, legal, medical advice
- Terms of service acknowledgment
- Professional consultation recommendations for one-way doors
- Liability waivers appropriate for advisory service

**Rationale**:
- Console version is personal tool for solo use
- Adding disclaimers to UI is straightforward later
- Focus v1 development on core functionality

### 14.8 Decomposition Edge Cases

**Additional Design Decision**: Handle problems that resist clean decomposition while maintaining single unified flow.

**Scenarios**:

1. **Already Atomic Problem**: "Should I name my startup FooBar or BarFoo?"
   - Action: Create single sub-problem (same as original problem)
   - Sub-problem: "Choose optimal name between FooBar and BarFoo"
   - Use standard deliberation flow (no special handling)

2. **Inherently Sequential Problem**: "How do I build and launch my product?"
   - Action: Decompose into sequential steps (Build → Test → Launch → Market)
   - Each step becomes sub-problem with dependencies
   - Standard flow with dependency order

3. **Highly Interconnected Problem**: Sub-problems have circular dependencies
   - Action: Identify "breaking points" to linearize
   - Example: Market research → Product design → Pricing (circular)
   - Break: Start with market research, revisit pricing after design
   - Use dependency metadata to guide order

4. **Problem Too Vague**: "How do I succeed?"
   - Action: Clarification questions to narrow scope
   - If still too vague after clarification, create single high-level sub-problem
   - Let expert debate surface the vagueness as issue
   - Recommendation may be "refine problem statement first"

5. **Overly Complex Problem**: Natural decomposition yields >5 sub-problems
   - Action: Group into 3-5 meta-problems at top level
   - Example: "Launch SaaS business" might yield 12 sub-problems
   - Group into: "Market validation" + "Product development" + "Go-to-market" + "Operations"
   - Each meta-problem can be recursively decomposed in follow-up sessions

**Rationale**: Single unified flow (always 1-5 sub-problems) simplifies architecture while handling all edge cases gracefully.

---

## 15. Implementation Notes

### 15.1 Console-Specific Constraints

**Target User**: Solo founder/developer (initial version for personal use)

**Interface Requirements**:
- Text-only, no graphics
- Progress indicators via text ("Round 3/10 - 30% complete")
- Intervention via prompts at checkpoints
- Export transcript as markdown

**Expert Count and Debate Rounds (v1 Defaults):**

**v1 console uses fixed configuration (no tiers):**

- **Expert Count**: 3-5 experts (adaptive based on problem domain)
  - Simple problems: 3 experts minimum
  - Complex problems: 5 experts maximum
  - System selects count based on domain diversity needed

- **Max Debate Rounds**: Complexity-based (research-backed)
  - Simple (complexity 1-3): 5 rounds max
  - Moderate (complexity 4-6): 7 rounds max
  - Complex (complexity 7-10): 10 rounds max
  - Hard cap: 15 rounds (cognitive overload prevention)

**Future (v2+):** Introduce tiered packages with different limits

**Quality Bar**:
- Time to recommendation: 5-15 minutes (target)
- Recommendations must be actionable and specific
- Trade-offs must be clearly surfaced
- User should learn something new from debate

### 15.2 Key Technical Decisions

**LLM Strategy**:
- Multiple instances (one per persona + facilitator + researcher)
- Parallel execution where possible (opening statements, votes)
- Sequential where required (debate rounds, synthesis)

**State Management**:

**v1 (In-Memory Only):**
- Session state in memory (no persistence)
- Session must complete in single sitting (5-15 min typical)
- Export capability: Save transcript as markdown after completion
- No resume capability (if user quits, session lost)

**v2 Enhancement:**
- Add pause/resume with state serialization (JSON/DB)
- Save partial progress
- Resume from any checkpoint
- Session history across multiple sittings

**Cost Optimization**:
- Use Haiku for parallel persona calls
- Use Sonnet for complex synthesis
- Target: $0.05-0.15 per sub-problem
- Overall session cost: <$1 for typical 3-5 sub-problem session

**Cost Estimates (based on Anthropic Claude pricing as of January 2025):**

**Pricing assumptions:**
- Haiku: $0.25 per million input tokens, $1.25 per million output tokens
- Sonnet: $3 per million input tokens, $15 per million output tokens

**Per sub-problem estimate: $0.05-0.15**

**Breakdown:**
- Expert personas (parallel): 5 experts × 7 rounds × ~500 tokens avg = ~17,500 input, ~3,500 output
  - Using Haiku: ~$0.009 per sub-problem
- Facilitator (sequential): ~10 calls × ~1,000 tokens avg = ~10,000 input, ~2,000 output
  - Using Sonnet: ~$0.06 per sub-problem
- Researcher (optional): 1-2 calls × ~1,500 tokens = ~$0.01 per sub-problem
- **Total: ~$0.08 per sub-problem (mid-range estimate)**

**Full session cost: <$1 for typical 3-5 sub-problem session**
- 3 sub-problems: ~$0.24
- 5 sub-problems: ~$0.40

**Note:** Actual costs vary based on debate length (early stopping reduces cost 20-40%), expert count, research requests, and problem complexity

### 15.3 Success Criteria

**v1 Console Release**:
- [ ] Successfully decomposes 90% of test problems
- [ ] Generates actionable recommendations with clear rationale
- [ ] Completes typical session in 5-15 minutes
- [ ] Surfaces trade-offs in 100% of recommendations
- [ ] Adaptive stopping works (30-40% of deliberations stop early)
- [ ] User intervention mechanism works at checkpoints
- [ ] Handles edge cases (too simple/complex) gracefully

**Quality Benchmarks** (based on research):
- Consensus level: >70% for clear decisions
- Average confidence: >0.7 for final votes
- Problem drift: <10% of deliberations
- Early stop rate: 30-40% (indicates adaptive stopping working)

---

**Document Version**: 1.0
**Last Updated**: 2025-01-11
**Status**: Design Complete - Ready for Implementation
