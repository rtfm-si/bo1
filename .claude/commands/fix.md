Bo1 Live UI Walkthrough: Local “Live UX Test” with Playwright MCP

GOAL
Run an efficient, local-only “live UI” test of the app using Playwright MCP:

- Launch the app in a real browser session (via Playwright).
- Exercise the main user flows end-to-end.
- Watch backend logs and browser console for errors.
- Verify HTTP responses, UI states, and basic UX expectations.
- Produce a short report of issues and suggested fixes.

This is a **local-only** test: only hit localhost / 127.0.0.1, never remote prod/staging.

CONSTRAINTS

- Follow all governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any frontend-level or folder-level CLAUDE/manifest files.
- Use Playwright MCP for all browser interactions.
- If a shell / logs / docker MCP tool is available, use it to tail logs; otherwise, describe which log commands should be run.
- Keep reasoning shallow and outputs concise.
- Minimise screenshots and traces to failing/interesting cases only.
- Do NOT hit production or external URLs; default to localhost dev URL.

ASSUMPTIONS

- The dev server either:
  - Is already running on localhost, OR
  - Can be started via the usual dev command (e.g. `npm run dev`, `pnpm dev`, etc.).
- A Playwright config exists (e.g. `playwright.config.*`) or a standard `npx playwright` setup is available.

---

## STEP 1 – DISCOVER DEV URL & PLAYWRIGHT SETUP

1. Inspect:
   - `package.json`
   - Svelte/SvelteKit config
   - `playwright.config.*` (if present)
2. Infer:
   - Dev URL (e.g. `http://localhost:5173`, `http://127.0.0.1:4173`, etc.).
   - Existing Playwright setup (test directory, helpers, baseURL).
3. If unsure:
   - Choose a sensible default (`http://localhost:5173`) and proceed, but note the assumption in the final report.

---

## STEP 2 – ENSURE LOCAL APP & LOGS ARE RUNNING

1. If a shell / docker / process MCP is available:
   - Check whether the dev server is already running; if not, start it using the appropriate command from `package.json`.
   - Start a **log tail** for backend/API logs (and/or dev server logs):
     - e.g. `pnpm dev` logs, docker compose logs, or backend process logs.
   - Keep the log tail running in the background while you drive the UI.
2. If no such MCP is available:
   - Do NOT attempt to start processes.
   - Instead, clearly specify in the final report:
     - Which commands the developer should run locally (dev server + logs) before invoking this prompt.

---

## STEP 3 – DEFINE CORE “LIVE UI” SCENARIOS

Using routes, components, and existing docs, derive a small set of **high-value flows**, for example (adapt to this repo):

- Smoke navigation:
  - Load home page.
  - Navigate through main sections (e.g. dashboard, meetings list, settings).
- Core Bo1-style flow (adapt to current product):
  - Create or start a “meeting” / “decision” session.
  - Fill any required form fields.
  - Trigger the main deliberation / processing flow.
  - Observe resulting UI (states, summaries, actions).
- Error / edge basics:
  - Try invalid or incomplete input on one key form; verify validation messages.
  - Try refreshing mid-flow; confirm it fails gracefully or resumes sensibly (depending on intended UX).

Keep the scenario list short (3–6 flows) but representative.

---

## STEP 4 – RUN SCENARIOS VIA PLAYWRIGHT MCP

For each scenario:

1. Use Playwright MCP to:

   - Open the dev URL.
   - Drive the UI just like a real user:
     - Click navigation links.
     - Fill in forms.
     - Submit actions.
     - Wait for responses and UI updates.

2. While doing this:

   - Watch backend/dev logs (if log tail MCP is active) for:
     - Exceptions / stack traces.
     - 4xx/5xx API responses.
     - Unexpected warnings.
   - Watch browser console logs (via Playwright) for:
     - Console errors/warnings.
     - Failed network requests.
     - Reactivity or hydration issues (if any).

3. For each important step, verify:
   - The page loads without console errors.
   - Important network requests return 2xx responses.
   - Expected text / elements appear (e.g. headings, buttons, key summaries).
   - Forms show validation errors when appropriate.
   - The UI responds within a reasonable time (no obvious “stuck” states).

Only capture screenshots or traces for failures or clearly broken UX; don’t spam.

---

## STEP 5 – CHECK RESPONSES & BASIC UX QUALITY

For each core flow:

1. Check HTTP-level behaviour:

   - No unexpected 4xx/5xx for normal user actions.
   - API responses that drive UI look correct (e.g. shape, key fields present).

2. Check UX essentials:

   - Clear primary action per page.
   - Meaningful error messages for invalid input.
   - Loading states instead of blank or frozen screens.
   - No obviously broken layouts (e.g. overlapping text, unusable mobile view on a key page, if viewport switching is supported in this run).

3. Note any issues with severity:
   - `P0` – Broken feature / crash / blocker.
   - `P1` – Serious UX or correctness issue.
   - `P2` – Minor annoyance / polish.

---

## STEP 6 – OPTIONAL: EMIT/UPDATE PLAYWRIGHT TESTS

If this repo already has Playwright tests:

1. For flows you just manually exercised:
   - Check if equivalent Playwright specs exist.
   - If they do but fail to cover what you saw, note this in the report.
   - If they don’t exist and the behaviour is stable & important:
     - Optionally scaffold a minimal Playwright test file or test case that captures the flow (using the project’s existing test style).

Keep any new tests small and focused; don’t generate a giant battery of tests here.

---

## STEP 7 – WRITE A SHORT REPORT (e.g. `ui_live_test.md`)

Create or update `ui_live_test.md` in the repo root with:

- `# Bo1 Live UI Test – {DATE}`

- `## Summary`

  - 3–7 bullets:
    - Flows tested.
    - Overall impression (e.g. “all core flows OK, some UX rough edges”).
    - # of P0/P1/P2 issues.

- `## Flows Covered`

  - List each scenario with 1–3 bullets of what was done and whether it passed.

- `## Issues Found`

  - Group by severity (P0/P1/P2).
  - For each: short description, page/route, and rough reproduction steps.

- `## Logs & Console`

  - Bullet any notable backend log errors.
  - Bullet any notable browser console errors/warnings.

- `## Suggested Next Steps`
  - 5–10 bullets of concrete follow-up actions:
    - “Add validation for X”
    - “Handle server error Y more gracefully”
    - “Create a regression test for flow Z”

Keep this file concise and focused on actionable findings.

---

## STEP 8 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finishing:

1. Confirm:

   - All interactions stayed on localhost / 127.0.0.1.
   - Playwright MCP was used for browser actions.
   - Logs were checked (or you clearly indicated what logs should be tailed).

2. Confirm:

   - Only UI-related files and `ui_live_test.md` were created or modified.
   - No governance or critical config files were changed.

3. If there were blocking environment issues (e.g. dev server wouldn’t start):
   - Clearly state this in `ui_live_test.md` under “Issues Found”.
   - Suggest what needs to be fixed before this prompt can be rerun successfully.

---

## OUTPUT REQUIREMENTS

- Apply any repository changes directly:
  - `ui_live_test.md`
  - Optional small additions/adjustments to Playwright tests (if created/updated).
- In the chat, provide a very short summary:
  - How many flows tested.
  - Count of P0/P1/P2 issues.
- Do NOT dump all logs or entire Playwright specs into the chat unless asked.

Now perform a local-only live UI test using Playwright MCP as described.
