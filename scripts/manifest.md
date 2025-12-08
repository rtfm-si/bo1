# scripts/ Manifest
Dev/ops utilities.

Key: check_migration_history.py, run-sql-migrations.sh
Governance: <deployment>
Rules: idempotent, --dry-run for destructive, document in header

BOUNDARY: operates independently; utility scripts only
MUST NOT: modify production code directly; alter agent logic
Fallback: local rules → parent manifest → root CLAUDE.md

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
