Ship: Pre-commit → Commit → PR → CI → Deploy

You are running inside the Bo1 repo with Claude Code.

GOAL
End-to-end workflow: validate, commit, PR, wait for CI, deploy to production.

CONSTRAINTS
- Follow CLAUDE.md governance
- Keep outputs concise (bullets, command snippets)
- Ask confirmation before: committing, pushing, creating PR, deploying
- Use existing tooling (Makefile, gh CLI, GitHub Actions)

---

## STEP 1: DISCOVER STATE

1. Run `git status` - check staged/unstaged changes
2. Run `git branch --show-current` - get current branch
3. Run `git log --oneline -5` - recent commits for context

Output a SHORT summary:
- Branch: ...
- Changes: staged X, unstaged Y
- Base branch: main

---

## STEP 2: PRE-COMMIT CHECKS (Docker)

Run checks in Docker (matches CI):

```bash
# Backend
docker-compose run --rm bo1 ruff check .
docker-compose run --rm bo1 ruff format --check .
docker-compose run --rm bo1 mypy bo1/ --install-types --non-interactive

# Frontend
docker-compose run --rm frontend npm run check

# Database migrations (ensure migrations are up to date)
docker-compose exec bo1 uv run alembic upgrade heads
```

If checks fail:
- Show SHORT error summary
- Ask: "Fix issues automatically? (ruff can auto-fix)"
- If yes, run `docker-compose run --rm bo1 ruff check --fix . && docker-compose run --rm bo1 ruff format .`

If checks pass, continue.

---

## STEP 3: RUN TESTS (Docker, No LLM)

```bash
docker-compose run --rm bo1 pytest -m "not requires_llm" -x -q
```

If tests fail:
- Show failure summary
- STOP and ask user how to proceed

If tests pass, continue.

---

## STEP 4: GENERATE COMMIT MESSAGE & COMMIT

1. Analyze changes with `git diff --cached` (if staged) or `git diff` (if unstaged)
2. Generate a conventional commit message based on the actual changes:
   - feat: new feature
   - fix: bug fix
   - refactor: code restructuring
   - docs: documentation
   - chore: maintenance
   - Format: `type: short description`

3. Show:
   - Files to commit
   - Generated commit message

4. Ask: "Commit with this message? (yes/edit/no)"

5. On "yes":
   - Stage all changes: `git add -A`
   - Commit with generated message

---

## STEP 5: PUSH & CREATE PR

1. Check if branch is already pushed: `git rev-parse --abbrev-ref @{upstream}`
2. Check if PR exists: `gh pr view --json number 2>/dev/null`

If no PR exists:
- Ask: "Push and create PR against main? (yes/no)"
- On yes:
  ```bash
  git push -u origin $(git branch --show-current)
  gh pr create --fill --base main
  ```

If PR exists:
- Ask: "Push updates to existing PR? (yes/no)"
- On yes: `git push`

Show PR URL.

---

## STEP 6: WAIT FOR CI

1. Get PR number: `gh pr view --json number -q .number`
2. Wait for CI checks:
   ```bash
   gh pr checks --watch
   ```

If CI fails:
- Show which check failed
- STOP - do not proceed to deploy

If CI passes, continue.

---

## STEP 7: MERGE PR (Optional)

Ask: "CI passed. Merge PR to main? (yes/no)"

On yes:
```bash
gh pr merge --squash --delete-branch
```

---

## STEP 8: DEPLOY TO PRODUCTION

Ask: "Deploy to production? (yes/no)"

On yes:
1. Explain: "This triggers the deploy-production GitHub Action with blue-green deployment"
2. Trigger deployment:
   ```bash
   gh workflow run deploy-production.yml -f confirm=deploy-to-production
   ```
3. Show workflow run URL:
   ```bash
   gh run list --workflow=deploy-production.yml --limit=1
   ```
4. Optionally watch: `gh run watch`

---

## STEP 9: FINAL SUMMARY

Output:
- Pre-commit: pass/fail
- Tests: pass/fail
- Commit: hash + message
- PR: URL + status
- CI: pass/fail
- Merge: done/skipped
- Deploy: triggered/skipped + workflow URL

---

## EXECUTION RULES

- Run each step sequentially
- Stop on any failure and report
- Never expose secrets
- Use `gh` CLI for all GitHub operations
- Use Docker for all operations:
  - Backend: `docker-compose run --rm bo1 ...`
  - Frontend: `docker-compose run --rm frontend ...`
- Production deploy is via GitHub Actions (not local scripts)
