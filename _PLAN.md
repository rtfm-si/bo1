# Plan: Non-Fixed Costs Analysis & Fair Usage Caps

## Status: NEEDS CLARIFICATION

The task `[BILLING][P2] Clarify scope of: "non-fixed costs (mentor chats, data analysis, competitor analysis) - cost analysis, fair usage caps, top 10% capping"` requires user input before implementation.

## Current State

**Existing infrastructure:**
- `api_costs` table tracks all LLM costs with `operation_type`, `node_name`, `user_id`
- `user_cost_periods` aggregates monthly costs per user
- `user_budget_settings` supports per-user hard limits and alert thresholds (admin-configured)
- `PlanConfig` defines tier limits for `mentor_daily` (10/50/unlimited)

**Missing:**
- No distinct tracking for "mentor chat" vs "data analysis" vs "competitor analysis" operation types
- No automatic fair usage caps based on usage percentiles
- No "top 10% capping" logic

## Clarification Questions

Before proceeding, please clarify:

1. **Operation categorization**: Should we add explicit `operation_type` values like `mentor_chat`, `data_analysis`, `competitor_analysis`? Currently these are tracked as generic `completion` or `summarization`.

2. **Fair usage caps scope**:
   - Per-feature caps (e.g., 50 mentor chats/day) vs per-cost caps (e.g., $5/month on mentor)?
   - Should caps be tier-specific or universal?

3. **Top 10% capping mechanism**:
   - Cap users in top 10% of usage to prevent runaway costs?
   - Alert-only or hard block?
   - Rolling window (daily/weekly/monthly)?

4. **Implementation priority**:
   - Cost analysis dashboard (admin visibility into per-feature costs)?
   - Automatic caps enforcement?
   - Both?

## Proposed Approaches (pending clarification)

### Option A: Cost Analysis Only
- Add granular `operation_type` tracking for mentor/data/competitor
- Admin dashboard showing per-feature cost breakdown
- No automatic caps (admin manually adjusts `user_budget_settings`)

### Option B: Automatic Fair Usage Caps
- Tier-specific cost budgets per feature category
- Soft warnings at 80%, hard cap at 100%
- Per-feature limits in `PlanConfig`

### Option C: Percentile-Based Capping
- Calculate daily/monthly usage percentiles
- Auto-throttle users above 90th percentile
- Requires background job for percentile calculation

---

**Action required**: Please clarify the scope before I proceed with implementation steps.
