# migrations/ Manifest
Alembic DB migrations.

Structure: versions/, env.py; alembic.ini at root
Governance: <deployment>, <migration_pattern>
Rules: upgrade+downgrade, idempotent, backward compatible
Do NOT load: full history, __pycache__/, unrelated folders

BOUNDARY: operates independently; do not load other folders
MUST NOT: influence UI/UX; modify agent logic; alter API without coordination
Fallback: local rules → parent manifest → root CLAUDE.md
Reasoning: ≤4 steps unless correctness requires expansion

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
