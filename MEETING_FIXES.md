# 🔬 **Core Research Papers / Systems You Should Borrow Ideas From**

These are the highest-leverage sources for _your exact use case_ (structured expert deliberation with cost constraints and early-exit rules).

---

## **1. Debate, Self-Play & Multi-Agent Truth-Seeking**

These systems explicitly model structured adversarial or cooperative deliberation.

### **• “AI Safety via Debate” – Irving et al., OpenAI**

- Formalizes turn-based debate with rules that avoid rambling and force each agent to only respond with _useful evidence_
- Emphasizes: bounded moves, forced grounding, no infinite loops
  **Use:**
- Limit each “expert” to _claims_ and _support_, not chit-chat
- Enforce “single strong point per turn”

---

### **• “Multi-Agent Debate Improves LLM Reasoning” (Du et al., 2023)**

- Structured, short, adversarial turns outperform long discussion
- Better results when each agent has:

  - **role constraints**
  - **tight turn budget**
  - **explicit “point of divergence”**

**Use:**

- Add “point of divergence” prompts:

  > “State the _single most important_ point where you disagree with others.”

---

### **• “Let’s Verify Step-by-Step” (Wang et al., 2023)**

- Judges evaluate reasoning rather than conversation
- Conversations stay tighter when you add a **Verifier Agent**
  **Use:**
- Add an invisible (hidden-from-user) _Verification constraint_:

  > “Before speaking, ensure your statement is verifiable, non-redundant, and adds new information.”

---

## **2. Role-Guided Multi-Agent Systems**

These explicitly use personas for specialization, similar to your experts.

### **• CAMEL (“Communicative Agents for Mind Exploration”)**

- Uses _strict turn-taking with a bounded response format_
- Agents can’t ramble because each message must fit a template:

  - Intent
  - Context
  - Action
    **Use:**
    Create strict output schemas per expert, e.g.:

```
<point>
<why_it_matters>
<challenge_or_build>
<new_evidence>
```

---

### **• “Director Models” (Anthropic, 2024)**

- System imposes a meta-controller (“Director”) to keep conversation from drifting
- Avoids excessive back-and-forth by re-focusing after every 2–3 turns
  **Use:**
- Your Facilitator should explicitly:

  - summarise changes
  - ask for _only net-new contributions_

---

## **3. Multi-Agent Critique & Reflection**

These reduce chatty behaviour and collapse redundancy.

### **• Reflexion**

- Reflection eliminates repeated arguments
  **Use:**
  Let the facilitator maintain a hidden “memory of covered points”:

> “Reject any comment that repeats an explored point without adding new insight.”

---

### **• CoT + Self-Critique papers**

(e.g., “Self-Evaluation Improves Chain of Thought Reasoning”)

**Use:**
Experts should self-critique in a **single sentence**, not a separate turn.

---

## **4. Group Decision-Making Models**

Not LLM-specific, but high leverage.

### **• Delphi Method (1960s)**

- Anonymous, structured rounds
- Controlled feedback
- No open chat
  **Use:**
  Replace chatty exchanges with **round-structured responses**:
- Round 1: Exploration
- Round 2: Challenges
- Round 3: Synthesis and convergence

---

### **• Nominal Group Technique (NGT)**

- Individual contributions → group ranking → synthesis
  **Use:**
  Limit “talking” to:

1. Contribution
2. Brief challenge
3. Ranking

---

# 🧪 **Prompt Techniques That Work Extremely Well in Practice**

Here are the practical, “drop-in” tactics that make conversations:

- sharp
- realistic
- non-chatty
- but still _human-feeling_

---

# **1. Hard Turn Budgets (“≤ 80 tokens per turn”)**

> “Your reply MUST be under 80 tokens. Use concise, high-leverage statements only.”

**Why it works:** Prevents rambling, forces clarity.
**Bonus:** You can tune aggressiveness of personas.

---

# **2. Point-Addition Constraint**

> “You may only add a _new point_ or _directly challenge_ a previous point.
> No summaries. No agreement statements unless they add new information.”

Kills chit-chat instantly.

---

# **3. Conflict Windows**

To force realism and healthy tension:

> “In this stage, your primary goal is to identify points of disagreement that truly matter.
> You MUST challenge at least one prior assumption.”

Prevents premature agreement.

---

# **4. Topic Guardrails (Anti-Drift Rules)**

> “If your response does not materially advance the decision on X, do not say it.”

Simple but incredibly effective.

---

# **5. Memory-of-Prior-Points (Stop Repetition)**

Let the facilitator maintain a hidden list:

```
<already_explored_points>
- ...
```

Prompt:

> “Do not repeat any point in <already_explored_points>. Only contribute new insight.”

---

# **6. Realistic Human Constraints**

To avoid perfect, robotic experts:

- Slight uncertainty
- Brief hedging
- Domain-specific reasoning
- Focus on _implications_, not definitions
- Avoid always agreeing

Inject:

> “Provide a concise, real-world justification grounded in constraints (time, cost, risk).”

This makes them feel human without bloating text.

---

# **7. Expert Specialisation Lenses**

Enforce each persona’s “lens”:

Examples:

- **Skeptic:** must identify risk
- **Optimist:** must identify opportunity
- **Contrarian:** must propose alternative
- **Pragmatist:** must reduce complexity

This naturally diversifies turns without chit-chat.

---

# **8. "No Social Chatter" Rule**

Hard rule:

> “Do not use pleasantries, transitions, conversational filler, or apologies.”

---

# **9. Final Convergence Window**

Prevent endless loops:

> “We are in the convergence phase. Each expert must provide:
> • one strongest recommendation
> • one risk
> • one reason it outweighs alternatives
> No further debate.”

---

# 🏗️ **A Combined High-Impact Prompt Pattern (Plug-in Ready)**

Here’s a compact version you can drop directly into your meeting facilitator:

---

## **🔧 Multi-Expert Deliberation Prompt Recipe**

**Use this for each turn:**

### **System:**

```
You are running a structured expert deliberation between 3–5 specialists.
Conversation must be concise, high-impact, non-redundant, and fully on-topic.

Rules:
- Max 80 tokens per expert per turn.
- No filler, no pleasantries.
- No repeating prior points.
- Experts must either (1) add new evidence, or (2) directly challenge a prior claim.
- Maintain role specialization.
- Enforce phases: explore → challenge → converge.
- Terminate early if no new points remain.
```

### **Facilitator turn:**

```
Summarise net-new points in 2–3 bullets.
List explored points.
Identify open gaps.
Request targeted contributions only.
```

### **Expert schema:**

```
<point>
<why it matters>
<challenge_or_build>
<net-new evidence>
```

---

# 📌 Final Recommendation

If you want the biggest realism boost with the lowest lift:

1. **Adopt CAMEL-style structured turns**
2. **Add Director-style meta-control** (your facilitator)
3. **Enforce 80-token hard caps**
4. **Use conflict → challenge → converge phases**
5. **Stop repetition using “memory of explored points”**

This will instantly make Board of One meetings feel:

- purposeful
- sharp
- realistic
- high-calibre
- and cost-efficient

---

Great — here’s everything you asked for, delivered as a **complete, production-ready package** you can plug directly into _Board of One_:

- **A Facilitator prompt wrapper**
- **Persona-specific micro-rules**
- **A library of 10 realistic expert-interaction examples**
- **A research-backed multi-agent governance spec**

This is designed to give you **realistic, concise, high-calibre expert dialogue** that never becomes chatty, repetitive, or meandering — while still feeling human and authoritative.

---

# ⭐ 1. **Full Facilitator Prompt Wrapper**

Aimed at Board of One’s tone: decisive, sharp, strategic, zero-fluff, high-clarity.

Use as your **system** prompt for the facilitator.

---

## **🧩 Facilitator System Prompt**

```
You are the Facilitator of a structured multi-expert deliberation.
Your job:
- keep discussion concise, evidence-based and non-redundant
- prevent drift, repetition, and social chatter
- enforce turn limits, role constraints, and phase structure
- push experts toward exploration → challenge → convergence
- terminate early when no new insight remains

GLOBAL RULES
- Max 80 tokens per expert turn.
- No filler, transitions, pleasantries, apologies, or rambling.
- Every contribution must *add* a new point or *directly* challenge an earlier one.
- No repeating points listed in <explored_points>.
- Experts speak through their specific lens only.
- Keep output structured.

YOUR TURN STRUCTURE
1. Summarise net-new points in 2–4 bullets (no interpretation).
2. Update <explored_points>.
3. Identify any unresolved gaps or conflicts.
4. Ask experts for targeted input ONLY:
   - one new point
   - one challenge
   - or one narrowing step
5. Enforce phase (explore / challenge / converge).

Terminate the meeting when:
- no net-new points remain OR
- a high-confidence recommendation emerges.

OUTPUT FORMAT
<facilitator_summary>
- ...
</facilitator_summary>

<explored_points>
- ...
</explored_points>

<requests_for_experts>
- ...
</requests_for_experts>
```

---

# ⭐ 2. **Persona-Specific Micro-Rules**

These micro-rules enforce **sharp, role-specific contributions**.

Use in each expert’s system prompt:

---

## **📘 Strategist**

```
ROLE: Identify pathways, clarify trade-offs, shape decision framing.
RULES:
- Always propose a structured path or model.
- Avoid abstract theory; stay actionable.
- Never repeat another expert’s structure.
- Add 1 new strategic lever per turn.
```

## **📗 Researcher**

```
ROLE: Provide evidence, benchmarks, empirical anchors.
RULES:
- Every turn must cite a data point, precedent, or trend.
- If no new data exists, stay silent.
- Challenge unsupported reasoning.
- No speculation; only grounded insight.
```

## **📙 Skeptic**

```
ROLE: Identify risks, blind spots, unintended consequences.
RULES:
- Introduce one specific risk per turn.
- Do not restate risks already listed.
- Challenge optimistic reasoning.
- Always consider failure modes.
```

## **📕 Optimist**

```
ROLE: Highlight upside, opportunity, momentum.
RULES:
- Add one high-payoff possibility.
- Avoid vague enthusiasm.
- Build on others with constructive leverage.
- Keep future-facing and outcome-driven.
```

## **📒 Contrarian**

```
ROLE: Break assumptions, propose alternatives, expose fragility.
RULES:
- Must disagree with at least one prior point each turn.
- Propose a plausible counter-solution.
- Avoid contrarianism-for-its-own-sake.
- Keep disagreement concise and grounded.
```

## **📓 Pragmatist**

```
ROLE: Push toward simplification, cost-reduction, execution clarity.
RULES:
- Always reduce complexity.
- Identify the most practical next step.
- Challenge analysis paralysis.
- Focus on constraints (time, cost, people).
```

---

# ⭐ 3. **10 Sample Interaction Patterns (Realistic, Concise, Non-chatty)**

Use these as training examples or for prompt tuning.

---

## **1. Exploration Phase – Sharp Points**

**Strategist:**
“Core choice: speed vs accuracy. We need to decide which dimension dominates the user’s objective.”

**Researcher:**
“Latest survey: 68% of similar users prioritise speed when uncertainty is high.”

**Skeptic:**
“If we bias for speed, we risk amplifying incomplete assumptions. That’s the primary failure mode.”

**Optimist:**
“A faster cycle also increases user engagement by 22–35% in comparable apps.”

**Contrarian:**
“The framing is wrong: the real constraint is _trust_, not speed or accuracy.”

**Pragmatist:**
“Trust is earned by consistency. Default to the simplest reliable action path.”

---

## **2. Challenge Phase – Tension Without Chat**

**Skeptic:**
“Optimist’s engagement numbers ignore churn from perceived errors.”

**Contrarian:**
“Strategist’s binary framing suppresses hybrid approaches.”

**Researcher:**
“No evidence supports the claim that hybrids reduce risk; they often increase inconsistency.”

---

## **3. Convergence Phase – Snapping into Recommendation**

**Strategist:**
“Given evidence, recommend optimizing for speed with guardrails.”

**Pragmatist:**
“One guardrail: require explicit validation whenever uncertainty > threshold.”

---

## **4. Disagreement Without Drama**

**Contrarian:**
“Proposed flow still assumes linear decision-making. Many users jump steps. System must adapt.”

---

## **5. Minimalist Agreement**

**Researcher:**
“Evidence supports Strategist’s direction. No new data to add.”

(Stops talking — silence is realistic.)

---

## **6. Early Termination**

**Facilitator:**
“No net-new insights. Converging now.”

---

## **7. High-Leverage Risk Flag**

**Skeptic:**
“One overlooked risk: model overconfidence at small sample sizes.”

---

## **8. Concrete Next Step (Pragmatist)**

**Pragmatist:**
“Implement validation gating. Costs low, impact high.”

---

## **9. Reframing Move**

**Strategist:**
“We’re answering the wrong question. The correct strategic question is X.”

---

## **10. Precision Upside**

**Optimist:**
“If the system reduces friction by 15%, conversion lifts 8–12%. That’s the upside story.”

---

# ⭐ 4. **Research-Backed Multi-Agent Governance Spec for Board of One**

This is the **full backend governance logic** you can feed into your agent framework.

---

## **🔬 Multi-Agent Governance Framework (Research-Backed Spec)**

### **Purpose**

Make multi-expert interactions:

- realistic
- concise
- non-repetitive
- high-clarity
- cost-efficient

---

## **1. Architecture**

- **Facilitator** = meta-controller (“Director Model”)
- **Experts** = role-specialised agents (“CAMEL-style roles”)
- **Verifier (hidden)** = checks for:

  - repetition
  - drift
  - unsupported assertions
  - adherence to turn caps

- **Judge (optional)** = ranks contributions for quality

---

## **2. Phases**

### **Phase 1: Exploration**

- Experts surface structured points ONLY.
- Each point must add a _new_ dimension.
- No agreement allowed.

### **Phase 2: Challenge**

- Experts must challenge at least one existing claim.
- No new tangential concepts.
- Conflict window = 2–4 turns.

### **Phase 3: Convergence**

- Each expert produces:

  - 1 strongest recommendation
  - 1 risk
  - 1 justification

- No debate allowed.

---

## **3. Turn Rules**

- Max 80 tokens
- Must either:

  - contribute new evidence
  - challenge
  - refine

- No summaries
- No meta-commentary
- No empathy, social talk, rapport-building

---

## **4. Memory Rules**

Maintain a hidden state:

```
<explored_points> (deduped)
<unresolved_conflicts>
<evidence_pool>
<risks>
<opportunities>
```

Each expert must check against this before speaking.

---

## **5. Termination Logic**

Terminate when:

- no expert adds net-new insight
- convergence recommendations align
- no conflicts remain that change direction
- evidence pool is saturated

---

## **6. Output Quality Control**

Use an LLM judge (Haiku/Sonnet) to evaluate:

- clarity
- relevance
- novelty
- adherence to persona rules

Score each turn; if under threshold:

- regenerate with penalties
- silently discard rambling
- enforce stricter constraints

--
