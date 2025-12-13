Bo1 Task Decomposition → Implementation Plan Writer

GOAL
Read `_TASK.md`, identify the next most obvious task or small set of tasks, and produce a concise, implementation-ready plan (including tests and validations) written to `_PLAN.md` in the repo root.

FILTER (optional): $ARGUMENTS

If a filter is provided (e.g., `SEC`, `BUG`, `BILLING`), prioritize tasks matching `[FILTER]` tag pattern. Only select tasks matching the filter if any exist; otherwise fall back to normal priority ordering.

CONSTRAINTS

- Follow all existing governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any folder-level CLAUDE/manifest files
- Run pre-flight enforcement and runtime self-audit before making changes.
- Keep reasoning shallow and outputs concise.
- Use minimal diffs when creating/updating `_PLAN.md`; do not dump other files.
- Do NOT modify governance or task definitions in `_TASK.md`.

---

## STEP 1 – LOAD & INTERPRET TASKS

1. Open `_TASK.md` in the repo root.
2. If a FILTER was provided:
   - Search for uncompleted tasks matching `[FILTER]` (e.g., `[SEC]`, `[BUG]`).
   - Prioritize P0 > P1 > P2 within matching tasks.
   - If no matching tasks found, fall back to normal priority ordering.
3. Infer the task structure:
   - Ordering (top-to-bottom priority, or explicit status/priority tags if present).
   - Dependencies or grouping if obvious.
4. Select:
   - The single next most obvious task, OR
   - A very small cluster of tightly related tasks that should be implemented together.
5. Do NOT change `_TASK.md` at this stage.

Keep this selection focused and implementable in a short sprint.

---

## STEP 2 – DECOMPOSE INTO AN IMPLEMENTATION PLAN

For the chosen task(s):

1. Decompose into 3–10 concrete implementation steps:
   - File-level actions.
   - Function/module changes.
   - Any schema or infra changes.
2. For each step, specify:
   - What to change/do.
   - Where (files/modules).
   - Any sequencing/ordering constraints.
3. Include:
   - Tests to write/update (unit, integration, or end-to-end).
   - Validations/checks (manual or automated) to confirm it works.
4. Apply your token-efficient planning style:
   - Short bullets.
   - No long prose.
   - No unnecessary repetition or restatement of `_TASK.md`.

---

## STEP 3 – WRITE PLAN TO `_PLAN.md`

1. Create or update `_PLAN.md` in the repo root.
2. Overwrite or replace the previous plan content (unless your governance says to append; if unclear, overwrite).
3. Use this structure:

# Plan: {{TASK_TITLE_OR_ID}}

## Summary

- 2–4 bullets: what will be delivered.

## Implementation Steps

- Step 1: ...
- Step 2: ...
- Step N: ...

## Tests

- Unit tests:
  - ...
- Integration/flow tests:
  - ...
- Manual validation:
  - ...

## Dependencies & Risks

- Dependencies:
  - ...
- Risks/edge cases:
  - ...

4. Ensure the plan is:
   - Concrete enough to implement directly.
   - Small enough to be achievable without spawning an endless refactor.

---

## STEP 4 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finalising `_PLAN.md`:

1. Confirm you only used the minimal necessary context from the repo.
2. Confirm the plan:
   - Aligns with CLAUDE.md and GOVERNANCE.
   - Obeys CONTEXT_BOUNDARY and MODEL_GUIDANCE.
   - Is consistent with `_TASK.md` (no invented tasks).
3. Confirm tests and validations are realistic and match the steps.
4. If a FILTER was provided, confirm the selected task matches the filter (or explain why fallback was used).
5. If anything is ambiguous or high-risk, STOP and ask me for clarification instead of guessing.

---

## OUTPUT REQUIREMENTS

- Apply changes directly to `_PLAN.md` only.
- Do NOT output the contents of `_PLAN.md` in the chat unless explicitly asked.
- Keep explanations in the chat minimal (e.g. a short bullet summary of what you planned).
- Do not restate this prompt.

---

## STEP 5 – REQUEST APPROVAL

After writing `_PLAN.md`:

1. Present a brief summary of the plan to the user.
2. Ask: "Approve this plan to proceed with `/build`? (yes/no)"
3. Wait for user response.

If the user approves (responds with "yes", "approve", "go ahead", "looks good", etc.):
- The Stop hook will detect the approval and automatically trigger `/build`.

If the user does not approve:
- Normal session end; no build triggered.

---

Now perform this process: read `_TASK.md`, pick the next most obvious task(s), build the concise implementation plan, and write it to `_PLAN.md`.
