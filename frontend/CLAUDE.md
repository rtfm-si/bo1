# frontend/ CLAUDE.md
Overrides root for UI. GOVERNANCE LOCK applies.

Rules:
- $env/dynamic/public not import.meta.env
- No business logic in components
- SSE via EventSource
- nginx serves static

DOMAIN PROTECTION:
- MUST NOT enforce backend rules
- MUST NOT modify agent logic (bo1/)
- MUST NOT alter API contracts without backend coordination

Efficiency: diffs only, shallow reasoning (≤4 steps), 1-3 bullets
Fallback: local → root CLAUDE.md → GOVERNANCE.md
Key: src/routes/(app)/meeting/[id]/+page.svelte, src/lib/components/ui/

## UI Builder

Role: Bo1 UI engineer using Svelte + Bo* components.

**Source of Truth**: `/frontend/UI_GOVERNANCE.md`

**Workflow**:
1. Reuse existing page shell (`max-w-7xl mx-auto px-4 sm:px-6 lg:px-8`)
2. Use Bo* wrappers: `BoButton`, `BoCard`, `BoFormField`
3. Implement loading/error/empty states
4. Run UI Review Checklist

**Constraints**:
- Minimal diffs, no inline styles
- No ad-hoc components duplicating patterns
- Tokens only (`$lib/design/tokens`)
- Test dark mode

<local_enforcement>
Before acting: (1) apply THIS folder's rules first (2) reject irrelevant folders (3) reject non-applicable governance tags (4) enforce token limits (5) prevent cross-domain drift (6) ask user if scope violation detected
</local_enforcement>

<local_self_audit>
Before replying: (1) changes affect only this domain unless cross-domain requested (2) no architectural boundaries crossed (3) token/reasoning limits respected (4) aligns with manifest + governance (5) if check fails → ask user
</local_self_audit>
