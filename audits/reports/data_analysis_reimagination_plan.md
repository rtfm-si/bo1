# Data Analysis Reimagination - Implementation Plan

## Vision

Transform the data analysis feature from a statistics dashboard into an **objective-driven insight engine** that:
1. Understands the user's business goals (from Context)
2. Evaluates dataset relevance to those goals
3. Generates actionable insights aligned with objectives
4. Guides users from data to decisions through conversation

---

## Part 1: Business Context Integration

### 1.1 Connect to Existing Context

The user's business context lives at `/context/overview`. We need to:

**Fetch at analysis time:**
```typescript
interface BusinessContext {
  northStarGoal: string;           // "Increase MRR by 30%"
  objectives: Objective[];          // Current business objectives
  kpis: KPI[];                      // Target metrics
  industry: string;                 // For benchmarking
  businessModel: string;            // SaaS, e-commerce, etc.
  targetMarket: string;
  challenges: string[];             // Current pain points
}
```

**Surface in analysis:**
- Show active objectives when analyzing data
- Filter insights by relevance to goals
- Warn if dataset doesn't serve any objective

### 1.2 Dataset Relevance Assessment

Before generating insights, the LLM should evaluate:

```
RELEVANCE ASSESSMENT PROMPT:

Given:
- User's North Star: {north_star_goal}
- Current Objectives: {objectives}
- Dataset columns: {columns}
- Dataset sample: {sample_rows}

Evaluate:
1. RELEVANCE SCORE (0-100): How useful is this data for the objectives?
2. RELEVANT OBJECTIVES: Which specific objectives can this data inform?
3. MISSING DATA: What additional data would strengthen the analysis?
4. RECOMMENDED FOCUS: What questions should we prioritize?

Output JSON:
{
  "relevance_score": 75,
  "relevant_objectives": ["Reduce customer churn", "Increase AOV"],
  "irrelevant_objectives": ["Expand to new markets"],
  "missing_data_suggestions": [
    "Customer acquisition date would enable cohort analysis",
    "Product category would reveal churn patterns by segment"
  ],
  "recommended_questions": [
    "Which customer segments have highest churn risk?",
    "What purchase patterns predict retention?"
  ],
  "dataset_purpose": "This data can help identify churn indicators and optimize for customer lifetime value."
}
```

### 1.3 Objective-Focused Analysis

Each insight should map to an objective:

```
CURRENT: "Baskets drive 31% of sales volume"

PROPOSED: "🎯 Relevant to: Increase Revenue by 20%

           Baskets drive 31% of sales volume but only 18% of revenue.
           Art & Sculpture contributes 22% of revenue from just 12% of transactions.

           → Opportunity: Shift marketing spend toward Art & Sculpture
             to accelerate revenue goal without increasing transaction volume."
```

---

## Part 2: New User Journey

### 2.1 Upload Page: Two Entry Points

The upload page offers two paths:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                                                         │    │
│  │           📁 Drop your CSV here                         │    │
│  │                                                         │    │
│  │           or click to browse                            │    │
│  │                                                         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ─────────────────────── OR ───────────────────────             │
│                                                                  │
│  🎯 Not sure what data you need?                                │
│                                                                  │
│  Select an objective to see what data would help:               │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ○ Increase MRR by 30%                                   │    │
│  │ ○ Reduce customer churn to < 5%                         │    │
│  │ ○ Expand to European markets                            │    │
│  │ ○ North Star: Reach $1M ARR                             │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  [What data do I need for this?]                                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 "What Data Do I Need?" Flow

When user selects an objective and clicks the button:

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  📊 To analyze "Reduce customer churn to < 5%"                  │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  ESSENTIAL DATA                                                  │
│  These columns are required for meaningful churn analysis:       │
│                                                                  │
│  ✓ Customer identifier (ID, email, account number)              │
│  ✓ Activity/purchase dates (to identify lapsed customers)       │
│  ✓ Status indicator (active, churned) OR last activity date     │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  VALUABLE ADDITIONS                                              │
│  These would strengthen the analysis:                            │
│                                                                  │
│  + Product/plan type (reveals which products have higher churn) │
│  + Customer tenure (identifies at-risk periods)                 │
│  + Support ticket count (predicts dissatisfaction)              │
│  + Usage metrics (engagement signals)                           │
│  + Revenue per customer (prioritize high-value retention)       │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  WHERE TO FIND THIS DATA                                         │
│                                                                  │
│  • CRM export (Salesforce, HubSpot, Pipedrive)                  │
│  • Subscription platform (Stripe, Chargebee, Recurly)           │
│  • Product analytics (Mixpanel, Amplitude, Heap)                │
│  • Support system (Zendesk, Intercom)                           │
│                                                                  │
│  ─────────────────────────────────────────────────────────────  │
│                                                                  │
│  [I have this data - Upload now]  [Check another objective]     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

If user clicks "Upload now", they're taken to upload with the objective pre-selected, triggering **Objective-Focused Mode**.

### 2.3 Two Analysis Modes

| Mode | Triggered When | Behavior |
|------|----------------|----------|
| **Objective-Focused** | High relevance (70+) OR user pre-selected objective | Insights tagged to objectives, recommendations specific to goals |
| **Open Exploration** | Low relevance OR no context OR user chooses to explore anyway | General patterns, anomalies, "what's interesting here", no objective tagging |

Both modes run the same technical analysis. The difference is how insights are framed.

### 2.4 Journey Map

```
UPLOAD PAGE
│
├─── Path A: "I have data" ──────────────────────────────────────┐
│    User drops CSV                                               │
│                                                                 │
└─── Path B: "What data do I need?" ─────────────────────────────┤
     User selects objective                                       │
     → Sees data requirements                                     │
     → Uploads with objective pre-selected                        │
                                                                  │
                                ↓                                 │
┌─────────────────────────────────────────────────────────────────┐
│ ANALYSIS                                                         │
│ "Analyzing your data..."                                         │
│ - Fetch business context                                         │
│ - Run relevance assessment                                       │
│ - Run statistical analysis (hidden)                              │
│ - Determine analysis mode                                        │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ RELEVANCE NOTICE (non-blocking, informational only)              │
│                                                                  │
│ HIGH RELEVANCE (70+):                                           │
│ → Badge: "85% aligned with your objectives"                      │
│ → Proceed to Objective-Focused Data Story                        │
│                                                                  │
│ MEDIUM RELEVANCE (40-69):                                       │
│ → Notice: "This data partially addresses your objectives"        │
│ → Shows which objectives match, which don't                      │
│ → Suggests what additional data would help                       │
│ → User always proceeds to analysis                               │
│                                                                  │
│ LOW RELEVANCE (<40):                                            │
│ → Notice: "This data doesn't directly address your objectives"   │
│ → "I'll analyze it openly and surface what's interesting"        │
│ → Suggests what data would address objectives                    │
│ → Proceed to Open Exploration Data Story                         │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ DATA STORY                                                       │
│                                                                  │
│ OBJECTIVE-FOCUSED MODE:                                          │
│ "Based on your goal to [North Star], here's what this reveals:" │
│ 🎯 [Objective 1]: [Insight aligned to this objective]           │
│ 🎯 [Objective 2]: [Insight aligned to this objective]           │
│                                                                  │
│ OPEN EXPLORATION MODE:                                           │
│ "Here's what stands out in your data:"                          │
│ 💡 [Interesting pattern 1]                                       │
│ 💡 [Interesting pattern 2]                                       │
│ 📊 [Key metrics and distributions]                               │
│                                                                  │
│ BOTH MODES INCLUDE:                                              │
│ ⚠️  Data Quality: [Issues that affect reliability]               │
│ 💡 Unexpected Finding: [Something worth investigating]           │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ CONVERSATION                                                     │
│ "What would you like to explore?"                                │
│                                                                  │
│ OBJECTIVE-FOCUSED: Questions derived from objectives + data      │
│ OPEN EXPLORATION: Questions about patterns, outliers, segments   │
│                                                                  │
│ [Free-form input always available]                               │
└─────────────────────────────────────────────────────────────────┘
                                ↓
┌─────────────────────────────────────────────────────────────────┐
│ INSIGHT → ACTION                                                 │
│ Each insight offers:                                             │
│ - [Add to Report]                                                │
│ - [Create Task] → Links to objectives/OKRs (if relevant)         │
│ - [Share with Board] → Decision meeting                          │
│ - [Dig Deeper]                                                   │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 Relevance Notice Examples

**High Relevance (non-blocking, just informational):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ✓ 85% aligned with your objectives                              │
│                                                                  │
│ This data is well-suited to analyze:                            │
│ • Reduce customer churn (strong match)                          │
│ • Increase MRR (partial match)                                  │
└─────────────────────────────────────────────────────────────────┘
```

**Medium Relevance (informative, suggests improvements):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ℹ️ 52% aligned with your objectives                              │
│                                                                  │
│ This data can help with:                                        │
│ ✓ Increase MRR - revenue patterns visible                       │
│                                                                  │
│ Limited insight available for:                                  │
│ ○ Reduce churn - missing customer activity dates                │
│                                                                  │
│ To strengthen churn analysis, add: last_purchase_date,          │
│ customer_status columns                                          │
│                                                                  │
│ [Continue with analysis]                                         │
└─────────────────────────────────────────────────────────────────┘
```

**Low Relevance (honest, but never blocking):**
```
┌─────────────────────────────────────────────────────────────────┐
│ ℹ️ About this analysis                                           │
│                                                                  │
│ This dataset has limited relevance to your current objectives.  │
│ I'll analyze it openly and surface what's interesting.          │
│                                                                  │
│ What this data CAN tell you:                                    │
│ • Product sales patterns                                        │
│ • Revenue distribution                                          │
│ • Category performance                                          │
│                                                                  │
│ For insights about "Reduce Churn", you'd need:                  │
│ • Customer identifiers                                          │
│ • Purchase/activity dates                                       │
│ • Customer status indicators                                    │
│                                                                  │
│ [Continue with open exploration]                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 2.6 No-Context Fallback

If user hasn't set up business context:

```
┌─────────────────────────────────────────────────────────────────┐
│ 💡 Get More Relevant Insights                                    │
│                                                                  │
│ I can analyze this data, but I'll give you better insights      │
│ if I know what you're trying to achieve.                        │
│                                                                  │
│ [Set up business context] [Analyze anyway]                      │
│                                                                  │
│ Quick setup - just tell me:                                     │
│ ┌─────────────────────────────────────────────────────────┐     │
│ │ What's your main business goal right now?               │     │
│ └─────────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘
```

---

## Part 3: UI/UX Specification

### 3.1 New Page Structure

**Route:** `/advisor/analyze` (upload) → `/datasets/[id]` (analysis)

```
┌─────────────────────────────────────────────────────────────────┐
│ HEADER                                                           │
│ [Dataset Name] [Relevance Badge: 85% aligned] [⚙️ Advanced]     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ OBJECTIVE BAR (collapsible)                                      │
│ 🎯 Analyzing for: Increase MRR 30% | Reduce Churn < 5%          │
│ [Change objectives]                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                                                                  │
│  YOUR DATA STORY                                                 │
│  ═══════════════                                                 │
│                                                                  │
│  [AI-generated narrative with objective tags]                    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ 🎯 Reduce Churn                                         │    │
│  │                                                         │    │
│  │ Your data shows 3 clear churn predictors:              │    │
│  │ • Customers with <2 purchases in 90 days: 4x churn     │    │
│  │ • Jewelry-only buyers: 2.5x more likely to lapse       │    │
│  │ • No purchase in category "Baskets": 1.8x churn        │    │
│  │                                                         │    │
│  │ [CHART: Churn probability by segment]                  │    │
│  │                                                         │    │
│  │ → Recommendation: Target jewelry buyers with basket    │    │
│  │   cross-sell within 30 days of first purchase          │    │
│  │                                                         │    │
│  │ [Add to Report] [Create Action] [Explore More]         │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │ ⚠️ Data Quality Notice                                  │    │
│  │                                                         │    │
│  │ 512 duplicate transactions detected (29%)              │    │
│  │ This may inflate your volume metrics.                  │    │
│  │                                                         │    │
│  │ [Review & Fix] [Analyze Anyway] [Ignore]               │    │
│  └─────────────────────────────────────────────────────────┘    │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ CONVERSATION                                                     │
│                                                                  │
│ ┌─────────────────────────────────────────────────────────┐     │
│ │ Ask anything about your data...                         │     │
│ └─────────────────────────────────────────────────────────┘     │
│                                                                  │
│ Suggested (based on your objectives):                           │
│ [Which customers should I prioritize to hit MRR goal?]          │
│ [What's causing the churn in jewelry segment?]                  │
│ [How do I cross-sell baskets to jewelry buyers?]                │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ REPORT PANEL (slide-out from right)                              │
│                                                                  │
│ Your Report                                          [Export ▼] │
│ ────────────                                                     │
│ □ Churn predictor analysis                                      │
│ □ Revenue by category breakdown                                 │
│ □ Recommended actions                                           │
│                                                                  │
│ [Generate Executive Summary]                                    │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Component Breakdown

| Component | Purpose | New/Modified |
|-----------|---------|--------------|
| `DataRequirementsPanel.svelte` | "What data do I need?" for selected objective | NEW |
| `ObjectiveSelector.svelte` | Select objective on upload page | NEW |
| `ObjectiveBar.svelte` | Show active objectives on analysis page | NEW |
| `RelevanceNotice.svelte` | Non-blocking relevance info, never gates | NEW |
| `DataStory.svelte` | AI narrative (objective-focused or open exploration) | NEW |
| `InsightCard.svelte` | Single insight with actions | NEW |
| `DataQualityNotice.svelte` | Actionable data issues | NEW |
| `ConversationPanel.svelte` | Elevated chat, mode-aware suggestions | MODIFIED |
| `ReportBuilder.svelte` | Collect insights, export | NEW |
| `AdvancedAnalysis.svelte` | Current Analyse tab content, hidden by default | MODIFIED |

### 3.3 Advanced Mode

Toggle in header: `[⚙️ Advanced]`

When enabled, adds:
- Full statistical breakdown (current Analyse tab)
- Column explorer with distributions
- Raw data preview with filtering
- Custom chart builder
- Query interface

---

## Part 4: Backend Architecture

### 4.1 New Endpoints

```python
# Data Requirements API (for "What Data Do I Need?" feature)

GET /api/v1/objectives/{id}/data-requirements
"""
Returns data requirements for analyzing a specific objective.
Called from upload page when user selects an objective.
"""
Response: {
    "objective": {
        "id": "obj_123",
        "name": "Reduce customer churn to < 5%",
        "current_value": "8%",
        "target_value": "5%"
    },
    "requirements": {
        "essential": [
            {
                "name": "Customer identifier",
                "description": "Unique ID, email, or account number",
                "example_columns": ["customer_id", "user_id", "email", "account_number"],
                "why_needed": "To track individual customer behavior over time"
            },
            {
                "name": "Activity dates",
                "description": "When customers took actions (purchases, logins, etc.)",
                "example_columns": ["purchase_date", "last_login", "activity_date"],
                "why_needed": "To identify lapsed customers and calculate churn"
            },
            {
                "name": "Status indicator",
                "description": "Whether customer is active, churned, or at-risk",
                "example_columns": ["status", "is_active", "churned_date"],
                "why_needed": "To label and predict churn outcomes"
            }
        ],
        "valuable_additions": [
            {
                "name": "Product/plan type",
                "description": "What the customer purchased or subscribed to",
                "insight_unlocked": "Reveals which products have higher churn rates"
            },
            {
                "name": "Customer tenure",
                "description": "How long they've been a customer",
                "insight_unlocked": "Identifies at-risk periods in customer lifecycle"
            },
            {
                "name": "Support interactions",
                "description": "Ticket count, resolution times, satisfaction scores",
                "insight_unlocked": "Predicts churn from support dissatisfaction"
            }
        ],
        "data_sources": [
            {
                "name": "CRM",
                "examples": ["Salesforce", "HubSpot", "Pipedrive"],
                "typical_columns": ["customer_id", "status", "created_date"]
            },
            {
                "name": "Subscription platform",
                "examples": ["Stripe", "Chargebee", "Recurly"],
                "typical_columns": ["subscription_status", "mrr", "churn_date"]
            }
        ]
    }
}


GET /api/v1/objectives/data-requirements
"""
Returns data requirements for all active objectives.
Used to show overview of what data would help across all goals.
"""
Response: {
    "objectives": [
        { "id": "obj_123", "name": "...", "requirements_summary": "..." },
        ...
    ]
}


# Dataset Analysis API

POST /api/v1/datasets/{id}/analyze
"""
Triggers full analysis pipeline.
Returns job_id for polling.
"""
Request: {
    "include_context": true,           # Fetch business context
    "objective_id": "obj_123",         # Optional: pre-selected objective (from "What Data Do I Need?" flow)
    "force_mode": "objective_focused"  # Optional: "objective_focused" | "open_exploration" | null (auto-detect)
}
Response: {
    "job_id": "analysis_abc123",
    "status": "processing",
    "analysis_mode": "objective_focused"  # or "open_exploration"
}


GET /api/v1/datasets/{id}/analysis
"""
Returns analysis results including relevance assessment and data story.
"""
Response: {
    "relevance": {
        "score": 85,
        "relevant_objectives": [...],
        "missing_data_suggestions": [...],
        "recommended_questions": [...]
    },
    "data_story": {
        "summary": "...",
        "insights": [
            {
                "id": "insight_1",
                "objective_id": "obj_123",
                "objective_name": "Reduce Churn",
                "headline": "3 clear churn predictors identified",
                "narrative": "...",
                "chart": { "type": "bar", "config": {...} },
                "recommendations": [...],
                "confidence": 0.85
            }
        ],
        "data_quality_issues": [...],
        "unexpected_findings": [...]
    },
    "technical_analysis": {
        // Current Analyse tab content - for advanced mode
        "column_profiles": [...],
        "correlations": [...],
        "outliers": [...],
        // etc.
    }
}


POST /api/v1/datasets/{id}/question
"""
Ask a question, receives objective-aware response.
"""
Request: {
    "question": "Which customers should I focus on?",
    "conversation_id": "conv_123",  # Optional: continue conversation
    "include_chart": true
}
Response: {
    "answer": {
        "narrative": "...",
        "chart": { "type": "...", "config": {...} },
        "relevant_objectives": ["obj_123"],
        "follow_up_questions": [...],
        "actions": [
            { "type": "add_to_report", "label": "Add to Report" },
            { "type": "create_task", "label": "Create Action Item" }
        ]
    },
    "conversation_id": "conv_123"
}


POST /api/v1/datasets/{id}/fix
"""
Apply data cleaning action.
"""
Request: {
    "action": "remove_duplicates",
    "config": { "keep": "first" }
}
Response: {
    "rows_affected": 512,
    "new_row_count": 1263,
    "reanalysis_required": true
}


POST /api/v1/datasets/{id}/report
"""
Generate exportable report.
"""
Request: {
    "insight_ids": ["insight_1", "insight_2"],
    "include_executive_summary": true,
    "format": "pdf"  # or "markdown", "slides"
}
Response: {
    "report_url": "/reports/report_abc123.pdf",
    "expires_at": "..."
}
```

### 4.2 Analysis Pipeline

```python
# bo1/analysis/pipeline.py

class DatasetAnalysisPipeline:
    """
    Orchestrates the full analysis flow.
    """

    async def analyze(self, dataset_id: str, user_id: str) -> AnalysisResult:
        # 1. Fetch business context
        context = await self.fetch_business_context(user_id)

        # 2. Load and profile dataset
        df = await self.load_dataset(dataset_id)
        profile = await self.generate_profile(df)

        # 3. Assess relevance to objectives
        relevance = await self.assess_relevance(
            profile=profile,
            objectives=context.objectives,
            north_star=context.north_star_goal
        )

        # 4. Generate objective-aligned insights
        insights = await self.generate_insights(
            profile=profile,
            context=context,
            relevance=relevance
        )

        # 5. Compile data story
        story = await self.compile_data_story(
            insights=insights,
            relevance=relevance,
            data_quality=profile.quality_issues
        )

        return AnalysisResult(
            relevance=relevance,
            data_story=story,
            technical_analysis=profile,
            insights=insights
        )
```

### 4.3 LLM Integration Points

| Step | LLM Role | Input | Output |
|------|----------|-------|--------|
| Relevance Assessment | Evaluate dataset-objective fit | Columns, sample, objectives | Score, matches, gaps |
| Insight Generation | Find objective-relevant patterns | Profile, context | Narrative insights |
| Data Story | Synthesize into narrative | All insights | Structured story |
| Question Answering | Respond to user queries | Question, profile, context | Answer with chart |
| Report Summary | Generate executive summary | Selected insights | Summary narrative |

---

## Part 5: Prompt Engineering

### 5.0 Data Requirements Generation Prompt

```markdown
# Data Requirements for Objective Analysis

## Your Role
You are a data analyst helping a business user understand what data they need to collect to analyze progress toward a specific objective.

## The Objective
**Name:** {objective_name}
**Description:** {objective_description}
**Target:** {target_value}
**Current:** {current_value}
**Industry:** {industry}
**Business Model:** {business_model}

## Your Task
Generate a comprehensive guide for what data would be needed to meaningfully analyze this objective.

Think about:
1. What metrics directly measure progress toward this objective?
2. What dimensions would allow segmentation and deeper analysis?
3. What temporal data is needed to track trends?
4. What contextual data would explain the "why" behind the numbers?

## Output Format
Return JSON:
{
    "objective_summary": "<1 sentence restating what we're trying to analyze>",
    "essential_data": [
        {
            "name": "<data type name>",
            "description": "<what this data represents>",
            "example_columns": ["<column_name_1>", "<column_name_2>"],
            "why_essential": "<why analysis fails without this>",
            "questions_answered": ["<what questions this enables>"]
        }
    ],
    "valuable_additions": [
        {
            "name": "<data type name>",
            "description": "<what this data represents>",
            "insight_unlocked": "<what additional insight this provides>",
            "priority": "high|medium|low"
        }
    ],
    "data_sources": [
        {
            "source_type": "<CRM|Analytics|Billing|Support|etc>",
            "example_tools": ["<Tool1>", "<Tool2>"],
            "typical_export_name": "<common export/report name>",
            "columns_typically_included": ["<col1>", "<col2>"]
        }
    ],
    "analysis_preview": "<2-3 sentences describing what kind of insights would be possible with this data>"
}

## Important
- Be specific to the objective, not generic
- Use industry-appropriate terminology
- Suggest realistic, commonly available data sources
- Prioritize actionability over comprehensiveness
```

### 5.1 Relevance Assessment Prompt

```markdown
# Dataset Relevance Assessment

## Your Role
You are a business analyst evaluating whether a dataset can help achieve specific business objectives.

## Business Context
**North Star Goal:** {north_star_goal}

**Current Objectives:**
{for obj in objectives}
- {obj.name}: {obj.description} (Target: {obj.target}, Current: {obj.current})
{/for}

**Industry:** {industry}
**Business Model:** {business_model}

## Dataset Information
**Name:** {dataset_name}
**Columns:** {columns_with_types}
**Row Count:** {row_count}
**Sample Data:**
{sample_rows}

## Your Task
Evaluate how well this dataset can inform progress toward the stated objectives.

Consider:
1. Does the data contain metrics that map to the KPIs?
2. Can we derive insights that directly inform decisions?
3. What's missing that would strengthen the analysis?
4. What questions can we definitively answer vs. only speculate on?

## Output Format
Return JSON:
{
    "relevance_score": <0-100>,
    "assessment_summary": "<2-3 sentences on overall fit>",
    "objective_matches": [
        {
            "objective_id": "<id>",
            "relevance": "high|medium|low|none",
            "explanation": "<why this data helps or doesn't>",
            "answerable_questions": ["<questions we CAN answer>"],
            "unanswerable_questions": ["<questions we CANNOT answer>"]
        }
    ],
    "missing_data": [
        {
            "data_needed": "<what's missing>",
            "why_valuable": "<how it would help>",
            "objectives_unlocked": ["<which objectives it would serve>"]
        }
    ],
    "recommended_focus": "<where to focus the analysis given limitations>"
}
```

### 5.2 Insight Generation Prompt

```markdown
# Objective-Aligned Insight Generation

## Your Role
You are a business analyst generating insights that help achieve specific objectives. Every insight must connect to a business goal.

## Business Context
{business_context}

## Relevant Objectives for This Dataset
{relevant_objectives}

## Dataset Analysis
**Statistical Profile:**
{column_profiles}

**Key Patterns Found:**
- Correlations: {correlations}
- Outliers: {outliers}
- Distributions: {distributions}
- Segments: {segments}

**Data Quality:**
{quality_issues}

## Your Task
Generate 3-5 insights that:
1. Directly address the relevant objectives
2. Are actionable (user can do something with this)
3. Are supported by the data (not speculation)
4. Include a recommended visualization

## Output Format
Return JSON array:
[
    {
        "objective_id": "<linked objective>",
        "headline": "<10 words max, the key finding>",
        "narrative": "<2-4 sentences explaining the insight in business terms>",
        "supporting_data": {
            "metric": "<key number>",
            "comparison": "<vs what>",
            "confidence": "<high|medium|low>"
        },
        "visualization": {
            "type": "bar|line|scatter|pie",
            "x_axis": "<column>",
            "y_axis": "<column>",
            "group_by": "<column or null>",
            "title": "<chart title>"
        },
        "recommendation": "<specific action to take>",
        "follow_up_questions": ["<what to explore next>"]
    }
]

## Important
- NO jargon (don't say "correlation coefficient", say "strong relationship")
- NO hedging (don't say "might", say what the data shows)
- ALWAYS connect to business impact
- If data quality issues affect an insight, say so
```

### 5.3 Data Story Synthesis Prompt

```markdown
# Data Story Synthesis

## Your Role
You are a business storyteller who transforms analytical findings into a compelling narrative for decision-makers.

## Inputs
**Business Context:** {context}
**Relevance Assessment:** {relevance}
**Generated Insights:** {insights}
**Data Quality Issues:** {quality_issues}

## Your Task
Create a "Data Story" that:
1. Opens with the most important finding relative to the North Star goal
2. Groups insights by objective
3. Acknowledges data limitations honestly
4. Ends with clear next steps

## Output Format
{
    "opening_hook": "<1 sentence that captures attention, references North Star>",
    "objective_sections": [
        {
            "objective_id": "<id>",
            "objective_name": "<name>",
            "summary": "<2-3 sentences synthesizing insights for this objective>",
            "insight_ids": ["<which insights belong here>"],
            "key_metric": "<the most important number>",
            "recommended_action": "<what to do>"
        }
    ],
    "data_quality_summary": "<honest assessment of data limitations>",
    "unexpected_finding": {
        "headline": "<something interesting not in objectives>",
        "narrative": "<why it might matter>",
        "should_investigate": true|false
    },
    "next_steps": [
        "<prioritized action 1>",
        "<prioritized action 2>",
        "<prioritized action 3>"
    ],
    "suggested_questions": [
        "<question derived from objectives + data>"
    ]
}
```

### 5.4 Conversation Response Prompt

```markdown
# Data Conversation Response

## Your Role
You are a helpful data analyst having a conversation about a dataset. You answer questions clearly and always connect back to business objectives when relevant.

## Context
**Business Objectives:** {objectives}
**Dataset Profile:** {profile}
**Previous Conversation:** {conversation_history}
**Available Columns:** {columns}

## User Question
{question}

## Your Task
Answer the question:
1. In plain business language (no statistical jargon)
2. With supporting data/numbers
3. With a visualization if it helps
4. Connected to relevant objectives
5. With suggested follow-up questions

## Response Format
{
    "answer_narrative": "<your response in markdown>",
    "key_finding": "<1 sentence summary>",
    "supporting_data": [
        {"label": "<what>", "value": "<number>", "context": "<vs what>"}
    ],
    "visualization": {
        "type": "<chart type>",
        "config": { ... },
        "title": "<title>",
        "insight_callout": "<what to notice in the chart>"
    } | null,
    "relevant_objectives": ["<objective_ids this relates to>"],
    "follow_up_questions": [
        "<natural next question 1>",
        "<natural next question 2>"
    ],
    "confidence": "high|medium|low",
    "caveats": ["<any limitations to this answer>"]
}
```

---

## Part 6: Data Model Changes

### 6.1 New Tables

```sql
-- Store analysis results for caching/history
CREATE TABLE dataset_analyses (
    id UUID PRIMARY KEY,
    dataset_id UUID REFERENCES datasets(id),
    user_id UUID REFERENCES users(id),

    -- Relevance assessment
    relevance_score INTEGER,
    relevance_assessment JSONB,

    -- Generated content
    data_story JSONB,
    insights JSONB,
    technical_analysis JSONB,

    -- Context snapshot (what objectives were active)
    context_snapshot JSONB,

    -- Metadata
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP,  -- For cache invalidation

    UNIQUE(dataset_id, user_id)
);

-- Store user reports
CREATE TABLE dataset_reports (
    id UUID PRIMARY KEY,
    dataset_id UUID REFERENCES datasets(id),
    user_id UUID REFERENCES users(id),

    title VARCHAR(255),
    insight_ids JSONB,  -- Array of insight IDs included
    executive_summary TEXT,

    -- Export info
    format VARCHAR(20),  -- pdf, markdown, slides
    file_url TEXT,

    created_at TIMESTAMP DEFAULT NOW()
);

-- Link insights to objectives for tracking
CREATE TABLE insight_objective_links (
    insight_id UUID,
    objective_id UUID REFERENCES objectives(id),
    relevance_score INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),

    PRIMARY KEY (insight_id, objective_id)
);
```

### 6.2 Modified Tables

```sql
-- Add to datasets table
ALTER TABLE datasets ADD COLUMN
    last_analysis_id UUID REFERENCES dataset_analyses(id);

-- Add to conversations table (for dataset chat)
ALTER TABLE conversations ADD COLUMN
    dataset_id UUID REFERENCES datasets(id);
ALTER TABLE conversations ADD COLUMN
    context_snapshot JSONB;  -- Business context at conversation time
```

---

## Part 7: Implementation Phases

### Phase 1: Foundation (Week 1-2)

**Goal:** Core infrastructure without UI changes

- [ ] Create `dataset_analyses` table and model
- [ ] Build `DatasetAnalysisPipeline` class
- [ ] Implement data requirements generation prompt + endpoint (`/objectives/{id}/data-requirements`)
- [ ] Implement relevance assessment prompt + endpoint
- [ ] Implement insight generation prompt (both objective-focused and open exploration modes)
- [ ] Implement data story synthesis prompt + endpoint
- [ ] Add business context fetching to analysis flow
- [ ] Add analysis mode detection (objective-focused vs open exploration)
- [ ] Write tests for all new endpoints

**Deliverable:** API returns objective-aligned analysis OR open exploration analysis (testable via API)

### Phase 2: Upload Page Enhancement (Week 3)

**Goal:** Add "What Data Do I Need?" feature to upload page

- [ ] Create `ObjectiveSelector.svelte` component
- [ ] Create `DataRequirementsPanel.svelte` component
- [ ] Modify upload page layout with two entry points
- [ ] Connect to `/objectives/{id}/data-requirements` endpoint
- [ ] Add objective pre-selection flow (upload with objective context)
- [ ] Test full "select objective → see requirements → upload" flow

**Deliverable:** Users can discover what data they need before uploading

### Phase 3: Analysis Page Redesign (Week 4)

**Goal:** Replace current tabs with new Story view

- [ ] Create `DataStory.svelte` component (supporting both analysis modes)
- [ ] Create `InsightCard.svelte` component
- [ ] Create `ObjectiveBar.svelte` component
- [ ] Create `RelevanceNotice.svelte` component (non-blocking, informational)
- [ ] Modify dataset page to show Story instead of tabs
- [ ] Hide current tabs behind "Advanced Mode" toggle
- [ ] Connect new components to new API endpoints

**Deliverable:** Users see Data Story on dataset page (objective-focused or open exploration)

### Phase 4: Conversation Elevation (Week 5)

**Goal:** Make chat the primary interaction

- [ ] Elevate `ConversationPanel` from footer to main panel
- [ ] Add mode-aware suggested questions (objective-focused vs open exploration)
- [ ] Implement inline chart generation in responses
- [ ] Add "Add to Report" action on responses
- [ ] Add conversation history sidebar

**Deliverable:** Full conversational analysis experience

### Phase 5: Data Quality Actions (Week 6)

**Goal:** Actionable data cleaning

- [ ] Create `DataQualityNotice.svelte` component
- [ ] Implement `/datasets/{id}/fix` endpoint
- [ ] Add duplicate removal action
- [ ] Add null handling actions
- [ ] Add "re-analyze after fix" flow

**Deliverable:** Users can fix data issues in-context

### Phase 6: Report Builder (Week 7)

**Goal:** Export insights

- [ ] Create `ReportBuilder.svelte` slide-out panel
- [ ] Implement insight selection/collection
- [ ] Implement executive summary generation
- [ ] Implement PDF export
- [ ] Implement markdown export

**Deliverable:** Users can export analysis reports

### Phase 7: Polish & Advanced Mode (Week 8-9)

**Goal:** Refinement and power user features

- [ ] Polish all UI components
- [ ] Implement full Advanced Mode (current Analyse tab content)
- [ ] Add raw data preview with filtering
- [ ] Add custom chart builder
- [ ] Performance optimization
- [ ] Error handling and edge cases
- [ ] Documentation

**Deliverable:** Production-ready feature

---

## Part 8: Success Metrics

### User Metrics
- Time from upload to first insight viewed
- Number of follow-up questions asked
- Report generation rate
- Return usage rate

### Quality Metrics
- Relevance score accuracy (user feedback)
- Insight actionability rating
- Data story clarity rating

### Business Metrics
- Feature adoption rate
- Conversion to paid (if applicable)
- Support ticket reduction for data analysis

---

## Part 9: Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| LLM generates irrelevant insights | High | Strong prompts + relevance filtering + confidence scores |
| Slow analysis for large datasets | Medium | Background processing + progressive loading |
| Users have no business context set up | Medium | Graceful fallback + in-context quick setup |
| Data quality issues skew insights | High | Prominent warnings + fix-first flow option |
| Over-reliance on LLM accuracy | High | Show confidence levels + "Show the math" option |

---

## Part 10: Files to Create/Modify

### New Files

```
frontend/src/lib/components/datasets/
├── DataStory.svelte
├── InsightCard.svelte
├── ObjectiveBar.svelte
├── RelevanceNotice.svelte
├── DataQualityNotice.svelte
├── ReportBuilder.svelte
└── AdvancedAnalysis.svelte

frontend/src/lib/components/upload/
├── ObjectiveSelector.svelte
└── DataRequirementsPanel.svelte

backend/api/routes/
├── dataset_analysis.py
└── objective_data_requirements.py

bo1/analysis/
├── pipeline.py
├── relevance.py
├── insights.py
├── story.py
├── data_requirements.py
└── prompts/
    ├── data_requirements.py
    ├── relevance_assessment.py
    ├── insight_generation.py
    ├── story_synthesis.py
    └── conversation.py
```

### Modified Files

```
frontend/src/routes/advisor/analyze/+page.svelte  # Upload page with two entry points
frontend/src/routes/datasets/[id]/+page.svelte  # New layout with Data Story
frontend/src/lib/components/chat/ConversationPanel.svelte  # Elevated + mode-aware
backend/api/main.py  # New routes
bo1/models/dataset.py  # New fields
bo1/models/objective.py  # Data requirements methods
```

---

## Appendix A: Example User Flow

**Scenario:** Sarah uploads sales data, has objective "Increase Q1 Revenue by 20%"

1. **Upload:** Sarah drops `q4_sales.csv`

2. **Analysis runs:**
   - Fetches her objectives
   - Assesses relevance: 78% - good fit for revenue goal
   - Generates insights focused on revenue drivers

3. **Data Story appears:**
   ```
   🎯 Relevant to: Increase Q1 Revenue by 20%

   Your Q4 data reveals a clear path to your Q1 goal:

   Premium products (Art & Sculpture) drove 40% of Q4 revenue
   from just 15% of transactions. If you increase premium
   product visibility by 25%, you could hit your Q1 target
   with current traffic levels.

   [Chart: Revenue contribution by category]

   ⚠️ Note: 12% of transactions have missing category data.
   This may understate premium product performance.

   → Recommended: Run a premium product spotlight campaign
     in January targeting your existing customer base.
   ```

4. **Sarah asks:** "Which customers buy premium products?"

5. **AI responds:**
   ```
   Your premium buyers have a clear profile:

   • 73% made a non-premium purchase first
   • Average 45 days between first purchase and premium purchase
   • Most common first category: Baskets (62%)

   [Chart: Customer journey to premium]

   This suggests your basket buyers are your best premium
   prospects. Consider a "basket → art" email sequence
   30 days after first purchase.

   🎯 This directly supports your Q1 revenue goal.

   [Add to Report] [Create Campaign Task]
   ```

6. **Sarah adds insight to report, exports PDF for team meeting**

---

## Appendix B: Handling Dataset-Objective Misalignment

When a dataset has low relevance to user objectives:

### Option 1: Suggest Alternative Uses
```
This sales data doesn't directly address your objective
"Expand to European markets" - there's no geographic data.

However, this data could help you:
• Identify your best-selling products (for market entry strategy)
• Understand customer purchasing patterns
• Optimize pricing before expansion

[Analyze for these insights] [Upload different data]
```

### Option 2: Suggest Missing Data
```
To analyze European expansion, you'd need:
• Customer location/country data
• Shipping destination information
• Currency of transactions

Do you have access to this data?
[Yes, I'll upload it] [No, analyze what I have]
```

### Option 3: Prompt for Context Update
```
Your current objectives don't match this data well.

This looks like operational sales data. Should we:
• Add "Improve operational efficiency" as an objective?
• Analyze anyway without objective alignment?
• Help you upload data that matches your objectives?
```

---

## Summary

This plan transforms the data analysis feature from **"here are your stats"** to **"here's what your data means for your goals"**.

Key shifts:
1. **Objective-first:** Every insight connects to user goals
2. **Conversation-first:** Chat is the primary interface, not tabs
3. **LLM as translator:** Technical analysis hidden, business narrative surfaced
4. **Honest about gaps:** Clear when data can't answer questions
5. **Action-oriented:** Every insight has a "what to do next"

The result: novices get guided insights, power users get depth on demand, and everyone gets analysis that matters to their actual business objectives.
