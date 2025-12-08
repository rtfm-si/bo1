Bo1 UI System Bootstrap (Svelte + shadcn-svelte)

GOAL
Create a consistent, modern UI/UX foundation for Bo1 using:

- Our existing design guides (design tokens, typography, spacing, color, etc.)
- Svelte
- shadcn-svelte (or equivalent shadcn port)
- Minimal, composable Bo\* UI wrappers

Deliver:

1. UI governance + checklist
2. Frontend Claude guidance for UI work
3. Canonical Bo\* components built on shadcn-svelte

CONSTRAINTS

- Follow all governance:
  - CLAUDE.md
  - GOVERNANCE.md
  - CONTEXT_BOUNDARY.md
  - MODEL_GUIDANCE.md
  - TASK_PATTERNS.md
  - TAGS.md
  - Any frontend-level CLAUDE/manifest files
- Use our existing design guides:
  - Tailwind config (colors, spacing, typography)
  - Any design tokens or docs in /docs, /frontend, /design, or similar
- Keep reasoning shallow and outputs concise.
- Use minimal diffs; do NOT dump entire files unless necessary.
- Do not modify global governance files; only update frontend-specific ones where needed.

---

## STEP 1 – DISCOVER EXISTING DESIGN GUIDES

1. Locate relevant frontend/design sources, for example:
   - /frontend/tailwind.config.\* or equivalent
   - /frontend/src/lib/components/ui or similar
   - /docs/\* design or UI guides (if they exist)
   - Any existing shadcn-svelte setup or config
2. Infer:
   - Core color tokens (primary, secondary, accent, muted, destructive, background, foreground).
   - Spacing/radius conventions.
   - Typography scale and preferred classes.
3. Keep this summary short; use it to drive the files you create, but don’t duplicate large content.

---

## STEP 2 – CREATE /frontend/UI_GOVERNANCE.md

Create or overwrite `/frontend/UI_GOVERNANCE.md` with a concise document that includes:

1. **Design System**

   - Reference our existing tokens (colors, spacing, typography) by name/class, not inline values.
   - Rules:
     - “Use Tailwind tokens and design tokens for colors/spacing/typography.”
     - “Do not introduce new arbitrary values without updating the design system.”

2. **Layout Conventions**

   - Page shell pattern (max width, padding, breakpoints).
   - Card/grid/list conventions.
   - Form layout pattern (labels, errors, helper text).

3. **Components & Patterns**

   - Mandates:
     - Use Bo\* wrappers (BoButton, BoCard, BoFormField, etc.) instead of raw HTML for core UI.
     - Use shadcn-svelte primitives via Bo\* wrappers.

4. **Interaction & States**

   - Loading, empty, error state expectations.
   - Button variants (primary, secondary, ghost, destructive).
   - Confirm only ONE primary action per view.

5. **UI Review Checklist**
   - Layout: reuse layout primitives, responsive at 3 breakpoints.
   - Visual: tokens only, canonical components only.
   - UX: clear primary action, proper states, concise copy.
   - Accessibility: semantics, labels, keyboard navigation, contrast.
   - Performance: avoid heavy recomputes, unnecessary re-renders.

Keep this file succinct and highly actionable.

---

## STEP 3 – UPDATE /frontend/CLAUDE.md WITH A UI BUILDER SECTION

1. Open `/frontend/CLAUDE.md` (create if missing).
2. Add a **UI Builder** section that:

   - States the role:
     - “When editing UI in /frontend, act as a Bo1 UI engineer using Svelte + shadcn-svelte + Bo\* components.”
   - References `/frontend/UI_GOVERNANCE.md` as the source of truth.
   - Includes a short “UI Builder Workflow”:
     1. Reuse existing page shell/layout.
     2. Use Bo\* wrappers and shadcn-svelte components.
     3. Implement loading/error/empty states.
     4. Run the UI Review Checklist.
   - Emphasises:
     - Minimal diffs.
     - No inline styles.
     - No ad-hoc components duplicating existing patterns.

3. Ensure this new section is compact and fits the token-efficiency rules in root CLAUDE.md.

---

## STEP 4 – CREATE CANONICAL Bo\* COMPONENTS (Svelte + shadcn-svelte)

Create the following components (paths may be adapted to existing structure, but default to):

- `/frontend/src/lib/components/ui/BoButton.svelte`
- `/frontend/src/lib/components/ui/BoCard.svelte`
- `/frontend/src/lib/components/ui/BoFormField.svelte`
- If an index file exists, update:
  - `/frontend/src/lib/components/ui/index.ts` (or equivalent) to export these.

Design rules:

1. **BoButton.svelte**

   - Wrap the shadcn-svelte Button.
   - Standardise variants: `default`, `secondary`, `outline`, `ghost`, `destructive`, `link`.
   - Enforce:
     - `size` options (e.g. `sm`, `md`, `lg`).
     - No inline classes for colors; always variant-based.
   - Provide a single, consistent API for buttons across the app.

2. **BoCard.svelte**

   - Wrap a shadcn-style card (header, title, description, content, footer slots).
   - Use design tokens for padding, radius, shadow.
   - Encourage composition via slots.

3. **BoFormField.svelte**
   - Standard wrapper for:
     - Label
     - Optional description/help text
     - Error message
     - Field slot (input/select/etc.)
   - Works with shadcn inputs, selects, etc.
   - Enforce consistent spacing and error display.

Implementation details:

- Use our existing Tailwind config and shadcn patterns.
- Prefer small, focused components; no extra business logic inside these wrappers.

---

## STEP 5 – OPTIONAL: LAYOUT PRIMITIVES

If not already present, create ONE small layout primitive file, e.g.:

- `/frontend/src/lib/components/layout/PageShell.svelte`

It should:

- Center content (`max-w-*`, `mx-auto`, `px-*`, `py-*`).
- Handle basic responsive spacing.
- Be referenced in UI_GOVERNANCE as the default page wrapper.

Keep it minimal.

---

## STEP 6 – SELF-CHECK (RUNTIME SELF-AUDIT)

Before finalising:

1. Confirm:
   - UI_GOVERNANCE.md uses our existing design guides (class names, tokens).
   - Bo\* components reuse shadcn-svelte and tokens correctly.
   - Frontend CLAUDE.md references UI_GOVERNANCE and Bo\* components.
2. Confirm:
   - No unrelated files changed.
   - No global governance files modified.
3. If any ambiguity about existing design conventions arises:
   - Make a best-effort guess that is consistent with the code you see.
   - Keep decisions local to `/frontend` and clearly expressed in docs.

---

## OUTPUT REQUIREMENTS

- Apply changes directly to:
  - /frontend/UI_GOVERNANCE.md
  - /frontend/CLAUDE.md
  - /frontend/src/lib/components/ui/BoButton.svelte
  - /frontend/src/lib/components/ui/BoCard.svelte
  - /frontend/src/lib/components/ui/BoFormField.svelte
  - Any necessary UI index exports
  - Optional layout primitive (PageShell)
- In the chat, output only:
  - A short list of files created/updated.
  - A bullet summary of the design rules enforced.
- Do not restate this prompt.

Now perform this UI system bootstrap.
