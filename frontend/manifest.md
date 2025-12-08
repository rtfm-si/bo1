# frontend/ Manifest
SvelteKit UI.

Structure: src/{routes/,lib/components/,lib/stores/,lib/api/}
Uses: backend/api/ via HTTP/SSE, SuperTokens
Governance: <code_quality>
Do NOT load: node_modules/, .svelte-kit/, build/, unrelated folders

BOUNDARY: operates independently; do not load backend/bo1 unless needed
MUST NOT: enforce backend rules; modify agent logic; alter SQL schema
Fallback: local rules → parent manifest → root CLAUDE.md
Reasoning: ≤4 steps unless correctness requires expansion

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>
