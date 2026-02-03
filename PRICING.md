# Bo1 Pricing Strategy

## Overview

Three paid tiers (Starter, Plus, Pro) using "Good-Better-Best" model targeting 90%+ net margin, plus add-ons and early-adopter incentives.

**Why 3 tiers?** Research shows:
- 30% higher conversion vs single-price
- Middle tier captures 60-70% of customers
- 43% higher ARPU vs flat-rate
- Premium tier anchors middle as "good value"

---

## Cost Basis

| Feature               | Unit Cost  | Notes                                |
| --------------------- | ---------- | ------------------------------------ |
| Meeting               | $0.50      | Multi-round deliberation, 5 personas |
| Mentor Chat           | $0.03-0.05 | Per message with prompt caching      |
| Data Analysis         | $0.10-0.20 | Per question on dataset              |
| SEO Analysis          | $0.30      | URL audit + recommendations          |
| SEO Article           | $1.00      | Full content generation              |
| Competitor Enrichment | $0.20      | Per competitor via Tavily            |

**Utilization assumption**: 40-60% of allocated resources typically used.

---

## Tier Structure

### Free (Lifetime - No Refresh)

| Feature       | Allocation                    |
| ------------- | ----------------------------- |
| Meetings      | 2 (lifetime, never refreshes) |
| Mentor Chats  | 2 (lifetime)                  |
| Data Analysis | 1 question (lifetime)         |
| SEO           | None                          |
| Competitors   | None                          |
| Add-ons       | Not eligible                  |

**Purpose**: Sample core meeting experience. Convert or churn.

---

### Starter - $19/month

| Feature          | Monthly Limit        |
| ---------------- | -------------------- |
| Meetings         | 2                    |
| Experts/Meeting  | 3 max                |
| Data Analyses    | 4 (2x meetings)      |
| Mentor Chats     | 8 (2x data)          |
| SEO Analyses     | 2                    |
| SEO Articles     | 1                    |
| Competitors      | 1 tracked            |
| Benchmarks       | Industry benchmarks  |

**Cost at 50% utilization**: ~$1.86
**Margin**: 90%

**Target user**: Solo founders making 1-2 strategic decisions/month.

---

### Plus - $49/month ⭐ MOST POPULAR

| Feature         | Monthly Limit        |
| --------------- | -------------------- |
| Meetings        | 4                    |
| Experts/Meeting | 3 max                |
| Data Analyses   | 8 (2x meetings)      |
| Mentor Chats    | 16 (2x data)         |
| SEO Analyses    | 2                    |
| SEO Articles    | 2                    |
| Competitors     | 2 tracked            |
| Benchmarks      | Industry benchmarks  |

**Cost at 50% utilization**: ~$3.42
**Margin**: 93%

**Target user**: Active solopreneurs, weekly strategic decisions. Expected 60-70% of paid users.

---

### Pro - $99/month

| Feature          | Monthly Limit        |
| ---------------- | -------------------- |
| Meetings         | 8                    |
| Experts/Meeting  | 5 max                |
| Data Analyses    | 16 (2x meetings)     |
| Mentor Chats     | 32 (2x data)         |
| SEO Analyses     | 2                    |
| SEO Articles     | 4                    |
| Competitors      | 3 tracked            |
| Benchmarks       | Industry benchmarks  |
| Priority Support | Yes                  |

**Cost at 50% utilization**: ~$6.44
**Margin**: 93%

**Target user**: Founders running multiple initiatives, 2x weekly decisions.

---

## Price Jump Analysis

| Jump | Increase | Industry Guidance |
|------|----------|-------------------|
| $19 → $49 | 158% | OK (creates clear differentiation) |
| $49 → $99 | 102% | Within 50-100% guideline |

The premium tier anchors the middle tier as a "good deal" - Pro doesn't need to be a bestseller.

---

## Add-Ons

| Add-On                 | Price | Cost  | Margin |
| ---------------------- | ----- | ----- | ------ |
| 3 Meeting Pack         | $10   | $1.50 | 85%    |
| 5 Meeting Pack         | $15   | $2.50 | 83%    |
| SEO Article (1)        | $6    | $1.00 | 83%    |
| Data Analysis Pack (3) | $5    | $0.45 | 91%    |

---

## Early Adopter Program

**First 200 paying customers**: 20% lifetime discount

| Tier    | Regular | Discounted |
| ------- | ------- | ---------- |
| Starter | $19/mo  | $15.20/mo  |
| Plus    | $49/mo  | $39.20/mo  |
| Pro     | $99/mo  | $79.20/mo  |

**Margin at discount**: Still 85%+ across all tiers.

---

## Comparison Table (Marketing)

|                     |    Free    | Starter | Plus ⭐ |   Pro    |
| ------------------- | :--------: | :-----: | :-----: | :------: |
| **Price**           |     $0     | $19/mo  | $49/mo  |  $99/mo  |
| **Meetings**        | 2 lifetime |  2/mo   |  4/mo   |   8/mo   |
| **Experts/Meeting** |     3      |    3    |    3    |    5     |
| **Data Analyses**   | 1 lifetime |  4/mo   |  8/mo   |  16/mo   |
| **Mentor Chats**    | 2 lifetime |  8/mo   |  16/mo  |  32/mo   |
| **SEO Analyses**    |     -      |  2/mo   |  2/mo   |   2/mo   |
| **SEO Articles**    |     -      |  1/mo   |  2/mo   |   4/mo   |
| **Competitors**     |     -      |    1    |    2    |    3     |
| **Benchmarks**      |     -      | Industry| Industry| Industry |
| **Add-ons**         |     No     |   Yes   |   Yes   |   Yes    |
| **Support**         | Community  |  Email  |  Email  | Priority |

---

## SEO Analysis Feature (TODO)

**Current state**: Weak, needs enhancement.

**Proposed enhancement**: User submits their URL and receives:

- Technical SEO audit (page speed, mobile, meta tags)
- Content optimization tips
- Keyword gap analysis
- Competitor comparison (if competitors tracked)
- Actionable improvement checklist

**Implementation note**: Integrate Tavily/Brave research + Claude analysis for URL-specific recommendations.

---

## Market Validation

### Competitor Pricing (2026)

**AI Chat/Advisor Tools**:

- Tidio AI: €29/mo + per-conversation
- Boei: €14/mo (2,000 AI messages)
- Enterprise chatbots: $1,200-5,000/mo

**SEO Tools**:

- Surfer SEO: $79-179/mo
- Semrush: $139-499/mo
- Ahrefs: Similar to Semrush

**AI Decision/Analytics**:

- Most AI tools: $19-49 starter, $79-149 pro
- GoHighLevel: $97 starter, $297 pro
- Whatagraph: $388-999/mo

### Bo1 Positioning

- **$19 Starter**: Entry-level, competitive with basic AI chatbots
- **$49 Plus**: Sweet spot, below Surfer ($79), competitive with AI tools
- **$99 Pro**: Premium tier, anchors value, competitive with serious tools
- **Value prop**: Multi-agent deliberation + advisor + analytics in one

---

## 3-Tier Psychology Research

### Why "Good-Better-Best" Works

1. **Decoy effect**: Premium tier makes middle look like great value
2. **Choice architecture**: 3 options = optimal (4+ reduces conversion by 30%)
3. **Self-selection**: Users correctly identify their tier
4. **Upsell path**: Clear upgrade journey from Starter → Plus → Pro

### Expected Distribution

| Tier | Expected % | Revenue Contribution |
|------|-----------|---------------------|
| Starter | 15-20% | Low (entry funnel) |
| Plus | 60-70% | Highest (profit center) |
| Pro | 15-20% | High per-user value |

### Naming Psychology

- "Plus" suggests lower tiers are missing something valuable
- Highlighting "MOST POPULAR" on middle tier increases selection by 15-30%
- Avoid generic metal-based naming (Bronze/Silver/Gold)

---

## Margin Analysis

| Scenario         | Starter ($19) | Plus ($49) | Pro ($99) |
| ---------------- | ------------- | ---------- | --------- |
| 30% utilization  | 94%           | 96%        | 96%       |
| 50% utilization  | 90%           | 93%        | 93%       |
| 70% utilization  | 86%           | 90%        | 91%       |
| 100% utilization | 80%           | 86%        | 87%       |

**All tiers exceed 90% target at typical (50%) utilization.**

### Realistic Usage Rationale

Solo business owners don't make 20 strategic decisions/month. The value is quality over quantity:
- **2-8 meetings/month** = 1-2 decisions per week max
- **Data analysis** supports meeting prep and follow-up (x2 meetings)
- **Mentor chats** guide execution between decisions (x2 data)
- **SEO** = maintenance activity, 2 analyses is plenty
- **Articles** scale with tier for content needs

---

## Implementation Checklist

- [ ] Update `bo1/billing/config.py` tier limits
- [ ] Create Stripe products/prices for 3 tiers
- [ ] Create 20% lifetime coupon (first 200)
- [ ] Update pricing page UI with "Most Popular" badge
- [ ] Migrate free users to lifetime model
- [ ] Enhance SEO analysis (URL submission)
- [ ] Test checkout flow E2E

---

## Sources

- [Advanced SaaS Pricing Psychology 2026](https://ghl-services-playbooks-automation-crm-marketing.ghost.io/advanced-saas-pricing-psychology-beyond-basic-tiered-models/)
- [Good-Better-Best vs A-La-Carte](https://www.getmonetizely.com/articles/good-better-best-vs-a-la-carte-pricing-which-model-converts-better)
- [SaaS Pricing Psychology](https://thegood.com/insights/saas-pricing/)
- [AI Chatbot Pricing 2026](https://www.tidio.com/blog/chatbot-pricing/)
- [Semrush Pricing](https://backlinko.com/semrush-pricing)
- [Surfer SEO Review](https://pikaseo.com/blog/surfer-seo-review)
- [2026 SaaS Pricing Guide](https://www.getmonetizely.com/blogs/the-2026-guide-to-saas-ai-and-agentic-pricing-models)
