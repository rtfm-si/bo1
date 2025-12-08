# backend/ Manifest
FastAPI, SSE streaming, auth.

Structure: api/{main,routers,event_collector,streaming,middleware/auth}.py
Uses: bo1/, Postgres, Redis, SuperTokens | Used by: frontend
Governance: <security> <deployment>
Do NOT load: full middleware chain, test fixtures, unrelated folders

BOUNDARY: operates independently; do not load frontend/bo1 agent logic
MUST NOT: modify agent logic; alter SQL schema decisions from here
Fallback: local rules → parent manifest → root CLAUDE.md
Reasoning: ≤4 steps unless correctness requires expansion

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
