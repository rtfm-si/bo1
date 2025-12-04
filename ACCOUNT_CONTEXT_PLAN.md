# Account & Business Context Architecture Plan

## Overview

Comprehensive three-layer business context system with account management, billing, and cross-user intelligence.

---

## Page Structure

```
/settings/
├── +layout.svelte          # Shared settings layout with sidebar nav
├── +page.svelte            # Redirect to /settings/account
├── account/
│   └── +page.svelte        # Account settings (email, password, profile)
├── context/
│   ├── +layout.svelte      # Tab navigation for 3 layers
│   ├── +page.svelte        # Redirect to overview
│   ├── overview/           # Layer 1: High-level (existing, moved)
│   │   └── +page.svelte
│   ├── strategic/          # Layer 2: Products, competitors, ICP, trends
│   │   └── +page.svelte
│   └── metrics/            # Layer 3: Business performance metrics
│       └── +page.svelte
├── billing/
│   └── +page.svelte        # Plans, usage, payment
└── team/                   # Future: team management
    └── +page.svelte
```

---

## Three-Layer Context System

### Layer 1: High-Level Context (Existing)
Basic business information for quick onboarding.

| Field | Description | Source |
|-------|-------------|--------|
| Company Name | Business name | Manual / Website |
| Website | Company URL | Manual |
| Industry | Vertical category | Manual / Enrichment |
| Business Stage | idea, early, growing, scaling | Manual |
| Primary Objective | acquire_customers, improve_retention, etc. | Manual |
| Business Model | B2B SaaS, Marketplace, D2C, etc. | Manual / Enrichment |
| Target Market | Customer segment description | Manual / Enrichment |
| Product Description | What you offer | Manual / Enrichment |

### Layer 2: Strategic Context (New)
Deeper strategic intelligence for better expert recommendations.

| Field | Description | Source |
|-------|-------------|--------|
| Products | Array of products with name, description, pricing | Website / Manual |
| Value Proposition | Core value statement | Website / Manual |
| Pricing Model | Subscription, usage-based, freemium, etc. | Website / Manual |
| Positioning | Market positioning statement | Website / Manual |
| Brand Tone | Professional, friendly, technical, etc. | Website / Manual |
| Competitors | Top 3-5 with strengths/weaknesses | Auto-detect / Manual |
| ICP | Ideal customer profile (demographics, firmographics, pain points) | Manual |
| Market Trends | Current industry trends | External APIs (Brave/Perplexity) |

**Cross-User Benefit:**
- Industry embeddings enable finding similar businesses
- Aggregated anonymized insights surface to all users in industry
- Competitor data shared (with consent) across user base

### Layer 3: Business Metrics (New)
Quantitative performance data for context-aware recommendations.

**Predefined Metrics (all businesses):**

| Metric | Definition | Importance | Unit |
|--------|------------|------------|------|
| MRR | Monthly Recurring Revenue | Core SaaS health metric | $ |
| ARR | Annual Recurring Revenue | Annual revenue baseline | $ |
| CAC | Customer Acquisition Cost | Sales & marketing efficiency | $ |
| LTV | Customer Lifetime Value | Long-term customer worth | $ |
| LTV:CAC | LTV to CAC Ratio | Unit economics health (>3 good) | ratio |
| Churn Rate | Monthly customer churn | Retention health | % |
| Net Revenue Retention | Revenue retention including expansion | Growth indicator | % |
| Conversion Rate | Trial/lead to paid conversion | Funnel efficiency | % |
| Payback Period | Months to recover CAC | Cash flow efficiency | months |
| Gross Margin | Revenue minus COGS | Profitability baseline | % |

**Metric Entry Fields:**
- `name` - Display name
- `definition` - What it measures
- `importance` - Why it matters for this business
- `value` - Current value
- `value_unit` - $, %, days, ratio
- `captured_at` - When value was entered
- `source` - manual, clarification, integration

**User-Defined Metrics:**
Users can add custom metrics relevant to their business/industry.

**Clarification Integration:**
When a clarifying question is answered that contains metric data, offer to save to metrics layer.

---

## Database Schema

### New Tables

```sql
-- Strategic context (Layer 2)
CREATE TABLE user_strategic_context (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    -- Products & Value Prop
    products JSONB DEFAULT '[]',      -- [{name, description, pricing, is_primary}]
    value_proposition TEXT,
    pricing_model TEXT,
    positioning TEXT,
    brand_tone TEXT,

    -- Competitors
    competitors JSONB DEFAULT '[]',   -- [{name, url, strengths, weaknesses, source, added_at}]

    -- ICP
    ideal_customer_profile JSONB,     -- {title, company_size, industry, pain_points[], goals[]}

    -- Market Trends (refreshed periodically)
    market_trends JSONB DEFAULT '[]', -- [{trend, source, source_url, captured_at}]
    trends_last_updated TIMESTAMPTZ,

    -- Embeddings for cross-user benefit
    industry_embedding VECTOR(1024),
    context_embedding VECTOR(1024),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id)
);

-- Business metrics (Layer 3)
CREATE TABLE user_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id TEXT NOT NULL,
    metric_key TEXT NOT NULL,         -- 'mrr', 'cac', 'churn', 'custom_xyz'

    -- Metric definition
    name TEXT NOT NULL,               -- "Monthly Recurring Revenue"
    definition TEXT,                  -- "Total recurring revenue per month"
    importance TEXT,                  -- "Core health metric for SaaS"
    category TEXT,                    -- 'growth', 'retention', 'financial', 'efficiency', 'custom'

    -- Value
    value DECIMAL,
    value_unit TEXT,                  -- '$', '%', 'days', 'ratio', etc.
    captured_at TIMESTAMPTZ,
    source TEXT DEFAULT 'manual',     -- 'manual', 'clarification', 'integration'

    -- Metadata
    is_predefined BOOLEAN DEFAULT false,
    display_order INT DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(user_id, metric_key)
);

-- Predefined metrics template (seeded once)
CREATE TABLE metric_templates (
    metric_key TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    definition TEXT NOT NULL,
    importance TEXT NOT NULL,
    category TEXT NOT NULL,
    value_unit TEXT NOT NULL,
    display_order INT DEFAULT 0,
    applies_to JSONB DEFAULT '["all"]'  -- ['saas', 'ecommerce', 'marketplace', 'all']
);

-- Industry insights (aggregated, anonymized for cross-user benefit)
CREATE TABLE industry_insights (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    industry TEXT NOT NULL,
    insight_type TEXT NOT NULL,       -- 'trend', 'benchmark', 'competitor', 'best_practice'
    content JSONB NOT NULL,
    embedding VECTOR(1024),
    source_count INT DEFAULT 1,       -- How many users contributed
    confidence DECIMAL DEFAULT 0.5,   -- Aggregated confidence
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ            -- Trends expire, benchmarks refresh quarterly
);

CREATE INDEX idx_industry_insights_industry ON industry_insights(industry);
CREATE INDEX idx_industry_insights_type ON industry_insights(insight_type);
CREATE INDEX idx_user_metrics_user ON user_metrics(user_id);
CREATE INDEX idx_user_strategic_user ON user_strategic_context(user_id);
```

### Seed Data: Metric Templates

```sql
INSERT INTO metric_templates (metric_key, name, definition, importance, category, value_unit, display_order, applies_to) VALUES
('mrr', 'Monthly Recurring Revenue', 'Total predictable revenue per month from subscriptions', 'Core health metric - indicates business scale and growth trajectory', 'financial', '$', 1, '["saas"]'),
('arr', 'Annual Recurring Revenue', 'MRR × 12 - annualized recurring revenue', 'Standard metric for valuation and planning', 'financial', '$', 2, '["saas"]'),
('cac', 'Customer Acquisition Cost', 'Total sales & marketing spend divided by new customers acquired', 'Measures efficiency of growth spend - lower is better', 'growth', '$', 3, '["all"]'),
('ltv', 'Customer Lifetime Value', 'Average revenue per customer over their entire relationship', 'Indicates long-term customer worth - should be >3x CAC', 'growth', '$', 4, '["all"]'),
('ltv_cac_ratio', 'LTV:CAC Ratio', 'Lifetime value divided by acquisition cost', 'Unit economics health - 3:1 is good, 5:1 is excellent', 'efficiency', 'ratio', 5, '["all"]'),
('monthly_churn', 'Monthly Churn Rate', 'Percentage of customers lost per month', 'Retention health - <2% monthly is good for SaaS', 'retention', '%', 6, '["saas"]'),
('nrr', 'Net Revenue Retention', 'Revenue retained from existing customers including expansion', 'Growth indicator - >100% means growing without new customers', 'retention', '%', 7, '["saas"]'),
('conversion_rate', 'Conversion Rate', 'Percentage of trials/leads that become paying customers', 'Funnel efficiency - varies by model (freemium vs sales-led)', 'growth', '%', 8, '["all"]'),
('payback_period', 'CAC Payback Period', 'Months required to recover customer acquisition cost', 'Cash flow efficiency - <12 months is good', 'efficiency', 'months', 9, '["saas"]'),
('gross_margin', 'Gross Margin', 'Revenue minus cost of goods sold, as percentage', 'Profitability baseline - >70% typical for SaaS', 'financial', '%', 10, '["all"]'),
('burn_rate', 'Monthly Burn Rate', 'Net cash spent per month', 'Runway indicator - how fast spending cash reserves', 'financial', '$', 11, '["all"]'),
('runway', 'Runway', 'Months of operation remaining at current burn rate', 'Survival metric - aim for >12 months', 'financial', 'months', 12, '["all"]');
```

---

## API Endpoints

### Strategic Context (Layer 2)

```
GET    /api/v1/context/strategic
       → Returns user's strategic context

PUT    /api/v1/context/strategic
       → Updates strategic context (partial update supported)
       Body: { products?, value_proposition?, competitors?, ... }

POST   /api/v1/context/strategic/enrich
       → Extracts products, positioning, tone from website
       Body: { website_url }
       → Returns { success, extracted: { products, value_proposition, ... } }

POST   /api/v1/context/competitors/detect
       → Auto-detects competitors using Brave Search
       Body: { industry?, product_description? }  (uses saved context if not provided)
       → Returns { competitors: [{ name, url, description }] }

POST   /api/v1/context/trends/refresh
       → Fetches current market trends
       Body: { industry }
       → Returns { trends: [{ trend, source, url }] }
```

### Business Metrics (Layer 3)

```
GET    /api/v1/metrics
       → Returns all user metrics with templates merged
       → { metrics: [...], templates: [...] }

GET    /api/v1/metrics/templates
       → Returns predefined metric templates
       Query: ?business_model=saas

PUT    /api/v1/metrics/:key
       → Updates a metric value
       Body: { value, captured_at? }

POST   /api/v1/metrics
       → Creates a custom metric
       Body: { metric_key, name, definition, importance, category, value_unit }

DELETE /api/v1/metrics/:key
       → Removes a custom metric (predefined cannot be deleted)
```

### Account & Billing

```
GET    /api/v1/account
       → Returns account info (email, name, created_at, subscription)

PUT    /api/v1/account
       → Updates account settings
       Body: { name?, email?, preferences? }

GET    /api/v1/billing/usage
       → Returns usage stats (meetings this month, API calls, etc.)

GET    /api/v1/billing/plan
       → Returns current plan details

POST   /api/v1/billing/portal
       → Creates Stripe billing portal session
       → Returns { url } for redirect
```

---

## Frontend Components

### Settings Layout (`/settings/+layout.svelte`)

```
┌─────────────────────────────────────────────────────────────┐
│  ← Back to Dashboard                    Board of One        │
├──────────────┬──────────────────────────────────────────────┤
│              │                                              │
│  Account     │                                              │
│  ────────    │            [Content Area]                    │
│  • Profile   │                                              │
│              │                                              │
│  Context     │                                              │
│  ────────    │                                              │
│  • Overview  │                                              │
│  • Strategic │                                              │
│  • Metrics   │                                              │
│              │                                              │
│  Billing     │                                              │
│  ────────    │                                              │
│  • Plan      │                                              │
│  • Usage     │                                              │
│              │                                              │
└──────────────┴──────────────────────────────────────────────┘
```

### Context Tabs (`/settings/context/+layout.svelte`)

```
┌─────────────────────────────────────────────────────────────┐
│  [Overview]  [Strategic]  [Metrics]                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│                    Tab Content                              │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Metrics Page (`/settings/context/metrics/+page.svelte`)

```
┌─────────────────────────────────────────────────────────────┐
│  Business Metrics                          [+ Add Metric]   │
│  Track key performance indicators                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FINANCIAL                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ MRR                              $___________        │   │
│  │ Monthly Recurring Revenue                            │   │
│  │ ℹ️ Core health metric for SaaS    Updated: Never     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Gross Margin                     ___________  %      │   │
│  │ Revenue minus COGS                                   │   │
│  │ ℹ️ >70% typical for SaaS          Updated: Never     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  GROWTH                                                     │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ CAC                              $___________        │   │
│  │ Customer Acquisition Cost                            │   │
│  │ ℹ️ Measures growth efficiency     Updated: Never     │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (Priority: High)
**Goal:** Restructure routes, create settings layout, move existing context

**Tasks:**
1. Create `/settings/+layout.svelte` with sidebar navigation
2. Create `/settings/+page.svelte` (redirect to account)
3. Create `/settings/account/+page.svelte` (basic profile page)
4. Create `/settings/context/+layout.svelte` with tab navigation
5. Move existing context page to `/settings/context/overview/+page.svelte`
6. Create `/settings/billing/+page.svelte` (placeholder with plan info)
7. Update dashboard navigation to point to new settings structure
8. Update all internal links

**Estimated effort:** 4-6 hours

### Phase 2: Business Metrics (Priority: High)
**Goal:** Enable users to track key business metrics

**Tasks:**
1. Create database migration for `user_metrics` and `metric_templates`
2. Seed predefined metrics
3. Create API endpoints: GET/PUT/POST/DELETE metrics
4. Build `/settings/context/metrics/+page.svelte`
5. Create MetricCard component
6. Add "Add Custom Metric" modal
7. Integrate with clarification flow (populate from answers)

**Estimated effort:** 6-8 hours

### Phase 3: Strategic Context (Priority: Medium)
**Goal:** Deeper business intelligence

**Tasks:**
1. Create database migration for `user_strategic_context`
2. Extend enrichment service for products/positioning extraction
3. Create API endpoints for strategic context
4. Build `/settings/context/strategic/+page.svelte`
5. Add competitor section with auto-detect
6. Add ICP builder
7. Integrate Brave Search for market trends

**Estimated effort:** 8-10 hours

### Phase 4: Cross-User Intelligence (Priority: Low)
**Goal:** Leverage collective knowledge

**Tasks:**
1. Create database migration for `industry_insights`
2. Add embeddings to strategic context on save
3. Build aggregation job for industry insights
4. Surface relevant insights during deliberation
5. Add "Industry Benchmarks" section to metrics

**Estimated effort:** 10-12 hours

### Phase 5: Billing Integration (Priority: Medium)
**Goal:** Full billing management

**Tasks:**
1. Integrate Stripe Customer Portal
2. Build usage tracking
3. Create plan comparison page
4. Add upgrade/downgrade flows

**Estimated effort:** 6-8 hours

---

## Integration Points

### Deliberation Context Injection
All three layers should be injected into expert deliberations:

```python
def build_context_prompt(user_id: str) -> str:
    """Build comprehensive context for deliberation."""
    context = load_user_context(user_id)  # Layer 1
    strategic = load_strategic_context(user_id)  # Layer 2
    metrics = load_user_metrics(user_id)  # Layer 3

    return f"""
## Business Context

**Company:** {context.company_name}
**Industry:** {context.industry}
**Stage:** {context.business_stage}
**Model:** {context.business_model}

## Strategic Position

**Value Proposition:** {strategic.value_proposition}
**Target Customer:** {strategic.ideal_customer_profile}
**Competitors:** {format_competitors(strategic.competitors)}

## Key Metrics

{format_metrics(metrics)}

## Recent Market Trends

{format_trends(strategic.market_trends)}
"""
```

### Clarification → Metrics Flow
When a clarifying question is answered with metric data:

1. Detect metric-like answers (numbers with units)
2. Prompt user: "Would you like to save this as a tracked metric?"
3. If yes, create/update metric entry
4. Future deliberations will have this data automatically

---

## Files to Create/Modify

### New Files
```
frontend/src/routes/(app)/settings/+layout.svelte
frontend/src/routes/(app)/settings/+page.svelte
frontend/src/routes/(app)/settings/account/+page.svelte
frontend/src/routes/(app)/settings/context/+layout.svelte
frontend/src/routes/(app)/settings/context/+page.svelte
frontend/src/routes/(app)/settings/context/overview/+page.svelte
frontend/src/routes/(app)/settings/context/strategic/+page.svelte
frontend/src/routes/(app)/settings/context/metrics/+page.svelte
frontend/src/routes/(app)/settings/billing/+page.svelte
frontend/src/lib/components/settings/SettingsSidebar.svelte
frontend/src/lib/components/settings/MetricCard.svelte
frontend/src/lib/components/settings/CompetitorCard.svelte

backend/api/strategic.py
backend/api/metrics.py
backend/api/account.py

migrations/versions/xxx_add_strategic_context.py
migrations/versions/xxx_add_user_metrics.py
migrations/versions/xxx_add_industry_insights.py
```

### Modified Files
```
frontend/src/lib/api/client.ts           # Add new API methods
frontend/src/lib/api/types.ts            # Add new types
frontend/src/routes/(app)/+layout.svelte # Update nav
backend/api/main.py                      # Register new routers
bo1/services/enrichment.py               # Extend for strategic extraction
bo1/graph/nodes/context.py               # Inject all layers
```

---

## Open Questions

1. **Competitor sharing:** Should detected competitors be shared across users (anonymized)? Requires consent model.

2. **Metric benchmarks:** Should we show industry benchmarks? ("Your churn is 5%, average SaaS is 3%")

3. **Trend refresh frequency:** How often to refresh market trends? Daily? Weekly? On-demand only?

4. **Embedding model:** Use Voyage AI (existing) or different model for context embeddings?

5. **Privacy:** What data can be aggregated for cross-user benefit? Need clear consent.

---

## Success Metrics

- **Adoption:** % of users with Layer 2/3 data populated
- **Completeness:** Average fields filled per layer
- **Engagement:** Settings page visits, metric updates
- **Quality:** Expert satisfaction with context (future survey)
- **Relevance:** Reduced clarifying questions (context answers them)
