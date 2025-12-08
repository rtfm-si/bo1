# backend/ CLAUDE.md
Overrides root for API. GOVERNANCE LOCK applies.

Rules:
- SuperTokens auth required
- SSE via event_collector, not direct
- Validate all user input
- Parameterized SQL only

DOMAIN PROTECTION:
- MUST NOT modify agent logic (bo1/)
- MUST NOT influence UI/UX decisions (frontend/)
- MUST NOT alter schema without migration

Efficiency: diffs only, shallow reasoning (≤4 steps), 1-3 bullets
Fallback: local → root CLAUDE.md → GOVERNANCE.md
Key: api/{main,event_collector,routers}.py

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>

<local_self_audit>
Before replying: (1) changes affect only this domain unless cross-domain requested (2) no architectural boundaries crossed (3) token/reasoning limits respected (4) aligns with manifest + governance (5) if check fails → ask user
</local_self_audit>
