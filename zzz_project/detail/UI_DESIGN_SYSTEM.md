# Board of One (bo1) - UI Design System

**Modern Web Application Design Document**

**Version**: 2.0
**Date**: 2025-11-14
**Status**: Design Ready for Implementation
**Target Platforms**: SvelteKit 5 (Svelte 5 Runes)

All detail design docs are located in /zzz_project/detail/

**IMPORTANT**: Cost/token metrics are **admin-only**. End users see convergence, confidence, and quality metrics—NOT costs, tokens, or cache hit rates. This design document reflects the user-facing experience. For admin dashboard design, see PLATFORM_ARCHITECTURE.md.

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Design Principles](#2-design-principles)
3. [Information Architecture](#3-information-architecture)
4. [Page Hierarchy & User Flows](#4-page-hierarchy--user-flows)
5. [Component Catalogue](#5-component-catalogue)
6. [Interaction Patterns](#6-interaction-patterns)
7. [Visual System Guidelines](#7-visual-system-guidelines)
8. [Responsive & Accessibility](#8-responsive--accessibility)
9. [Wireframes](#9-wireframes)
10. [State Management & Data Flow](#10-state-management--data-flow)
11. [Technical Integration Points](#11-technical-integration-points)
12. [Implementation Phases](#12-implementation-phases)

---

## 1. Executive Summary

### 1.1 UX Vision

Board of One transforms complex decision-making from overwhelming to structured through AI-powered multi-perspective deliberation. The web UI must embody:

- **Clarity over complexity**: Progressive disclosure, show only what matters now
- **Speed & efficiency**: Minimal clicks, intelligent defaults, parallel loading
- **Transparency**: Full visibility into AI reasoning, costs, and process
- **User sovereignty**: System recommends, never directs—user controls every decision point
- **Delightful feedback**: Real-time updates, smooth animations, clear progress

### 1.2 Core User Flow (5-7 Phases)

```
Problem Input → Decomposition Review → Context Collection (conditional) →
Persona Selection → Live Deliberation → Voting & Synthesis → Export & Archive
```

**Time to Value**: 5-15 minutes from problem input to actionable recommendation
**Pricing**: Trial (£0, 2-3 deliberations), Core (£25/month), Pro (£50/month) - see PRICING_STRATEGY.md

### 1.3 Key Design Challenges Solved

| Challenge                     | Solution                                                                                   |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| Long deliberations (5-15 min) | Real-time progress, collapsible history, background processing                             |
| Quality transparency          | Convergence tracking, confidence levels, user-friendly metrics (NO cost data)              |
| Complex multi-agent output    | Chat-style contributions with color-coding, expandable reasoning                           |
| State management              | Auto-save, 24h sessions, resume from any phase                                             |
| Adaptive complexity           | UI scales from simple (2 personas, 2 sub-problems) to complex (5 personas, 8 sub-problems) |
| Dual-mode architecture        | Console (admin/debug) + Web (end users) with shared backend                                |

---

## 2. Design Principles

### 2.1 Declutter Aggressively

**Principle**: Only show what the user needs at THIS step.

**Implementation**:

- ✅ Use **progressive disclosure**: Hide advanced options behind "Advanced" accordions
- ✅ **Sticky context bar**: Show current phase, cost, round counter without full nav
- ✅ **Empty states**: Guide users with helpful CTAs when no data exists
- ✅ **Smart defaults**: Pre-select optimal configurations, allow override
- ✅ **Collapsible sections**: Hide completed phases, allow expand for review

**Anti-patterns to avoid**:

- ❌ Don't show full navigation when user is mid-deliberation
- ❌ Don't display all 45 personas—only show recommended + allow search
- ❌ Don't show raw JSON/technical details in main flow (hide in debug panel)

---

### 2.2 Prioritize Speed

**Principle**: Minimize clicks, reduce friction, provide instant feedback.

**Implementation**:

- ✅ **One-click approvals**: Default to "Continue" for common paths
- ✅ **Parallel loading**: Show contributions as they arrive (WebSocket/SSE)
- ✅ **Optimistic UI**: Update immediately, rollback on error
- ✅ **Keyboard shortcuts**: `Enter` to continue, `Cmd+K` for command palette
- ✅ **Auto-save**: Never ask "Save changes?" unless destructive

**Metrics**:

- Problem input → Decomposition: <10 seconds (with loading state)
- Approval clicks: Max 2-3 for entire flow
- Session resume: <2 seconds from dashboard

---

### 2.3 Modern Patterns

**Components to Use**:

- ✅ **Cards**: Sub-problem cards, persona cards, vote cards
- ✅ **Drawers**: Session details, persona profiles, debug metrics
- ✅ **Bottom sheets**: Quick actions, cost summary (mobile)
- ✅ **Sticky context bar**: Phase indicator + cost tracker (always visible)
- ✅ **Toasts**: Non-blocking success/error messages
- ✅ **Modals**: Destructive actions only (delete session, cancel deliberation)

**Layout Patterns**:

- ✅ **Centered content**: Max 1200px width for readability
- ✅ **Sidebar navigation**: Collapsible session list (desktop)
- ✅ **Tabs**: Switch between "Contributions", "Metrics", "Transcript"
- ✅ **Timeline**: Visualize deliberation rounds with branch points

---

### 2.4 System-Level Clarity

**States to Design**:

| State              | Component       | Message                                                               |
| ------------------ | --------------- | --------------------------------------------------------------------- |
| **Empty**          | Dashboard       | "No active sessions. Create your first deliberation." [+ New Session] |
| **Loading**        | Deliberation    | Skeleton contributions with shimmer, "Maria is analyzing..."          |
| **Error**          | LLM call failed | "AI service temporarily unavailable. Retrying (2/3)..." [Retry Now]   |
| **Success**        | Vote complete   | "All 5 experts have voted. Generating synthesis..." ✓                 |
| **Budget warning** | Cost tracker    | "⚠️ Session cost: $0.85 (85% of $1 budget)"                           |
| **Cache hit**      | Contribution    | "💾 Cached response (saved $0.02)"                                    |

**Error Recovery**:

- Auto-retry with exponential backoff (show retry count)
- Fallback to degraded mode (e.g., skip cache if unavailable)
- Allow manual intervention ("Skip this step", "Try different persona")

---

### 2.5 Accessibility (WCAG AA Minimum)

**Requirements**:

- ✅ **Keyboard navigation**: All actions accessible via Tab/Enter/Arrow keys
- ✅ **Screen reader support**: Semantic HTML, ARIA labels, live regions for updates
- ✅ **Color contrast**: 4.5:1 for text, 3:1 for UI components
- ✅ **Focus indicators**: Visible focus rings (not removed by CSS)
- ✅ **Motion controls**: Respect `prefers-reduced-motion` for animations
- ✅ **Text scaling**: Support up to 200% zoom without horizontal scroll

**Testing**:

- Use axe DevTools for automated checks
- Manual keyboard navigation testing
- Screen reader testing (NVDA/JAWS on Windows, VoiceOver on macOS/iOS)

---

### 2.6 Consistent Component Vocabulary

**Spacing Scale** (Tailwind-style):

```
xs: 4px   (tight elements, icon padding)
sm: 8px   (input padding, button padding)
md: 16px  (card padding, section spacing)
lg: 24px  (between major sections)
xl: 32px  (page margins)
2xl: 48px (hero sections, phase dividers)
```

**Type Scale**:

```
xs:   12px  (metadata, timestamps)
sm:   14px  (body text, labels)
base: 16px  (primary content)
lg:   18px  (subheadings)
xl:   24px  (section headings)
2xl:  32px  (page titles)
3xl:  48px  (hero text)
```

**Border Radius**:

```
sm: 4px   (buttons, inputs)
md: 8px   (cards, panels)
lg: 12px  (modals, drawers)
full: 9999px (pills, badges)
```

---

## 3. Information Architecture

### 3.1 Site Map

```
/ (Landing Page - Public)
  ├── /signup (Authentication - Supabase Social OAuth)
  ├── /login
  └── /auth/callback (OAuth callback)

/dashboard (Authenticated - User View)
  ├── /sessions
  │   ├── /new (Create New Session)
  │   ├── /[session_id] (Active Session)
  │   │   ├── /problem (Phase 1: Problem Input)
  │   │   ├── /decomposition (Phase 2: Review Sub-problems)
  │   │   ├── /context (Phase 3: Conditional Q&A)
  │   │   ├── /personas (Phase 4: Select Experts)
  │   │   ├── /deliberation (Phase 5: Live Discussion)
  │   │   ├── /synthesis (Phase 6: Final Report + Social Sharing)
  │   │   └── /actions (Phase 7: Action Tracking - see ACTION_TRACKING_FEATURE.md)
  │   └── /archived (View Past Sessions)
  ├── /personas (Browse Expert Library)
  ├── /settings
  │   ├── /profile (User profile, subscription)
  │   ├── /privacy (GDPR controls: export, delete, retention)
  │   └── /billing (Stripe subscription management)
  └── /help
      ├── /docs (User guide)
      └── /examples (Sample sessions)

/share/[token] (Public - Read-Only Synthesis Reports)

/admin (Authenticated - Admin Role Required)
  ├── /analytics (Cost metrics, token usage, cache hit rates)
  ├── /sessions (Inspect any session with full cost data)
  ├── /users (User management, anonymization)
  └── /logs (Audit logs)

/privacy-policy (Public)
/terms-of-service (Public)
```

### 3.2 Navigation Structure

**Primary Navigation** (Sidebar, desktop):

- Dashboard (home icon)
- Active Sessions (list icon, badge count)
- Personas (grid icon)
- Settings (gear icon)
- Help (question icon)

**Secondary Navigation** (Within session):

- **Stepper**: Shows 7 phases, highlights current
- **Breadcrumbs**: Dashboard > Session #1234 > Deliberation
- **Context Bar** (sticky top): Phase name, round counter, cost tracker

**No Navigation** (Immersive mode):

- During deliberation, hide sidebar (toggle with `Cmd+B`)
- Keep only context bar visible
- Show "Exit Deliberation" button

---

## 4. Page Hierarchy & User Flows

### 4.1 Dashboard (`/`)

**Purpose**: Launch new sessions, resume active, review archived.

**Layout**:

```
┌─────────────────────────────────────────────────────┐
│ [Sidebar]  │  Dashboard                             │
│            │                                         │
│ > Dashboard│  Welcome back, [User]!                 │
│  Sessions  │                                         │
│  Personas  │  [+ New Deliberation]  [View Examples] │
│  Settings  │                                         │
│  Help      │  ─────────────────────────────────     │
│            │  Active Sessions (2)                    │
│            │  ┌──────────────────────────────────┐  │
│            │  │ Session #1234                    │  │
│            │  │ "Should I pivot to law firms?"   │  │
│            │  │ Phase: Deliberation (Round 3/7)  │  │
│            │  │ Cost: $0.42 | 12 min ago         │  │
│            │  │ [Resume]                         │  │
│            │  └──────────────────────────────────┘  │
│            │  ┌──────────────────────────────────┐  │
│            │  │ Session #1230                    │  │
│            │  │ "Build SaaS vs mobile app?"      │  │
│            │  │ Phase: Context Collection        │  │
│            │  │ Cost: $0.08 | 3 hours ago        │  │
│            │  │ [Resume]                         │  │
│            │  └──────────────────────────────────┘  │
│            │                                         │
│            │  Archived Sessions (15)                 │
│            │  [View All] →                           │
└─────────────────────────────────────────────────────┘
```

**Components**:

- Session card (title, phase, cost, timestamp, resume CTA)
- Empty state (no sessions)
- Search/filter (by date, cost, status)

**Actions**:

- [+ New Deliberation] → `/sessions/new`
- [Resume] → `/sessions/[id]/[phase]`
- [View Examples] → `/help/examples`

---

### 4.2 Phase 1: Problem Input (`/sessions/new` or `/sessions/[id]/problem`)

**Purpose**: Capture user's complex problem/decision.

**Layout**:

```
┌─────────────────────────────────────────────────────┐
│ ← Back to Dashboard    Problem Input      [1 of 7] │
├─────────────────────────────────────────────────────┤
│                                                     │
│  What problem or decision would you like help with? │
│                                                     │
│  ┌───────────────────────────────────────────────┐ │
│  │ I have $50K saved and 12 months runway.      │ │
│  │ Should I build a B2B SaaS dashboard tool,    │ │
│  │ a consumer mobile app for habit tracking, or │ │
│  │ a freelance marketplace for technical        │ │
│  │ writers?                                     │ │
│  │                                              │ │
│  │ [500 characters used]                        │ │
│  └───────────────────────────────────────────────┘ │
│                                                     │
│  > Add Context (optional) ▼                         │
│    ┌─────────────────────────────────────────────┐ │
│    │ Budget: $50,000                             │ │
│    │ Timeline: 12 months                         │ │
│    │ Constraints: Solo founder, no technical     │ │
│    │              co-founder                     │ │
│    └─────────────────────────────────────────────┘ │
│                                                     │
│                           [Analyze Problem] →      │
└─────────────────────────────────────────────────────┘
```

**Components**:

- Large textarea (auto-resize, min 3 lines)
- Character counter (no hard limit, guide to 200-500)
- Collapsible "Add Context" with structured fields (budget, timeline, constraints)
- Primary CTA: [Analyze Problem]

**Validation**:

- Minimum 50 characters (warn if too short)
- Suggest expanding if <100 chars

**Actions**:

- [Analyze Problem] → Trigger DecomposerAgent, show loading state → Phase 2

---

### 4.3 Phase 2: Decomposition Review (`/sessions/[id]/decomposition`)

**Purpose**: Review AI-generated sub-problems, approve or modify.

**Layout**:

```
┌─────────────────────────────────────────────────────┐
│ ← Problem Input    Decomposition Review    [2 of 7]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  I've broken your problem into 4 sub-problems:      │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 1. Market Opportunity Sizing               │   │
│  │    Complexity: ████████░░ (8/10)           │   │
│  │    Goal: Which has fastest path to $5K MRR?│   │
│  │    [Expand] ▼                               │   │
│  └─────────────────────────────────────────────┘   │
│  ┌─────────────────────────────────────────────┐   │
│  │ 2. Solo-Founder Feasibility                │   │
│  │    Complexity: ███████░░░ (7/10)           │   │
│  │    Goal: Which can one person build & sell?│   │
│  │    Dependencies: After #1                   │   │
│  │    [Expand] ▼                               │   │
│  └─────────────────────────────────────────────┘   │
│  ... (2 more)                                       │
│                                                     │
│  [Modify Sub-problems]  [Approve & Continue] →     │
└─────────────────────────────────────────────────────┘
```

**Components**:

- Sub-problem card:
  - Title, complexity bar (visual), goal, dependencies badge
  - Expandable: Show full context, constraints
  - Edit icon (opens modal)
- Dependency visualization (simple: "After #1, #2" or graph for complex)

**Modification Actions** (Modal):

- Edit goal
- Change complexity (slider 1-10)
- Add/remove dependencies
- Delete sub-problem
- Add new sub-problem

**Actions**:

- [Modify] → Opens edit modal
- [Approve & Continue] → Trigger ContextCollectorAgent → Phase 3 or Phase 4 (skip if no gaps)

---

### 4.4 Phase 3: Context Collection (`/sessions/[id]/context`)

**Purpose**: Answer internal gap questions to fill information needs.

**Conditional**: Only shown if DecomposerAgent identifies INTERNAL gaps.

**Layout**:

```
┌─────────────────────────────────────────────────────┐
│ ← Decomposition    Context Collection      [3 of 7]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  To give you the best recommendation, I need a few  │
│  details about your situation:                      │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 🔴 Critical (2)                             │   │
│  │                                             │   │
│  │ 1. What are your technical skills?          │   │
│  │    ┌──────────────────────────────────────┐ │   │
│  │    │ Full-stack dev, decent at design,    │ │   │
│  │    │ weak at sales/marketing              │ │   │
│  │    └──────────────────────────────────────┘ │   │
│  │                                             │   │
│  │ 2. What's your previous startup experience? │   │
│  │    ┌──────────────────────────────────────┐ │   │
│  │    │ One failed startup (SaaS, 18 months) │ │   │
│  │    └──────────────────────────────────────┘ │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │ 🟡 Nice to Have (1)  [Show] ▼              │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  [Skip for Now]                [Continue] →        │
└─────────────────────────────────────────────────────┘
```

**Components**:

- Priority sections: Critical (red), Nice to Have (yellow)
- Question cards with textarea (auto-resize)
- Skip option (allowed, but warn: "May reduce recommendation quality")

**Validation**:

- None (all fields optional, but encourage completing Critical)

**Actions**:

- [Continue] → Save context, proceed to Phase 4
- [Skip for Now] → Warn, then proceed to Phase 4

---

### 4.5 Phase 4: Persona Selection (`/sessions/[id]/personas`)

**Purpose**: Review recommended expert personas, approve or modify.

**Layout**:

```
┌─────────────────────────────────────────────────────┐
│ ← Context Collection    Persona Selection  [4 of 7]│
├─────────────────────────────────────────────────────┤
│                                                     │
│  I've assembled a board of 4 experts for your       │
│  problem:                                           │
│                                                     │
│  ┌──────────────────┐ ┌──────────────────┐         │
│  │ 💼 Zara          │ │ 💰 Maria         │         │
│  │ Growth Hacker    │ │ Finance Strategist│         │
│  │                  │ │                  │         │
│  │ Why: Market     │ │ Why: Financial   │         │
│  │ validation &     │ │ risk analysis    │         │
│  │ growth channels  │ │                  │         │
│  │                  │ │                  │         │
│  │ [View Profile]   │ │ [View Profile]   │         │
│  └──────────────────┘ └──────────────────┘         │
│  ┌──────────────────┐ ┌──────────────────┐         │
│  │ 🔧 Wei           │ │ ⚠️ Ahmad         │         │
│  │ Tech Architect   │ │ Risk Officer     │         │
│  │ ...              │ │ ...              │         │
│  └──────────────────┘ └──────────────────┘         │
│                                                     │
│  Coverage: Strategic ✓ Tactical ✓ Domain ✓         │
│                                                     │
│  [Modify Selection]         [Begin Deliberation] → │
└─────────────────────────────────────────────────────┘
```

**Components**:

- Persona card:
  - Icon (emoji or avatar), name, title
  - 1-sentence "Why selected" rationale
  - [View Profile] → Drawer with full bio, traits, temperature
- Coverage indicator: Strategic/Tactical/Domain checkmarks
- Modify option: Opens persona picker (grid of all 45, search/filter)

**Actions**:

- [Modify Selection] → Opens persona picker modal
- [View Profile] → Opens drawer with full persona details
- [Begin Deliberation] → Trigger Initial Round → Phase 5

---

### 4.6 Phase 5: Live Deliberation (`/sessions/[id]/deliberation`)

**Purpose**: Real-time multi-round expert discussion.

**Layout** (Chat-style):

```
┌─────────────────────────────────────────────────────┐
│ ← Personas    Deliberation    [5 of 7]             │
│ Round 3/7 | Convergence: 62% | Cost: $0.42          │
├─────────────────────────────────────────────────────┤
│                                                     │
│ ┌─────────────────────────────────────────────┐    │
│ │ 🎯 Facilitator  |  Round 1                   │    │
│ │ Let's begin with market opportunity. Each    │    │
│ │ expert, please share your opening thoughts.  │    │
│ └─────────────────────────────────────────────┘    │
│                                                     │
│ ┌─────────────────────────────────────────────┐    │
│ │ 💼 Zara  |  Initial Contribution              │    │
│ │ I see three distinct market opportunities... │    │
│ │ [Show Thinking] ▼  |  Tokens: 287 | $0.002   │    │
│ └─────────────────────────────────────────────┘    │
│                                                     │
│ ┌─────────────────────────────────────────────┐    │
│ │ 💰 Maria  |  Initial Contribution             │    │
│ │ From a financial perspective, the SaaS       │    │
│ │ option has lower burn rate...                │    │
│ │ 💾 Cached (saved $0.02)                      │    │
│ └─────────────────────────────────────────────┘    │
│                                                     │
│ ... (more contributions)                            │
│                                                     │
│ ┌─────────────────────────────────────────────┐    │
│ │ 🎯 Facilitator  |  Round 2 Decision          │    │
│ │ Decision: CONTINUE                           │    │
│ │ Next speaker: Wei (address Zara's concern   │    │
│ │ about technical feasibility)                 │    │
│ └─────────────────────────────────────────────┘    │
│                                                     │
│ [Generating Wei's response...] ⏳                   │
│                                                     │
└─────────────────────────────────────────────────────┘
│ [View Metrics] [Export Transcript] [End Early] ⏸  │
└─────────────────────────────────────────────────────┘
```

**Components**:

- **Sticky context bar**: Round counter, convergence %, cost tracker
- **Contribution panel**:
  - Color-coded by persona (Facilitator: blue, Experts: unique colors)
  - Expandable "Show Thinking" (internal reasoning)
  - Metadata footer: Tokens, cost, cache badge
- **Loading state**: Skeleton panel with shimmer, "[Persona] is analyzing..."
- **Round dividers**: Visual break between rounds with round number
- **Moderator interventions**: Special highlight (e.g., orange border for Contrarian)

**Tabs** (Bottom or sidebar):

- Contributions (default view)
- Metrics (convergence/novelty/conflict charts)
- Transcript (plain text, copyable)

**Actions**:

- Auto-scroll to latest contribution
- [End Early] → Warn "This may reduce quality", confirm → Force vote
- [View Metrics] → Opens drawer with convergence charts
- [Export Transcript] → Download markdown (even if incomplete)

**Real-time Updates**:

- Use WebSocket or Server-Sent Events (SSE) for live contributions
- Show typing indicators when LLM is generating
- Update cost/token counters in real-time

---

### 4.7 Phase 6: Voting & Synthesis (`/sessions/[id]/synthesis`)

**Purpose**: Display expert votes and final synthesized recommendation.

**Layout** (Two sub-phases):

**6a. Voting Collection** (Loading state):

```
┌─────────────────────────────────────────────────────┐
│ ← Deliberation    Voting    [6 of 7]                │
│ Collecting votes... (4/4 complete) ✓                │
├─────────────────────────────────────────────────────┤
│                                                     │
│  Experts are now voting on the best path forward.   │
│                                                     │
│  ✓ Zara voted (Confidence: High)                    │
│  ✓ Maria voted (Confidence: Medium)                 │
│  ✓ Wei voted (Confidence: High)                     │
│  ✓ Ahmad voted (Confidence: Medium)                 │
│                                                     │
│  Synthesizing final recommendation... ⏳            │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**6b. Synthesis Report** (Final output):

```
┌─────────────────────────────────────────────────────┐
│ ← Voting    Synthesis    [6 of 7]                   │
│ Session Complete | Total Cost: $0.68 | 14 min       │
├─────────────────────────────────────────────────────┤
│                                                     │
│  # Final Recommendation                             │
│                                                     │
│  ## Executive Summary                               │
│  Based on deliberation with 4 experts, we recommend │
│  pursuing the **B2B SaaS dashboard tool** as your   │
│  best path forward. This option balances...         │
│                                                     │
│  ## Key Insights                                    │
│  - Market validation: Fastest path to $5K MRR (6mo) │
│  - Solo feasibility: Achievable with your skills    │
│  - Competitive landscape: Clear differentiation     │
│                                                     │
│  ## Vote Distribution                               │
│  ┌───────────────────────────────────────┐          │
│  │ Option A (SaaS): 3 votes (75%)        │          │
│  │ Option B (Mobile): 1 vote (25%)       │          │
│  │ Consensus Level: High (75%)           │          │
│  └───────────────────────────────────────┘          │
│                                                     │
│  > Dissenting Views ▼                               │
│    Maria raised concerns about SaaS competition...  │
│                                                     │
│  ## Conditions for Success                          │
│  - Validate market need within 6 weeks             │
│  - Build MVP within 3 months                        │
│  - Allocate $5K for initial marketing              │
│                                                     │
│  ## Next Steps                                      │
│  1. Week 1-2: Customer interviews (20 prospects)    │
│  2. Week 3-4: Build landing page, collect signups   │
│  3. Week 5-12: Develop MVP                          │
│                                                     │
│  [Download PDF] [Export JSON] [View Full Transcript]│
│                           [Archive Session] →       │
└─────────────────────────────────────────────────────┘
```

**Components**:

- **Markdown rendering**: Render synthesis report with syntax highlighting
- **Vote cards**: Show each expert's vote, confidence bar, reasoning (collapsible)
- **Vote distribution chart**: Pie or bar chart
- **Dissenting views**: Collapsible section for minority opinions
- **Download options**: PDF (formatted), JSON (raw data), Markdown (transcript)

**Actions**:

- [Download PDF] → Generate and download formatted report
- [Export JSON] → Download session state as JSON
- [View Full Transcript] → Opens modal with full deliberation history
- [Archive Session] → Mark complete, redirect to dashboard

---

### 4.8 Additional Pages

#### Personas Library (`/personas`)

**Purpose**: Browse all 45 expert personas, understand their specializations.

**Layout**:

```
┌─────────────────────────────────────────────────────┐
│ Personas  [Search: "finance"]  [Filter: Category ▼]│
├─────────────────────────────────────────────────────┤
│                                                     │
│ Showing 8 personas in Finance                       │
│                                                     │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐            │
│ │💰 Maria  │ │💵 Chen   │ │📊 Priya  │            │
│ │Finance   │ │CFO       │ │Investment│            │
│ │Strategist│ │Advisor   │ │Analyst   │            │
│ │          │ │          │ │          │            │
│ │[Profile] │ │[Profile] │ │[Profile] │            │
│ └──────────┘ └──────────┘ └──────────┘            │
│ ... (5 more)                                        │
│                                                     │
└─────────────────────────────────────────────────────┘
```

**Features**:

- Grid view with cards (avatar, name, title)
- Search by name, category, traits
- Filter by: Category (marketing, finance, tech, etc.), Traits (analytical, creative, etc.)
- Click persona → Drawer with full profile (bio, traits, temperature, example contributions)

#### Settings (`/settings`)

**Tabs**:

1. **Preferences**: UI theme (light/dark), language, notifications
2. **Budget**: Set max cost per session, low balance alerts
3. **API**: Anthropic API key, Voyage API key, Redis connection string

#### Help (`/help`)

**Sections**:

1. **User Guide**: How to use Bo1, best practices
2. **Examples**: Sample sessions with real problems (solopreneur scenarios from PRD)
3. **FAQ**: Common questions, troubleshooting

---

## 5. Component Catalogue

### 5.1 Core Components

#### 5.1.1 Session Card

**Usage**: Dashboard, archived sessions list

**Anatomy** (User View - NO cost):

```
┌────────────────────────────────────────────┐
│ Session #1234                              │
│ "Should I pivot to law firms?"             │
│                                            │
│ Phase: Deliberation (Round 3/7)            │
│ Convergence: 62%  |  12 min ago            │
│                                            │
│ [Resume] →                                 │
└────────────────────────────────────────────┘
```

**Props**:

- `sessionId: string`
- `title: string` (first 50 chars of problem)
- `phase: string` (current phase name)
- `roundInfo?: string` (e.g., "Round 3/7")
- `convergenceScore?: number` (0-1, displayed as %)
- `timestamp: Date`
- `onResume: () => void`

**Variants**:

- Default (active session)
- Archived (dimmed, no resume button)
- Completed (green checkmark icon)

---

#### 5.1.2 Sub-Problem Card

**Usage**: Decomposition review

**Anatomy**:

```
┌──────────────────────────────────────────┐
│ 1. Market Opportunity Sizing             │
│    Complexity: ████████░░ (8/10)         │
│    Goal: Which has fastest path to $5K...│
│    Dependencies: None                    │
│                                          │
│    [Expand Details] ▼                    │
└──────────────────────────────────────────┘
```

**Props**:

- `number: number` (1-5)
- `title: string`
- `complexity: number` (1-10)
- `goal: string`
- `context?: string` (shown when expanded)
- `dependencies: number[]` (IDs of prerequisite sub-problems)
- `onEdit: () => void`

**States**:

- Collapsed (default)
- Expanded (show full context)
- Editing (modal or inline edit)

---

#### 5.1.3 Persona Card

**Usage**: Persona selection, persona library

**Anatomy**:

```
┌──────────────────────────┐
│ 💼 Zara                  │
│ Growth Hacker            │
│                          │
│ Why: Market validation   │
│ & growth channels        │
│                          │
│ [View Profile] →         │
└──────────────────────────┘
```

**Props**:

- `code: string` (e.g., "zara")
- `name: string`
- `archetype: string`
- `icon: string` (emoji or avatar URL)
- `rationale?: string` (why selected)
- `onViewProfile: () => void`
- `onSelect?: () => void` (for picker mode)
- `selected?: boolean`

**Variants**:

- Selection view (shows rationale)
- Library view (no rationale)
- Picker view (with checkbox)

---

#### 5.1.4 Contribution Panel

**Usage**: Deliberation view

**Anatomy** (User View - NO cost/token metadata):

```
┌───────────────────────────────────────────┐
│ 💼 Zara  |  Initial Contribution          │
│                                           │
│ I see three distinct market opportunities │
│ based on the constraints you've shared... │
│                                           │
│ > Show Thinking ▼                         │
│   (Collapsed: Internal reasoning)         │
│                                           │
│ 2 minutes ago                             │
└───────────────────────────────────────────┘
```

**Props**:

- `personaCode: string`
- `personaName: string`
- `personaIcon: string`
- `content: string` (markdown)
- `thinking?: string` (internal reasoning, collapsible)
- `roundNumber: number`
- `contributionType: string` (initial, response, moderator, facilitator)
- `timestamp: Date` (displayed as relative time)

**Color Coding**:

- Facilitator: Blue border/background
- Personas: Unique color per persona (consistent throughout session)
- Moderators: Orange/yellow border (special highlight)

**States**:

- Collapsed thinking (default)
- Expanded thinking (show internal reasoning)
- Loading (skeleton with shimmer)

---

#### 5.1.5 Vote Card

**Usage**: Voting & synthesis view

**Anatomy**:

```
┌────────────────────────────────────────┐
│ 💼 Zara                                │
│                                        │
│ Decision: YES (Option A: SaaS)         │
│ Confidence: ████████░░ (80%)          │
│                                        │
│ > Reasoning ▼                          │
│   Based on market validation data...   │
│                                        │
│ Conditions: None                       │
└────────────────────────────────────────┘
```

**Props**:

- `personaCode: string`
- `personaName: string`
- `decision: "yes" | "no" | "abstain" | "conditional"`
- `reasoning: string`
- `confidence: number` (0-1)
- `conditions?: string[]`

**Variants**:

- Simple (collapsed reasoning)
- Detailed (expanded reasoning)
- Conditional (show conditions list)

---

#### 5.1.6 Context Bar (Sticky)

**Usage**: Always visible during session (top of page)

**Anatomy** (User View - NO cost metrics):

```
┌─────────────────────────────────────────┐
│ Phase: Deliberation  |  Round 3/7       │
│ Convergence: 62%  |  Confidence: High   │
└─────────────────────────────────────────┘
```

**Props**:

- `phase: string`
- `round?: { current: number, max: number }`
- `convergenceScore?: number` (0-1, displayed as %)
- `confidenceLevel?: "low" | "medium" | "high"`

**States**:

- Normal (convergence < 70%)
- Good (convergence 70-85%, green badge)
- Strong (convergence > 85%, green badge with checkmark)

**Behavior**:

- Updates in real-time as rounds progress
- Shows convergence trend (increasing/stable/decreasing)
- Click to expand metrics drawer (convergence charts, NOT cost)

---

### 5.2 Layout Components

#### 5.2.1 Sidebar Navigation

**Desktop**:

```
┌──────────────┐
│ Bo1          │
│──────────────│
│ > Dashboard  │
│   Sessions   │
│   Personas   │
│   Settings   │
│   Help       │
│──────────────│
│ Active (2)   │
│ • Session 1  │
│ • Session 2  │
└──────────────┘
```

**Mobile**: Hidden, replaced by bottom navigation or hamburger menu

**Props**:

- `activeSessions: Session[]`
- `currentRoute: string`

**Behavior**:

- Collapsible with `Cmd+B` (desktop)
- Show badge count for active sessions
- Highlight current route

---

#### 5.2.2 Stepper (Phase Progress)

**Visual**:

```
● ─── ● ─── ○ ─── ○ ─── ○ ─── ○ ─── ○
1     2     3     4     5     6     7
```

**States**:

- Completed (●, green)
- Current (●, blue, larger)
- Upcoming (○, gray)

**Labels** (on hover):

1. Problem Input
2. Decomposition
3. Context Collection (optional)
4. Persona Selection
5. Deliberation
6. Synthesis
7. Export

**Behavior**:

- Click completed steps to review (non-destructive)
- Can't skip ahead to uncompleted steps

---

#### 5.2.3 Modal

**Usage**: Destructive actions, detailed forms

**Sizes**:

- Small (400px): Confirmations
- Medium (600px): Forms (edit sub-problem)
- Large (800px): Persona picker, full transcript

**Anatomy**:

```
┌────────────────────────────────┐
│ [Title]                    [X] │
│────────────────────────────────│
│                                │
│ [Content]                      │
│                                │
│────────────────────────────────│
│           [Cancel] [Confirm]   │
└────────────────────────────────┘
```

**Props**:

- `title: string`
- `size: "sm" | "md" | "lg"`
- `onClose: () => void`
- `onConfirm?: () => void`
- `children: ReactNode`

**Behavior**:

- Close on Escape key
- Close on backdrop click (unless form is dirty)
- Trap focus within modal

---

#### 5.2.4 Drawer (Side Panel)

**Usage**: Persona profiles, metrics, debug info

**Anatomy**:

```
┌──────────────────────────────────┐
│                        ┌─────────┤
│ Main Content           │ Drawer  │
│                        │         │
│                        │ [Close] │
│                        │         │
│                        │ Content │
│                        │         │
└────────────────────────└─────────┘
```

**Sizes**:

- Small (320px): Metrics summary
- Medium (480px): Persona profiles
- Large (640px): Full debug panel

**Behavior**:

- Slide in from right
- Overlay on mobile (full width)
- Close on Escape or backdrop click

---

### 5.3 Feedback Components

#### 5.3.1 Toast Notification

**Usage**: Success/error messages, non-blocking alerts

**Variants**:

- Success (green): "✓ Session saved successfully"
- Error (red): "⚠️ Failed to load persona. Retrying..."
- Warning (yellow): "⚠️ Approaching budget limit ($0.85 / $1.00)"
- Info (blue): "ℹ️ Cache hit rate improved to 82%"

**Behavior**:

- Auto-dismiss after 5 seconds (success/info)
- Persist until dismissed (error/warning)
- Stack multiple toasts (max 3 visible)

---

#### 5.3.2 Loading States

**Skeleton Screen** (Deliberation):

```
┌───────────────────────────────────────┐
│ ░░░░░░  |  ░░░░░░░░░░░░               │
│                                       │
│ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░     │
│ ░░░░░░░░░░░░░░░░░░░░░░               │
│                                       │
│ ░░░░░░░░ | ░░░░ | ░░░░               │
└───────────────────────────────────────┘
```

**Shimmer effect**: Animated gradient sweep

**Progress Spinners** (Inline):

- "Analyzing problem... ⏳"
- "Maria is thinking... 💭"
- "Generating synthesis... ✍️"

---

#### 5.3.3 Empty States

**Dashboard (No Sessions)**:

```
┌─────────────────────────────────────┐
│                                     │
│         📋                          │
│   No active sessions                │
│                                     │
│   Get started by creating your      │
│   first deliberation.               │
│                                     │
│   [+ New Deliberation]              │
│                                     │
└─────────────────────────────────────┘
```

**Archived Sessions (None)**:

```
┌─────────────────────────────────────┐
│   🗄️ No archived sessions yet       │
│                                     │
│   Completed sessions will appear    │
│   here for future reference.        │
└─────────────────────────────────────┘
```

---

### 5.4 Social Sharing Components

#### 5.4.1 Social Sharing Panel

**Usage**: Synthesis report page (after deliberation complete)

**Component**:

```svelte
<div class="social-sharing">
  <h3>Share Your Deliberation</h3>

  <!-- Privacy Control -->
  <label>
    <input type="checkbox" bind:checked={sharePublicly} on:change={toggleSharing} />
    Allow public sharing (generates shareable link)
  </label>

  {#if sharePublicly}
    <!-- Share Link -->
    <div class="share-link">
      <input type="text" readonly value={shareUrl} />
      <button on:click={copyLink}>Copy Link</button>
    </div>

    <!-- Share Buttons -->
    <div class="share-buttons">
      <button class="btn-linkedin" on:click={shareOnLinkedIn}>
        <LinkedInIcon /> Share on LinkedIn
      </button>

      <button class="btn-twitter" on:click={shareOnTwitter}>
        <TwitterIcon /> Share on Twitter
      </button>

      <button class="btn-email" on:click={emailReport}>
        <EmailIcon /> Email Report
      </button>
    </div>
  {/if}
</div>
```

**Props**:

- `sessionId: string`
- `synthesisReport: SynthesisReport`
- `shareEnabled: boolean` (user's privacy setting)
- `onToggleSharing: (enabled: boolean) => void`

**See Also**: SOCIAL_SHARING_LANDING.md for full implementation details

---

#### 5.4.2 Public Share Page

**Route**: `/share/[token]`

**Purpose**: Display read-only synthesis report for shared sessions

**Privacy**: Only shows synthesis report (NOT full transcript, NOT cost metrics)

**Component Structure**:

- Header: Problem statement, completion date, duration, convergence
- Executive Summary
- Key Insights
- Vote Distribution (chart)
- Dissenting Views (if any)
- Next Steps
- Footer: CTA to create own deliberation

**See Also**: SOCIAL_SHARING_LANDING.md for wireframes and implementation

---

### 5.5 GDPR Privacy Controls

#### 5.5.1 Privacy Settings Page

**Route**: `/settings/privacy`

**Components**:

**Data Export**:

```svelte
<section class="data-export">
  <h2>Data Export</h2>
  <p>Download all your data in JSON format (GDPR Art. 15: Right to Access)</p>

  <button on:click={exportData}>Export My Data</button>
  <p class="help-text">You will receive a download link via email within 30 days.</p>
</section>
```

**Account Deletion**:

```svelte
<section class="account-deletion">
  <h2>Delete Account</h2>
  <p>Permanently delete your account and anonymize all data (GDPR Art. 17: Right to Erasure)</p>

  <button class="btn-danger" on:click={requestDeletion}>Delete My Account</button>

  <details class="deletion-faq">
    <summary>What happens when I delete my account?</summary>
    <ul>
      <li>Your email and personal data will be anonymized within 30 days</li>
      <li>Problem statements and contributions will be redacted</li>
      <li>Anonymized data remains for analytics (non-identifiable)</li>
      <li>You can cancel deletion by logging in during the 30-day grace period</li>
    </ul>
  </details>
</section>
```

**Data Retention**:

```svelte
<section class="data-retention">
  <h2>Data Retention</h2>
  <p>Control how long your data is kept</p>

  <label>
    <input type="radio" name="retention" value="365" bind:group={retentionDays} />
    1 year (default)
  </label>

  <label>
    <input type="radio" name="retention" value="730" bind:group={retentionDays} />
    2 years
  </label>

  <label>
    <input type="radio" name="retention" value="-1" bind:group={retentionDays} />
    Indefinite (keep forever)
  </label>

  <button on:click={updateRetention}>Save Preference</button>
</section>
```

**See Also**: SECURITY_COMPLIANCE.md for full GDPR implementation

---

## 6. Interaction Patterns

### 6.1 Real-Time Updates

**Technology**: WebSocket or Server-Sent Events (SSE)

**Events to Stream**:

- `contribution.new`: New expert contribution arrived
- `contribution.update`: Update convergence/quality metrics
- `round.complete`: Round finished, show summary
- `phase.transition`: Move to next phase
- `vote.received`: Expert voted
- `synthesis.progress`: Synthesis generation progress

**UI Behavior**:

- Auto-scroll to new contributions (with "Jump to latest" button if user scrolled up)
- Update convergence score in real-time
- Show typing indicators ("Maria is typing...")
- Smooth animations for new elements (fade in)

---

### 6.2 Progressive Disclosure

**Principle**: Don't overwhelm users with all information at once.

**Implementation**:

1. **Collapsible Sections**:

   - "Show Thinking" (contribution panels)
   - "Dissenting Views" (synthesis report)
   - "Advanced Options" (problem input)
   - "Nice to Have Questions" (context collection)

2. **Expandable Cards**:

   - Sub-problem cards (show goal by default, expand for full context)
   - Persona cards (show name/title, expand for full profile)

3. **Tabs**:

   - Deliberation view: "Contributions" (default), "Metrics", "Transcript"
   - Settings: "Preferences", "Budget", "API"

4. **Modals/Drawers**:
   - Full persona profile (drawer)
   - Edit sub-problem (modal)
   - Full metrics (drawer)

---

### 6.3 Keyboard Shortcuts

**Global**:

- `Cmd+K`: Command palette (quick actions)
- `Cmd+B`: Toggle sidebar
- `Escape`: Close modal/drawer

**Navigation**:

- `Cmd+1-7`: Jump to phase (1=Problem, 2=Decomposition, etc.)
- `Cmd+N`: New session

**Actions**:

- `Enter`: Confirm/continue (when CTA is focused)
- `Cmd+Enter`: Submit form (problem input, context questions)

**Deliberation View**:

- `J/K`: Navigate contributions (Vim-style)
- `E`: Expand/collapse thinking
- `T`: Open transcript view

---

### 6.4 Responsive Behavior

**Breakpoints**:

- Mobile: 0-639px
- Tablet: 640-1023px
- Desktop: 1024px+

**Adaptations**:

| Component           | Mobile                       | Desktop              |
| ------------------- | ---------------------------- | -------------------- |
| Sidebar             | Hidden (hamburger menu)      | Visible, collapsible |
| Sub-problem cards   | Stacked vertically           | 2 columns (if >2)    |
| Persona cards       | 1 per row                    | Grid (2-3 per row)   |
| Contribution panels | Full width                   | Max 800px centered   |
| Cost tracker        | Bottom sheet (tap to expand) | Sticky top bar       |
| Stepper             | Horizontal scroll            | Full width           |

**Mobile-Specific**:

- Bottom navigation (Dashboard, Sessions, Settings)
- Swipe gestures (swipe left on session card to delete/archive)
- Pull-to-refresh on dashboard
- Bottom sheets for quick actions

---

## 7. Visual System Guidelines

### 7.1 Color Palette

**Primary Colors** (Brand):

```css
--primary-50: #eff6ff; /* Lightest blue */
--primary-100: #dbeafe;
--primary-200: #bfdbfe;
--primary-300: #93c5fd;
--primary-400: #60a5fa;
--primary-500: #3b82f6; /* Primary blue */
--primary-600: #2563eb; /* Primary dark */
--primary-700: #1d4ed8;
--primary-800: #1e40af;
--primary-900: #1e3a8a; /* Darkest blue */
```

**Semantic Colors**:

```css
--success-500: #10b981; /* Green */
--warning-500: #f59e0b; /* Amber */
--error-500: #ef4444; /* Red */
--info-500: #3b82f6; /* Blue */
```

**Neutral Colors** (Gray):

```css
--gray-50: #f9fafb;
--gray-100: #f3f4f6; /* Background light */
--gray-200: #e5e7eb; /* Border light */
--gray-300: #d1d5db;
--gray-400: #9ca3af; /* Muted text */
--gray-500: #6b7280; /* Secondary text */
--gray-600: #4b5563; /* Body text */
--gray-700: #374151;
--gray-800: #1f2937; /* Headings */
--gray-900: #111827; /* Black */
```

**Persona Colors** (Contribution panels):

```css
--persona-1: #3b82f6; /* Blue */
--persona-2: #10b981; /* Green */
--persona-3: #f59e0b; /* Amber */
--persona-4: #8b5cf6; /* Purple */
--persona-5: #ec4899; /* Pink */
--facilitator: #06b6d4; /* Cyan */
--moderator: #f97316; /* Orange */
```

**Usage**:

- Assign personas colors 1-5 in order selected
- Facilitator always cyan
- Moderators always orange

---

### 7.2 Typography

**Font Stack**:

```css
--font-sans: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
--font-mono: "JetBrains Mono", "Fira Code", monospace;
```

**Type Scale** (rem):

```css
--text-xs: 0.75rem; /* 12px */
--text-sm: 0.875rem; /* 14px */
--text-base: 1rem; /* 16px */
--text-lg: 1.125rem; /* 18px */
--text-xl: 1.25rem; /* 20px */
--text-2xl: 1.5rem; /* 24px */
--text-3xl: 1.875rem; /* 30px */
--text-4xl: 2.25rem; /* 36px */
```

**Line Heights**:

```css
--leading-tight: 1.25; /* Headings */
--leading-normal: 1.5; /* Body text */
--leading-relaxed: 1.75; /* Long-form content */
```

**Font Weights**:

```css
--font-normal: 400;
--font-medium: 500;
--font-semibold: 600;
--font-bold: 700;
```

**Usage Guidelines**:

- Headings: `font-semibold` or `font-bold`
- Body text: `font-normal`, `leading-normal`
- Metadata/timestamps: `text-sm`, `text-gray-500`
- Code/data: `font-mono`

---

### 7.3 Spacing System

**Scale** (Tailwind-compatible):

```css
--space-1: 0.25rem; /* 4px */
--space-2: 0.5rem; /* 8px */
--space-3: 0.75rem; /* 12px */
--space-4: 1rem; /* 16px */
--space-5: 1.25rem; /* 20px */
--space-6: 1.5rem; /* 24px */
--space-8: 2rem; /* 32px */
--space-10: 2.5rem; /* 40px */
--space-12: 3rem; /* 48px */
--space-16: 4rem; /* 64px */
```

**Common Patterns**:

- Card padding: `space-6` (24px)
- Input padding: `space-3` (12px vertical), `space-4` (16px horizontal)
- Section spacing: `space-8` (32px)
- Page margins: `space-6` to `space-12` (24-48px)

---

### 7.4 Elevation (Shadows)

```css
--shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
--shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
--shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1);
--shadow-xl: 0 20px 25px -5px rgb(0 0 0 / 0.1);
--shadow-2xl: 0 25px 50px -12px rgb(0 0 0 / 0.25);
```

**Usage**:

- Cards: `shadow-sm` (default), `shadow-md` (hover)
- Modals: `shadow-xl`
- Drawers: `shadow-2xl`
- Sticky elements: `shadow-md`

---

### 7.5 Border Radius

```css
--radius-sm: 4px; /* Buttons, inputs */
--radius-md: 8px; /* Cards, panels */
--radius-lg: 12px; /* Modals, drawers */
--radius-full: 9999px; /* Pills, avatars */
```

---

### 7.6 Animations & Transitions

**Duration**:

```css
--duration-fast: 150ms; /* Micro-interactions */
--duration-normal: 250ms; /* Default */
--duration-slow: 350ms; /* Complex transitions */
```

**Easing**:

```css
--ease-in: cubic-bezier(0.4, 0, 1, 1);
--ease-out: cubic-bezier(0, 0, 0.2, 1);
--ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);
```

**Common Transitions**:

- Hover effects: `transition: all 150ms ease-out;`
- Page transitions: `transition: opacity 250ms ease-in-out;`
- Drawer slide: `transition: transform 350ms ease-out;`

**Motion Preferences**:

```css
@media (prefers-reduced-motion: reduce) {
  * {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
```

---

## 8. Responsive & Accessibility

### 8.1 Responsive Breakpoints

```css
/* Mobile-first approach */
@media (min-width: 640px) {
  /* sm: Tablet */
}
@media (min-width: 1024px) {
  /* lg: Desktop */
}
@media (min-width: 1280px) {
  /* xl: Large desktop */
}
```

### 8.2 Layout Adaptations

**Mobile** (<640px):

- Single column layout
- Bottom navigation
- Full-width cards
- Hamburger menu for sidebar
- Bottom sheets for cost tracker

**Tablet** (640-1023px):

- 2-column grid for cards (where applicable)
- Sidebar toggleable (overlay when open)
- Larger touch targets (min 44x44px)

**Desktop** (1024px+):

- Sidebar always visible (unless manually collapsed)
- 3-column grid for persona cards
- Hover states enabled
- Keyboard shortcuts active

### 8.3 Accessibility (WCAG AA)

**Semantic HTML**:

```html
<main role="main" aria-label="Deliberation">
  <section aria-labelledby="round-1-heading">
    <h2 id="round-1-heading">Round 1</h2>
    <article aria-label="Contribution from Zara">...</article>
  </section>
</main>
```

**ARIA Live Regions** (Real-time updates):

```html
<div aria-live="polite" aria-atomic="true">New contribution from Maria</div>
```

**Focus Management**:

- Visible focus indicators (outline: 2px solid primary-500)
- Trap focus in modals/drawers
- Return focus after modal close
- Skip to main content link

**Color Contrast**:

- Text on background: 4.5:1 minimum
- UI components: 3:1 minimum
- Don't rely on color alone (use icons + text)

**Screen Reader Support**:

- Meaningful alt text for images
- Label all form inputs
- Announce loading states
- Describe complex visualizations (e.g., "Convergence at 62%, increasing")

---

## 9. Wireframes

### 9.1 Dashboard (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│ [☰] Bo1                    [Search...]            [User] [⚙] │
├───────┬───────────────────────────────────────────────────────┤
│       │                                                       │
│ Dash  │  Welcome back, User!                                  │
│ ──────│                                                       │
│ >Sess │  ┌──────────────────────────┐  ┌──────────────────┐  │
│ Perso │  │ [+ New Deliberation]     │  │ [View Examples]  │  │
│ Setti │  └──────────────────────────┘  └──────────────────┘  │
│ Help  │                                                       │
│       │  Active Sessions (2)                                  │
│       │  ┌───────────────────────────────────────────────┐   │
│ Activ │  │ 📋 Session #1234                              │   │
│ (2)   │  │ "Should I pivot to law firms?"                │   │
│       │  │ Phase: Deliberation (Round 3/7)               │   │
│ • S1  │  │ Convergence: 62%  |  12 min ago               │   │
│ • S2  │  │                                    [Resume] → │   │
│       │  └───────────────────────────────────────────────┘   │
│       │  ┌───────────────────────────────────────────────┐   │
│       │  │ 📋 Session #1230                              │   │
│       │  │ "Build SaaS vs mobile app?"                   │   │
│       │  │ Phase: Context Collection                     │   │
│       │  │ 3 hours ago                                   │   │
│       │  │                                    [Resume] → │   │
│       │  └───────────────────────────────────────────────┘   │
│       │                                                       │
│       │  Archived Sessions (15)                [View All] →  │
│       │                                                       │
└───────┴───────────────────────────────────────────────────────┘
```

### 9.2 Problem Input (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│ ← Dashboard         Problem Input                    [1 of 7] │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  What problem or decision would you like help with?           │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ I have $50K saved and 12 months runway. Should I build  │ │
│  │ a B2B SaaS dashboard tool, a consumer mobile app for    │ │
│  │ habit tracking, or a freelance marketplace for          │ │
│  │ technical writers?                                      │ │
│  │                                                         │ │
│  │                                                         │ │
│  │                                      [500 characters]   │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  > Add Context (optional) ▼                                   │
│                                                               │
│                                                               │
│                                       [Analyze Problem] →     │
└───────────────────────────────────────────────────────────────┘
```

### 9.3 Decomposition Review (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│ ← Problem Input    Decomposition Review              [2 of 7] │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  I've broken your problem into 4 sub-problems:                │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ 1. Market Opportunity Sizing                          │   │
│  │    Complexity: ████████░░ (8/10)                      │   │
│  │    Goal: Which has fastest path to $5K MRR?           │   │
│  │    Dependencies: None                                 │   │
│  │                                           [Edit] [▼]  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ 2. Solo-Founder Feasibility                           │   │
│  │    Complexity: ███████░░░ (7/10)                      │   │
│  │    Goal: Which can one person build and sell?         │   │
│  │    Dependencies: After #1                             │   │
│  │                                           [Edit] [▼]  │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ 3. Competitive Landscape                              │   │
│  │    Complexity: ██████░░░░ (6/10)                      │   │
│  │    ... (collapsed)                                    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐   │
│  │ 4. Go-to-Market Fit                                   │   │
│  │    ... (collapsed)                                    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  [+ Add Sub-problem]                                          │
│                                                               │
│                      [Modify]  [Approve & Continue] →         │
└───────────────────────────────────────────────────────────────┘
```

### 9.4 Persona Selection (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│ ← Context         Persona Selection                  [4 of 7] │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  I've assembled a board of 4 experts for your problem:        │
│                                                               │
│  ┌────────────────────┐  ┌────────────────────┐              │
│  │ 💼 Zara            │  │ 💰 Maria           │              │
│  │ Growth Hacker      │  │ Finance Strategist │              │
│  │                    │  │                    │              │
│  │ Why: Market        │  │ Why: Financial     │              │
│  │ validation &       │  │ risk analysis      │              │
│  │ growth channels    │  │                    │              │
│  │                    │  │                    │              │
│  │ [View Profile] →   │  │ [View Profile] →   │              │
│  └────────────────────┘  └────────────────────┘              │
│                                                               │
│  ┌────────────────────┐  ┌────────────────────┐              │
│  │ 🔧 Wei             │  │ ⚠️ Ahmad           │              │
│  │ Tech Architect     │  │ Risk Officer       │              │
│  │                    │  │                    │              │
│  │ Why: Technical     │  │ Why: Downside      │              │
│  │ feasibility &      │  │ scenarios &        │              │
│  │ architecture       │  │ risk mitigation    │              │
│  │                    │  │                    │              │
│  │ [View Profile] →   │  │ [View Profile] →   │              │
│  └────────────────────┘  └────────────────────┘              │
│                                                               │
│  Coverage: ✓ Strategic  ✓ Tactical  ✓ Domain Expert          │
│                                                               │
│                   [Modify Selection]  [Begin Deliberation] → │
└───────────────────────────────────────────────────────────────┘
```

### 9.5 Live Deliberation (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│ ← Personas      Deliberation                         [5 of 7] │
│ Round 3/7  |  Convergence: 62%  |  Confidence: High           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 🎯 Facilitator  |  Round 1  |  9:03 AM                  │ │
│  │                                                         │ │
│  │ Let's begin with market opportunity sizing. Each       │ │
│  │ expert, please share your opening thoughts.            │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 💼 Zara  |  Initial Contribution  |  9:03 AM            │ │
│  │                                                         │ │
│  │ I see three distinct market opportunities based on     │ │
│  │ your constraints. The B2B SaaS dashboard has the       │ │
│  │ fastest path to revenue if you can...                  │ │
│  │                                                         │ │
│  │ > Show Thinking ▼                                      │ │
│  │                                                         │ │
│  │ 2 minutes ago                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 💰 Maria  |  Initial Contribution  |  9:04 AM           │ │
│  │                                                         │ │
│  │ From a financial perspective, the SaaS option has      │ │
│  │ lower burn rate but longer time to first revenue...    │ │
│  │                                                         │ │
│  │ 1 minute ago                                           │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ 🔧 Wei  |  Initial Contribution  |  9:04 AM             │ │
│  │ ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░ (generating...)         │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                               │
│  ──────────────────────────────────────────────────────────  │
│  Tabs: > Contributions  |  Metrics  |  Transcript            │
└───────────────────────────────────────────────────────────────┘
│  [View Metrics]  [Export Transcript]  [End Early] ⏸          │
└───────────────────────────────────────────────────────────────┘
```

### 9.6 Synthesis Report (Desktop)

```
┌───────────────────────────────────────────────────────────────┐
│ ← Voting          Synthesis                          [6 of 7] │
│ Completed  |  Convergence: 75%  |  Duration: 14 min           │
├───────────────────────────────────────────────────────────────┤
│                                                               │
│  # Final Recommendation                                       │
│                                                               │
│  ## Executive Summary                                         │
│                                                               │
│  Based on deliberation with 4 experts over 5 rounds, we       │
│  recommend pursuing the **B2B SaaS dashboard tool** as your   │
│  best path forward. This option balances your technical       │
│  skills, timeline constraints, and market opportunity.        │
│                                                               │
│  ## Key Insights                                              │
│                                                               │
│  - **Market validation**: B2B customers have immediate need   │
│    and budget, providing fastest path to $5K MRR (est 6mo)   │
│  - **Solo feasibility**: Achievable with your full-stack      │
│    skills, minimal design requirements for dashboard          │
│  - **Competitive landscape**: Clear differentiation possible  │
│    by focusing on specific vertical (e.g., law firms)         │
│  - **Go-to-market fit**: Product-led growth reduces need for  │
│    strong sales skills                                        │
│                                                               │
│  ## Vote Distribution                                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │ Option A (B2B SaaS): 3 votes (75%)  ███████████████░░░ │  │
│  │ Option B (Mobile):   1 vote  (25%)  ████░░░░░░░░░░░░░░ │  │
│  │ Consensus Level: High (75%)                            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  > Dissenting Views ▼                                         │
│    Wei raised concerns about competitive landscape...         │
│                                                               │
│  ## Conditions for Success                                    │
│                                                               │
│  - Validate market need within 6 weeks (20 customer calls)    │
│  - Build MVP within 3 months with limited feature set         │
│  - Allocate $5K for initial marketing/lead gen                │
│                                                               │
│  ## Next Steps                                                │
│                                                               │
│  1. Week 1-2: Customer interviews (20 B2B prospects)          │
│  2. Week 3-4: Build landing page, collect email signups       │
│  3. Week 5-12: Develop core dashboard features (MVP)          │
│  4. Week 13: Launch beta, gather feedback                     │
│                                                               │
│  [Download PDF]  [Export JSON]  [View Full Transcript]        │
│                                         [Archive Session] →   │
└───────────────────────────────────────────────────────────────┘
```

### 9.7 Mobile Wireframes

**Dashboard (Mobile)**:

```
┌─────────────────────┐
│ ☰  Bo1          👤  │
├─────────────────────┤
│                     │
│ [+ New Session]     │
│                     │
│ Active Sessions (2) │
│                     │
│ ┌─────────────────┐ │
│ │ Session #1234   │ │
│ │ "Pivot to law   │ │
│ │  firms?"        │ │
│ │                 │ │
│ │ Deliberation    │ │
│ │ (Round 3/7)     │ │
│ │                 │ │
│ │ $0.42 | 12m ago │ │
│ │                 │ │
│ │ [Resume] →      │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ Session #1230   │ │
│ │ ...             │ │
│ └─────────────────┘ │
│                     │
└─────────────────────┘
│ [Home][Sessions]  │
│ [Settings][Help]    │
└─────────────────────┘
```

**Deliberation (Mobile)**:

```
┌─────────────────────┐
│ ← Deliberation      │
│ Round 3/7           │
│ Convergence: 62%    │
├─────────────────────┤
│                     │
│ ┌─────────────────┐ │
│ │ 🎯 Facilitator  │ │
│ │                 │ │
│ │ Let's begin...  │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ 💼 Zara         │ │
│ │                 │ │
│ │ I see three     │ │
│ │ distinct market │ │
│ │ opportunities...│ │
│ │                 │ │
│ │ > Thinking ▼    │ │
│ │                 │ │
│ │ 2 min ago       │ │
│ └─────────────────┘ │
│                     │
│ ┌─────────────────┐ │
│ │ 💰 Maria        │ │
│ │ ░░░░░░░░░░░...  │ │
│ └─────────────────┘ │
│                     │
│ (auto-scroll)       │
└─────────────────────┘
│ [Metrics] [Pause]   │
└─────────────────────┘
```

---

## 10. State Management & Data Flow

### 10.1 Global State (Redux/Zustand Pattern)

**Store Structure**:

```typescript
interface AppState {
  // User session
  user: {
    id: string;
    preferences: UserPreferences;
    budget: BudgetSettings;
  };

  // Active sessions
  sessions: {
    active: Session[];
    archived: Session[];
    current: Session | null;
  };

  // Current session state
  deliberation: {
    sessionId: string;
    phase: Phase;
    problem: Problem;
    subProblems: SubProblem[];
    selectedPersonas: PersonaProfile[];
    contributions: ContributionMessage[];
    votes: Vote[];
    synthesis: SynthesisReport | null;

    // Real-time metrics
    currentRound: number;
    maxRounds: number;
    convergenceScore: number;
    totalCost: number;
    cacheHitRate: number;
  };

  // UI state
  ui: {
    sidebarCollapsed: boolean;
    activeDrawer: string | null;
    activeModal: string | null;
    toasts: Toast[];
  };
}
```

### 10.2 Data Flow (Actions)

**Session Lifecycle**:

```typescript
// Create new session
dispatch(createSession({ problem: string, context?: Context }))
  → POST /api/sessions
  → Update state.sessions.active
  → Navigate to /sessions/[id]/problem

// Save decomposition
dispatch(saveDecomposition({ subProblems: SubProblem[] }))
  → PUT /api/sessions/[id]/decomposition
  → Update state.deliberation.subProblems
  → Navigate to /sessions/[id]/context

// Begin deliberation
dispatch(beginDeliberation({ personas: string[] }))
  → POST /api/sessions/[id]/deliberation/start
  → Open WebSocket connection
  → Navigate to /sessions/[id]/deliberation

// Receive contribution (WebSocket)
socket.on('contribution.new', (contribution) => {
  dispatch(addContribution(contribution))
  → Update state.deliberation.contributions
  → Update state.deliberation.totalCost
  → Auto-scroll to latest
})

// Complete synthesis
dispatch(completeSynthesis())
  → GET /api/sessions/[id]/synthesis
  → Update state.deliberation.synthesis
  → Navigate to /sessions/[id]/synthesis
```

### 10.3 Backend API Endpoints

**Session Management**:

```
POST   /api/sessions                 - Create new session
GET    /api/sessions                 - List all sessions
GET    /api/sessions/:id             - Get session details
PUT    /api/sessions/:id             - Update session
DELETE /api/sessions/:id             - Delete session
POST   /api/sessions/:id/archive     - Archive session
```

**Deliberation Flow**:

```
POST   /api/sessions/:id/decompose            - Trigger decomposition
PUT    /api/sessions/:id/decomposition        - Save sub-problems
POST   /api/sessions/:id/context              - Save context answers
PUT    /api/sessions/:id/personas             - Select personas
POST   /api/sessions/:id/deliberation/start   - Begin deliberation
POST   /api/sessions/:id/deliberation/end     - Force end early
GET    /api/sessions/:id/synthesis            - Get final report
```

**Real-time**:

```
WS     /api/sessions/:id/stream               - WebSocket for live updates
```

**Personas**:

```
GET    /api/personas                          - List all personas
GET    /api/personas/:code                    - Get persona details
```

**Exports**:

```
GET    /api/sessions/:id/export/pdf           - Download PDF report
GET    /api/sessions/:id/export/json          - Download JSON data
GET    /api/sessions/:id/export/markdown      - Download markdown transcript
```

---

## 11. Technical Integration Points

### 11.1 Backend Integration (Python → Web)

**API Layer** (FastAPI):

```python
# New module: bo1/api/routes.py
from fastapi import FastAPI, WebSocket
from bo1.orchestration.deliberation import DeliberationOrchestrator

app = FastAPI()

@app.post("/api/sessions")
async def create_session(problem: ProblemInput):
    session = await orchestrator.create_session(problem)
    return {"session_id": session.id}

@app.websocket("/api/sessions/{session_id}/stream")
async def stream_deliberation(websocket: WebSocket, session_id: str):
    await websocket.accept()
    async for event in orchestrator.stream_events(session_id):
        await websocket.send_json(event)
```

**Event Streaming**:

```python
# bo1/orchestration/events.py
class DeliberationEvent:
    type: str  # "contribution.new", "round.complete", etc.
    data: dict
    timestamp: datetime

async def emit_event(event: DeliberationEvent):
    """Emit event to WebSocket subscribers"""
    await redis_pubsub.publish(f"session:{session_id}", event.json())
```

### 11.2 State Synchronization (Redis ↔ Web)

**Redis Keys**:

```
session:{session_id}:state          - Full DeliberationState JSON
session:{session_id}:contributions  - List of contributions
session:{session_id}:metrics        - Real-time metrics
session:{session_id}:events         - Event stream (pub/sub)
```

**State Updates**:

- Every contribution → Save to Redis
- Every round → Update metrics
- Phase transition → Update state
- Client reconnect → Restore from Redis

### 11.3 Real-time Architecture

**Technology**: WebSocket with fallback to SSE (Server-Sent Events)

**Flow**:

```
1. Client connects to WS /api/sessions/:id/stream
2. Backend subscribes to Redis pub/sub channel
3. DeliberationOrchestrator emits events as contributions arrive
4. Redis pub/sub broadcasts to all subscribers
5. WebSocket pushes events to client
6. Client updates UI in real-time
```

**Event Types**:

```typescript
type DeliberationEvent =
  | { type: "contribution.new"; data: ContributionMessage }
  | {
      type: "contribution.update";
      data: { id: string; tokens: number; cost: number };
    }
  | { type: "round.complete"; data: { roundNumber: number; summary: string } }
  | { type: "phase.transition"; data: { newPhase: Phase } }
  | { type: "vote.received"; data: Vote }
  | { type: "synthesis.progress"; data: { progress: number } }
  | { type: "error"; data: { message: string } };
```

---

## 12. Implementation Phases

### Phase 1: MVP (Core Flow) - 3-4 weeks

**Goal**: Functional web UI for complete deliberation flow

**Features**:

- ✅ Dashboard (create session, list active/archived)
- ✅ Problem input (textarea, basic validation)
- ✅ Decomposition review (display sub-problems, approve/modify)
- ✅ Persona selection (display recommended, basic modification)
- ✅ Live deliberation (real-time contributions, WebSocket)
- ✅ Synthesis report (markdown rendering, basic export)
- ✅ Cost tracker (sticky bar, real-time updates)

**Tech Stack**:

- Frontend: SvelteKit or Next.js (React)
- Backend: FastAPI (new module in `bo1/api/`)
- State: Redux or Zustand
- Styling: Tailwind CSS
- Components: Radix UI or shadcn/ui

**Deliverables**:

- Working web app (localhost)
- Basic responsive (desktop + mobile)
- No auth (single-user MVP)

---

### Phase 2: Enhanced UX - 2-3 weeks

**Goal**: Improve usability and polish

**Features**:

- ✅ Advanced decomposition editing (drag-to-reorder, dependency graph)
- ✅ Persona picker (search, filter, full profiles in drawer)
- ✅ Metrics dashboard (convergence/novelty charts, cost breakdown)
- ✅ Transcript export (PDF with styling, JSON, Markdown)
- ✅ Keyboard shortcuts (command palette, Vim-style navigation)
- ✅ Empty states (helpful CTAs, examples)
- ✅ Error handling (retry logic, graceful degradation)

**Deliverables**:

- Polished UX with animations
- Comprehensive error states
- Full keyboard navigation

---

### Phase 3: Advanced Features - 3-4 weeks

**Goal**: Power user features and optimization

**Features**:

- ✅ Session management (pause/resume, duplicate, templates)
- ✅ Budget controls (set limits, alerts, auto-stop)
- ✅ Collaboration (share session read-only link)
- ✅ History & comparison (compare past deliberations)
- ✅ Custom personas (user-created experts, saved to account)
- ✅ Advanced metrics (embeddings visualization, drift detection)
- ✅ Research integration (show external sources in deliberation)

**Deliverables**:

- Full-featured web app
- User accounts & auth
- Shareable sessions

---

### Phase 4: Production Ready - 2-3 weeks

**Goal**: Deploy to production

**Features**:

- ✅ Authentication (email/password, OAuth)
- ✅ User profiles (settings, preferences, API keys)
- ✅ Payment integration (credits, subscriptions)
- ✅ Rate limiting & quotas
- ✅ Analytics & monitoring (Posthog, Sentry)
- ✅ SEO & meta tags
- ✅ Legal (privacy policy, terms of service)

**Deliverables**:

- Production deployment (Vercel/Railway)
- Monitoring & alerts
- Documentation & help center

---

## Appendix A: Component Props Reference

### SessionCard

```typescript
interface SessionCardProps {
  sessionId: string;
  title: string;
  phase: Phase;
  roundInfo?: string;
  convergenceScore?: number; // 0-1, displayed as %
  timestamp: Date;
  onResume: () => void;
  variant?: "active" | "archived" | "completed";
}
```

### SubProblemCard

```typescript
interface SubProblemCardProps {
  number: number;
  title: string;
  complexity: number; // 1-10
  goal: string;
  context?: string;
  dependencies: number[];
  expanded?: boolean;
  onEdit: () => void;
  onExpand?: () => void;
}
```

### PersonaCard

```typescript
interface PersonaCardProps {
  code: string;
  name: string;
  archetype: string;
  category: string;
  icon: string;
  rationale?: string;
  selected?: boolean;
  onViewProfile: () => void;
  onSelect?: () => void;
}
```

### ContributionPanel

```typescript
interface ContributionPanelProps {
  personaCode: string;
  personaName: string;
  personaIcon: string;
  content: string; // Markdown
  thinking?: string; // Markdown
  roundNumber: number;
  contributionType: "initial" | "response" | "moderator" | "facilitator";
  timestamp: Date;
  expanded?: boolean;
  onToggleThinking?: () => void;
}
```

### VoteCard

```typescript
interface VoteCardProps {
  personaCode: string;
  personaName: string;
  decision: "yes" | "no" | "abstain" | "conditional";
  reasoning: string;
  confidence: number; // 0-1
  conditions?: string[];
  expanded?: boolean;
  onToggle?: () => void;
}
```

### ContextBar

```typescript
interface ContextBarProps {
  phase: Phase;
  round?: { current: number; max: number };
  convergenceScore?: number; // 0-1, displayed as %
  confidenceLevel?: "low" | "medium" | "high";
  onExpandMetrics?: () => void;
}
```

---

## Appendix B: Color System (Persona Colors)

**Assignment Logic**:

```typescript
const PERSONA_COLORS = [
  "#3b82f6", // Blue
  "#10b981", // Green
  "#f59e0b", // Amber
  "#8b5cf6", // Purple
  "#ec4899", // Pink
];

const FACILITATOR_COLOR = "#06b6d4"; // Cyan
const MODERATOR_COLOR = "#f97316"; // Orange

function getPersonaColor(personaCode: string, index: number): string {
  if (personaCode === "facilitator") return FACILITATOR_COLOR;
  if (personaCode.startsWith("moderator")) return MODERATOR_COLOR;
  return PERSONA_COLORS[index % PERSONA_COLORS.length];
}
```

---

## Appendix C: Responsive Breakpoints

```typescript
export const BREAKPOINTS = {
  sm: 640, // Tablet
  md: 768, // Tablet landscape
  lg: 1024, // Desktop
  xl: 1280, // Large desktop
  "2xl": 1536, // Extra large
};

// Usage in Tailwind
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3">
  {/* 1 col mobile, 2 cols tablet, 3 cols desktop */}
</div>;
```

---

## Appendix D: Accessibility Checklist

- [ ] All interactive elements keyboard accessible
- [ ] Focus indicators visible (not removed)
- [ ] ARIA labels on all icons/buttons without text
- [ ] Live regions for real-time updates
- [ ] Color contrast 4.5:1 minimum
- [ ] Form inputs labeled
- [ ] Error messages announced
- [ ] Skip to main content link
- [ ] Semantic HTML (header, main, nav, article)
- [ ] Alt text for images
- [ ] Respect prefers-reduced-motion
- [ ] Text zoom up to 200% without horizontal scroll

---

**END OF DESIGN DOCUMENT**

---

This design system provides a complete, implementation-ready blueprint for building the Board of One web UI. It prioritizes clarity, speed, and user sovereignty while maintaining full accessibility and modern UX patterns.

**Next Steps**:

1. Review & validate design decisions with stakeholders
2. Set up SvelteKit 5 (Svelte 5 Runes) project boilerplate
3. Configure Supabase Auth (Google, LinkedIn, GitHub OAuth)
4. Set up PostgreSQL + pgvector database schema
5. Begin Phase 1 implementation (MVP)

**Related Documentation**:

- **PLATFORM_ARCHITECTURE.md**: Backend infrastructure, database schema, observability
- **PRICING_STRATEGY.md**: Subscription tiers, feature gates, fraud prevention
- **ACTION_TRACKING_FEATURE.md**: Post-deliberation accountability system
- **SECURITY_COMPLIANCE.md**: GDPR compliance, anonymization, security
- **SOCIAL_SHARING_LANDING.md**: Social features, landing page, SEO
- **CONSOLE_WEB_INTEGRATION.md**: Dual-mode architecture (Console + Web)
- **DESIGN_SUMMARY.md**: Overview of entire design package (91,500+ words)
