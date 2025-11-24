Treat this like designing an autopilot for the meeting.

At each step/round you measure a few things, then have very explicit rules for:

- when **it’s not allowed to end yet**, and
- when it **must or should end**.

---

## 1. Codify the meeting as a scored process

Think of each step as a “round” of deliberation (up to 10). After each round, compute scores.

### 1.1. Define the key dimensions

We essentially care about:

1. **Exploration** – have we really unpacked the problem?
2. **Convergence** – are the experts aligning on a solution?
3. **Relevance/focus** – are we on topic?
4. **Novelty vs repetition** – are we still learning anything new?
5. **Cost/time** – how many paid steps have we used?

You can codify each as a 0–1 score per round.

---

### 1.2. Exploration score `E_r` (round r)

Goal: avoid agreeing too early.

Mechanics (LLM-friendly):

- Maintain a checklist of aspects that should be explored for _any_ decision, e.g.:

  - Problem clarity
  - Objectives/success criteria
  - Options/alternatives
  - Key assumptions
  - Risks/failure modes
  - Constraints (time, money, resources)
  - Impact on stakeholders
  - Dependencies/unknowns

- After each round, have a judge agent tag each message against these aspects and mark them as:

  - `not_mentioned`
  - `mentioned_superficially`
  - `discussed_deeply`

- Turn that into a score:

```text
For each aspect:
  0 = not_mentioned
  0.5 = mentioned_superficially
  1 = discussed_deeply

E_r = average over all aspects
```

So if 6/8 aspects are deeply discussed and 2 are superficial, `E_r` might be ~0.75.

---

### 1.3. Convergence / agreement score `C_r`

Each expert must state, at the end of each round:

- their **current preferred option** (e.g. Option A/B/C, or “Defer decision”)
- their **confidence** (0–1)

You can then compute:

- **Consensus level**: proportion of experts backing the same option.
- **Disagreement**: how spread they are (entropy or variance of choices).

Simple version:

```text
C_r = fraction of experts backing the leading option *
      average confidence of those experts
```

So:

- 4 of 5 experts choose A with avg confidence 0.8 → `C_r = 0.8 * (4/5) = 0.64`

---

### 1.4. Relevance / focus score `F_r`

You want to penalise drift.

- Split messages into chunks (per speaker turn).
- Judge agent labels each chunk:

  - `on_topic_core` (directly about the decision)
  - `on_topic_context` (useful background)
  - `off_topic` (tangents, unrelated)

Then:

```text
F_r = (#on_topic_core + 0.5 * #on_topic_context) / total_chunks
```

---

### 1.5. Novelty vs repetition score `N_r`

You want to avoid going in circles.

Simplest version using embeddings or fuzzy matching:

- For each new contribution, compare to **all previous contributions**.
- If it’s highly similar to an earlier one → mark as `repeated`.
- If it introduces new risks, options, arguments → mark as `novel`.

Then:

```text
N_r = #novel_chunks / ( #novel_chunks + #repeated_chunks )
```

You can also compute a **recent novelty** over the last 2–3 rounds only.

---

### 1.6. Cost and step pressure

Let:

- `r` = current round number (1–10)
- `cost_per_step` = known cost
- `total_cost_so_far = r * cost_per_step`

You don’t need a fancy model; just keep these so you can say:

- “We’re at round 7/10; marginal gains must be high to continue.”

---

### 1.7. Combined “meeting completeness index” `M_r`

Now combine these into a single 0–1 index:

```text
M_r = wE * E_r + wC * C_r + wF * F_r + wN * (1 - N_r_recent)
```

Where:

- `N_r_recent` is **lack of novelty** over recent rounds.
- So `(1 - N_r_recent)` grows when novelty drops (we’re “done exploring”).

Example weights:

- `wE = 0.35` (exploration is key)
- `wC = 0.35` (agreement is key)
- `wF = 0.2` (focus)
- `wN = 0.1` (stopping when no new info)

You can tune these, but this gives you a numeric “how complete does this feel?” at each step.

---

## 2. Rules so it doesn’t end too early or drag on

Now you define **hard rules** and **soft rules**.

### 2.1. Guardrails against ending too early

You can encode:

**Minimum exploration before allowing a decision**

```text
Rule 1 – Min rounds:
  r < MIN_ROUNDS  → cannot end (e.g. MIN_ROUNDS = 3)

Rule 2 – Exploration threshold:
  E_r < E_min     → cannot end (e.g. E_min = 0.6)

Rule 3 – Coverage completeness:
  At least X% of aspects must be ‘discussed_deeply’
  (e.g. 70% of aspects)
```

If user tries to end before that, facilitator says:

> “We haven’t fully explored risks/assumptions yet. Let’s do one more round focusing only on those.”

**Disagreement early = explore more**

If:

- `C_r` is high (everyone likes one option),
- **but** `E_r` is low or some aspects are untouched (e.g. no risk discussion),

then enforce an “exploration round”:

```text
If C_r > 0.6 and E_r < 0.5 and r <= 5:
  force another round,
  explicitly targeted at missing aspects.
```

---

### 2.2. Guardrails against dragging on

You also encode “enough is enough”.

**Diminishing returns rule**

Look at ΔE, ΔC over the last few rounds:

```text
ΔE_recent = E_r - E_{r-2}
ΔC_recent = C_r - C_{r-2}
N_r_recent = novelty over last 2 rounds
```

Then:

```text
If r >= MIN_ROUNDS
   AND E_r >= E_target (e.g. 0.7)
   AND C_r >= C_target (e.g. 0.7)
   AND N_r_recent <= novelty_floor (e.g. 0.2)
   THEN strongly recommend ending.
```

**Hard cap**

Regardless of anything:

```text
If r == 10:
  Enforce decision or explicit “no-decision” outcome with summary
```

**Circular debate rule**

If:

- `N_r_recent` is low (very repetitive),
- `F_r` is dropping (off-topic),
- `C_r` is _not_ improving,

then the facilitator should either:

- **force a decision**, or
- explicitly **park the topic** and summarise why we can’t decide.

Example:

```text
If r >= 5
  AND N_r_recent <= 0.3
  AND (C_r - C_{r-2}) < 0.05
  THEN
    prompt: "We seem to be repeating ourselves.
             Shall we decide between these remaining options now,
             or record as 'no decision' with blockers?"
```

---

### 2.3. Putting it all together – simple control loop

Pseudo-logic per round:

```python
for r in range(1, 11):
    run_deliberation_round(r)  # experts talk

    E_r = compute_exploration_score(history)
    C_r = compute_convergence_score(expert_votes)
    F_r = compute_focus_score(history_recent)
    N_r_recent = compute_novelty_recent(history_recent)

    # Safety: cannot end yet
    if r < MIN_ROUNDS or E_r < E_min or not enough_aspects_covered():
        facilitator_prompt_for_more_exploration(missing_aspects)
        continue  # go to next round

    # Suggest ending if strong signals
    if (E_r >= E_target and
        C_r >= C_target and
        N_r_recent <= novelty_floor):
        ask_user_to_confirm_decision()
        if user_confirms:
            break
        else:
            facilitator_prompt_targeted("any remaining doubts/risks?")

    # If we’re stuck/circular
    elif (r >= 5 and
          N_r_recent <= low_novelty and
          improvement_in_C_small()):
        facilitator_prompt_resolution_or_park()

    # Hard cap
    if r == 10:
        force_decision_or_no_decision()
        break
```

---

### 2.4. How this specifically prevents your two failure modes

**1. Ending too early with a shallow, suboptimal decision**

- You **refuse to end** while:

  - `E_r < E_min`
  - missing critical aspects (e.g. no risk discussion)
  - `r < MIN_ROUNDS`

- If there’s early consensus but low exploration, you inject a _targeted exploration round_:

  - “Everyone seems to like Option A. Before we commit, let’s quickly explore:

    - main risks,
    - assumptions,
    - alternative B or ‘do nothing’.”

So you can’t “agree in round 1” and walk away cheaply.

---

**2. Dragging on too long and polluting the decision**

- You monitor:

  - Novelty dropping (`N_r_recent` low)
  - Agreement stable or only marginally improving
  - Focus dropping (`F_r` low)

When all three align, you:

- prompt a decision (“We appear done – let’s pick”)
- or deliberately close with “parked/no-decision” plus blockers

You also:

- enforce a **hard 10-step cap**
- and raise the bar for continuing beyond e.g. round 7 (higher thresholds for additional rounds).

---

## 1. JSON schema for a Judge agent per round

This is the **single object** your judge agent returns for each round of deliberation.

```jsonc
{
  "meeting_id": "bo1-2025-11-24-xyz",
  "round_index": 3,

  "summary": {
    "round_brief": "Experts clarified success metrics and surfaced 3 main options.",
    "key_new_points": [
      "Defined success as +10% MRR within 6 months.",
      "Identified Option C (partnership) as alternative.",
      "Flagged risk of overloading current team."
    ]
  },

  "exploration": {
    "aspects": [
      {
        "name": "problem_clarity",
        "coverage_level": "deep", // "none" | "shallow" | "deep"
        "notes": "Problem restated in measurable terms."
      },
      {
        "name": "objectives",
        "coverage_level": "deep",
        "notes": "Primary and secondary objectives agreed."
      },
      {
        "name": "options_alternatives",
        "coverage_level": "shallow",
        "notes": "Three options mentioned, not compared."
      },
      {
        "name": "risks_failure_modes",
        "coverage_level": "none",
        "notes": "Risks not explicitly discussed yet."
      },
      {
        "name": "constraints",
        "coverage_level": "shallow",
        "notes": "Budget hint, no hard limits."
      },
      {
        "name": "stakeholders_impact",
        "coverage_level": "none",
        "notes": "Stakeholder impact not discussed."
      },
      {
        "name": "dependencies_unknowns",
        "coverage_level": "shallow",
        "notes": "Some unknowns noted but not structured."
      }
    ],
    "exploration_score": 0.46, // 0–1 numeric: avg over mapped levels
    "missing_critical_aspects": ["risks_failure_modes", "stakeholders_impact"]
  },

  "convergence": {
    "options_considered": ["Option_A", "Option_B", "Option_C"],
    "expert_positions": [
      {
        "expert_id": "expert_1",
        "preferred_option": "Option_A",
        "confidence": 0.7, // 0–1 self-rated
        "notes": "Believes A is fastest to implement."
      },
      {
        "expert_id": "expert_2",
        "preferred_option": "Option_B",
        "confidence": 0.6,
        "notes": "Concerns about tech debt in A."
      },
      {
        "expert_id": "expert_3",
        "preferred_option": "Option_A",
        "confidence": 0.8,
        "notes": "Sees strong alignment with current roadmap."
      }
    ],
    "leading_option": "Option_A",
    "leading_option_support_fraction": 0.67, // 2/3 experts
    "leading_option_avg_confidence": 0.75,
    "convergence_score": 0.5, // e.g. fraction * avg_confidence
    "disagreement_notes": "One expert prefers B due to tech risk concerns."
  },

  "focus": {
    "message_annotations": [
      {
        "message_id": "m1",
        "speaker_id": "expert_1",
        "topic_relevance": "core", // "core" | "context" | "off_topic"
        "notes": "Clarified decision goal."
      },
      {
        "message_id": "m2",
        "speaker_id": "expert_2",
        "topic_relevance": "context",
        "notes": "Background on last quarter results."
      },
      {
        "message_id": "m3",
        "speaker_id": "expert_3",
        "topic_relevance": "off_topic",
        "notes": "Digression into hiring strategy."
      }
    ],
    "core_count": 10,
    "context_count": 4,
    "off_topic_count": 2,
    "focus_score": 0.71, // (core + 0.5*context) / total
    "focus_drift_notes": "Some drift into hiring; should be refocused."
  },

  "novelty": {
    "novel_points_count": 5,
    "repeated_points_count": 7,
    "novelty_score_overall": 0.42, // novel / (novel + repeated)
    "novelty_score_recent": 0.3, // same but last 1–2 rounds only
    "examples_novel_points": [
      "Introducing Option C as partnership.",
      "Quantified success metric for MRR."
    ],
    "examples_repeated_points": [
      "Reiterated that Option A is fastest.",
      "Repeated concern about limited team capacity."
    ]
  },

  "cost_time": {
    "round_index": 3,
    "max_rounds": 10,
    "estimated_cost_this_round": 0.35, // e.g. £/$
    "estimated_cost_cumulative": 1.05,
    "time_elapsed_minutes": 18,
    "time_budget_minutes": 45
  },

  "composite": {
    "exploration_score": 0.46,
    "convergence_score": 0.5,
    "focus_score": 0.71,
    "low_novelty_score": 0.7, // 1 - novelty_score_recent

    "weights_used": {
      "exploration": 0.35,
      "convergence": 0.35,
      "focus": 0.2,
      "low_novelty": 0.1
    },
    "meeting_completeness_index": 0.51 // 0–1, weighted sum
  },

  "stop_continue_recommendation": {
    "status": "continue_targeted", // "must_continue" | "continue_targeted" | "ready_to_decide" | "park_or_abort"
    "rationale": [
      "Exploration of risks and stakeholder impact is insufficient.",
      "Convergence is forming but one expert has unresolved concerns."
    ],
    "next_round_focus_prompts": [
      "Surface and analyse top 3 risks for Option A vs B.",
      "Discuss who is most impacted by this decision and how."
    ]
  }
}
```

**Notes on how you’d implement the judge LLM:**

- Input: transcript of current round + high-level history summary + previous metrics.
- Output: **only** this JSON, no prose.
- Orchestrator: parses this JSON, stores it, and applies the stopping rules from the config below.

---

## 2. Config object for scoring + thresholds

A separate **config JSON** controls how you interpret those metrics for different meeting types.

### 2.1. Generic config schema

```jsonc
{
  "version": 1,
  "meeting_type": "strategic", // "tactical" | "strategic" | "default"

  "weights": {
    "exploration": 0.35,
    "convergence": 0.35,
    "focus": 0.2,
    "low_novelty": 0.1
  },

  "round_limits": {
    "min_rounds": 3,
    "max_rounds": 10
  },

  "thresholds": {
    "exploration": {
      "min_to_allow_end": 0.6, // E_r must be >= this to be allowed to end
      "target_good": 0.75 // E_r >= this counts as “well explored”
    },
    "convergence": {
      "min_to_allow_end": 0.6, // C_r must be >= this to be allowed to end
      "target_good": 0.75
    },
    "focus": {
      "min_acceptable": 0.6, // below this = bad drift, suggestion to refocus
      "target_good": 0.8
    },
    "novelty": {
      "novelty_floor_recent": 0.25 // if novelty_score_recent <= this, we’re repeating
    },
    "composite": {
      "min_index_to_recommend_end": 0.7 // M_r threshold to actively suggest ending
    },
    "progress": {
      "min_delta_convergence_over_2_rounds": 0.05, // less than this = stalled
      "min_delta_exploration_over_2_rounds": 0.05
    }
  },

  "rules": {
    "require_exploration_coverage": {
      "enabled": true,
      "required_aspects_deep": [
        "problem_clarity",
        "objectives",
        "risks_failure_modes"
      ],
      "min_fraction_deep_overall": 0.6
    },

    "early_consensus_requires_extra_check": {
      "enabled": true,
      "early_round_cutoff": 5,
      "convergence_high": 0.7,
      "exploration_low": 0.55,
      "forced_next_round_focus": ["risks_failure_modes", "options_alternatives"]
    },

    "stalled_debate_detection": {
      "enabled": true,
      "rounds_before_check": 5,
      "low_novelty_recent": 0.3,
      "min_delta_convergence_over_2_rounds": 0.05,
      "action": "prompt_resolution_or_park" // Orchestrator behaviour
    }
  }
}
```

---

### 2.2. Example configs: tactical vs strategic

**Tactical decision (bias to shorter, cheaper)**

```jsonc
{
  "meeting_type": "tactical",
  "weights": {
    "exploration": 0.3,
    "convergence": 0.4,
    "focus": 0.2,
    "low_novelty": 0.1
  },
  "round_limits": {
    "min_rounds": 2,
    "max_rounds": 7
  },
  "thresholds": {
    "exploration": {
      "min_to_allow_end": 0.5,
      "target_good": 0.65
    },
    "convergence": {
      "min_to_allow_end": 0.65,
      "target_good": 0.8
    },
    "focus": {
      "min_acceptable": 0.7,
      "target_good": 0.85
    },
    "novelty": {
      "novelty_floor_recent": 0.2
    },
    "composite": {
      "min_index_to_recommend_end": 0.65
    },
    "progress": {
      "min_delta_convergence_over_2_rounds": 0.05,
      "min_delta_exploration_over_2_rounds": 0.03
    }
  }
}
```

**Strategic decision (bias to deeper exploration)**

```jsonc
{
  "meeting_type": "strategic",
  "weights": {
    "exploration": 0.4,
    "convergence": 0.3,
    "focus": 0.2,
    "low_novelty": 0.1
  },
  "round_limits": {
    "min_rounds": 3,
    "max_rounds": 10
  },
  "thresholds": {
    "exploration": {
      "min_to_allow_end": 0.65,
      "target_good": 0.8
    },
    "convergence": {
      "min_to_allow_end": 0.55,
      "target_good": 0.7
    },
    "focus": {
      "min_acceptable": 0.6,
      "target_good": 0.8
    },
    "novelty": {
      "novelty_floor_recent": 0.3
    },
    "composite": {
      "min_index_to_recommend_end": 0.72
    },
    "progress": {
      "min_delta_convergence_over_2_rounds": 0.04,
      "min_delta_exploration_over_2_rounds": 0.04
    }
  }
}
```

---

### 2.3. How your orchestrator uses this (minimal logic)

Each round:

1. Get `judge_output` (first JSON).
2. Load `config` for this meeting.
3. Compute **stop/continue** based on config (or just trust `stop_continue_recommendation.status`).

Minimal control logic sketch:

```python
def should_allow_end(judge, cfg):
    r = judge["cost_time"]["round_index"]
    min_r = cfg["round_limits"]["min_rounds"]

    E = judge["exploration"]["exploration_score"]
    C = judge["convergence"]["convergence_score"]
    F = judge["focus"]["focus_score"]

    if r < min_r:
        return False
    if E < cfg["thresholds"]["exploration"]["min_to_allow_end"]:
        return False
    if C < cfg["thresholds"]["convergence"]["min_to_allow_end"]:
        return False
    if F < cfg["thresholds"]["focus"]["min_acceptable"]:
        return False

    # Optional extra aspect coverage rule…
    return True
```

Then:

- If `!should_allow_end` → facilitator prompts next round with `next_round_focus_prompts`.
- If allowed and composite index ≥ `min_index_to_recommend_end` and novelty low → facilitator proposes decision to user.

---
