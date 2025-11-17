# Admin Dashboard Specification - Board of One v2

**Version**: 1.0
**Date**: 2025-11-14
**Status**: Technical Specification
**Author**: Product & Engineering Team

---

## Overview

This document specifies the admin dashboard requirements for Board of One v2 web interface, including real-time session monitoring, AI usage analytics, and user engagement metrics.

**Key Requirements**:
1. Monitor active sessions (longest running, highest cost)
2. Kill runaway/expensive sessions with one click
3. Track AI costs by phase, plan tier, and time period
4. Measure user engagement (DAU, sessions/user, completion rate, retention)
5. Calculate revenue margins by plan tier

---

## 1. Real-Time Session Monitoring

### 1.1 Active Sessions Dashboard

**URL**: `/admin/sessions`

**Features**:
- Top 10 longest running sessions
- Top 10 highest cost sessions
- Real-time updates (5-second polling)
- Filter by plan tier
- Sort by duration or cost
- One-click kill with confirmation

**Table Columns**:
| Column | Data | Format | Flags |
|--------|------|--------|-------|
| User | Email + User ID | `user@example.com` `(user_123)` | - |
| Plan | Tier badge | `FREE` `PRO` `ENTERPRISE` | Color-coded |
| Problem | Title (truncated) | Max 50 chars | - |
| Duration | HH:MM:SS | `00:45:23` | ⚠️ if >2x median |
| Cost | USD | `$0.125` | 💰 if >90th %ile |
| Phase | Current phase | `Round 3 (3/10)` | - |
| Actions | Kill button | Red button | Confirmation modal |

**Summary Stats** (top of page):
- Total active sessions
- Runaway count (>2x median duration)
- Expensive count (>90th percentile cost)
- Total active cost

### 1.2 Runaway Detection

**Runaway Session Criteria**:
- Duration > 2x median duration (last 30 days)
- OR: Cost > 90th percentile (last 30 days)
- OR: Stuck in same phase for >10 minutes

**Visual Indicators**:
- Yellow row highlight
- ⚠️ Warning icon
- "Runaway" badge

**Auto-Actions** (optional, configurable):
- Send alert to admin Slack channel
- Email notification to admin
- Auto-kill after 2 hours (with user notification)

### 1.3 Kill Session Modal

**Confirmation Dialog**:
```
Kill Session?

User: john@example.com (Pro Plan)
Problem: Should we invest $500K...
Duration: 01:23:45
Cost: $0.245

This will:
- Terminate the session immediately
- Preserve checkpoint (user can inspect)
- Notify user via email
- Log termination in audit trail

Reason (required):
[Dropdown: Runaway | High Cost | User Request | System Maintenance | Other]

[Text area for notes]

[ Cancel ]  [ Kill Session ]
```

**Audit Trail**:
```json
{
  "session_id": "bo1_abc123",
  "killed_by": "admin_user_456",
  "killed_at": "2025-11-14T15:30:00Z",
  "reason": "runaway",
  "notes": "Session stuck in Round 5 for 45 minutes",
  "user_notified": true
}
```

---

## 2. AI Usage Analytics

### 2.1 Cost Analytics Dashboard

**URL**: `/admin/analytics/costs`

**Time Range Selector**:
- Last 24 Hours (hourly breakdown)
- Last 7 Days (daily breakdown)
- Last 30 Days (weekly breakdown)
- Custom Date Range

**Summary Cards**:
| Metric | Format | Description |
|--------|--------|-------------|
| Total AI Cost | `$1,234.56` | Sum of all AI costs in period |
| Total Sessions | `3,456` | Number of completed sessions |
| Avg Cost/Session | `$0.357` | Total cost / total sessions |
| Cost vs Budget | `42% of $3,000` | Budget utilization |

### 2.2 Cost by Phase (Pie Chart)

**Phases Tracked**:
1. **Problem Decomposition** - Initial problem breakdown
2. **Persona Selection** - LLM-based expert matching
3. **Initial Round** (Round 0) - All personas contribute
4. **Round 1 Deliberation** - Facilitator + 1-2 personas
5. **Round 2 Deliberation** - Continue discussion
6. **Round 3-15 Deliberation** - Additional rounds
7. **Moderator Interventions** - Contrarian/Skeptic/Optimist
8. **Voting** - Vote collection + calibration
9. **Final Synthesis** - Recommendation generation
10. **Research** - Internal/external knowledge retrieval

**Chart**:
- Interactive pie chart (Chart.js or Recharts)
- Click slice to drill down
- Show % of total cost
- Color-coded by phase type (setup, deliberation, synthesis)

### 2.3 Cost by Plan Tier (Bar Chart)

**Tiers**:
- Free (0-3 sessions/month, basic personas)
- Pro ($29/month, unlimited sessions, advanced personas)
- Enterprise (custom pricing, white-label, API access)

**Metrics per Tier**:
| Tier | Sessions | Total Cost | Avg Cost | Revenue | Margin % |
|------|----------|------------|----------|---------|----------|
| Free | 1,234 | $123.45 | $0.100 | $0 | -100% |
| Pro | 5,678 | $890.12 | $0.157 | $4,350 | 79.5% |
| Enterprise | 123 | $234.56 | $1.907 | $3,000 | 92.2% |

**Margin Calculation**:
```
Margin % = ((Revenue - AI Cost) / Revenue) * 100
```

**Insights**:
- Flag negative margin tiers (Free tier expected)
- Highlight high-margin tiers (Enterprise)
- Show cost per active user

### 2.4 Cost Over Time (Line Chart)

**X-Axis**: Time period (hour, day, week)
**Y-Axis**: Cost (USD)

**Lines**:
- Total cost
- By tier (Free, Pro, Enterprise) - stacked area chart
- Cost target/budget (dashed line)

**Annotations**:
- Spikes (hover to see cause: new feature launch, promo, bug)
- Budget threshold crossings

### 2.5 Detailed Phase Breakdown Table

| Phase | Total Cost | % of Total | Sessions | Avg per Session | Model |
|-------|------------|------------|----------|-----------------|-------|
| Problem Decomposition | $45.67 | 5.2% | 1,234 | $0.037 | Sonnet 4.5 |
| Persona Selection | $23.45 | 2.7% | 1,234 | $0.019 | Sonnet 4.5 |
| Initial Round | $234.56 | 26.8% | 1,234 | $0.190 | Sonnet 4.5 |
| Round 1 Deliberation | $178.90 | 20.4% | 1,100 | $0.163 | Sonnet 4.5 |
| Round 2 Deliberation | $145.23 | 16.6% | 890 | $0.163 | Sonnet 4.5 |
| ... | ... | ... | ... | ... | ... |
| **Total** | **$875.45** | **100%** | **1,234** | **$0.710** | - |

**Sortable Columns**: Click to sort by cost, % of total, or avg per session

**Drill-Down**: Click phase to see:
- Cost breakdown by model (Sonnet vs Haiku)
- Token usage (input, output, cached)
- Sessions using this phase
- Cost trend over time

---

## 3. User Engagement Metrics

### 3.1 Engagement Dashboard

**URL**: `/admin/analytics/engagement`

**Summary Cards**:
| Metric | Value | Change | Description |
|--------|-------|--------|-------------|
| Active Users (7d) | 1,234 | +12% ↗ | Unique users with sessions in last 7 days |
| Total Sessions | 5,678 | +8% ↗ | All sessions in time period |
| Completion Rate | 78.5% | -2% ↘ | % of sessions reaching synthesis |
| Avg Sessions/User | 4.6 | +5% ↗ | Sessions per active user |

### 3.2 Daily Active Users (DAU) Trend

**Chart**: Line chart, last 30 days

**Metrics**:
- DAU (daily active users)
- 7-day moving average (smooth trend)
- WAU (weekly active users) - secondary axis
- MAU (monthly active users) - annotation

**Goal Lines**:
- Target DAU (configurable)
- Previous period comparison (dotted line)

### 3.3 Engagement by Plan Tier

**Table**:
| Tier | Active Users | Sessions | Avg Sessions/User | Completion Rate | Avg Duration | Revenue |
|------|--------------|----------|-------------------|-----------------|--------------|---------|
| Free | 456 | 789 | 1.7 | 65.2% | 8m 23s | $0 |
| Pro | 678 | 3,456 | 5.1 | 82.3% | 12m 45s | $19,662 |
| Enterprise | 100 | 1,433 | 14.3 | 91.7% | 18m 12s | $5,000 |

**Insights**:
- Free users: Lower engagement (1.7 sessions/user vs 5.1 for Pro)
- Enterprise users: Highest completion rate (91.7%)
- Pro tier: Sweet spot (5.1 sessions/user, 82.3% completion)

**Actions**:
- Upsell Free → Pro (highlight engagement boost)
- Retain Pro users (high engagement, good revenue)
- White-glove Enterprise (high value, critical success)

### 3.4 Feature Usage (Top 10)

**Table**:
| Feature | Total Usage | Unique Users | Avg per User | Adoption % |
|---------|-------------|--------------|--------------|------------|
| Multi-round deliberation | 4,567 | 1,123 | 4.1 | 91.0% |
| Moderator interventions | 2,345 | 678 | 3.5 | 55.0% |
| Research integration | 1,234 | 456 | 2.7 | 37.0% |
| Time travel (rewind) | 789 | 234 | 3.4 | 19.0% |
| Pause/resume session | 567 | 123 | 4.6 | 10.0% |
| Export to PDF | 456 | 234 | 1.9 | 19.0% |
| Share deliberation | 234 | 123 | 1.9 | 10.0% |
| Custom personas | 123 | 45 | 2.7 | 3.6% |
| API access | 89 | 12 | 7.4 | 1.0% |
| Integrations (Slack, etc) | 45 | 8 | 5.6 | 0.6% |

**Insights**:
- High adoption: Multi-round (91%), Moderators (55%)
- Medium adoption: Research (37%), Time travel (19%)
- Low adoption: Pause/resume (10%), Custom personas (3.6%)

**Actions**:
- Promote low-adoption features (tutorials, tooltips)
- Deprecate unused features (<1% adoption after 3 months)
- Invest in high-adoption features (polish, expand)

### 3.5 Retention Cohort Analysis

**Cohort Matrix** (Weekly cohorts):

| Signup Week | Week 0 | Week 1 | Week 2 | Week 3 | Week 4 |
|-------------|--------|--------|--------|--------|--------|
| 2025-W45 | 100% | 45% | 32% | 28% | 25% |
| 2025-W46 | 100% | 52% | 38% | 31% | - |
| 2025-W47 | 100% | 48% | 35% | - | - |
| 2025-W48 | 100% | 50% | - | - | - |
| 2025-W49 | 100% | - | - | - | - |

**Color Scale**: Green (>40%) → Yellow (20-40%) → Red (<20%)

**Metrics**:
- Week 1 retention: 45-52% (target: >50%)
- Week 4 retention: 25% (target: >30%)
- Trend: Improving (W46 better than W45)

**Actions**:
- Improve onboarding (boost Week 1 retention)
- Engagement campaigns (email, in-app) at Week 2
- Feature discovery (tooltips, tutorials)

---

## 4. Backend Implementation

### 4.1 API Endpoints

```python
# GET /api/admin/sessions/active
# Returns: list[ActiveSession]
# Includes: user, plan, duration, cost, percentile, flags

# POST /api/admin/sessions/{session_id}/kill
# Body: { reason: str, notes: str }
# Returns: { status: "killed", session_id: str }

# GET /api/admin/analytics/costs
# Query params: range (day|week|month)
# Returns: { phase_costs, tier_costs, time_series, summary }

# GET /api/admin/analytics/engagement
# Query params: range (day|week|month)
# Returns: { tier_stats, dau_trend, feature_usage, retention_cohorts, summary }
```

### 4.2 Database Schema

```sql
-- Session metrics (main analytics table)
CREATE TABLE session_metrics (
    session_id VARCHAR(100) PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    plan_tier VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    total_cost DECIMAL(10, 6) NOT NULL,
    total_tokens INTEGER NOT NULL,
    metrics_json JSONB NOT NULL,  -- { phase_costs: {...}, total_cost: 0.5, ... }
    phase_metrics_json JSONB,     -- [{ phase, node, cost, tokens, ... }, ...]
    INDEX idx_user_created (user_id, created_at),
    INDEX idx_tier_created (plan_tier, created_at),
    INDEX idx_status_created (status, created_at)
);

-- Feature usage tracking
CREATE TABLE feature_usage (
    id SERIAL PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    session_id VARCHAR(100),
    feature_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    INDEX idx_user_feature (user_id, feature_name),
    INDEX idx_feature_date (feature_name, created_at)
);

-- Materialized view for fast percentile queries
CREATE MATERIALIZED VIEW session_cost_percentiles AS
SELECT
    DATE_TRUNC('day', created_at) as date,
    plan_tier,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY total_cost) as p50_cost,
    PERCENTILE_CONT(0.9) WITHIN GROUP (ORDER BY total_cost) as p90_cost,
    PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY total_cost) as p95_cost,
    PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY total_cost) as p99_cost,
    PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY
        EXTRACT(EPOCH FROM (completed_at - created_at))) as p50_duration,
    AVG(total_cost) as avg_cost,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration,
    COUNT(*) as session_count
FROM session_metrics
WHERE status = 'completed'
AND created_at >= NOW() - INTERVAL '90 days'
GROUP BY date, plan_tier;

-- Refresh daily (cron job)
CREATE INDEX idx_percentiles_date ON session_cost_percentiles (date, plan_tier);
```

### 4.3 Cost Tracking in Graph Nodes

```python
# bo1/graph/nodes.py
async def decompose_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Track cost for problem decomposition phase."""

    start_time = datetime.now()

    # Call decomposer
    sub_problems, llm_response = await decomposer.decompose(state["problem"])

    duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

    # Initialize phase costs if not exists
    if "phase_costs" not in state["metrics"]:
        state["metrics"]["phase_costs"] = {}

    # Aggregate cost for this phase
    state["metrics"]["phase_costs"]["problem_decomposition"] = llm_response.cost_total

    # Detailed metrics for analytics
    if "phase_metrics" not in state:
        state["phase_metrics"] = []

    state["phase_metrics"].append({
        "phase": "problem_decomposition",
        "node": "decompose",
        "model": llm_response.model,
        "input_tokens": llm_response.token_usage.input_tokens,
        "output_tokens": llm_response.token_usage.output_tokens,
        "cache_read_tokens": llm_response.token_usage.cache_read_tokens,
        "cache_creation_tokens": llm_response.token_usage.cache_creation_tokens,
        "cost": llm_response.cost_total,
        "duration_ms": duration_ms,
        "timestamp": datetime.now().isoformat()
    })

    return state

async def persona_contribute_node(state: DeliberationGraphState) -> DeliberationGraphState:
    """Track cost per round (Round 1, Round 2, etc.)."""

    round_number = state["round_number"]
    phase_key = f"round_{round_number}_deliberation"

    # ... call persona ...

    # Aggregate cost for this round
    if phase_key not in state["metrics"]["phase_costs"]:
        state["metrics"]["phase_costs"][phase_key] = 0.0

    state["metrics"]["phase_costs"][phase_key] += llm_response.cost_total

    # Detailed metrics
    state["phase_metrics"].append({
        "phase": phase_key,
        "node": "persona_contribute",
        "persona_code": speaker_code,
        "persona_name": speaker_name,
        "round": round_number,
        "model": llm_response.model,
        "cost": llm_response.cost_total,
        # ... other metrics ...
    })

    return state
```

### 4.4 Real-Time Updates (WebSocket Alternative)

For admin dashboard, use **Server-Sent Events (SSE)** for simplicity:

```python
# backend/api/admin.py
from fastapi.responses import StreamingResponse
import asyncio

@router.get("/sessions/active/stream")
async def stream_active_sessions(
    admin_id: str = Depends(require_admin_role)
):
    """Stream active session updates via SSE."""

    async def event_generator():
        while True:
            # Fetch current active sessions
            sessions = await get_active_sessions()

            # Send as SSE event
            yield f"data: {json.dumps(sessions)}\n\n"

            # Wait 5 seconds
            await asyncio.sleep(5)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream"
    )
```

**Frontend** (SvelteKit):
```typescript
onMount(() => {
  const eventSource = new EventSource('/api/admin/sessions/active/stream');

  eventSource.onmessage = (event) => {
    sessions = JSON.parse(event.data);
  };

  return () => eventSource.close();
});
```

---

## 5. UI/UX Design

### 5.1 Color Scheme

**Plan Tier Badges**:
- Free: `#e3f2fd` background, `#1565c0` text (light blue)
- Pro: `#f3e5f5` background, `#6a1b9a` text (light purple)
- Enterprise: `#e8f5e9` background, `#2e7d32` text (light green)

**Status Indicators**:
- Normal: `#4caf50` (green)
- Warning (runaway): `#ff9800` (orange)
- Critical (expensive): `#f44336` (red)

### 5.2 Responsive Design

- Desktop (>1200px): Full table view, side-by-side charts
- Tablet (768-1200px): Stacked charts, scrollable tables
- Mobile (<768px): Card view, accordion sections

### 5.3 Accessibility

- WCAG 2.1 AA compliance
- Keyboard navigation (Tab, Enter, Escape)
- Screen reader support (ARIA labels)
- Color contrast ratio >4.5:1
- Focus indicators on interactive elements

---

## 6. ntfy.sh Notification System

### 6.1 Overview

**ntfy.sh** is a simple HTTP-based pub/sub notification service. Perfect for real-time admin alerts without complex infrastructure.

**Why ntfy.sh?**
- ✅ Zero setup (no server required)
- ✅ Self-hosted option available
- ✅ HTTP-based (simple `POST` requests)
- ✅ Multi-platform (iOS, Android, Desktop, Web)
- ✅ Priority levels, tags, actions
- ✅ Free tier generous (no auth required)

**Topics Used**:
- `bo1_runaway_sessions` - Runaway/expensive session alerts
- `bo1_cost_reports` - Daily/weekly cost summaries
- `bo1_user_acquisition` - New user signups, milestones
- `bo1_system_health` - Errors, performance issues, deployment status

### 6.2 Runaway Session Alerts

**Trigger**: When session exceeds thresholds:
- Duration >2x median (last 30 days)
- Cost >90th percentile
- Stuck in same phase >10 minutes

**Alert Format**:
```
🚨 Runaway Session Detected

User: john@example.com (Pro)
Session: bo1_abc123
Duration: 01:45:23 (2.3x median)
Cost: $0.456 (95th percentile)
Phase: Round 5 (stuck for 12 minutes)

[View Session] [Kill Session]
```

**Implementation**:
```python
# bo1/notifications/ntfy.py
import httpx
from datetime import datetime

NTFY_SERVER = "https://ntfy.sh"
RUNAWAY_TOPIC = "bo1_runaway_sessions"

async def send_runaway_alert(session: dict) -> None:
    """Send runaway session alert to ntfy.sh."""

    message = (
        f"🚨 Runaway Session Detected\n\n"
        f"User: {session['user_email']} ({session['plan_tier'].upper()})\n"
        f"Session: {session['session_id']}\n"
        f"Duration: {format_duration(session['duration_seconds'])} "
        f"({session['duration_vs_median']:.1f}x median)\n"
        f"Cost: ${session['total_cost']:.3f} ({session['cost_percentile']}th percentile)\n"
        f"Phase: {session['current_phase']} (stuck for {session['phase_duration_minutes']} min)"
    )

    # Add action buttons
    base_url = "https://admin.boardof.one"
    actions = [
        {
            "action": "view",
            "label": "View Session",
            "url": f"{base_url}/admin/sessions?highlight={session['session_id']}"
        },
        {
            "action": "http",
            "label": "Kill Session",
            "url": f"{base_url}/api/admin/sessions/{session['session_id']}/kill",
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {session['admin_api_key']}"
            },
            "body": json.dumps({"reason": "runaway_auto_kill"})
        }
    ]

    async with httpx.AsyncClient() as client:
        await client.post(
            f"{NTFY_SERVER}/{RUNAWAY_TOPIC}",
            headers={
                "Title": "Runaway Session Alert",
                "Priority": "urgent",  # High priority (notification sound)
                "Tags": "warning,money_with_wings",  # Emoji tags
                "Click": f"{base_url}/admin/sessions",
                "Actions": json.dumps(actions)
            },
            data=message.encode('utf-8')
        )

# Call from session monitoring loop
async def monitor_active_sessions():
    """Background task: Check for runaway sessions every 60 seconds."""

    while True:
        sessions = await get_active_sessions()

        for session in sessions:
            if session["is_runaway"] and not session.get("alerted"):
                # Send alert
                await send_runaway_alert(session)

                # Mark as alerted (don't spam)
                redis.hset(f"session:{session['session_id']}:meta", "alerted", "true")

        await asyncio.sleep(60)  # Check every minute
```

**Priority Levels**:
- `max` (5): Critical runaway (>3x median, >$1 cost)
- `urgent` (4): High runaway (>2x median, >90th percentile)
- `high` (3): Medium runaway (stuck in phase >10 min)

### 6.3 Daily Cost Reports

**Schedule**: Every day at 9:00 AM UTC (cron job)

**Report Format**:
```
📊 Daily Cost Report - Nov 14, 2025

💰 Total Cost: $234.56 (+12% vs yesterday)
📈 Sessions: 1,234 (+8%)
💵 Avg/Session: $0.190 (-3%)

By Tier:
  Free: $12.34 (87 sessions)
  Pro: $189.23 (989 sessions)
  Enterprise: $32.99 (158 sessions)

Top Phases:
  1. Initial Round: $67.89 (29%)
  2. Round 1: $45.67 (19%)
  3. Synthesis: $34.56 (15%)

🎯 Budget Status: 42% of monthly ($3,000)

[View Dashboard]
```

**Implementation**:
```python
# bo1/jobs/daily_cost_report.py
from datetime import datetime, timedelta

async def send_daily_cost_report():
    """Generate and send daily cost report."""

    # Get yesterday's data
    yesterday = datetime.now() - timedelta(days=1)
    stats = await get_cost_stats(
        start=yesterday.replace(hour=0, minute=0, second=0),
        end=yesterday.replace(hour=23, minute=59, second=59)
    )

    # Get previous day for comparison
    day_before = yesterday - timedelta(days=1)
    prev_stats = await get_cost_stats(
        start=day_before.replace(hour=0, minute=0, second=0),
        end=day_before.replace(hour=23, minute=59, second=59)
    )

    # Calculate changes
    cost_change = ((stats["total_cost"] - prev_stats["total_cost"]) /
                   prev_stats["total_cost"] * 100)
    session_change = ((stats["total_sessions"] - prev_stats["total_sessions"]) /
                      prev_stats["total_sessions"] * 100)

    message = (
        f"📊 Daily Cost Report - {yesterday.strftime('%b %d, %Y')}\n\n"
        f"💰 Total Cost: ${stats['total_cost']:.2f} "
        f"({cost_change:+.0f}% vs yesterday)\n"
        f"📈 Sessions: {stats['total_sessions']} "
        f"({session_change:+.0f}%)\n"
        f"💵 Avg/Session: ${stats['avg_cost_per_session']:.3f}\n\n"
        f"By Tier:\n"
    )

    for tier, tier_stats in stats["by_tier"].items():
        message += (
            f"  {tier.capitalize()}: ${tier_stats['cost']:.2f} "
            f"({tier_stats['sessions']} sessions)\n"
        )

    message += f"\nTop Phases:\n"
    for i, (phase, cost) in enumerate(stats["top_phases"][:3], 1):
        pct = (cost / stats['total_cost']) * 100
        message += f"  {i}. {phase}: ${cost:.2f} ({pct:.0f}%)\n"

    # Budget tracking
    monthly_budget = 3000  # Configurable
    month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
    month_cost = await get_cost_stats(start=month_start, end=datetime.now())
    budget_pct = (month_cost["total_cost"] / monthly_budget) * 100

    message += f"\n🎯 Budget Status: {budget_pct:.0f}% of monthly (${monthly_budget:,})"

    await send_ntfy(
        topic="bo1_cost_reports",
        title="Daily Cost Report",
        message=message,
        priority="default",
        tags="chart_with_upwards_trend,money_bag",
        click_url="https://admin.boardof.one/admin/analytics/costs"
    )

# Schedule with cron or APScheduler
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()
scheduler.add_job(
    send_daily_cost_report,
    'cron',
    hour=9,
    minute=0,
    timezone='UTC'
)
scheduler.start()
```

### 6.4 Weekly Cost Summaries

**Schedule**: Every Monday at 9:00 AM UTC

**Report Format**:
```
📊 Weekly Cost Summary - Week 46, 2025

💰 Total: $1,234.56 (last 7 days)
📈 Sessions: 5,678
📊 Avg/Session: $0.217

Week-over-Week:
  Cost: +15% 📈
  Sessions: +12% 📈
  Avg/Session: +3% 📈

Top Spenders (by tier):
  Enterprise: $456.78 (37%)
  Pro: $678.90 (55%)
  Free: $98.88 (8%)

Insights:
  ✅ Margin improved: Pro tier up 5%
  ⚠️ Free tier cost growing (limit usage?)
  📈 Enterprise adoption up 20%

Monthly Projection: $5,234 (over budget!)

[View Dashboard] [Download CSV]
```

**Implementation**:
```python
async def send_weekly_cost_summary():
    """Generate and send weekly cost summary."""

    # Get last 7 days
    end = datetime.now()
    start = end - timedelta(days=7)
    stats = await get_cost_stats(start=start, end=end)

    # Get previous week for comparison
    prev_end = start
    prev_start = prev_end - timedelta(days=7)
    prev_stats = await get_cost_stats(start=prev_start, end=prev_end)

    # Calculate changes
    cost_change = ((stats["total_cost"] - prev_stats["total_cost"]) /
                   prev_stats["total_cost"] * 100)

    # Generate insights
    insights = []
    for tier in ["free", "pro", "enterprise"]:
        tier_margin = calculate_margin(tier, stats)
        prev_margin = calculate_margin(tier, prev_stats)
        if tier_margin > prev_margin + 5:
            insights.append(f"✅ Margin improved: {tier.capitalize()} tier up {tier_margin - prev_margin:.0f}%")

    # Monthly projection
    days_in_month = 30
    daily_avg = stats["total_cost"] / 7
    monthly_projection = daily_avg * days_in_month

    message = build_weekly_summary_message(stats, prev_stats, insights, monthly_projection)

    await send_ntfy(
        topic="bo1_cost_reports",
        title=f"Weekly Summary - Week {datetime.now().strftime('%U, %Y')}",
        message=message,
        priority="default",
        tags="calendar,chart_with_upwards_trend",
        actions=[
            {
                "action": "view",
                "label": "View Dashboard",
                "url": "https://admin.boardof.one/admin/analytics/costs?range=week"
            },
            {
                "action": "http",
                "label": "Download CSV",
                "url": "https://admin.boardof.one/api/admin/analytics/export?range=week&format=csv"
            }
        ]
    )
```

### 6.5 User Acquisition Alerts

**Triggers**:
- New user signup
- Milestone reached (100, 500, 1000, 5000, 10000 users)
- First paid conversion (Free → Pro)
- Enterprise signup

**Alert Formats**:

**New User Signup**:
```
🎉 New User Signup

Email: alice@startup.com
Plan: Free
Source: organic_search
Signup via: Google OAuth

Total Users: 1,234 (+1)

[View User Profile]
```

**Milestone Reached**:
```
🎊 User Milestone: 1,000 Users!

Total Signups: 1,000
Active (7d): 456 (45.6%)
Paid: 123 (12.3%)

Growth:
  This Week: +67 users
  Last Week: +54 users
  Acceleration: +24% 📈

[View Dashboard]
```

**First Paid Conversion**:
```
💰 First Paid Conversion!

User: alice@startup.com
Plan: Free → Pro ($29/mo)
Time to Convert: 3 days
Sessions Before Convert: 5

MRR Impact: +$29
Total MRR: $1,234

[View User Journey]
```

**Implementation**:
```python
# bo1/notifications/user_acquisition.py

async def send_signup_alert(user: dict):
    """Send alert when new user signs up."""

    total_users = await get_total_user_count()

    message = (
        f"🎉 New User Signup\n\n"
        f"Email: {user['email']}\n"
        f"Plan: {user['plan_tier'].capitalize()}\n"
        f"Source: {user['signup_source']}\n"
        f"Signup via: {user['auth_method']}\n\n"
        f"Total Users: {total_users:,} (+1)"
    )

    await send_ntfy(
        topic="bo1_user_acquisition",
        title="New User Signup",
        message=message,
        priority="low",  # Don't spam for every signup
        tags="tada,bust_in_silhouette",
        click_url=f"https://admin.boardof.one/admin/users/{user['id']}"
    )

    # Check for milestones
    if total_users in [100, 500, 1000, 5000, 10000]:
        await send_milestone_alert(total_users)

async def send_milestone_alert(user_count: int):
    """Send alert when user milestone reached."""

    stats = await get_user_stats()

    message = (
        f"🎊 User Milestone: {user_count:,} Users!\n\n"
        f"Total Signups: {user_count:,}\n"
        f"Active (7d): {stats['active_7d']} ({stats['active_7d_pct']:.1f}%)\n"
        f"Paid: {stats['paid_users']} ({stats['paid_pct']:.1f}%)\n\n"
        f"Growth:\n"
        f"  This Week: +{stats['growth_this_week']} users\n"
        f"  Last Week: +{stats['growth_last_week']} users\n"
        f"  Acceleration: {stats['growth_acceleration']:+.0f}% 📈"
    )

    await send_ntfy(
        topic="bo1_user_acquisition",
        title=f"Milestone: {user_count:,} Users!",
        message=message,
        priority="high",  # Important milestone
        tags="partying_face,trophy",
        click_url="https://admin.boardof.one/admin/analytics/engagement"
    )

async def send_conversion_alert(user: dict, plan_change: dict):
    """Send alert when user upgrades to paid plan."""

    conversion_time_days = (
        datetime.now() - user['created_at']
    ).days

    mrr_delta = calculate_mrr_delta(plan_change["from"], plan_change["to"])
    total_mrr = await get_total_mrr()

    message = (
        f"💰 Paid Conversion!\n\n"
        f"User: {user['email']}\n"
        f"Plan: {plan_change['from'].capitalize()} → {plan_change['to'].upper()}\n"
        f"Time to Convert: {conversion_time_days} days\n"
        f"Sessions Before Convert: {user['session_count']}\n\n"
        f"MRR Impact: +${mrr_delta}\n"
        f"Total MRR: ${total_mrr:,}"
    )

    await send_ntfy(
        topic="bo1_user_acquisition",
        title="Paid Conversion!",
        message=message,
        priority="high",  # Revenue event
        tags="money_bag,rocket",
        click_url=f"https://admin.boardof.one/admin/users/{user['id']}/journey"
    )
```

### 6.6 System Health Alerts

**Triggers**:
- Error rate spike (>5% of requests)
- Performance degradation (p95 latency >2s)
- Service downtime (health check fails)
- Deployment status (success/failure)
- Database issues (connection pool exhausted)

**Alert Format**:
```
🚨 Error Rate Spike

Current: 12.5% (last 5 min)
Normal: 1.2% baseline
Threshold: 5%

Top Errors:
  1. OpenAI timeout (45 errors)
  2. Redis connection (23 errors)
  3. Invalid session state (12 errors)

[View Logs] [View Metrics]
```

**Implementation**:
```python
# bo1/monitoring/health.py

async def check_error_rate():
    """Monitor error rate and alert if spike detected."""

    current_rate = await get_error_rate(minutes=5)
    baseline_rate = await get_error_rate(hours=24)
    threshold = 0.05  # 5%

    if current_rate > threshold and current_rate > baseline_rate * 3:
        top_errors = await get_top_errors(limit=3)

        message = (
            f"🚨 Error Rate Spike\n\n"
            f"Current: {current_rate * 100:.1f}% (last 5 min)\n"
            f"Normal: {baseline_rate * 100:.1f}% baseline\n"
            f"Threshold: {threshold * 100:.0f}%\n\n"
            f"Top Errors:\n"
        )

        for i, error in enumerate(top_errors, 1):
            message += f"  {i}. {error['type']} ({error['count']} errors)\n"

        await send_ntfy(
            topic="bo1_system_health",
            title="Error Rate Spike!",
            message=message,
            priority="urgent",
            tags="rotating_light,warning",
            actions=[
                {"action": "view", "label": "View Logs",
                 "url": "https://admin.boardof.one/admin/logs"},
                {"action": "view", "label": "View Metrics",
                 "url": "https://admin.boardof.one/admin/metrics"}
            ]
        )

async def send_deployment_alert(deployment: dict):
    """Send alert when deployment completes."""

    if deployment["status"] == "success":
        message = (
            f"✅ Deployment Successful\n\n"
            f"Version: {deployment['version']}\n"
            f"Environment: {deployment['env']}\n"
            f"Duration: {deployment['duration_seconds']}s\n"
            f"Deployed by: {deployment['deployed_by']}"
        )
        priority = "default"
        tags = "white_check_mark,rocket"
    else:
        message = (
            f"❌ Deployment Failed\n\n"
            f"Version: {deployment['version']}\n"
            f"Environment: {deployment['env']}\n"
            f"Error: {deployment['error']}\n"
            f"Rollback: {deployment['rollback_triggered']}"
        )
        priority = "urgent"
        tags = "x,warning"

    await send_ntfy(
        topic="bo1_system_health",
        title=f"Deployment {deployment['status'].upper()}",
        message=message,
        priority=priority,
        tags=tags
    )
```

### 6.7 Notification Configuration

**Environment Variables**:
```bash
# .env
NTFY_SERVER=https://ntfy.sh  # Or self-hosted: https://ntfy.example.com
NTFY_RUNAWAY_TOPIC=bo1_runaway_sessions
NTFY_COST_TOPIC=bo1_cost_reports
NTFY_ACQUISITION_TOPIC=bo1_user_acquisition
NTFY_HEALTH_TOPIC=bo1_system_health

# Optional: Authentication for self-hosted
NTFY_USERNAME=admin
NTFY_PASSWORD=your_secure_password

# Alert thresholds
RUNAWAY_DURATION_MULTIPLIER=2.0  # 2x median
RUNAWAY_COST_PERCENTILE=90       # 90th percentile
ERROR_RATE_THRESHOLD=0.05        # 5%
PERFORMANCE_LATENCY_THRESHOLD=2000  # 2 seconds (ms)
```

**Admin Settings UI** (`/admin/settings/notifications`):
```typescript
<form>
  <h2>ntfy.sh Notifications</h2>

  <label>
    <input type="checkbox" bind:checked={settings.runaway_alerts_enabled} />
    Runaway Session Alerts
  </label>

  <label>
    <input type="checkbox" bind:checked={settings.daily_cost_reports_enabled} />
    Daily Cost Reports (9:00 AM UTC)
  </label>

  <label>
    <input type="checkbox" bind:checked={settings.weekly_summaries_enabled} />
    Weekly Summaries (Monday 9:00 AM UTC)
  </label>

  <label>
    <input type="checkbox" bind:checked={settings.user_acquisition_alerts_enabled} />
    User Acquisition Alerts
  </label>

  <label>
    <input type="checkbox" bind:checked={settings.system_health_alerts_enabled} />
    System Health Alerts
  </label>

  <h3>Thresholds</h3>
  <label>
    Runaway Duration Multiplier:
    <input type="number" step="0.1" bind:value={settings.runaway_duration_multiplier} />
  </label>

  <label>
    Cost Percentile Threshold:
    <input type="number" bind:value={settings.runaway_cost_percentile} />
  </label>

  <button>Save Settings</button>
</form>
```

### 6.8 Subscribing to Notifications

**Web** (browser):
1. Visit `https://ntfy.sh/bo1_runaway_sessions`
2. Click "Subscribe"
3. Enable notifications in browser

**Mobile** (iOS/Android):
1. Install ntfy app
2. Add topic: `bo1_runaway_sessions`
3. Repeat for other topics

**Desktop**:
```bash
# Linux/Mac
ntfy subscribe bo1_runaway_sessions

# Or with authentication (self-hosted)
ntfy subscribe \
  --user admin \
  --password your_password \
  https://ntfy.example.com/bo1_runaway_sessions
```

**Email Forwarding**:
Configure ntfy to forward to email:
```bash
ntfy subscribe bo1_runaway_sessions \
  --cmd "sendmail admin@boardof.one"
```

### 6.9 Testing Notifications

**Test Endpoint**:
```python
@router.post("/admin/notifications/test")
async def test_notification(
    topic: str,
    admin_id: str = Depends(require_admin_role)
):
    """Send test notification to verify setup."""

    test_messages = {
        "runaway": "🧪 Test: Runaway session alert",
        "cost": "🧪 Test: Daily cost report",
        "acquisition": "🧪 Test: User acquisition alert",
        "health": "🧪 Test: System health alert"
    }

    await send_ntfy(
        topic=get_topic_name(topic),
        title="Test Notification",
        message=test_messages.get(topic, "Test message"),
        priority="low",
        tags="test_tube"
    )

    return {"status": "sent", "topic": topic}
```

**Admin UI Test Button**:
```typescript
<button onclick={() => testNotification('runaway')}>
  Test Runaway Alert
</button>
```

---

## 7. Implementation Timeline

**Week 10: Admin Backend (5 days)**
- [ ] Day 1-2: PostgreSQL schema + migrations
- [ ] Day 2-3: Admin API endpoints (sessions, analytics)
- [ ] Day 3-4: Cost tracking in graph nodes
- [ ] Day 4-5: SSE streaming + testing

**Week 11: Admin Frontend (5 days)**
- [ ] Day 1-2: Active sessions dashboard
- [ ] Day 2-3: Cost analytics dashboard (charts)
- [ ] Day 3-4: Engagement metrics dashboard
- [ ] Day 4-5: Polish, testing, deployment

**Total Effort**: 2 weeks (10 days) - 1 full-stack engineer

---

## 7. Success Metrics

**Admin Dashboard Usage**:
- Admins use dashboard daily (>5 days/week)
- Average session duration: >10 minutes (indicates engagement)
- Kill switch used: <5 sessions/week (runaway prevention working)

**Operational Impact**:
- Runaway sessions reduced by 80% (vs pre-dashboard)
- Cost anomalies detected within 1 hour
- User complaints about stuck sessions reduced by 90%

**Business Impact**:
- AI cost per session reduced by 15% (via optimization insights)
- Margin % increased by 10% (better tier pricing)
- Feature adoption increased by 25% (via engagement insights)

---

**Document Version**: 1.0
**Status**: Ready for Implementation
**Approval Required**: Product Manager, Engineering Lead
**Estimated Effort**: 2 weeks (1 full-stack engineer)
**Dependencies**: LangGraph migration (Weeks 1-9), PostgreSQL setup
