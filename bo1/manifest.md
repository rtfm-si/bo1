# bo1/ Manifest
Core library: graph, prompts, models, state.

Structure: graph/, prompts/, models/, agents/, state/, llm/, data/
Uses: Postgres, Redis, Anthropic | Used by: backend/api/
Governance: <architecture> <agent_governance> <llm_rules>
Do NOT load: personas.json content, migration history, unrelated folders

BOUNDARY: operates independently; do not load backend/frontend unless cross-folder needed
MUST NOT: modify agent logic from other folders; alter meeting progression
Fallback: local rules → parent manifest → root CLAUDE.md
Reasoning: ≤4 steps unless correctness requires expansion

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
