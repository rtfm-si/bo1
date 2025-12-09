Bo1 Task Decomposition: \_TODO.md → \_TASK.md

GOAL
Read `_TODO.md`, decompose its contents into individual high-level tasks with distinct, single-function features, and write the resulting task list to `_TASK.md` in the repo root.

Each task should:

- Represent one clear, deliverable feature/change.
- Be independently understandable and implementable.
- Not bundle multiple unrelated concerns.

CONSTRAINTS

- Follow all governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any folder-level CLAUDE/manifest files.
- Run pre-flight enforcement and runtime self-audit before making changes.
- Keep reasoning shallow and outputs concise.
- Use minimal diffs.
- Do NOT modify governance files or business specs; only `_TASK.md` (and read `_TODO.md`).

---

## STEP 1 – READ & UNDERSTAND `_TODO.md`

1. Open `_TODO.md` in the repo root.
2. Identify:
   - Sections or groupings (e.g. headings, bullets).
   - Items that represent:
     - Features
     - Refactors
     - Infrastructure changes
     - UX improvements
     - Documentation work
3. For each item, determine whether it is:
   - A single clear task already, OR
   - A bundle of multiple tasks, OR
   - Too vague and needs to be turned into a clearer, high-level task.

Do NOT change `_TODO.md`.

---

## STEP 2 – DECOMPOSE INTO DISTINCT, SINGLE-FUNCTION TASKS

For each item in `_TODO.md`:

1. If it contains multiple independent concerns (e.g. “add X AND refactor Y AND fix Z”):
   - Split it into multiple high-level tasks, each with one purpose.
2. If it is vague (e.g. “improve UX for meetings”):
   - Transform it into a high-level, outcome-focused task (e.g. “Improve meeting creation UX: reduce steps, clarify required fields, add validation messages”).
3. Ensure each resulting task:
   - Has a single, clear goal.
   - Is not an implementation plan (no step-by-step detail; that belongs in `_PLAN.md` later).
   - Can be reasonably completed as one feature/change.

Keep task text short but explicit enough that future you/Claude can write an implementation plan from it.

---

## STEP 3 – MERGE WITH EXISTING `_TASK.md` (IF PRESENT)

1. Open `_TASK.md` if it exists.
2. Detect the existing structure:
   - Checkbox style (e.g. `- [ ] Task description`)
   - Sections (e.g. “Backlog”, “In Progress”, “Done”)
3. Do NOT reorder or delete existing tasks.

4. De-duplicate:
   - If a new task from `_TODO.md` is clearly already represented in `_TASK.md`:
     - Do NOT add a duplicate.
   - If there is a similar task:
     - Prefer the clearer version; do not silently merge texts unless they are obviously the same.

---

## STEP 4 – WRITE NEW TASKS TO `_TASK.md`

1. Use the existing task format; if there is none, default to:

```
   - [ ] Short, single-function task description…
```

2. If `_TASK.md` has a “Backlog” or similar section:

   - Append new tasks there.
   - Otherwise, add a new section at the end, e.g.:

```
   ## Task backlog (from \_TODO.md, YYYY-MM-DD)

   - [ ] Task 1…
   - [ ] Task 2…
```

3. For each new task, ensure: - It is one line (or a short line with a brief parenthetical if needed).

   - It describes a single function/feature/change (no “and also” chains).
   - It is written in language that a future implementation-planning prompt can consume.

4. Do not assign priorities here unless `_TASK.md` already uses a priority convention.

   - If it does, follow the existing convention (e.g. [P0], [P1]).

## STEP 5 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finalising:

1.  Confirm:

    - Every new task is derived from \_TODO.md.
    - No obvious tasks from \_TODO.md were missed.
    - Each task is single-function and high-level (not a step-by-step implementation).

2.  Confirm:

    - Existing tasks in \_TASK.md were not changed, moved, or removed (except for avoiding exact duplicates).

3.  Confirm:

    - Only `_TASK.md` was modified.
    - Changes are minimal and structurally consistent with the existing document.

4.  If any `_TODO.md` item is too ambiguous to convert into a sensible task:
    Create a single meta-task like:

        ```
        - [ ] Clarify scope of: "<original TODO text>" (ambiguous item from _TODO.md)
        ```

    Do not invent detailed tasks for unclear items.

## OUTPUT REQUIREMENTS

- Apply changes directly to `_TASK.md`
- Do NOT modify `_TODO.md`.
- Do NOT dump `_TASK.md` in the chat.

  In the chat, provide only a short summary:

  - Number of new tasks added.
  - Whether any ambiguous items were left as “clarify scope” tasks.

  Do not restate this prompt.

Now:

- Read `_TODO.md`.
- Decompose it into distinct, single-function high-level tasks.
- Merge them into `_TASK.md` as described.
