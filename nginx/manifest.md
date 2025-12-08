# nginx/ Manifest
Production routing, static serving, SSL.

Governance: <deployment>
Rules: static at /var/www/boardofone/static-{env}/, never proxy via Node

BOUNDARY: operates independently; infra config only
MUST NOT: modify application code; alter agent logic; change schema
Fallback: local rules → parent manifest → root CLAUDE.md

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
