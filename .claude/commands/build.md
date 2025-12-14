Bo1 Build Executor: Implement \_PLAN.md and Sync \_TASK.md

GOAL
Work through the implementation steps in `_PLAN.md`, update the codebase accordingly, run appropriate tests/validations, then update `_TASK.md`:

- Check off tasks completed in this pass.
- Remove tasks that were already completed in previous passes.
- Keep the remaining task list prioritised and focused.

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
- Use minimal diffs; do not dump entire files unless necessary.
- Do NOT modify governance files, `_TASK.md` semantics, or `_PLAN.md` structure.

---

## STEP 1 – READ AND INTERPRET `_PLAN.md`

1. Open `_PLAN.md` in the repo root.
2. Identify:
   - Task title / ID.
   - Implementation steps.
   - Tests/validations section.
   - Dependencies & risks.
3. Confirm the scope is small enough for a focused build pass. If the plan is too large, focus on the first coherent subset of steps and note that in comments if needed.

Do NOT change `_PLAN.md` yet.

---

## STEP 1.5 – RUN DATABASE MIGRATIONS (IF APPLICABLE)

Before implementing code changes, ensure database is up to date:

```bash
docker-compose exec bo1 uv run alembic upgrade head
```

If migration fails:
- Show error summary
- STOP build - do not proceed with code changes that depend on schema
- Migration must succeed before implementation continues

Note: Alembic executes migrations in dependency order automatically. Multiple pending migrations will run sequentially in a single transaction per migration.

---

## STEP 2 – IMPLEMENT THE PLAN (CODE & SCHEMA)

For each Implementation Step in `_PLAN.md`:

1. Determine:
   - Which files/modules are affected.
   - Whether this is a bugfix, feature, refactor, or migration (use TASK_PATTERNS).
2. Apply minimal changes:
   - Make the smallest diff that satisfies the step.
   - Avoid rewriting whole files unless explicitly required.
3. If DB/schema/migrations are involved:
   - Add or adjust migrations following existing patterns.
   - Keep migrations incremental and reversible if your standards require it.
4. Keep changes tightly scoped to the current plan; do not opportunistically refactor unrelated code.

5. If implementation touches `/frontend` or UI:
   - Read `/frontend/UI_GOVERNANCE.md`.
   - Use Bo* components (BoButton, BoCard, BoFormField, etc.) and shadcn-svelte.
   - Ensure:
     - Responsive layout.
     - Loading/error/empty states.
     - UI Review Checklist is satisfied.

---

## STEP 3 – TESTS & VALIDATIONS

1. From `_PLAN.md`'s Tests section, identify:

   - Unit tests to add/modify.
   - Integration/flow tests to add/modify.
   - Manual validation steps.

2. Implement tests:

   - Create/extend test files with minimal, focused cases.
   - Prefer deterministic tests that directly validate the new behaviour.

3. Run tests – USE TARGETED TESTING BY DEFAULT:

   - **Default (low/medium risk):** Run only the test file(s) directly related to changed code.
     - Example: Changed `event_collector.py` → run `pytest tests/api/test_event_collector.py`
   - **High risk only:** Run the full test suite (`pytest tests/ --ignore=tests/integration`) when:
     - Changing shared utilities, base classes, or core infrastructure
     - Modifying database schema or migrations
     - Altering authentication/authorization logic
     - Refactoring imports or module structure
   - If targeted tests fail, fix issues before considering broader suite.

4. For manual validation:
   - Document clear, short steps an operator can run locally (e.g. API call, CLI command, UI flow).

---

## STEP 4 – UPDATE `_TASK.md` (CHECK OFF & CLEAN UP)

1. Open `_TASK.md` in the repo root.

2. Identify entries that correspond to the plan just implemented:

   - Match by ID, title, or description.
   - If tasks use checkboxes (e.g. `- [ ]` / `- [x]`) or explicit status tags, respect that format.

3. For tasks completed in this pass:

   - Mark them as completed according to the existing convention (e.g. `- [x]` or `STATUS: done`).
   - If your governance or `_TASK.md` structure implies moving completed tasks to a “Done” or archive section, apply that.

4. For tasks that were clearly completed in previous passes but still appear as open:

   - Mark them as completed and then remove or move them to a completed/archived section, according to the current `_TASK.md` conventions.
   - Ensure no references remain to obsolete work.

5. For remaining tasks:

   - Keep them in priority order; do NOT reorder unless the document’s structure clearly indicates a priority change.
   - Do NOT invent new tasks; only keep, complete, or remove existing ones.

6. Ensure `_TASK.md` remains:
   - Focused on current, outstanding work.
   - Free of stale or duplicate entries for the plan just implemented.

---

## STEP 5 – AUDIT REPORT TASK DECOMPOSITION (IF APPLICABLE)

If the plan was an **audit task** (e.g. security audit, dependency audit, compliance audit) that produced a report file in `audits/reports/`:

1. Identify the report file created (e.g. `audits/reports/auth-security.report.md`)

2. Extract actionable findings from the report:
   - Look for sections like "Recommendations", "Remediation", "Priority Actions", or findings marked as Medium/High/Critical
   - Each finding with a clear remediation becomes a task

3. Decompose findings into `_TASK.md`:
   - For each actionable finding, create a task following the existing `_TASK.md` format
   - Use appropriate tags (e.g. `[SECURITY]`, `[AUDIT]`) and priority levels
   - Add tasks under a new section: `## Task backlog (from {audit_name}, YYYY-MM-DD)`
   - De-duplicate: do not add tasks that already exist in `_TASK.md`

4. Task format for audit findings:
   ```
   - [ ] [{TAG}][{PRIORITY}] {Brief description of remediation} ({effort estimate if available})
   ```

Skip this step if:
- The plan was not an audit task
- No report file was generated
- The report has no actionable remediation items

---

## STEP 6 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finalising changes:

1. Confirm:

   - Only relevant files and tests were modified.
   - `_TASK.md` updates accurately reflect completed work.
   - No governance or manifest files were altered.

2. Validate:

   - The implementation matches `_PLAN.md`.
   - Tests/validations are aligned with the described behaviour.
   - There are no obvious leftover TODOs related to this plan.

3. If audit findings were decomposed:
   - Confirm new tasks in `_TASK.md` match the report's remediation items
   - Confirm no duplicate tasks were added

4. If you detect ambiguity or risk (e.g. unclear task mapping, large breaking changes), STOP and:
   - Summarise the issue.
   - Ask me for clarification rather than guessing.

---

## OUTPUT REQUIREMENTS

- Apply changes directly to code, tests, migrations, and `_TASK.md` as needed.
- Do NOT overwrite `_PLAN.md`; treat it as the current plan of record unless asked otherwise.
- In the chat, provide only a short summary:
  - Files touched.
  - Tests run (and their status).
  - Tasks checked off or removed.
  - If audit: report location and number of remediation tasks added to `_TASK.md`.
  - If UI changes: which components were added/changed, and confirm UI checklist applied.
- Do not restate this prompt.

Now execute this build pass:

- Implement `_PLAN.md`
- Run tests/validations
- Update `_TASK.md` so it reflects the current reality and keeps the task list prioritised and focused.
