# migrations/ CLAUDE.md
Overrides root for migrations. GOVERNANCE LOCK applies.

Rules:
- Alembic preferred over raw SQL
- Test: upgrade head → downgrade -1
- Auto-run on deploy
- Idempotent, backward compatible

DOMAIN PROTECTION:
- MUST NOT influence UI/UX decisions
- MUST NOT modify agent logic
- MUST NOT break backward compatibility during blue-green

Efficiency: diffs only, shallow reasoning (≤4 steps)
Fallback: local → root CLAUDE.md → GOVERNANCE.md
Commands: alembic revision --autogenerate, upgrade head, downgrade -1

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>

<local_self_audit>
Before replying: (1) changes affect only this domain unless cross-domain requested (2) no architectural boundaries crossed (3) token/reasoning limits respected (4) aligns with manifest + governance (5) if check fails → ask user
</local_self_audit>
