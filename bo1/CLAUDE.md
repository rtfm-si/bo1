# bo1/ CLAUDE.md
Overrides root for core library. GOVERNANCE LOCK applies.

Rules:
- recommendations NOT votes
- state_to_v1() / v1_to_state() for conversions
- db_session() always
- XML tags in prompts
- Limits: 6 rounds, 20 recursion

SAFETY CONSTRAINTS:
- MUST NOT modify persona roles without explicit request
- MUST NOT alter meeting progression logic
- MUST NOT introduce circular agent reasoning
- MUST NOT bypass cost controls

Efficiency: diffs only, shallow reasoning (≤4 steps), 1-3 bullets
Fallback: local → root CLAUDE.md → GOVERNANCE.md
Key: graph/{config,state,nodes/}, prompts/

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>

<local_self_audit>
Before replying: (1) changes affect only this domain unless cross-domain requested (2) no architectural boundaries crossed (3) token/reasoning limits respected (4) aligns with manifest + governance (5) if check fails → ask user
</local_self_audit>
