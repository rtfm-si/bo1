Bo1 Full Audit Suite Runner → Tasks in \_TASK.md

GOAL
Run ALL defined audits sequentially (not in parallel), collect the issues they find, and convert those issues into clear, de-duplicated, actionable tasks written into `_TASK.md` in the repo root.

Audits to run (in this order, sequentially):

1. architecture_flow `.claude/commands/audit/architecture_flow.md`
2. performance_scalability `.claude/commands/audit/performance_scalability.md`
3. llm_alignment `.claude/commands/audit/llm_alignment.md`
4. data_model `.claude/commands/audit/data_model.md`
5. observability `.claude/commands/audit/observability.md`
6. api_contract `.claude/commands/audit/api_contract.md`
7. reliability `.claude/commands/audit/reliability.md`
8. cost_optimisation `.claude/commands/audit/cost_optimisation.md`

OPTIONAL (if present and wired as audits):

- secure (red/blue team) `.claude/commands/secure.md`
- clean `.claude/commands/clean.md`

CONSTRAINTS

- Follow all governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any manifests and folder-level CLAUDE files.
- Use the existing audit prompts and/or audit manifests; do NOT invent new audit logic.
- Run audits sequentially, re-using minimal context per audit to keep tokens down.
- Keep reasoning shallow and outputs concise.
- Use minimal diffs; do NOT rewrite entire `_TASK.md`, only update/append what’s needed.
- Do NOT modify governance or audit prompt files.

---

## STEP 1 – PREPARE TASK STRUCTURE

1. Open `_TASK.md` in the repo root, if it exists.
2. Detect its structure:
   - Are tasks bullet points? Checkboxes? Headings + lists?
   - Are there existing sections (e.g. “Backlog”, “In Progress”, “Done”, etc.)?
3. Do NOT change its overall organisation; you will:
   - Add a new section for audit-derived tasks, OR
   - Append tasks to the existing backlog section, following its format.

Define a simple tagging scheme for new tasks:

- `[ARCH]` for architecture_flow
- `[PERF]` for performance_scalability
- `[LLM]` for llm_alignment
- `[DATA]` for data_model
- `[OBS]` for observability
- `[API]` for api_contract
- `[REL]` for reliability
- `[COST]` for cost_optimisation
- Optional: `[SEC]`, `[TEST]`, `[CLEAN]` if those audits are included

---

## STEP 2 – RUN EACH AUDIT SEQUENTIALLY

For each audit type in order:

1. Load its manifest (if present) and/or use its canonical audit prompt:

   - architecture_flow
   - performance_scalability
   - llm_alignment
   - data_model
   - observability
   - api_contract
   - reliability
   - cost_optimisation

2. Execute the audit with:

   - Minimal necessary context.
   - Respect for CONTEXT_BOUNDARY and MODEL_GUIDANCE.
   - Shallow reasoning, concise outputs.

3. Capture only the **issues / recommendations / gaps** section from each audit:

   - Do NOT pull in long narrative, diagrams, or full reports.
   - Focus on items that naturally translate into tasks:
     - “Refactor X to Y.”
     - “Add tests for Z.”
     - “Remove deprecated A.”
     - “Add logging/metrics for B.”
     - “Update API contract for C.”

4. For each issue, derive a concise, actionable task line:
   - Prefer language like:
     - “Refactor {{module}} to separate {{concern}} from {{concern}}.”
     - “Add integration tests for {{flow}} covering {{cases}}.”
     - “Remove unused table/column {{name}} and update code/migrations.”
     - “Add structured logs + correlation IDs for {{component}}.”

Keep a per-audit internal list of candidate tasks.

---

## STEP 3 – DE-DUPLICATE AND PRIORITISE TASKS

Before writing to `_TASK.md`:

1. Merge tasks across audits that clearly describe the same work.

   - E.g., architecture and performance audits both flagging the same refactor.
   - Create a single task with combined rationale where needed.

2. Check against existing `_TASK.md`:

   - If a similar task already exists, do NOT add a new one.
   - Instead, ensure the existing task is still relevant and leave it as-is.
   - Use simple text matching and common sense to avoid duplicates.

3. Assign simple priority hints (for internal ordering only), e.g.:
   - `P0` – critical / blocking / security / correctness
   - `P1` – high-value within next sprint
   - `P2` – nice-to-have / later

You don't need complex scoring; just note priority in the task text.

---

## STEP 3.5 – VERIFY IMPLEMENTATIONS BEFORE WRITING

**CRITICAL:** Before writing ANY task to `_TASK.md`, verify it is not already implemented:

1. For each candidate task, check the `<verification_checks>` section of the originating manifest
2. Run the relevant verification (grep for function, check migrations, etc.)
3. **Skip** tasks where implementation already exists
4. **Modify** task scope if partial implementation exists (e.g., "migrate remaining 50 endpoints" not "migrate all endpoints")

Common verification patterns:
- **Indexes**: Check `migrations/versions/` for `*_index*.py` or `z15_*`, `z16_*` naming
- **Metrics**: Grep `backend/api/middleware/metrics.py` and `health.py`
- **Error handling**: Grep for `http_error(` usage count
- **Caching**: Check for Redis cache patterns in target files

If a task was generated but implementation exists, log it as "Already implemented: [task]" in audit output but do NOT add to `_TASK.md`.

---

## STEP 4 – WRITE AUDIT-DERIVED TASKS TO `_TASK.md`

1. Decide where to place audit tasks:

   - If `_TASK.md` has a clear backlog section, append tasks there.
   - Otherwise, append a new section at the end:

     ```markdown
     ## Audit-derived tasks (YYYY-MM-DD)

     - [ ] [TAG][P?] Short, concrete task description…
     ```

2. For each new task, write a single line in the existing style, e.g.:

   - `- [ ] [ARCH][P1] Refactor meeting orchestration module to separate agent routing from HTTP handlers.`
   - `- [ ] [PERF][P0] Parallelise expert contribution calls in round execution pipeline.`
   - `- [ ] [DATA][P1] Remove unused column {{col_name}} from {{table_name}} and update related queries/migrations.`
   - `- [ ] [OBS][P1] Add structured logs + correlation IDs to meeting start/finish API handlers.`

3. Keep descriptions:

   - Short and implementation-ready.
   - Specific enough that a future plan in `_PLAN.md` can break them down.

4. Do NOT alter existing tasks except to avoid duplication (step 3); this prompt is about adding audit-driven work, not reprioritising everything.

---

## STEP 5 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finalising:

1. Confirm:

   - Each audit was run once, sequentially.
   - You did not pull in unnecessary context or long reports.
   - Only `_TASK.md` was modified (plus any audit report files the audits themselves wrote).

2. Confirm for `_TASK.md`:

   - New tasks follow the existing style and structure.
   - No obvious duplicates.
   - Tags correctly reflect the originating audit (`[ARCH]`, `[PERF]`, etc.).
   - **CRITICAL**: Every task was verified against codebase before inclusion (Step 3.5).

3. If any audit produced ambiguous or speculative issues:
   - Do not create tasks for those.
   - Or, group them under a single meta-task like:
     - `- [ ] [TAG][P2] Human review of ambiguous issues from {{audit_type}} audit.`

4. Confirm implementation verification:
   - Tasks for indexes, metrics, error handling were verified against migrations/ and middleware/
   - No tasks were added for already-implemented features
   - Partial implementations result in scoped tasks (e.g., "remaining N endpoints")

---

## OUTPUT REQUIREMENTS

- Apply changes directly to `_TASK.md` and audit report files, if the audits create them.
- Do NOT dump `_TASK.md` to the chat.
- In the chat, provide a SHORT summary only:
  - How many new tasks were added per audit type.
  - Whether any tasks were skipped due to duplication or ambiguity.
- Do not restate this prompt.

Now run the full audit suite sequentially, extract issues, de-duplicate them, and write the resulting tasks into `_TASK.md` as described.
