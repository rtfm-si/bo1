Bo1 Governance Suite Runner

GOAL
Run one or more governance passes (1–5) against this repo and update CLAUDE.md / GOVERNANCE / manifests as needed.

PASSES

1. Repo & file discovery + basic CLAUDE.md scaffold `.claude/commands/framework/1.md`
2. Governance & safety rules `.claude/commands/framework/2.md`
3. LLM behaviour, prompt patterns, task patterns `.claude/commands/framework/3.md`
4. Token efficiency, caching, and model routing `.claude/commands/framework/4.md`
5. Audit & continuous improvement hooks `.claude/commands/framework/5.md`

USAGE

- If we're doing a fresh setup: run passes 1–5 in order.
- If we've just changed LLM usage or agent architecture: run passes 3 and 4.
- If we're changing governance, security, or legal constraints: run pass 2 and 5.

INSTRUCTIONS

1. Ask which passes to run, or infer from context (if already specified in the task).
2. For each pass:
   - Load existing CLAUDE.md / GOVERNANCE / manifests.
   - Apply only the minimal changes necessary.
   - Keep diffs small and focused.
3. Never blow away existing working config; always refactor, don’t nuke.
