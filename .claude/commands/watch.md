Bo1 Meeting Deep Investigation – UI + Logs + DB + Playwright MCP

GOAL
Given a meeting URL, investigate that meeting end-to-end using:

- The live UI (via Playwright MCP)
- Backend logs
- Database records
- Browser console & network traces

You should:

- If the meeting is running: watch it “live” and monitor events.
- If the meeting is completed / failed / stopped: reconstruct what happened.
- Identify UX/UI issues, missing or confusing events, and technical leaks.
- Produce a concise, actionable report.

INPUT
<meeting_url> = [PASTE MEETING URL HERE]

CONSTRAINTS

- Follow all governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any folder-level CLAUDE/manifest files.
- Treat all user data as sensitive; do not dump raw PII in the report.
- Keep reasoning shallow and outputs concise.
- Use minimal diffs; do NOT modify application code, data, or migrations.
- Read-only DB access: only SELECT/EXPLAIN, never destructive queries.
- Use Playwright MCP for all browser-based interactions.
- If shell/log/DB MCP tools are available, use them; otherwise, clearly specify what should be run manually.

DELIVERABLE

- A single investigation report file in the repo root:

  `meeting_investigation_<MEETING_ID>.md`

  containing:

  - Summary
  - Timeline reconstruction
  - UI/UX issues
  - Technical / data issues
  - Console/log errors
  - Recommendations

---

## STEP 1 – IDENTIFY MEETING & STATUS

1. Parse <meeting_url>:

   - Extract meeting identifier (ID/slug) from the path or query params.
   - If multiple patterns are possible, pick the one that matches existing routes.

2. Use DB MCP (or equivalent) to look up the meeting:

   - Inspect likely tables (e.g. `meetings`, `sessions`, `deliberations`, `decisions`, `runs`).
   - SELECT by meeting ID/slug to retrieve:
     - Status (running, completed, failed, cancelled, etc.).
     - Start/end timestamps.
     - Associated workspace/user IDs.
     - Any stored summary/outcome fields.

3. Determine mode:
   - If status indicates active/in-progress: run **Live Watch Mode**.
   - If status indicates completed/failed/stopped: run **Post-Mortem Mode**.
   - If status unknown/ambiguous: do both:
     - Try to watch the URL with Playwright.
     - Also reconstruct from logs/DB.

Record the derived meeting ID and status for use in the report filename.

---

## STEP 2 – SET UP LOG & CONSOLE OBSERVATION

1. If a shell/log MCP is available:

   - Start a log tail for relevant services:
     - Backend API / orchestrator logs.
     - LLM orchestration / worker logs.
     - Meeting engine / LangGraph worker (if separate).
   - Filter logs by:
     - Meeting ID / correlation IDs.
     - Request paths related to this meeting.

2. Prepare to capture:

   - Errors, warnings, stack traces.
   - Long-running operations.
   - Events that should be reflected in the UI (decomposition, expert selection, rounds, summaries, etc.).

3. For Playwright MCP:
   - Configure it to:
     - Capture browser console logs (errors/warnings).
     - Optionally capture network events for this meeting session (if trivial to enable).

---

## STEP 3 – LIVE WATCH MODE (IF MEETING IS ACTIVE)

1. Use Playwright MCP to:

   - Open <meeting_url> in a real browser.
   - Observe:
     - Page load behaviour (time to interactive, errors).
     - UI event stream as the meeting progresses.

2. As the meeting runs, track:

   - UI events in the timeline:
     - Problem decomposition.
     - Experts selected (who/what perspective).
     - Rounds of contributions.
     - Interventions (moderator, skeptic/contrarian/optimist etc., if applicable).
     - Synthesis/summary & conclusions.
   - Time between visible UI updates:
     - Identify long gaps where nothing visible happens.

3. Cross-check with backend logs:

   - For each backend event (node fired, LLM call, state change, round progression):
     - Is there a corresponding **user-visible UI entry**?
     - If logs show important events with no UI representation, note them.

4. Watch for:

   - Duplicate UI entries representing the same event.
   - “Technical” entries that should be admin-only (e.g. raw error traces, internal node IDs, technical function names).
   - UI events that are unclear or confusing in wording, ordering, or grouping.
   - Missing expected entries:
     - Decomposition not shown.
     - Persona/expert selection missing.
     - Round numbers unclear.
     - Final summary/conclusions not clearly surfaced.

5. Track timing:
   - Approximate how long each phase takes (decomposition, expert generation, rounds, summary).
   - Identify long gaps between:
     - Backend events.
     - UI updates.
   - Flag cases where logs show activity but UI appears “stalled” or blank.

---

## STEP 4 – POST-MORTEM MODE (COMPLETED / FAILED MEETING)

1. From DB:

   - Retrieve full event / state history for the meeting:
     - Meeting-level record.
     - Node/step events.
     - Agent/LLM call logs (as available).
     - Stored UI event stream / timeline table, if exists.

2. From logs:

   - Filter logs by this meeting ID/time window.
   - Identify:
     - Errors/exceptions.
     - Retries, timeouts, rate limit events.
     - Any errors that would have impacted the UI.

3. From the UI (via Playwright MCP):

   - Open <meeting_url> in its “completed” or “review” state.
   - Observe:
     - Timeline entries (events, rounds, experts, summary).
     - Any error or warning messages.
     - The final summary and action items (if applicable).

4. Reconstruct a **chronological timeline**:
   - DB/log events vs. UI-visible events.
   - Note places where:
     - Log events exist with no UI counterpart.
     - UI shows confusing or redundant entries.
     - Technical/internal events are visible that should be masked for non-admins.

---

## STEP 5 – UI/UX QUALITY & CONTENT CHECKS

Across both modes (live or post-mortem):

1. Look for **duplicate UI event entries**:

   - Same event/data appearing multiple times with no real difference.
   - Repetitive logs with slightly different wording that confuse the user.

2. Look for **technical event entries visible to non-admin users**:

   - Raw error traces or stack snippets.
   - Internal node IDs, function names, or graph labels.
   - Implementation details that don’t help decision understanding.

3. Look for **confusing or unclear entries**:

   - Labels that don’t match user mental model (e.g. “Node_7 completed” instead of “Round 2: Expert contributions completed”).
   - Sudden changes of terminology (e.g. “experts” vs “personas” vs “agents”).
   - Vague messages like “LLM error” without user-actionable guidance.

4. Look for **missing UI entries** that should be present:

   - Decomposition: clearly show how the problem was broken into subproblems.
   - Experts selected: who/what perspectives were included, and why (if available).
   - Rounds: number, order, and high-level purpose of each round.
   - Summary & conclusions: final recommendation + rationale clearly visible.
   - Any “important backend events” visible in logs but not reflected in the UI.

5. Identify **UI elements that could be improved**:
   - Ordering of entries (e.g. mixing technical and high-level items).
   - Grouping (e.g. all events of a round grouped with a header).
   - Wording improvements (short, outcome-focused labels).
   - Loading/empty states where users currently see “nothing happening”.

---

## STEP 6 – TIMING, GAPS & PERFORMANCE

Using DB timestamps, logs, and Playwright observations:

1. Estimate:

   - Time from meeting start → first visible UI event.
   - Time between major milestones:
     - Decomposition → expert generation.
     - Experts → first round contributions.
     - Last contributions → summary.
   - Total meeting duration.

2. Identify:

   - Long gaps between backend events.
   - Long gaps between backend events and the UI reflecting them.
   - Periods where logs show work happening but the UI remains static.

3. Mark as issues when:
   - The user is likely to think the system is “stuck”.
   - There are silent failures or retries the user never sees.

---

## STEP 7 – CONSOLE & NETWORK ERRORS (PLAYWRIGHT)

While interacting with the meeting UI (live or post-mortem):

1. Capture:

   - Browser console errors/warnings.
   - Failed network requests (especially 4xx/5xx).
   - Hydration/SSR mismatch warnings, if any.
   - Svelte/SvelteKit runtime warnings that indicate subtle bugs.

2. Classify:
   - P0 – Crashes / broken flows / persistent errors.
   - P1 – Serious console errors that degrade UX or reliability.
   - P2 – Noisy but non-breaking warnings (should be cleaned up).

---

## STEP 8 – WRITE REPORT: `meeting_investigation_<MEETING_ID>.md`

Create or overwrite `meeting_investigation_<MEETING_ID>.md` with:

# Meeting Investigation – <MEETING_ID>

## 1. Summary

- Status: running / completed / failed / unknown
- 3–7 bullets describing:
  - What worked.
  - What is broken or unclear.
  - Overall user experience for this meeting.

## 2. Timeline Reconstruction

- High-level chronological view:
  - Key backend/log events.
  - Key UI-visible events.
  - Noted gaps and mismatches.

## 3. UI & UX Issues

- Duplicate entries:
  - List where/what.
- Technical leakage:
  - Events/messages that should be admin-only.
- Confusing entries:
  - Examples + suggested wording/grouping improvements.
- Missing entries:
  - Events that happened (from logs/DB) but were not shown in UI.

## 4. Performance & Gaps

- Approx. timings between phases.
- Long gaps with no visible UI updates.
- Cases where backend events didn’t translate into user feedback.

## 5. Console & Log Errors

- Browser console highlights (errors/warnings).
- Backend log errors related to this meeting.
- Network-level failures (HTTP 4xx/5xx).

## 6. Recommendations

- Short, actionable bullet list:
  - UI changes (wording, grouping, new events).
  - Masking of technical/internal events for non-admins.
  - Performance/feedback improvements (spinners, progress, interim messages).
  - Any suggested tests or monitoring improvements.

KEEP THIS FILE CONCISE AND ACTIONABLE, NOT A DUMP OF RAW LOGS.

---

## STEP 9 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finishing:

1. Confirm:

   - You did not modify DB or meeting data.
   - You did not change application code.
   - You only created/updated `meeting_investigation_<MEETING_ID>.md`.

2. Confirm:
   - All observations are tied to this specific meeting.
   - PII is not exposed unnecessarily in the report.
   - Issues and recommendations are concrete and refer to specific parts of the UI/flow.

---

## OUTPUT REQUIREMENTS

- Apply changes directly to `meeting_investigation_<MEETING_ID>.md` only.
- Do NOT dump full logs, DB rows, or entire UI HTML in the chat.
- In the chat, give a very short summary:
  - Meeting ID and status.
  - Number of major issues (P0/P1) vs minor (P2).
- Do not restate this prompt.

Now perform the full investigation for <meeting_url> as described.
