# tests/ Manifest
Pytest suites mirroring bo1/.

Structure: mirrors bo1/; api/, integration/, manual/
Governance: <testing>
Rules: fixtures for db, mock LLM, integration hits real services
Do NOT load: __pycache__/, .pytest_cache/, full fixtures, unrelated folders

BOUNDARY: operates independently; test code only
MUST NOT: modify production code; alter agent logic; change schema
Fallback: local rules → parent manifest → root CLAUDE.md
Reasoning: ≤4 steps unless correctness requires expansion

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
