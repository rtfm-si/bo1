# Feature Roadmap

Prioritized by: implementation speed, dependencies, and user value.

## Tier 5: Premium Features (High Effort, High Value)

_Differentiated value, potential monetization_

- [ ] **Mentor Mode** - 1-2w

  - Chat directly with an expert (like ChatGPT)
  - Has business context, problem history, actions
  - Natural extension of meeting system
  - mentors can be grouped under categories as well:
    Leadership
    Product
    Marketing
    Founder Psychology
    Productivity
    Career
    etc...
    chat to all in category as an 'addon' package?
    can be 'called' from within an action, with the convo linked to action, and summary added to action as an 'update'

- [ ] **Gated features system** - 2-3d

  - User A sees page X, User B doesn't
  - Enables tier-based access control

- [ ] **Tier plans infrastructure** - 3-5d

  - Depends on gated features
  - Pricing page, feature limits per tier
  - different levels of market insight and competitor watch are unlocked at different plans

- [ ] **Action replanning** - 1w
  - Track action outcomes - user inputs progress updates
  - "What went wrong" flow
  - Replan based on results
  - Actions have deadlines - basic capability chase user for update, and mentors can follow up 'need any help with...?' if plan tier allows

---

## Tier 6: Team & Scale Features (Later Stage)

_Build after core product is solid_

- [ ] **Workspaces** - 1-2w

  - Team containers
  - Shared meetings, business context

- [ ] **Projects** - 1w

  - Group related meetings
  - Depends on workspaces

- [ ] **Informal expert tier** - 1w

  - Sole trader / small business level personas
  - Depends on business context system

- [ ] **Competition research** - 1w
  - Auto-identify and research competitors (basic capability on sign up (plan tier specific)
  - Depends on business context onboarding
  - Use Brave and Tavily
  - Can request market updates every month maybe (plan tier)?
  - embeddings are used to ensure we dont make repeated expensive searches for the same businesses / markets etc - just reuse existing if recent

---

## Tier 7: Marketing & Growth (Ongoing)

- [ ] **Landing page SEO** - 2-3d

  - Meta tags, structured data, content optimization

- [ ] **Footer pages audit** - 1d

  - Terms, privacy, about pages need updating & checking

- [ ] **Suggested questions from business context** - 2-3d
  - CTA to add business context when starting new meeting
  - Depends on business context system

---

## Cleanup Tasks

- [ ] Verify "Sub-Problem Complete" taxonomy change (may already be done)
- [ ] Remove "Synthesis" label if no longer in use
- [ ] Fix "The Bottom Line" duplicate in UI

---

new thoughts:

remove 'delete context' from settings context > overview

deleted meetings should delete actions
gantt fails to load

option to delete actions (all delete operations should be 'soft delete' where the record is masked from ui for end user, but admin can still see the record)

Admin should be able to 'impersonate' a user and see their dashboard, meetings, actions etc but with the additional admin views (like costs, failed meetings etc etc)

NB - only completed meetings should have actions showing up. failed meetings should probably be masked from end users dashboard (except admin). in progress should only show actions when the meeting has completed.

when actions are closed (completed / killed etc) the dependant actions should 'auto update'?

projects should be able to be tagged with ai generated categories and filterable

gantt chart should be filterable by project

gantt chart should be accessible from actions tab

what do top level page links look like?
meetings -< projects -< actions

ntfy report didnt trigger this am

email send for those on wait list

is the graph too complicated?
should we simplify? cap max sub problems?
are we breaking down complex problem into problems that need solving, or are they unnecessary? must be direct and relevant to problem

need to make sure summarization works better
sub problems fail and summary generated - this is wrong (maybe fxed - check)

research being stored?
should be retrieved locally

'still working..' isn't great and messages need to be more consistent
still display / trigger multiple 'completed' results

admin counts not working

are we persisting everything to db (full review)

business context & competitor research
stripe (only when working)
promotions
settings/account
feature request?
report a problem
help
main pages on landing page
actions tracking
kanban board for actions

'x people joined waitlist'

need multiple sample reports covering different sizes of business and different depths of problem

clarify should be a toggle (answer with / without), or skippable questions?

on mobile, 'connected' should flow under 'active'

seem to lose completed meetings/actions/business context etc on deploy? are we properly persisting and reloading from pg?
maybe need to bring forward redis postgres work

feels like there is a significant performance bottleneck somewhere in meetings. we are using haiku 4.5, we shou,ld get a response approx every 5s, but we sometimes (more frequently than expected) see gaps of 30s - whats going on? deep investigation required into retries, etc

mobile page navigation doesn't work - text too big
app navigation isnt great in general
dashboard should be the 'control centre':
start new meeting
overall projects, meetings, actions etc - progress in the last 7 days..?
how to navigate : meetings > projects > actions
i think you can start projects or meetings

deployment to prod is often successful, but the app actually fails. our tests dont seem to cover page load and interactivity etc. whats missing? how do we improve confidence in deployment actually works

add auto seo

twitter, bluesky

create a bank of meetings with context we can run through the meeting generator. like a bunch of posts we can queue up

---the following is an AI SEO feature:
**“Plan implementation of this system in detail: architecture, prompts, tasks, and phase breakdown.”**

---

## 0. Context & Objective

**Goal:**
Build an automated “growth engine” that:

1. Generates high-quality SEO guides on relevant topics.
2. Creates and schedules social posts (with images/GIFs) to promote them.
3. Ingests social comments, learns from them, and (optionally) replies.
4. Feeds all of that feedback back into future topics, pages and posts.

**Stack assumptions:**

- Frontend: Svelte app.
- Backend: Python (FastAPI/Flask/Django).
- DB: Postgres (or similar relational).
- Optional: n8n (or equivalent) for some automations.

---

## 1. High-Level System Overview

The system has five main subsystems:

1. **SEO Content Engine**

   - Topic & keyword discovery
   - Page idea generation
   - Page content generation
   - Publishing & performance tracking

2. **Media Asset Bank**

   - Pre-generated hero/OG images
   - Meeting demo loops (GIF/MP4)
   - Conceptual illustrations / brand art

3. **Social Autoposter**

   - Social bundle generation (Twitter/Bluesky/LinkedIn)
   - Scheduling
   - Platform posting

4. **Comment Ingestion & Learning**

   - Fetch comments/replies
   - Classify & tag
   - Summarise feedback
   - Draft replies & manage a comment inbox

5. **Feedback Loops**

   - Feedback → new keywords/topics
   - Feedback → page refreshes & FAQs
   - Feedback → improved social messaging

The Planner LLM should take this outline and turn each subsystem into concrete tasks, data flows, and prompts.

---

## 2. Core Data Model (Tables & Relationships)

### 2.1 SEO Content

- `seo_topic`

  - `id`
  - `name`
  - `description`
  - `search_intent` (awareness / consideration / decision)
  - `funnel_stage` (top / mid / bottom)
  - `priority_score` (0–100)
  - `status` (idea / selected / in_progress / live)
  - `tags` (e.g. `{pricing, burnout}`)
  - `created_at`, `updated_at`

- `seo_keyword`

  - `id`
  - `topic_id` → `seo_topic.id`
  - `phrase`
  - `intent` (informational / commercial / transactional)
  - `funnel_stage`
  - `source` (seed / llm_expanded / gsc / competitor_inferred)
  - `estimated_value` (0–100, simple heuristic initially)
  - `created_at`

- `seo_page`

  - `id`
  - `topic_id` → `seo_topic.id`
  - `slug`
  - `page_type` (guide / template / comparison / playbook)
  - `target_keyword`
  - `title`
  - `meta_description`
  - `h1`
  - `body_md` (markdown or HTML)
  - `status` (draft / pending_review / live)
  - `tags`
  - `hero_image_url` (static page image)
  - `og_image_url`
  - `created_at`, `updated_at`
  - `last_generated_at`

- (Optional, later) `seo_page_version`

  - For versioning different prompts/generations.

- (Optional, later) `seo_metrics_daily`

  - `page_id`
  - `date`
  - `impressions`, `clicks`, `avg_position`
  - `sessions`, `signups`

---

### 2.2 Media Asset Bank

- `media_asset`

  - `id`
  - `type` (`guide_hero`, `meeting_loop`, `concept_illustration`, `persona_avatar`)
  - `seo_page_id` (nullable)
  - `topic_id` (nullable)
  - `tags` (e.g. `{pricing, growth, decision}`)
  - `url_image` (PNG/JPEG)
  - `url_gif` (short loop)
  - `url_video` (MP4/WebM)
  - `created_at`

---

### 2.3 Social Posts

- `social_post`

  - `id`
  - `platform` (`twitter`, `linkedin`, `bluesky`)
  - `seo_page_id` → `seo_page.id`
  - `media_asset_id` → `media_asset.id` (nullable)
  - `text`
  - `link_url` (with UTM params)
  - `scheduled_at`
  - `posted_at`
  - `status` (pending / posted / failed / skipped)
  - `error_message` (nullable)
  - `approved` (bool; initial manual review)
  - `created_at`

---

### 2.4 Comments & Feedback

- `social_comment`

  - `id`
  - `platform`
  - `platform_post_id`
  - `platform_comment_id`
  - `social_post_id` → `social_post.id`
  - `author_handle`
  - `text`
  - `created_at` (time of comment)
  - `imported_at`
  - `sentiment` (positive / neutral / negative)
  - `intent` (question / praise / complaint / objection / feature_request / bug_report / off_topic)
  - `themes` (array of tags)
  - `needs_response` (bool)
  - `priority` (0–100)
  - `handled_status` (new / summarised / replied / escalated)
  - `reply_text_draft` (nullable)
  - `reply_status` (none / drafted / approved / posted)

- `feedback_summary`

  - `id`
  - `scope_type` (`topic` or `seo_page`)
  - `scope_id` (id of topic/page)
  - `period_start`, `period_end`
  - `summary_md` (markdown bullets)
  - `suggested_keywords` (JSON array)
  - `suggested_faqs` (JSON array of `{question, answer_draft}`)
  - `created_at`

---

## 3. Pipelines / Jobs

### 3.1 Topic & Keyword Discovery

**Trigger:** manually (via admin) or weekly job.

**Inputs:**

- Seed topics (short list).
- Competitor URLs (optional).
- Existing GSC queries (optional, later).

**Steps:**

1. Build a prompt for an LLM to:

   - Propose 5–10 core topics for the audience.
   - For each topic, propose 5–15 concrete search queries.
   - Label queries with `intent` and `funnel_stage`.

2. Parse JSON output.
3. Upsert `seo_topic` and `seo_keyword` rows.
4. Mark new topics as `status='idea'`.

**Outputs:**

- Populated `seo_topic` and `seo_keyword` tables with fresh ideas.

---

### 3.2 Page Idea Generation

**Trigger:** daily or on demand.

**Inputs:**

- `seo_topic` with `status='idea'` or `selected`.
- Attached `seo_keyword`s.

**Steps:**

1. Select topics and a subset of keywords per topic that:

   - Match desired intent (e.g. informational/commercial).
   - Match funnel stages (consideration/decision).

2. For each topic–keyword pair, ask LLM to:

   - Propose a single page idea: `page_type`, `working_title`, `slug`, `cta_focus`, short reasoning.

3. Insert new `seo_page` rows with:

   - `topic_id`, `target_keyword`, `slug`, `title`, `status='draft'`.

**Outputs:**

- Draft `seo_page` records awaiting content generation.

---

### 3.3 Page Content Generation

**Trigger:** when `seo_page.status='draft'` and `body_md` is null.

**Inputs:**

- `seo_page` row (title, slug, target keyword, page_type).
- Topic description and tags.
- Brand tone + claim rules.
- Optionally, previous `feedback_summary` for that topic/page.

**Steps:**

1. LLM call to generate:

   - `meta_description`
   - `h1`
   - `body_md` (full guide with headings, examples, CTA).

2. Optional second LLM pass:

   - As “editor” to enforce tone, remove risky claims, tighten structure.

3. Save content to `seo_page`.
4. Set `status='pending_review'`.

**Outputs:**

- Content-filled pages ready for human review and/or auto-publish.

---

### 3.4 Publishing

**Trigger:** manual approval, or auto for low-risk pages.

**Inputs:**

- `seo_page` with `status='pending_review'`.

**Steps:**

1. Human reviews and approves (or auto-approve based on rules).
2. Set `status='live'`, update `last_generated_at`.
3. Ensure Svelte route `/guides/[slug]` renders:

   - Title, meta, body, CTAs.

4. Update sitemap and robots if needed.

**Outputs:**

- Live URL for each guide.

---

### 3.5 Media Asset Generation

**Types:**

1. **Guide hero / OG image (per `seo_page`)**

   - HTML/CSS template that uses `title`, `target_keyword`, and brand colours.
   - Render via Puppeteer/Playwright → PNG.
   - Store as `media_asset` (`type='guide_hero'`) and update `seo_page.hero_image_url` / `og_image_url`.

2. **Meeting demo loops (few generic ones)**

   - Scripted demo route in app (`/demo/meeting`).
   - Record via Playwright video.
   - Trim & convert via ffmpeg → MP4 + GIF.
   - Store as `media_asset` (`type='meeting_loop'`) with tags.

3. **Conceptual illustrations**

   - Generate manually with an image model.
   - Tag by theme and store as `media_asset` (`type='concept_illustration'`).

**Outputs:**

- Reusable media assets linked to pages/topics or generic.

---

### 3.6 Social Bundle Generation

**Trigger:** when a `seo_page` transitions to `live`.

**Inputs:**

- `seo_page` (title, summary, URL).
- Optional: short summary derived from `body_md`.

**Steps:**

1. LLM prompt to produce JSON:

   - `twitter`: 2–3 short posts.
   - `linkedin`: 1–2 longer posts with different angles.

2. For each generated post:

   - Build `link_url` with UTM params.
   - Select best `media_asset` based on `seo_page.tags`, `topic_id`, and platform rules.
   - Create `social_post` rows with:

     - `platform`, `seo_page_id`, `media_asset_id`, `text`, `link_url`, `status='pending'`, `approved=false`.

   - Assign `scheduled_at` (staggered over coming days).

**Outputs:**

- A queue of `social_post` records for each new page.

---

### 3.7 Social Posting

**Trigger:** periodic worker (cron) or n8n flow.

**Inputs:**

- `social_post` where:

  - `status='pending'`
  - `approved=true`
  - `scheduled_at <= now()`.

**Steps:**

1. For each eligible post:

   - Upload media to platform if present.
   - Publish post via platform API (or via n8n connector).

2. On success:

   - Set `status='posted'`, `posted_at=now()`.

3. On error:

   - Set `status='failed'`, store `error_message`.

**Outputs:**

- Live social posts, tracked against pages.

---

### 3.8 Comment Ingestion

**Trigger:** periodic worker per platform (e.g. every 15–60 minutes).

**Inputs:**

- Platform credentials & API access.
- IDs of posts we’ve created (`social_post`).

**Steps:**

1. For each platform:

   - Fetch replies/comments to our posts within a time window.

2. For each new comment:

   - Upsert `social_comment` using `platform_post_id` + `platform_comment_id`.
   - Link to `social_post_id`.

**Outputs:**

- Fresh `social_comment` rows for downstream processing.

---

### 3.9 Comment Classification & Reply Drafting

**Trigger:** periodic worker (e.g. every 15 minutes).

**Inputs:**

- `social_comment` with `handled_status='new'`.

**Steps:**

1. LLM classification:

   - Input: comment text, original post text.
   - Output JSON: `sentiment`, `intent`, `themes[]`, `needs_response`, `priority`.
   - Update corresponding fields in `social_comment`.

2. For comments where `needs_response=true`:

   - LLM generates `reply_text_draft` (short, on-brand, safe).
   - Set `reply_status='drafted'`.

**Outputs:**

- Classified comments with drafted replies.

---

### 3.10 Comment Inbox & Reply Posting

**Admin UI:**

- List of comments needing attention, with filters:

  - By platform, by intent, by priority.

- For each:

  - Show comment, original post, classification, `reply_text_draft`.
  - Actions: **Approve**, **Edit & Approve**, **Skip/Escalate**.

**Worker for replies:**

- Select `social_comment` with:

  - `reply_status='approved'`.

- Post reply via API.
- On success: `reply_status='posted'`, `handled_status='replied'`.
- On error: mark as failed and store message.

---

### 3.11 Feedback Summarisation & Integration

**Trigger:** daily or weekly job.

**Inputs:**

- `social_comment` from a time window, grouped by `seo_page_id` and `topic_id`.

**Steps:**

1. For each page/topic:

   - Gather comments and basic engagement metrics.
   - LLM summarisation:

     - Key questions & objections.
     - Areas of confusion.
     - Suggested improvements or new FAQs.
     - Suggested new keywords/topics.

2. Write `feedback_summary` entry per scope.
3. **Feed into other pipelines:**

   - Add `suggested_keywords` into the next topic/keyword discovery run as extra seeds.
   - Pass relevant `feedback_summary` into:

     - Future page content refresh prompts.
     - Future social bundle prompts (to better address objections).

**Outputs:**

- Persistent summaries that inform future content and posts.

---

## 4. Governance & Guardrails

The Planner LLM should explicitly design:

- **Rate limits**

  - Max pages/week
  - Max social posts/day/platform
  - Max auto-replies/day

- **Human checkpoints**

  - Topic selection (from `seo_topic.idea` → `selected`)
  - Page approval (`pending_review` → `live`)
  - Social post approval (`social_post.approved`)
  - Reply approval for high-risk comment types

- **Tone & claims rules**

  - System-level instructions in all content and social prompts:

    - No guarantees of results.
    - No legal/financial/medical advice.
    - No hypey AI buzzword soup.
    - Helpful, pragmatic, respectful.

---

## 5. What the Planner LLM Should Do Next

When you hand this to another LLM, ask it to:

1. Turn each pipeline into:

   - Detailed sequence diagrams or flow descriptions.
   - Concrete Python task signatures and Svelte route specs.
   - Specific LLM prompts (system + user) and JSON schemas.

2. Propose:

   - Error-handling strategies (API failures, bad LLM output).
   - Monitoring/metrics for each subsystem.

3. Prioritise implementation into phases:

   - Phase 1: SEO Content Engine + hero images.
   - Phase 2: Social Autoposter + media bank usage.
   - Phase 3: Comment ingestion + manual replies.
   - Phase 4: Feedback loops + semi-auto replies.

---

a project can have many actions (and sub projects)
a meeting can have many projects and actions
an action can only be attributed to a single project
an action can have sub actions

mentors can assist with actions
expert panels can assist with meetings
expert panels are made up of mentors

--- the following is an AI ops 'self healing' style feature where the codebase auto corrects errors
At a high level, you want: **“when prod blows up, an AI engineer grabs the crash, ships a safe patch, and rolls it out”** on your DO stack.

You can get close, but it _must_ be sandboxed. Think:

> **Prod → Telemetry → Incident queue → AI-fixer in a dev clone → CI/tests → Controlled deploy to prod**

I’ll lay it out concretely with DigitalOcean + Docker + GitHub + Claude Code.

---

## 1. Overall architecture on DigitalOcean

Assume:

- App is containerised (Docker / docker-compose)
- Source of truth is GitHub
- CI/CD is GitHub Actions
- You already have (or will have) basic logging / error tracking

### Minimal DO setup

- **Droplet 1 – Prod**

  - Reverse proxy: Nginx / Traefik
  - App containers
  - Postgres (if self-hosted) or managed DO DB

- **Droplet 2 – Dev/AI-ops sandbox**

  - Git clone of repo
  - Claude Code CLI + your “AI ops” scripts
  - Runner for CI tests (or just let GitHub do CI and this box is only for AI editing)

- Optional later: **Droplet 3 – Staging** for canary deploys

---

## 2. The runtime failure → “AI ticket” flow

### 2.1 Capture failures in prod

Instrument the app so every “meeting failure” spits out:

- `meeting_id`
- Error (stack trace, message)
- Request context (user id, org, parameters, decision config)
- Relevant logs (last N lines from the meeting worker/container)

**Store this in a central place**:

- DB table `meeting_failures`
- Or a queue (e.g. Redis stream, pgmq, RabbitMQ, n8n workflow trigger)

Example DB schema:

```sql
CREATE TABLE meeting_failures (
  id BIGSERIAL PRIMARY KEY,
  meeting_id UUID NOT NULL,
  error_type TEXT,
  error_message TEXT,
  stack_trace TEXT,
  component TEXT,        -- e.g. "meeting-worker", "scheduler"
  occurred_at TIMESTAMP NOT NULL DEFAULT now(),
  raw_context JSONB
);
```

You also tag a “severity” and “auto-fix candidate” flag if you can (e.g. HTTP 5xx vs user error, transient LLM failure vs logic bug).

### 2.2 Trigger the AI ops pipeline

You then have a **background worker** that runs either:

- On the dev/AI-ops droplet, polling `meeting_failures` for new rows
- Or via something like n8n, listening to a webhook / queue

When it sees a failure that looks like a **code bug** (not just transient LLM outage), it:

1. Fetches the failure record(s)
2. Optionally enriches them with:

   - “Similar failures in last X hours”
   - Git commit hash currently deployed
   - Link to logs/dashboard (Grafana, etc.)

3. Prepares a **prompt + context bundle** for Claude Code.

---

## 3. How Claude Code fits in

You **do not** want Claude editing your live droplet. You want it editing the **git repo** in a controlled environment.

### 3.1 Repo-centric workflow

On the AI-ops droplet:

- Clone your GitHub repo:

  - `origin` = GitHub
  - `prod` branch = what’s currently deployed

- Install Claude Code CLI + your MCP tools
- Create a script `ai_fix_meeting_failure.py` (or similar) that:

  1. Creates a new branch:

     - `ai-fix/meeting-<meeting_id>` or `ai-fix/<error-signature>`

  2. Uses Claude Code to:

     - Read failing code paths (based on stack trace)
     - Propose a patch
     - Apply patch to the repo

  3. Runs tests
  4. If tests pass and risk checks pass:

     - Push branch to GitHub
     - Optionally auto-open PR via GitHub API
     - Optionally label PR `ai-autofix`, attach failure context

Claude prompt (in spirit):

- _System_: “You are the AI ops engineer. Only propose **minimal, non-breaking** patches that fix the specific bug, no feature work, no schema changes.”
- _User content_:

  - Error logs / stack trace
  - Snippets of relevant files
  - Your coding rules (from your existing governance framework)
  - “Do not modify: migrations, pricing logic, auth, billing, schema files.”

---

## 4. CI / Tests / Non-breaking guarantees

Your **guardrails live in CI**, not in blind trust of Claude.

### 4.1 CI pipeline for AI branches

Use GitHub Actions with something like:

1. **Static checks**

   - Lint (ruff/eslint)
   - Type checks (mypy/tsc)
   - Security checks (bandit, dependency scan)

2. **Unit tests**

   - Especially around the component that failed

3. **Integration/smoke tests**

   - Spin a temporary container stack (docker-compose) and:

     - Run a synthetic “meeting” flow
     - Ensure it completes successfully
     - Ensure core routes respond (healthcheck, login, start meeting, etc.)

4. **Policy checks**

   - Scripts that enforce **“non-breaking only”**, e.g.:

     - Reject if DB migrations changed
     - Reject if files under `billing/` or `auth/` changed
     - Reject if > N files changed or diff size > threshold
     - Reject if public API schema (OpenAPI spec) changed

If all pass, mark PR as **“safe candidate”**.

### 4.2 Automatic vs manual deploy

You have options:

- **Phase 1 (safer)**:

  - AI creates PR + passes CI
  - You get Slack / email:

    - “AI fix ready for bug X – click to merge and deploy”

  - You eyeball and hit merge

- **Phase 2 (limited auto-deploy)**:

  - For labelled, low-risk classes of bugs (timeouts, null checks, missing imports), auto-merge + deploy if:

    - Single file touched
    - No schema changes
    - Tests + smoke tests pass

  - Otherwise require human review

---

## 5. Deployment from GitHub to DigitalOcean

You probably want:

- **Images built in CI**, not on the droplet
- **GitHub → DO** via:

### Option A: Docker on Droplet + GitHub Actions

1. CI builds Docker image and pushes to Docker Hub / GHCR.
2. GitHub Action runs SSH step:

   - SSH into the droplet
   - `docker-compose pull && docker-compose up -d --no-deps <service>`
   - Or use a small deploy script on the droplet

3. Staging first, then prod:

   - For AI-autofixes, you can:

     - Deploy to staging droplet
     - Run a synthetic “meeting” end-to-end test hitting that staging URL
     - Only then deploy same image tag to prod.

### Option B: DigitalOcean App Platform

- CI pushes image
- DO App Platform auto-deploys when new image arrives
- You gate auto-deploys so only specific branches/tags (e.g. `prod`) trigger it.

Given your DIY tendencies and cost constraints, **Option A with 2–3 droplets + docker-compose + GitHub Actions** is likely the sweet spot.

---

## 6. Concrete “AI Ops” components you need to build

### A. Telemetry + failure capture

- Add error handlers in:

  - Meeting orchestration worker
  - LLM call layer (timeout, provider errors)
  - Any orchestrator (n8n / background queue)

- Write to `meeting_failures` table + log aggregator (Sentry, OpenTelemetry, etc.).

### B. AI-Ops worker service

Small Python service running on AI-ops droplet:

- Poll failures
- Deduplicate similar incidents
- Decide “eligible for AI fix?” (rules like: repeated identical stack trace, not user input error)
- Prepare context bundle:

  - Error logs
  - Last deployed commit hash
  - Git repo path

- Call Claude Code CLI (or via API with your own wrapper) to:

  - Create branch
  - Apply patch
  - Commit changes

- Push branch & open PR via GitHub API.

### C. CI guardrail scripts

- `check_non_breaking.sh`:

  - Fail if:

    - `migrations/` changed
    - `schema.sql` / `db/schema` changed
    - `billing/`, `auth/` touched (unless you explicitly allow)
    - More than N files changed

- Synthetic “meeting” test script:

  - Hit a test endpoint or run internal function that simulates:

    - Create test user
    - Create test meeting
    - Run full Bo1 meeting (short, cheap config)
    - Assert: final status = `completed`, no errors.

### D. Deployment hook

- GitHub Action:

  - Trigger: merge to `prod` branch
  - Jobs:

    - Build + push image
    - SSH to staging

      - Deploy new image
      - Run smoke tests

    - If staging pass:

      - SSH to prod
      - Deploy same tag

---

## 7. Risk boundaries for “non-breaking only”

Make it explicit in code & policy:

**Allowed for auto-fix:**

- Null/undefined checks
- Fixing missing imports / wrong variable names
- Obvious logic bug inside a single function
- Timeouts / retry logic around LLM calls
- Extra guards around external API responses
- Logging / metrics additions

**Not allowed (must be manual):**

- DB schema or migration changes
- Changes to auth / permissions / RLS
- Pricing / billing logic
- Changes to external contracts (APIs, webhooks)
- Big refactors / cross-cutting changes

Your AI prompt should clearly state this, and your CI script should enforce it.

---

## 8. How I’d roll this out in stages

1. **Stage 0 – Observability**

   - Meeting failure table + dashboards
   - Alerts to Slack/Email

2. **Stage 1 – AI as assistant**

   - AI-ops worker generates:

     - GitHub issues with suggested patches
     - PRs that you manually review & deploy

3. **Stage 2 – Semi-auto**

   - For low-risk classes, allow “one-click merge+deploy” from Slack/issue link.

4. **Stage 3 – Auto for narrow class**

   - “Non-breaking” auto-deploy pipeline for a very constrained set of bugs
   - Everything else still goes through human.
