# .github/ Manifest
CI/CD workflows.

Key: Deploy to Production (blue-green), PR checks
Governance: <deployment>
Rules: auto migrations on deploy, tests before merge

BOUNDARY: operates independently; CI/CD config only
MUST NOT: modify application code; alter agent logic; change schema
Fallback: local rules → parent manifest → root CLAUDE.md

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
