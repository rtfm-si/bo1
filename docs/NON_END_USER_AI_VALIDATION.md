Here’s the playbook you need: a **repeatable, automated, model-agnostic evaluation system** that scores quality at each stage of your Board of One deliberation pipeline. The goal: **consistent, comparable, statistically meaningful signals** you can use to decide:

- Haiku vs Sonnet
- Haiku in Round 1 + Sonnet in Round 2
- Full Sonnet
- Model mixtures
- Cost vs quality trade-offs
- Where to place “smart precision” upgrades (e.g., only send hard sub-problems to Sonnet)

Below is a clear, practical blueprint.

---

# 1. Break the Meeting Flow Into Objective, Measurable Units

Each stage has different quality expectations. You should evaluate _each independently_.

### **1. Problem Parsing**

Accuracy of:

- Goals
- Constraints
- Context
- Success criteria

Metrics:

- **Span extraction accuracy** (compare model extraction to a gold standard set).
- **Constraint completeness** score.

### **2. Sub-problem Decomposition**

Metrics:

- **Atomicity** — no sub-problem should contain multiple questions.
- **Coverage** — all critical elements must be covered.
- **Non-overlap** — sub-problems shouldn’t duplicate each other.

Scored by an evaluator model.

### **3. Persona Contributions**

Metrics:

- **Relevance** to sub-problem
- **Depth** (evidence, alternatives, risks considered)
- **Novelty** (non-duplicated insights)
- **Actionability**
- **Internal consistency**

### **4. Balancers / Conflict Resolution**

Metrics:

- **Correct challenge / correction behaviour**
- **Reduction of contradictory statements**
- **Improvement of clarity**

### **5. Synthesis / Final Recommendation**

Metrics:

- **Traceability** — does the conclusion reflect expert content?
- **Risk identification completeness**
- **Clear next steps**
- **No hallucinated info**

---

# 2. Build a Local “Scoring LLM” Layer (Automated Evaluation)

### Use a _separate evaluator model_ that:

- Takes the model output
- Compares it to structured scoring rubrics
- Returns both **scores** and **rationales**

This gives automation, consistency and reproducibility.

**Best models for evaluators**:

- Sonnet 3.7 (top-tier reliability)
- GPT-5 mini or 5 small (cheap, consistent)
- Qwen 2.5 72B (if local)

Evaluator prompts follow something like:

> You are the quality evaluator for a deliberation stage.
> Score the response on a 1–10 scale across the following criteria...
> Provide:
>
> 1. Per-criterion numerical score
> 2. One-sentence rationale per criterion
> 3. Final weighted score

Then you run the evaluation across many samples.

---

# 3. Use **Paired Comparison Testing** (ELO System)

This is more robust than scoring in isolation.

### Method:

1. Produce two outputs for the same task:
   **Haiku-A** vs **Sonnet-B**
2. Feed them _side-by-side_ to a judging model:
   “Which is better, and why?”
3. Increment an **ELO rating** for each model per stage (like chess rankings).

Benefits:

- Very sensitive to quality differences
- Doesn’t require a human
- Utterly model-agnostic
- Works well with subjective domains (arguments, writing quality)

This lets you confidently answer:

- “Is Haiku good enough for sub-problem decomposition?”
- “Should synthesis always be Sonnet?”

---

# 4. Monte-Carlo Sampling Under Variation

Because of randomness and instruction-following variance, you need spread.

Technique:

1. For each stage and each model, generate **10–20 variants** using:

   - different seeds
   - slight prompt variations
   - temperature banding (0.2–0.5)

2. Score each variant
3. Compute:

   - mean
   - variance
   - worst-case
   - 95% confidence interval

Why this matters:
Some models (Haiku especially) occasionally produce brilliant answers but have higher variance. Sonnet is more stable. This shows up sharply in this test.

---

# 5. Create **Golden Examples** (Truth Data)

You need a small curated dataset of:

- ~30 “problems” covering different industries, scenarios, levels of complexity
- For each:

  - gold-standard extraction
  - gold-standard sub-problems
  - gold-standard expert viewpoints
  - gold-standard synthesis

Where do these gold standards come from?

- Mix of your own work
- A Sonnet-tier output cleaned by you
- Occasionally a domain expert if needed

Then you can compute:

- F1 for extraction
- Coverage for decomposition
- Semantic similarity scores
- Counterfactual reasoning checks

---

# 6. Add **Semantic Consistency Tests (Self-Critique)**

You can do a structured post-hoc self-check:

### For any output:

Ask a judge model:

- “List any incorrect assumptions.”
- “List any contradictions.”
- “List any missing risks or alternative interpretations.”

Score counts of:

- hallucinations
- missed risks
- contradictions
- unsupported claims

Sonnet is very strong at doing these audits.

---

# 7. Add **Task Difficulty Weighting**

Not all tasks are equal.

For example:

- High-complexity multi-constraint problems matter more than trivial ones.
- Round 2 synthesis matters more than a single persona contribution.

You can:

- label each test case with difficulty
- weight its score higher in global metrics

This produces a better “real-world quality score” for each model pairing.

---

# 8. Build a Full **Automated Evaluation Matrix**

Example:

| Stage              | Haiku  | Sonnet | Haiku→Sonnet | Sonnet→Haiku | Mix |
| ------------------ | ------ | ------ | ------------ | ------------ | --- |
| Problem Extraction | 7.2    | 9.0    | 8.7          | 8.4          | 8.9 |
| Decomposition      | 6.8    | 9.2    | 9.0          | 8.5          | 9.2 |
| Expert Viewpoints  | 7.5    | 8.8    | 8.6          | 8.1          | 8.9 |
| Balancing          | 6.5    | 9.3    | 8.5          | 7.8          | 9.1 |
| Synthesis          | 7.0    | 9.5    | 9.3          | 8.7          | 9.4 |
| Stability (Var)    | Medium | Low    | Med-Low      | Med          | Low |

You generate this table automatically, weekly.

---

# 9. Final Recommended Pipeline

Here’s the configuration that tends to win across similar products:

### **Fast path (default)**

- Round 1 Expert Contributions → Haiku
- Balancer → Sonnet-mini
- Synthesis → Sonnet
- Sub-problems → Sonnet-mini
- Risk checks → Sonnet

### **High assurance path (Pro tier)**

- Everything after Round 1 → Sonnet
- Hard sub-problems auto-detected → Sonnet
- “Surge control” (overly confident answers) → Sonnet judge
- Model voted scoring → Sonnet

Your evaluation system will tell you precisely where to place these boundaries.

---

# 10. Implementation Blueprint (Practical)

### Build this workflow:

**1. Input:**
Problem + random seed + model version

**2. Output generation:**
Run the pipeline for each model config.

**3. Judge:**
Sonnet evaluates each output with:

- scoring rubric
- comparison vs gold
- contradictions
- hallucinations
- risk completeness
- quality score

**4. Aggregation:**
Compute per-stage scores.

**5. Long-term tracking:**
Store:

- model version
- prompt version
- configuration
- metrics
- evaluation date

Build a dashboard:

- spider charts
- ELO graph
- cost vs quality
- variance over time
- confidence intervals

You can even integrate this into n8n or an internal FastAPI + Postgres table.

---

# The Result

You’ll end up with:

- **Objective quality scoring**
- **Automated end-to-end evaluation**
- **Statistical confidence in model selection**
- **Clear triggers for when a cheaper model is “good enough”**
- **Justification for mixing models**
- **Non-user-dependent evaluation signals**

It becomes your invisible QA department for the AI board.

---

If you want, I can generate:

✅ a detailed **evaluation rubric** for each meeting stage
✅ a **JSON schema** for storing evaluation scores
✅ a **FastAPI evaluation microservice**
✅ a **Sonnet judge prompt** ready to plug into your pipeline
✅ a **reporting dashboard spec**
Just tell me which direction you want to take.
