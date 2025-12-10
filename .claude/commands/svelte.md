<task>
Bo1 Svelte 5 Compliance Audit & Migration

GOAL
Audit and migrate this project to be fully compliant with Svelte 5 (runes-first where appropriate), updating components and utilities as needed. Use Svelte MCP tools to:

- Understand current Svelte/SvelteKit and code patterns.
- Migrate away from legacy APIs/patterns where possible.
- Ensure all new/updated components are Svelte 5–compliant and autofixed.

CONSTRAINTS

- Treat this as a production migration: minimal, safe changes with clear intent.
- Prefer Svelte 5 runes mode for new/updated components unless the codebase is clearly using legacy mode intentionally.
- Do NOT invent new features; only modernise existing behaviour and APIs.
- Keep diffs small and focused (no mass rewrites).
- When in doubt, consult official docs via `get_documentation` BEFORE changing behaviour.
- Every time you write or modify a Svelte component or Svelte module, you MUST:
  1. Call `svelte-autofixer` with the code.
  2. Apply all necessary fixes.
  3. Call `svelte-autofixer` again.
  4. Repeat until the tool returns no issues or suggestions.
- Only then is that file considered complete.

DOCS USAGE (get_documentation)
Use `get_documentation` proactively when:

- Understanding or migrating legacy syntax or features:
  - `svelte/v5-migration-guide`
  - `svelte/what-are-runes`
  - `svelte/legacy-overview`
  - `svelte/legacy-*` pages as needed (export let, reactive statements, on:, slots, etc.)
- Migrating whole projects / major features:
  - `cli/sv-migrate`
- Ensuring correct SvelteKit usage:
  - `kit/introduction`
  - `kit/project-structure`
  - `kit/routing`
  - `kit/state-management`
- Checking performance, accessibility, and best practices:
  - `kit/performance`
  - `svelte/performance`
  - `svelte/accessibility`
- Clarifying specific language features:
  - Runes: `$state`, `$derived`, `$effect`, `$props`, `$bindable`, `$inspect`, `$host`
  - Templates & blocks: `svelte/if`, `svelte/each`, `svelte/snippet`, `svelte/@render`, etc.

Always prefer reading **targeted** docs over guessing.

STEP 1 – DISCOVER CURRENT STATE

1. Inspect `package.json`, Svelte config, and project structure to understand:
   - Svelte version and SvelteKit version (if applicable).
   - Whether the project is using runes or legacy APIs (or a mix).
2. Identify:
   - All `.svelte` files.
   - Any `.svelte.js` / `.svelte.ts` modules or shared Svelte utilities.
3. Build a mental map of:
   - Legacy patterns present (reactive labels, `export let`, `$:`, legacy stores-only reactivity, `on:` events, legacy slots).
   - Places where Svelte 5 runes would clearly improve clarity and correctness.

If unclear how to handle a pattern, call `get_documentation` for the relevant migration page.

STEP 2 – PRIORITISE MIGRATION TARGETS

1. Prioritise these for migration first:
   - High-traffic or core routes/pages.
   - Shared UI components used widely.
   - Components with heavy reactivity or complex state.
2. Defer deeply-nested or rarely used components if necessary, but still ensure basic Svelte 5 compatibility (no broken behaviour).

STEP 3 – MIGRATE COMPONENTS TO SVELTE 5 PATTERNS
For each selected component/module:

1. If it is clearly legacy-style:

   - Consult:
     - `svelte/v5-migration-guide`
     - `svelte/what-are-runes`
     - Relevant `svelte/legacy-*` docs as needed.
   - Apply minimal, clear changes to:
     - Replace legacy reactivity (`$:`/reactive labels) with runes-appropriate patterns (`$state`, `$derived`, `$effect`) where appropriate.
     - Modernise props handling and state management.
     - Update event handling and bindings to Svelte 5 idioms.

2. For all changed or newly created Svelte files:

   - Run the strict `svelte-autofixer` loop:
     - Call `svelte-autofixer` with the component/module code.
     - Apply all suggested fixes.
     - Repeat until `svelte-autofixer` reports no issues or suggestions.

3. Preserve behaviour:
   - Do not change semantics or user-visible behaviour unless required by the migration.
   - If a behavioural change is unavoidable, keep it minimal and clearly intentional in the diff.

STEP 4 – ENSURE SVELTEKIT & PROJECT-LEVEL COMPLIANCE (IF APPLICABLE)
If this is a SvelteKit project:

1. Check routing, load functions, and server modules:
   - Use `kit/project-structure`, `kit/routing`, `kit/load`, `kit/state-management` as needed.
2. Ensure:
   - Modern, supported APIs and patterns.
   - No reliance on deprecated or removed SvelteKit features.
3. For any server-only / env-related code, validate via:
   - `$app/server`, `$env/*` docs.

Apply `svelte-autofixer` to any Svelte modules you update that contain Svelte-specific logic.

STEP 5 – FINAL CONSISTENCY & SAFETY CHECK

1. Ensure:
   - No mixed “half-migrated” components (old and new patterns clashing).
   - No obvious legacy APIs left in critical components.
   - All modified Svelte files have passed the `svelte-autofixer` loop.
2. If any parts of the project are intentionally left in legacy mode:
   - Ensure they still compile and run correctly.
   - Minimise interop friction with runes-based components.

OUTPUT

- Update the Svelte components and modules directly in the project, using minimal, clear diffs.
- For the user, provide a brief summary only:
  - What main areas were migrated.
  - Which major patterns were modernised (e.g., reactivity, props, events).
  - Any deliberately remaining legacy sections and why.

Do NOT print entire files in the final response unless strictly necessary.

</task>
