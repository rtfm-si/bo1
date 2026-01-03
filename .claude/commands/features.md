<load_manifest path="audits/manifests/feature_explorer.manifest.xml" />

<manifest_reference>
Use the loaded audit manifest to:

- enforce scope (browser-only, evidence-first, NO meetings)
- enforce constraints (no code changes, read-only except test data)
- produce exactly the expected_outputs (_FEATURE_EXPLORER_REPORT.md)
- follow scenario steps in order (respecting feature area dependencies)
- apply severity_rules and evidence_rule strictly
- track feature_coverage_matrix for comprehensive reporting
</manifest_reference>

# Comprehensive Feature Explorer — All Features Except Meetings

You are a Comprehensive Feature Explorer for Board of One.
You will use Playwright MCP to behave like a real end user and test ALL application features EXCEPT meetings/deliberations.
You MUST NOT propose or output code changes, patches, diffs, or PR steps. Only diagnostics and suggested improvements.

---

## INPUTS (Configure Before Run)

```yaml
base_url: "https://boardof.one" # or http://localhost:5173 for local
test_user_id: "<from one-time setup>" # SuperTokens user ID
test_email: "e2e.test@boardof.one"
supertokens_core_url: "http://supertokens:3567" # internal, or via tunnel for prod
supertokens_api_key: "<from E2E_SUPERTOKENS_API_KEY env var>"
cookie_domain: "boardof.one" # or localhost for local
```

If any input is missing, prompt the user before starting.

---

## ONE-TIME SETUP (Same as e2e.md)

This test uses the same test user as the meeting E2E. If not already set up, see `/e2e` command for one-time user setup instructions.

---

## PRE-RUN: Session Injection (Every Run)

**IMPORTANT**: This replaces OAuth flow. No login page interaction needed.

### Step 0.1: Create Session via SuperTokens Core API

Use Bash to create a fresh session for the test user:

```bash
SESSION_RESPONSE=$(curl -s -X POST "${SUPERTOKENS_CORE_URL}/recipe/session" \
  -H "Content-Type: application/json" \
  -H "api-key: ${SUPERTOKENS_API_KEY}" \
  -d "{
    \"userId\": \"${TEST_USER_ID}\",
    \"userDataInJWT\": {},
    \"userDataInDatabase\": {},
    \"enableAntiCsrf\": false
  }")

ACCESS_TOKEN=$(echo $SESSION_RESPONSE | jq -r '.accessToken.token')
REFRESH_TOKEN=$(echo $SESSION_RESPONSE | jq -r '.refreshToken.token')
```

### Step 0.2: Open base_url (unauthenticated)

Use `browser_navigate` to `{base_url}` to establish page context.

### Step 0.3: Inject Session Cookies via Playwright

Use `browser_evaluate` to set cookies:

```javascript
// For production (HTTPS)
document.cookie = `sAccessToken=${ACCESS_TOKEN}; path=/; domain=${COOKIE_DOMAIN}; SameSite=Lax; Secure`;
document.cookie = `sRefreshToken=${REFRESH_TOKEN}; path=/; domain=${COOKIE_DOMAIN}; SameSite=Lax; Secure`;

// For localhost (HTTP)
document.cookie = `sAccessToken=${ACCESS_TOKEN}; path=/; SameSite=Lax`;
document.cookie = `sRefreshToken=${REFRESH_TOKEN}; path=/; SameSite=Lax`;
```

### Step 0.4: Reload to apply session

Use `browser_navigate` to reload `{base_url}`.

### Step 0.5: Verify authenticated state

Take `browser_snapshot` and confirm:

- Dashboard/home content loads (not landing page)
- User menu or avatar visible
- No "Sign in" button

**If NOT authenticated**: Record as Critical issue (ISS-001: Session injection failed) and STOP.

---

## CORE REQUIREMENTS

### Evidence Capture (MANDATORY)

After EVERY step, you MUST:

1. Take a screenshot using `browser_take_screenshot`
2. Check console messages using `browser_console_messages`
3. Check network requests using `browser_network_requests`
4. Note any visible UI issues (stuck loaders, broken layout, disabled buttons)

### Issue Reporting Rule

**CRITICAL: No issue may be reported without at least one evidence item.**
Every issue block MUST include:

- Screenshot filename, OR
- Console log excerpt, OR
- Network endpoint + status code, OR
- Precise UI location reference

### Recovery Policy (Feature Explorer Specific)

Unlike meeting E2E which stops on blocker, Feature Explorer continues:

1. Capture screenshot and console state immediately
2. Attempt ONE recovery action (refresh OR navigate back)
3. If recovery fails, record failure and SKIP to next feature area
4. Continue testing remaining features
5. Never abandon entire test for single feature failure

---

## SCENARIO STEPS

Execute steps in order. Each feature area can be tested independently after auth.

### PART 1: DASHBOARD (Steps 1.1-1.5)

#### Step 1.1: Verify Dashboard Loads

- Confirm dashboard page loads after auth
- Take snapshot of full dashboard
- Record: all visible widgets, any missing sections

#### Step 1.2: Activity Heatmap

- Locate activity heatmap component
- Take screenshot
- Record: data presence, date range, interaction state

#### Step 1.3: Pending Reminders Widget

- Locate reminders/tasks widget
- Take screenshot
- Record: reminder count, action items shown

#### Step 1.4: Value Metrics Panel

- Locate metrics/KPI display
- Take screenshot
- Record: metric values, any loading states

#### Step 1.5: Recent Meetings Widget

- Locate recent meetings list
- Take screenshot
- Record: meeting count, status indicators

---

### PART 2: CONTEXT MANAGEMENT (Steps 2.1-2.10)

#### Step 2.1: Navigate to Context Overview

- Find and click context/business context link
- Take snapshot of context page
- Record: navigation path, page load state

#### Step 2.2: View Business Context

- Review existing context fields (or note if empty)
- Take screenshot
- Record: field population, any validation states

#### Step 2.3: Edit Business Context

- Click edit or modify a field
- Make a minor test change (e.g., add "E2E Test" to notes)
- Save and verify
- Take screenshot
- Record: save success, any errors, field persistence

#### Step 2.4: Navigate to Metrics

- Find metrics configuration page
- Take snapshot
- Record: custom metrics list, add button visibility

#### Step 2.5: Add/View Custom Metrics

- If no metrics: attempt to add a test metric
- If metrics exist: view details
- Take screenshot
- Record: metric CRUD capability, validation

#### Step 2.6: Navigate to Competitors

- Find competitor tracking page
- Take snapshot
- Record: competitor list, add button, tier limits shown

#### Step 2.7: Add Test Competitor

- Click add competitor
- Enter: "E2E Test Competitor Inc"
- Save and verify addition
- Take screenshot
- Record: add success, tier limit enforcement

#### Step 2.8: Trigger Competitor Enrichment

- Click enrich/refresh on test competitor
- Wait for enrichment (may take 10-30s)
- Take screenshot
- Record: enrichment status, data populated, errors

#### Step 2.9: View Market Trends

- Navigate to trends panel
- Take screenshot
- Record: trend data presence, refresh capability

#### Step 2.10: Check Key Metrics Display

- Navigate to key metrics view
- Take screenshot
- Record: metric cards, values, comparison data

#### Step 2.11: Navigate to Session Sharing

- Find a completed meeting/session (from meetings list or dashboard)
- Open the session detail view
- Take screenshot
- Record: share button visibility, session status

#### Step 2.12: Create Share Link

- Click share button to open share modal
- Select TTL option (7 days)
- Generate share link
- Take screenshot
- Record: link generation success, copy button, TTL display

#### Step 2.13: Test Public Share Link

- Copy the generated share link
- Open new tab and navigate to share link
- Take screenshot
- Record: public view loads, data visible, owner name masked

#### Step 2.14: Revoke Share Link

- Return to share modal
- Revoke the share link
- Take screenshot
- Record: revocation success, link invalidated

---

### PART 3: MENTOR SESSIONS (Steps 3.1-3.11)

#### Step 3.1: Navigate to Mentor

- Find and click mentor/advisor link
- Take snapshot of mentor page
- Record: chat interface, persona selector visibility

#### Step 3.2: Select Data Analyst Persona

- Click persona selector
- Choose "Data Analyst" persona
- Take screenshot
- Record: persona options available, selection confirmation

#### Step 3.3: Send Test Message

- Enter: "What metrics should I track for a SaaS business?"
- Send message
- Wait for streaming response (up to 60s)
- Take screenshot of response
- Record: streaming behavior, response quality, latency

#### Step 3.4: Switch to Sales Coach Persona

- Click persona selector again
- Choose "Sales Coach" persona
- Take screenshot
- Record: persona switch, chat context handling

#### Step 3.5: Send Follow-up Message

- Enter: "How should I structure my sales pipeline?"
- Send and wait for response
- Take screenshot
- Record: persona-appropriate response, context awareness

#### Step 3.6: View Conversation History

- Navigate to conversation history list
- Take screenshot
- Record: conversation count, timestamps, persona labels

#### Step 3.7: Return to Previous Conversation

- Click on an earlier conversation
- Verify messages load
- Take screenshot
- Record: history retrieval, message integrity

#### Step 3.8: Test @mention Autocomplete

- Start a new message
- Type "@" to trigger mention autocomplete
- Take screenshot
- Record: autocomplete popup appears, mention types shown (meetings, actions, datasets)

#### Step 3.9: Use @mention in Message

- Select a meeting or action from autocomplete
- Complete message: "What were the key outcomes from @[selected item]?"
- Send and wait for response
- Take screenshot
- Record: mention resolved, context included in response

#### Step 3.10: Check Context Sources Badge

- Look for context sources indicator in response
- Take screenshot
- Record: sources badge visibility, referenced items listed

#### Step 3.11: Test Repeated Topics Detection

- If available, check for repeated topics indicator
- Take screenshot
- Record: repeated topics shown, suggestions for patterns

---

### PART 4: DATASETS (Steps 4.1-4.7)

#### Step 4.1: Navigate to Datasets

- Find and click datasets link
- Take snapshot of datasets page
- Record: existing datasets, upload button visibility

#### Step 4.2: Upload Test CSV

Create a simple test CSV first:

```csv
Month,Revenue,Customers
Jan,10000,100
Feb,12000,120
Mar,15000,150
```

- Click upload
- Select/drag the test file
- Wait for processing
- Take screenshot
- Record: upload progress, validation, success/failure

#### Step 4.3: View Dataset Profile

- Click on uploaded dataset
- View profile/summary tab
- Take screenshot
- Record: column stats, data types, row count

#### Step 4.4: Ask Dataset Question

- Navigate to Q&A/chat for dataset
- Enter: "What's the trend in revenue?"
- Send and wait for response
- Take screenshot
- Record: response content, chart generation

#### Step 4.5: Verify Chart Generation

- Check if chart was generated with response
- Take screenshot of chart (if present)
- Record: chart type, accuracy, interactivity

#### Step 4.6: View Dataset Conversations

- Navigate to conversation history for dataset
- Take screenshot
- Record: conversation list, message persistence

#### Step 4.7: Delete Test Dataset

- Find delete option for test dataset
- Confirm deletion
- Verify removal from list
- Take screenshot
- Record: delete success, confirmation dialog

---

### PART 5: DATA ANALYSIS (Steps 5.1-5.3)

#### Step 5.1: Navigate to Analysis

- Find and click analysis link
- Take snapshot of analysis page
- Record: interface layout, input fields

#### Step 5.2: Ask General Question

- Enter: "How can I analyze customer churn?"
- Send and wait for response
- Take screenshot
- Record: guidance quality, recommended approaches

#### Step 5.3: Verify Guidance Response

- Review response for actionable guidance
- Take screenshot
- Record: response completeness, relevance

---

### PART 6: PROJECTS (Steps 6.1-6.6)

#### Step 6.1: Navigate to Projects

- Find and click projects link
- Take snapshot of projects page
- Record: project list, create button, filters

#### Step 6.2: Create Test Project

- Click create project
- Enter name: "E2E Test Project"
- Enter description: "Created by feature explorer"
- Save project
- Take screenshot
- Record: creation success, project details

#### Step 6.3: View Project Details

- Click on created project
- View details page
- Take screenshot
- Record: project fields, action list, session list

#### Step 6.4: View Project Gantt

- Navigate to Gantt view for project
- Take screenshot
- Record: Gantt rendering, timeline display

#### Step 6.5: Check Auto-generated Suggestions

- Look for project suggestions based on context
- Take screenshot
- Record: suggestions presence, relevance

#### Step 6.6: Update Project Status

- Change project status (e.g., active → on_hold)
- Save and verify
- Take screenshot
- Record: status update success, UI feedback

---

### PART 7: ACTIONS (Steps 7.1-7.7)

#### Step 7.1: Navigate to Actions

- Find and click actions link
- Take snapshot of actions page
- Record: action list, view options

#### Step 7.2: View Kanban Board

- Switch to Kanban view
- Take screenshot
- Record: columns displayed, action cards, drag capability

#### Step 7.3: View Global Gantt

- Switch to Gantt view
- Take screenshot
- Record: timeline rendering, dependencies shown

#### Step 7.4: Filter Actions

- Apply filter by status or project
- Take screenshot
- Record: filter functionality, result accuracy

#### Step 7.5: View Action Detail

- Click on an action (if any exist)
- View detail modal/page
- Take screenshot
- Record: action fields, update options, history

#### Step 7.6: Test Status Transition

- If action exists, change status (e.g., backlog → in_progress)
- Save and verify
- Take screenshot
- Record: transition success, Kanban update

#### Step 7.7: Test Dependency UI

- If multiple actions exist, try adding dependency
- Take screenshot
- Record: dependency UI, validation

---

### PART 8: REPORTS (Steps 8.1-8.3)

#### Step 8.1: Competitor Reports

- Navigate to competitor reports
- Take snapshot
- Record: report content, competitor data, charts

#### Step 8.2: Meetings Report

- Navigate to meetings history report
- Take snapshot
- Record: meeting list, statistics, filters

#### Step 8.3: Benchmarks Report

- Navigate to benchmarks report
- Take snapshot
- Record: benchmark data, peer comparisons

---

### PART 9: SETTINGS - ACCOUNT (Steps 9.1-9.3)

#### Step 9.1: Navigate to Account Settings

- Find and click settings → account
- Take snapshot
- Record: account fields, edit options

#### Step 9.2: View Account Information

- Review displayed account info
- Take screenshot
- Record: email, name, profile data

#### Step 9.3: Check Profile Editing

- Verify edit capability (button/form)
- Take screenshot (do NOT save changes)
- Record: edit form fields, validation

---

### PART 10: SETTINGS - SECURITY (Steps 10.1-10.7)

#### Step 10.1: Navigate to Security Settings

- Navigate to settings → security
- Take snapshot
- Record: security options available

#### Step 10.2: Check 2FA Status

- Look for 2FA/TOTP section
- Take screenshot
- Record: 2FA enabled/disabled status, setup button visibility

#### Step 10.3: Verify Password UI

- Look for password change option
- Take screenshot (do NOT change password)
- Record: password form presence, requirements shown

#### Step 10.4: Initiate 2FA Setup

- Click "Enable 2FA" or "Setup 2FA" button
- Wait for QR code to generate
- Take screenshot
- Record: QR code displayed, secret key shown, authenticator instructions

#### Step 10.5: View Backup Codes

- Look for backup codes section (may appear after setup initiation)
- Take screenshot
- Record: backup codes count (usually 10), copy/download options

#### Step 10.6: Test 2FA Verification UI

- Look for TOTP code input field
- Take screenshot (do NOT complete setup - would lock account)
- Record: 6-digit input field, verify button, cancel option

#### Step 10.7: Cancel 2FA Setup

- Click cancel/back to exit setup without enabling
- Take screenshot
- Record: clean exit, no 2FA enabled, settings preserved

---

### PART 11: SETTINGS - PRIVACY (Steps 11.1-11.6)

#### Step 11.1: Navigate to Privacy Settings

- Navigate to settings → privacy
- Take snapshot
- Record: privacy options listed

#### Step 11.2: View GDPR Consent

- Find GDPR/consent section
- Take screenshot
- Record: consent status, date, options

#### Step 11.3: Check Data Export

- Find data export option
- Take screenshot
- Record: export button, format options

#### Step 11.4: Check Data Retention

- Find retention period setting
- Take screenshot
- Record: current setting, options available

#### Step 11.5: Check Account Deletion UI

- Find account deletion option
- Take screenshot (do NOT delete)
- Record: deletion flow, warnings shown

#### Step 11.6: Check Research Sharing Consent

- Look for research sharing / anonymized data consent option
- Take screenshot
- Record: consent status (opted in/out), toggle functionality, explanation text

---

### PART 12: SETTINGS - BILLING (Steps 12.1-12.4)

#### Step 12.1: Navigate to Billing

- Navigate to settings → billing
- Take snapshot
- Record: billing page layout

#### Step 12.2: View Current Plan

- Check displayed plan information
- Take screenshot
- Record: plan tier, features, limits

#### Step 12.3: Check Upgrade Options

- Find upgrade/change plan option
- Take screenshot
- Record: available plans, pricing display

#### Step 12.4: Test Checkout Initiation

- Click upgrade (if available)
- Verify Stripe checkout starts
- Take screenshot
- Record: checkout redirect, back navigation
- NOTE: Do NOT complete payment

---

### PART 13: SETTINGS - WORKSPACE (Steps 13.1-13.5)

#### Step 13.1: Navigate to Workspace Settings

- Navigate to settings → workspace
- Take snapshot
- Record: workspace info displayed

#### Step 13.2: View Workspace Details

- Review workspace name, settings
- Take screenshot
- Record: editable fields, save options

#### Step 13.3: Check Member List

- View workspace members
- Take screenshot
- Record: member count, roles displayed

#### Step 13.4: Verify Invitation Capability

- Find invite member option
- Take screenshot
- Record: invite form/button, email input

#### Step 13.5: Check Role Management

- Look at role assignment UI
- Take screenshot
- Record: role options, permissions display

---

### PART 14: SETTINGS - INTEGRATIONS (Steps 14.1-14.5)

#### Step 14.1: Navigate to Integrations

- Navigate to settings → integrations
- Take snapshot
- Record: integrations page layout

#### Step 14.2: View Available Integrations

- List all shown integrations (calendar, etc.)
- Take screenshot
- Record: integration types, connect buttons

#### Step 14.3: Check Connection Status

- Review status indicators for each
- Take screenshot
- Record: connected vs available states

#### Step 14.4: Test Google Calendar Connect

- Find Google Calendar integration
- Click connect button
- Take screenshot of OAuth redirect or modal
- Record: OAuth flow initiates, scopes requested
- NOTE: Do NOT complete OAuth - just verify flow starts

#### Step 14.5: Cancel Calendar Connection

- Cancel/close the OAuth flow
- Return to integrations page
- Take screenshot
- Record: clean return, no connection created

---

### PART 15: ONBOARDING & WELCOME (Steps 15.1-15.4)

#### Step 15.1: Check Onboarding Progress

- Look for onboarding indicator/checklist
- Take screenshot
- Record: progress percentage, steps shown

#### Step 15.2: Verify Tour Availability

- Check if guided tour is available/completed
- Take screenshot
- Record: tour trigger, completion status

#### Step 15.3: Navigate to Welcome Page

- Navigate to /welcome page
- Take screenshot
- Record: page loads, personalized greeting, demo questions visible

#### Step 15.4: Test Demo Questions

- View demo/suggested questions
- Click refresh to get new suggestions (if available)
- Take screenshot
- Record: question categories, question relevance to context, click behavior

---

### PART 16: FEEDBACK & RATINGS (Steps 16.1-16.3)

#### Step 16.1: Locate Feedback UI

- Find feedback/rating submission option
- Take screenshot
- Record: feedback button location, form type

#### Step 16.2: Verify Rating Capability

- Check rating UI (thumbs up/down)
- Take screenshot (do NOT submit)
- Record: rating options, submission flow

#### Step 16.3: Test Feedback Form

- Find feedback submission form (feature request / problem report)
- Open feedback modal
- Take screenshot
- Record: form fields, category options, submit button
- NOTE: Do NOT submit feedback

---

### PART 17: SEO MODULE (Steps 17.1-17.5)

#### Step 17.1: Navigate to SEO

- Navigate to /seo page
- Take snapshot
- Record: page loads, main sections visible

#### Step 17.2: View Keyword Research

- Look for keyword research section
- Take screenshot
- Record: keyword input, suggestion display

#### Step 17.3: Check Topic Management

- Look for topic/content management section
- Take screenshot
- Record: topic list, add topic UI

#### Step 17.4: View Quota/Limits

- Check remaining quota display
- Take screenshot
- Record: quota indicator, tier limits shown

#### Step 17.5: Check Autopilot Settings

- Look for autopilot configuration
- Take screenshot
- Record: autopilot toggle, scheduling options

---

### PART 18: HELP CENTER (Steps 18.1-18.4)

#### Step 18.1: Navigate to Help

- Navigate to /help page
- Take snapshot
- Record: page layout, search bar, categories

#### Step 18.2: Search Help Articles

- Enter search query: "getting started"
- Take screenshot
- Record: search results, article previews

#### Step 18.3: View Help Category

- Click on a category in sidebar
- Take screenshot
- Record: category articles, navigation

#### Step 18.4: View Help Article

- Click on an article
- Take screenshot
- Record: article content, formatting, back navigation

---

### PART 19: CLEANUP & END (Steps 19.1-19.3)

#### Step 19.1: Delete Test Project

- Navigate back to projects
- Delete "E2E Test Project" if created
- Verify deletion
- Take screenshot
- Record: delete success

#### Step 19.2: Delete Test Competitor

- Navigate to competitors
- Delete "E2E Test Competitor Inc" if created
- Verify deletion
- Take screenshot
- Record: delete success

#### Step 19.3: End Session

- Close browser using `browser_close`
- Record: clean session end

---

## OUTPUT: _FEATURE_EXPLORER_REPORT.md

Create the report file with this EXACT structure:

````markdown
---
run_id: <generate uuid>
started_at_utc: <iso timestamp>
ended_at_utc: <iso timestamp>
total_duration_minutes: <calculated>
env:
  base_url: <actual url used>
  browser: chromium
  viewport: 1440x900
account:
  user: <test_email used>
  tier: <subscription tier>
scenario: feature_coverage_v1
---

# Board of One — Comprehensive Feature Explorer Report

## Summary

- Result: PASS | WARN | FAIL
- Total features tested: <n>
- Total issues: <n>
- Critical: <n> / Major: <n> / Minor: <n>
- Top 3 problems:
  1. <short description>
  2. <short description>
  3. <short description>

## Feature Coverage Matrix

| Feature Area   | Steps | Passed | Failed | Skipped | Status |
| -------------- | ----: | -----: | -----: | ------: | ------ |
| Dashboard      |     5 |      x |      x |       x | PASS   |
| Context+Share  |    14 |      x |      x |       x | WARN   |
| Mentor+Mention |    11 |      x |      x |       x | PASS   |
| Datasets       |     7 |      x |      x |       x | PASS   |
| Analysis       |     3 |      x |      x |       x | PASS   |
| Projects       |     6 |      x |      x |       x | PASS   |
| Actions        |     7 |      x |      x |       x | WARN   |
| Reports        |     3 |      x |      x |       x | PASS   |
| Account        |     3 |      x |      x |       x | PASS   |
| Security+2FA   |     7 |      x |      x |       x | PASS   |
| Privacy+GDPR   |     6 |      x |      x |       x | PASS   |
| Billing        |     4 |      x |      x |       x | PASS   |
| Workspace      |     5 |      x |      x |       x | PASS   |
| Integrations   |     5 |      x |      x |       x | PASS   |
| Onboarding     |     4 |      x |      x |       x | PASS   |
| Feedback       |     3 |      x |      x |       x | PASS   |
| SEO Module     |     5 |      x |      x |       x | PASS   |
| Help Center    |     4 |      x |      x |       x | PASS   |
| **TOTAL**      |   102 |      x |      x |       x |        |

## Timeline

| Step | Feature Area | Action            | Expected          | Observed        | Duration   | Evidence               |
| ---: | ------------ | ----------------- | ----------------- | --------------- | ---------: | ---------------------- |
|  0.x | Auth         | Session inject    | Cookies set       | <what happened> | <seconds>s | console: <note>        |
|  1.1 | Dashboard    | Load dashboard    | Widgets visible   | <what happened> | <seconds>s | screenshot: <filename> |
|  ... | ...          | ...               | ...               | ...             | ...        | ...                    |

## Issues

### ISS-001 — <Short title>

- Severity: Critical | Major | Minor
- Category: UI | Console | Network | Backend | UX | Performance | Data | GDPR
- Feature Area: <Dashboard | Context | Mentor | etc.>
- Where: <page/route + component if known>
- Repro steps:
  1. <step>
  2. <step>
- Observed:
  - <what actually happened>
- Expected:
  - <what should happen>
- Evidence:
  - Screenshot: <filename>
  - Console: `<key lines>`
  - Network: `<endpoint + status>`
- Likely cause (hypothesis):
  - <educated guess>
- Suggested improvements / fixes (no code):
  - <actionable recommendation>
- Workaround (if any):
  - <temporary solution>

### ISS-002 — ...

(repeat for each issue)

## Tier-Specific Notes

Test account tier: <free | starter | pro | enterprise>

| Feature            | Tier Limit Hit | Expected Behavior | Actual Behavior |
| ------------------ | -------------- | ----------------- | --------------- |
| Competitors        | <yes/no>       | Max 3 (free)      | <observed>      |
| Mentor Convos      | <yes/no>       | Limited (free)    | <observed>      |
| Dataset Q&A        | <yes/no>       | Limited (free)    | <observed>      |

## Recommendations (Prioritized)

1. <highest priority fix>
2. <next priority>
3. <etc>

## Appendix

### Console excerpts

```txt
<relevant console errors/warnings>
```
````

### Network failures

| Method | URL      | Status | Notes           |
| ------ | -------- | ------ | --------------- |
| GET    | /api/... | 500    | <error message> |
| ...    | ...      | ...    | ...             |

```

---

## CLASSIFICATION RULES

### Severity
- **Critical**: Feature completely broken, data loss, auth failures, payment broken, GDPR violations
- **Major**: Feature works but with significant errors, broken UI, confusing UX, data inconsistency
- **Minor**: Cosmetic issues, non-blocking warnings, copy improvements, performance suggestions

### Category
- **UI**: Visual/layout issues, broken components, rendering problems
- **Console**: JavaScript errors, React warnings, CSP issues
- **Network**: HTTP errors (4xx/5xx), timeouts, CORS failures
- **Backend**: Server errors reflected in responses
- **UX**: Confusing flows, unclear labels, missing feedback
- **Performance**: Slow loads, long waits, stalls
- **Data**: Missing data, incorrect display, sync issues
- **GDPR**: Privacy violations, consent issues, data handling problems

---

## SELF-CHECK BEFORE COMPLETING

1. Did every reported issue include evidence? If not, remove it or add evidence.
2. Did you test all 19 feature areas (102 steps)?
3. Did you capture screenshots after each major step?
4. Is the report file named exactly `_FEATURE_EXPLORER_REPORT.md`?
5. Does the YAML frontmatter have all required fields?
6. Are issues numbered sequentially (ISS-001, ISS-002, ...)?
7. Is the feature coverage matrix complete with all 18 rows?
8. Did you clean up test data (project, competitor)?
9. Did you test session sharing with a completed meeting?
10. Did you test mentor @mentions functionality?

---

## BEGIN

Start by:
1. Confirming all inputs are available (prompt for missing)
2. Navigate to base_url
3. Execute scenario steps with evidence capture
4. Track feature coverage matrix throughout
5. Write _FEATURE_EXPLORER_REPORT.md when complete
```
