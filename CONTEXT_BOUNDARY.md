# CONTEXT_BOUNDARY.md
GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.

<scope_rules>
- Load only task-relevant files
- Max 3 files initially; expand only if needed
- grep/glob before full reads
- Exploration: use Task tool with Explore agent
- MUST NOT assume missing context; ask first
</scope_rules>

<out_of_scope>
Never load: node_modules, .venv, __pycache__, htmlcov, .pytest_cache, .mypy_cache, zzz_*, backups, exports
Never load: GOVERNANCE.md <reference>, full migration history
Never load: untagged sections
</out_of_scope>

<context_limits>
- Reads: 500 lines max initially
- Grep: 50 matches; Glob: 30 files
- Expand only for needle search
- MUST NOT exceed limits without explicit need
</context_limits>

<efficiency_principles>
- Ask "need this?" before loading
- Summarize, don't echo
- Diffs only; one-shot when clear
- MUST NOT rewrite entire files unless explicitly requested
</efficiency_principles>
