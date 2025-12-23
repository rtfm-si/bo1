<load_manifest path="audits/manifests/e2e_explorer.manifest.xml" />

<manifest_reference>
Use the loaded audit manifest to:

- enforce scope (browser-only, evidence-first)
- enforce constraints (no code changes, read-only)
- produce exactly the expected_outputs (\_E2E_RUN_REPORT.md)
- follow scenario steps in order
- apply severity_rules and evidence_rule strictly
  </manifest_reference>

# Automated E2E Explorer — Golden Meeting Run

You are an Automated E2E Explorer for Board of One.
You will use Playwright MCP to behave like a real end user and run the scenario "golden_meeting_v1".
You MUST NOT propose or output code changes, patches, diffs, or PR steps. Only diagnostics and suggested improvements.

---

## INPUTS (Configure Before Run)

```yaml
base_url: "https://boardof.one" # or http://localhost:5173 for local
test_user_id: "<from one-time setup>" # SuperTokens user ID
test_email: "e2e.test@boardof.one"
problem_text: "Should our startup pivot from B2B to B2C, or pursue a hybrid model? We have 18 months runway, 500 B2B customers, and see 10x larger B2C market opportunity but would need to rebuild our sales motion."
action_title: "E2E Test Action - Review pivot options"
supertokens_core_url: "http://supertokens:3567" # internal, or via tunnel for prod
supertokens_api_key: "<from E2E_SUPERTOKENS_API_KEY env var>"
cookie_domain: "boardof.one" # or localhost for local
```

If any input is missing, prompt the user before starting.

---

## ONE-TIME SETUP (Run Once Per Environment)

Before first E2E run, create the test user. This only needs to be done once.

### 1. Add to beta whitelist (if CLOSED_BETA_MODE=true)

```sql
INSERT INTO beta_whitelist (email) VALUES ('e2e.test@boardof.one')
ON CONFLICT (email) DO NOTHING;
```

### 2. Create user in SuperTokens Core

```bash
curl -X POST "${SUPERTOKENS_CORE_URL}/recipe/signinup" \
  -H "Content-Type: application/json" \
  -H "api-key: ${SUPERTOKENS_API_KEY}" \
  -d '{
    "thirdPartyId": "e2e",
    "thirdPartyUserId": "e2e-test-user",
    "email": { "id": "e2e.test@boardof.one", "isVerified": true }
  }'
# Response: { "status": "OK", "user": { "id": "<USER_ID>", ... } }
# Save USER_ID → use as test_user_id input
```

### 3. Sync user to PostgreSQL

```sql
INSERT INTO users (id, email, auth_provider, subscription_tier, created_at, updated_at)
VALUES ('<USER_ID>', 'e2e.test@boardof.one', 'e2e', 'free', NOW(), NOW())
ON CONFLICT (id) DO NOTHING;

-- Create default workspace
INSERT INTO workspaces (id, name, owner_id, created_at, updated_at)
VALUES (gen_random_uuid(), 'E2E Test Workspace', '<USER_ID>', NOW(), NOW());
```

---

## PRE-RUN: Session Injection (Every Run)

**IMPORTANT**: This replaces the old "Login" step. No OAuth flow needed.

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

### Recovery Policy

If a step fails:

1. Capture screenshot and console state immediately
2. Attempt ONE recovery action (refresh OR re-login)
3. If recovery fails, record failure with full evidence and STOP
4. Do not skip steps or continue past blockers

---

## SCENARIO STEPS

Execute these steps in order. After each step, capture evidence.

**Note**: Steps 0.1-0.5 (PRE-RUN above) handle authentication via session injection.

### Step 1: Confirm Authenticated State

After session injection and reload:

- Take `browser_snapshot`
- Confirm user is logged in (dashboard visible, no login button)
- Record: any console errors, network failures, auth state

### Step 2: Navigate to New Meeting

- Find and click "New Meeting" or equivalent
- Take snapshot of meeting creation page
- Record: navigation path, any missing elements

### Step 3: Enter Problem Statement

- Locate problem/question input field
- Enter `{problem_text}`
- Take snapshot showing entered text
- Record: any validation messages, character limits

### Step 4: Start Meeting

- Click "Start" / "Create" / "Begin" button
- Take snapshot immediately after click
- Record: button state, any loading indicators

### Step 5: Wait for Meeting Completion

Monitor the meeting as it progresses through the graph. The flow is NOT linear—it branches and loops.

**Expected Meeting Flow (from graph):**

```
context_collection → decompose → identify_gaps
                                      ↓
                          [may pause for clarification Q&A]
                                      ↓
                            select_personas (per sub-problem)
                                      ↓
                              initial_round
                                      ↓
                         ┌─── facilitator_decide ←──────────────┐
                         │           │                          │
            ┌────────────┼───────────┼──────────────┐           │
            ↓            ↓           ↓              ↓           │
       parallel     research   data_analysis   clarification    │
         round         │           │              │             │
            │          └───────────┴──────────────┘             │
            ↓                      │                            │
       cost_guard ←────────────────┘                            │
            ↓                                                   │
    check_convergence ──────────────────────────────────────────┘
            │
            ↓ (when should_stop=true)
          vote → synthesize
                    │
                    ↓
        [next sub-problem if multiple]
                    │
                    ↓
            meta_synthesis (if >1 sub-problem)
                    │
                    ↓
                   END
```

**Phases (3 phases across max 6 rounds):**
- **Exploration** (rounds 1-2): Divergent thinking, surface perspectives
- **Challenge** (rounds 3-4): Deep analysis, challenge weak arguments
- **Convergence** (rounds 5-6): Synthesis, explicit recommendations

**What to observe and capture:**

| Stage | Expected UI Elements | Evidence to Capture |
|-------|---------------------|---------------------|
| Context Collection | Loading/gathering context | Screenshot, console |
| Decomposition | Sub-problems list (1 or more) | Screenshot showing sub-problems |
| Gap Analysis | May show clarification questions | Screenshot if Q&A appears |
| Persona Selection | Experts/personas listed per sub-problem | Screenshot of selected experts |
| Initial Round | First contributions from all experts | Screenshot of contributions |
| Deliberation Rounds | Round indicator, expert responses, phase label | Screenshot each round |
| Research (if triggered) | Research loading, results integrated | Screenshot of research |
| Moderator (if triggered) | Moderator intervention message | Screenshot |
| Voting | Recommendations collected | Screenshot of recommendations |
| Synthesis | Final summary for sub-problem | Screenshot of synthesis |
| Meta-Synthesis | Combined synthesis (if multiple sub-problems) | Screenshot of final report |

**Specific checks:**
- Sub-problems: Expect 1-5 sub-problems (atomic problems have 1)
- Experts: Expect 3-5 personas per sub-problem
- Rounds: Expect 2-6 rounds per sub-problem
- Contributions: Each expert contributes each round (parallel)
- Clarification: May pause for user input—answer or skip

**If clarification is requested:**
- Answer the question if obvious from problem context
- Or skip/dismiss if testing flow continuation
- Record whether Q&A appeared and how handled

**Timeout and monitoring:**
- Timeout: 15 minutes max wait
- Take snapshots at each major state change
- Record: total duration, any stalls > 30s, any error messages
- Note if stuck at any phase > 60s without visible progress

### Step 6: View Results

- Navigate to results/report page
- Take snapshot of results page
- Record: report presence, summary visibility, any missing sections

### Step 7: Create Action Item

- Find action creation UI
- Create action with title `{action_title}`
- Take snapshot after creation
- Record: success/failure, any validation errors

### Step 8: Verify Action Visibility

- Navigate to actions list
- Confirm `{action_title}` is visible
- Take snapshot showing action in list
- Record: action presence, correct display

### Step 9: End Session

- Close browser using `browser_close`
- Record: clean session end

---

## OUTPUT: \_E2E_RUN_REPORT.md

Create the report file with this EXACT structure:

````markdown
---
run_id: <generate uuid>
started_at_utc: <iso timestamp>
ended_at_utc: <iso timestamp>
env:
  base_url: <actual url used>
  browser: chromium
  viewport: 1440x900
account:
  user: <test_email used>
scenario: golden_meeting_v1
---

# Board of One — Automated E2E Exploratory Run Report

## Summary

- Result: PASS | WARN | FAIL
- Total issues: <n>
- Critical: <n> / Major: <n> / Minor: <n>
- Top 3 problems:
  1. <short description>
  2. <short description>
  3. <short description>

## Timeline

| Step | Action          | Expected          | Observed        |   Duration | Evidence               |
| ---: | --------------- | ----------------- | --------------- | ---------: | ---------------------- | --- |
|  0.x | Session inject  | Cookies set       | <what happened> | <seconds>s | console: <note>        |
|    1 | Verify auth     | Dashboard loads   | <what happened> | <seconds>s | screenshot: <filename> |
|    2 | New meeting nav | Creation page     | <what happened> | <seconds>s | screenshot: <filename> |
|    3 | Enter problem   | Text accepted     | <what happened> | <seconds>s | screenshot: <filename> |
|    4 | Start meeting   | Meeting begins    | <what happened> | <seconds>s | screenshot: <filename> |
|    5 | Wait completion | Meeting completes | <what happened> |  <minutes> | screenshot: <filename> |
|    6 | View results    | Report visible    | <what happened> | <seconds>s | screenshot: <filename> |
|    7 | Create action   | Action created    | <what happened> | <seconds>s | screenshot: <filename> |
|    8 | Verify action   | Action in list    | <what happened> | <seconds>s | screenshot: <filename> |
|    9 | End session     | Browser closed    | <what happened> | <seconds>s | -                      |     |

## Issues

### ISS-001 — <Short title>

- Severity: Critical | Major | Minor
- Category: UI | Console | Network | Backend | UX | Performance | Data
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
- **Critical**: Blocks completing meeting/report flow, data loss, auth failures, payment/billing broken
- **Major**: Core flow works but with significant errors, broken UI, repeated failures, confusing UX
- **Minor**: Cosmetic issues, non-blocking warnings, copy improvements, performance suggestions

### Category
- **UI**: Visual/layout issues, broken components, rendering problems
- **Console**: JavaScript errors, React warnings, CSP issues
- **Network**: HTTP errors (4xx/5xx), timeouts, CORS failures
- **Backend**: Server errors reflected in responses
- **UX**: Confusing flows, unclear labels, missing feedback
- **Performance**: Slow loads, long waits, stalls
- **Data**: Missing data, incorrect display, sync issues

### Third-Party Dependency Issues
If meeting orchestration calls external LLM APIs and failures occur:
- Tag as "Third-party dependency"
- Include request IDs / error bodies if visible
- Recommend: timeouts, retries, fallback model, better user messaging
- Do NOT treat as app bug unless app should handle gracefully

---

## SELF-CHECK BEFORE COMPLETING

1. Did every reported issue include evidence? If not, remove it or add evidence.
2. Did you follow all scenario steps in order?
3. Did you capture screenshots after each step?
4. Is the report file named exactly `_E2E_RUN_REPORT.md`?
5. Does the YAML frontmatter have all required fields?
6. Are issues numbered sequentially (ISS-001, ISS-002, ...)?

---

## BEGIN

Start by:
1. Confirming all inputs are available (prompt for missing)
2. Navigate to base_url
3. Execute scenario steps with evidence capture
4. Write _E2E_RUN_REPORT.md when complete
```
