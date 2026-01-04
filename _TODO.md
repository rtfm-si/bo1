mentor breadcrumbs duplicated

peer benchmarks needs to move from context to reports/benchmarks and a tab in here (1 tab industry, 1 tab peer)

context> metrics: user should be able to remove metrics 'not relevant to me' and replace with metrics from metrics.md. CTA 'need a new metric?' > feature request. we should have a bank of metrics that are more relevant for different industries and D2C direct to customer product sales, rather than saas recurring revenue & churn etc. we should pick the top 5 metrics relevant for the business (based on provided context) and ask them to populate that, with others optionally / populated over time rather than a list of 20 right up front.

use ontology below to update metrics.md, extend metrics to cover any not already covered for all types of solo, small and medium sized businesses who might use boardof.one :
Below is a **normalized KPI ontology** designed for **analytics + AI reasoning**.
It’s structured so KPIs can be **derived, reasoned over, compared across business models**, and used by agents without hard-coding logic.

This is not a list of metrics — it’s the **semantic spine** those metrics hang from.

---

## 1. Ontology design goals (implicit)

- **Model-agnostic**: works for SaaS, marketplace, AI, fintech, etc.
- **Composable**: KPIs derive from primitives.
- **Reasonable by AI**: clear causality, directionality, constraints.
- **Operational**: maps cleanly to SQL/dbt/metrics layers.

---

## 2. Core ontology layers

### Layer 0 — Entity Scope

What the KPI applies to.

| Scope       | Examples                 |
| ----------- | ------------------------ |
| Company     | Burn rate, runway        |
| Customer    | LTV, churn risk          |
| User        | Activation, engagement   |
| Account     | Expansion, seat usage    |
| Transaction | Conversion, failure rate |
| Feature     | Adoption, ROI            |
| System      | Latency, uptime          |
| Team        | Velocity, utilisation    |
| Channel     | CAC, attribution         |
| Market      | Share, penetration       |

> Every KPI **must declare exactly one primary scope**.

---

### Layer 1 — KPI Domain (Why it exists)

| Domain        | Description                              |
| ------------- | ---------------------------------------- |
| Growth        | Increasing absolute scale                |
| Efficiency    | Output per unit input                    |
| Profitability | Revenue vs cost                          |
| Retention     | Sustained value over time                |
| Acquisition   | Bringing users/customers in              |
| Engagement    | Depth & frequency of use                 |
| Reliability   | System / ops stability                   |
| Quality       | Output correctness / satisfaction        |
| Velocity      | Speed of learning or delivery            |
| Risk          | Fragility, concentration, compliance     |
| Leverage      | Ability to scale without linear cost     |
| Trust         | Safety, predictability, brand confidence |

---

### Layer 2 — KPI Primitive Type (How it’s measured)

| Primitive    | Meaning                         |
| ------------ | ------------------------------- |
| Count        | Absolute number                 |
| Rate         | Events per time                 |
| Ratio        | One quantity divided by another |
| Percentage   | Normalized ratio                |
| Duration     | Time elapsed                    |
| Currency     | Monetary value                  |
| Score        | Composite or indexed value      |
| Distribution | Variance / spread               |
| Boolean      | Pass/fail, on/off               |

> AI agents should **prefer ratios & rates** for reasoning.

---

### Layer 3 — Directionality

How to interpret movement.

| Direction        | Meaning                 |
| ---------------- | ----------------------- |
| Higher is Better | e.g. NRR, margin        |
| Lower is Better  | e.g. churn, latency     |
| Optimal Band     | e.g. pricing elasticity |
| Contextual       | Depends on lifecycle    |

This prevents AI from making naïve “optimize everything upward” mistakes.

---

### Layer 4 — Temporal Behavior

How the KPI behaves over time.

| Behavior          | Examples           |
| ----------------- | ------------------ |
| Leading Indicator | Activation rate    |
| Lagging Indicator | Revenue            |
| Coincident        | Usage volume       |
| Volatile          | Usage spikes       |
| Sticky            | Retention          |
| Seasonal          | GMV, media traffic |

---

### Layer 5 — Dependency Graph

What this KPI depends on.

| Dependency Type    | Examples               |
| ------------------ | ---------------------- |
| Upstream Driver    | CAC → LTV              |
| Downstream Outcome | Activation → Retention |
| Constraint         | Margin caps growth     |
| Trade-off          | Latency vs cost        |
| Amplifier          | Network effects        |
| Dampener           | Compliance friction    |

This is **critical for AI reasoning**.

---

## 3. Normalized KPI schema (canonical)

This is the **minimum schema** every KPI should conform to.

```yaml
kpi_id: string
name: string
domain: enum
primary_scope: enum
primitive_type: enum
directionality: enum
unit: string
time_window: string
formula: string
dependencies:
  upstream: [kpi_id]
  downstream: [kpi_id]
lifecycle_relevance:
  - pre_pmf
  - post_pmf
  - scale
risk_flags:
  - volatility
  - concentration
  - irreversibility
interpretation_notes: string
```

---

## 4. Example: normalized KPI instances

### Example 1 — Activation Rate

```yaml
kpi_id: activation_rate
name: Activation Rate
domain: Engagement
primary_scope: User
primitive_type: Percentage
directionality: Higher is Better
unit: "%"
time_window: 7d
formula: activated_users / new_users
dependencies:
  upstream: [onboarding_completion]
  downstream: [retention_rate, expansion_rate]
lifecycle_relevance: [pre_pmf, post_pmf]
risk_flags: []
interpretation_notes: >
  Strong leading indicator of product-market fit.
```

---

### Example 2 — Net Revenue Retention

```yaml
kpi_id: nrr
name: Net Revenue Retention
domain: Retention
primary_scope: Account
primitive_type: Percentage
directionality: Higher is Better
unit: "%"
time_window: 12m
formula: (starting_mrr + expansion - churn) / starting_mrr
dependencies:
  upstream: [product_adoption, pricing_fit]
  downstream: [arr_growth, valuation_multiple]
lifecycle_relevance: [post_pmf, scale]
risk_flags: [concentration]
interpretation_notes: >
  >100% indicates compounding growth without new acquisition.
```

---

### Example 3 — Cost per Inference (AI Product)

```yaml
kpi_id: cost_per_inference
name: Cost per Inference
domain: Efficiency
primary_scope: Transaction
primitive_type: Currency
directionality: Lower is Better
unit: "$"
time_window: per_event
formula: total_inference_cost / total_inferences
dependencies:
  upstream: [model_choice, caching_rate]
  downstream: [gross_margin, pricing_floor]
lifecycle_relevance: [post_pmf, scale]
risk_flags: [volatility]
interpretation_notes: >
  Hard lower bound on sustainable pricing.
```

---

## 5. KPI reasoning rules (AI-native)

These are **system-level rules** your AI agents should follow.

### Rule 1 — Never optimize in isolation

> Every KPI must be evaluated with at least **one upstream and one downstream dependency**.

### Rule 2 — Lifecycle-aware weighting

```text
pre-PMF → engagement, velocity > revenue
post-PMF → retention, unit economics
scale → predictability, leverage, risk
```

### Rule 3 — Ratios beat absolutes

AI should prefer:

- Revenue **per** customer
- Cost **per** event
- Output **per** employee

### Rule 4 — Flat curves > spikes

Stability often beats growth in scale decisions.

---

## 6. How this plugs into analytics stacks

### In practice:

- **dbt**: KPIs as models + YAML metadata
- **BI**: ontology drives grouping, not dashboards
- **AI agents**:

  - diagnose root causes
  - simulate changes
  - warn about second-order effects

### Example AI query enabled by ontology:

> “What KPIs are limiting ARR growth _without increasing burn_?”

This is only answerable if dependencies + directionality are explicit.

---

## 7. What this unlocks (strategically)

- AI-generated **board reports**
- Automated **early warning systems**
- Strategy simulations (“what breaks if we double X?”)
- Cross-business benchmarking without nonsense comparisons

---

If you want next, I can:

- translate this into **dbt YAML + SQL templates**
- generate **KPI dependency DAGs**
- or map it directly onto **Board-of-One style AI deliberation agents**

This ontology is the foundation for all of those.

Below is the **irreducible core KPI set** that **every business** should track, regardless of industry, model, or stage.

This is the **minimum viable instrumentation** for running a business that doesn’t lie to you.

No fluff. No SaaS bias. No investor vanity.

---

## The 12 Core Metrics (Universal)

### 1. Revenue

**What**: Money coming in
**Why**: Without revenue (or a credible path), nothing else matters
**Unit**: Currency / time
**Watch for**: Trend, not absolute size

---

### 2. Revenue Growth Rate

**What**: Speed of revenue change
**Why**: Direction beats magnitude
**Unit**: % (MoM / YoY)
**Watch for**: Deceleration before absolute decline

---

### 3. Gross Margin

**What**: Revenue minus direct costs
**Why**: Determines whether scale helps or hurts
**Unit**: %
**Watch for**: Margin compression as volume increases

---

### 4. Net Cash Burn / Cash Flow

**What**: Net cash in vs out
**Why**: Time is your scarcest resource
**Unit**: Currency / month
**Watch for**: Burn rising faster than learning or revenue

---

### 5. Cash Runway

**What**: Time until cash exhaustion
**Why**: Prevents accidental death
**Unit**: Months
**Watch for**: Runway shrinking without commensurate progress

---

### 6. Customer Acquisition Cost (CAC)

**What**: Cost to acquire one customer
**Why**: Sets the floor for sustainable growth
**Unit**: Currency
**Watch for**: CAC creep as easy channels saturate

---

### 7. Customer Lifetime Value (LTV)

**What**: Total value per customer
**Why**: Caps what you can afford to spend
**Unit**: Currency
**Watch for**: Assumptions hiding churn or discounting

---

### 8. Retention / Churn

**What**: Customers who stay vs leave
**Why**: Growth without retention is a leak
**Unit**: %
**Watch for**: Cohort decay, not averages

---

### 9. Engagement / Usage

**What**: How often customers actually use the product
**Why**: Revenue follows usage eventually
**Unit**: Frequency / time
**Watch for**: Activity without value creation

---

### 10. Conversion Rate

**What**: Progression through your core funnel
**Why**: Reveals friction and positioning problems
**Unit**: %
**Watch for**: Step-to-step drop-offs

---

### 11. Unit Economics

**What**: Profit or loss per customer / transaction
**Why**: Prevents scaling losses
**Unit**: Currency or %
**Watch for**: Hidden variable costs

---

### 12. Concentration Risk

**What**: Dependency on few customers, channels, people
**Why**: Single-point failure risk
**Unit**: % share of top 1–3
**Watch for**: “It’s fine for now” thinking

---

## The 4 Meta-Metrics (often ignored, always fatal)

These aren’t numbers you pull from Stripe — but they’re universal.

### 13. Learning Velocity

**What**: How fast you turn information into decisions
**Signal**: Experiments/month, decision cycle time

---

### 14. Decision Quality

**What**: Are decisions reversible, informed, and timely
**Signal**: Rework rate, post-mortems, overrides

---

### 15. Operational Reliability

**What**: Ability to deliver consistently
**Signal**: Downtime, incident frequency

---

### 16. Trust

**What**: Confidence customers place in you
**Signal**: Retention, referrals, complaints, payment friction

---

## If you had to reduce this to **5** (absolute minimum)

1. **Revenue trend**
2. **Gross margin**
3. **Cash runway**
4. **Retention**
5. **Unit economics**

Everything else is derivative.

---

## One hard rule (non-negotiable)

> If a metric does not **change a decision**, it is not a KPI.

Track fewer metrics.
But understand them **deeply**.
