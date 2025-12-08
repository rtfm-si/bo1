# TASK_PATTERNS.md
GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.
Load specific pattern tag only. MUST NOT invent new workflow steps.

<bugfix_pattern>
1. grep/logs → find error
2. Read 50-100 lines around error
3. Minimal diff fix
4. make test
5. 1-line summary
</bugfix_pattern>

<feature_pattern>
1. Confirm scope (ask if ambiguous)
2. Find similar patterns
3. Implement following conventions
4. Add tests
5. make pre-commit
6. List changed files
</feature_pattern>

<refactor_pattern>
1. Identify what/why
2. Ensure test coverage
3. Incremental changes, test between
4. Verify no regressions
5. Summarize
</refactor_pattern>

<review_pattern>
1. Read changed files only
2. Check quality, security, patterns
3. Issues as file:line bullets
4. Concrete fixes only
</review_pattern>

<migration_pattern>
1. Design schema change
2. alembic revision --autogenerate
3. Check upgrade/downgrade
4. Test both directions
5. Verify idempotent
6. Ready for deploy
</migration_pattern>

<post_task_checks>
Claude MUST run after ANY pattern:
1. Verify diffs are minimal
2. Verify tests/sanity checks suggested where relevant
3. Verify no governance/domain rules broken
4. Run runtime_self_audit before final answer
5. If doubt exists → ask user instead of guessing
</post_task_checks>
