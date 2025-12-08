# UI Governance - Bo1 Frontend

GOVERNANCE LOCK: Follow root CLAUDE.md; do not expand without user request.

## Design System

**Tokens**: Use `$lib/design/tokens` for all values.
- Colors: `brand-*`, `neutral-*`, `error-*`, `warning-*`, `success-*`, `info-*`
- Typography: `textStyles.h1/h2/h3/body/small/label` from tokens
- Spacing: 4px grid (`p-4`, `gap-3`, `space-y-2`)
- Radius: `rounded-md` (default), `rounded-lg` (cards)
- Shadows: `shadow-sm/md/lg` (use sparingly)

**Rules**:
- Use Tailwind token classes, never arbitrary values
- Dark mode: Use `dark:` variants, test both modes
- No inline styles except CSS variables

## Layout Conventions

**Page Shell**:
```svelte
<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
  <!-- content -->
</div>
```

**Breakpoints**: `sm:640px`, `md:768px`, `lg:1024px`, `xl:1280px`

**Patterns**:
- Cards: `<BoCard>` with header/content/footer slots
- Forms: `<BoFormField>` wrapping inputs
- Lists: `space-y-*` for vertical, `gap-*` for grid/flex

## Components

**Required**: Use Bo* wrappers, not raw HTML for core UI.
- `<BoButton>` - all buttons
- `<BoCard>` - content containers
- `<BoFormField>` - form inputs with label/error

**Existing**: Reuse `$lib/components/ui/*` (Button, Card, Input, Alert, Badge, Modal, etc.)

## Interaction States

**Button Variants**: `brand`, `secondary`, `outline`, `ghost`, `danger`
- One primary action per view
- Use `loading` prop during async ops

**States** (required):
- Loading: `<Spinner>` or skeleton
- Empty: Message + optional action
- Error: `<Alert variant="error">` with retry

## UI Review Checklist

- [ ] Uses Bo* components, not raw HTML
- [ ] Tokens only, no arbitrary values
- [ ] Responsive at sm/md/lg
- [ ] Loading/empty/error states
- [ ] Single primary action
- [ ] Semantic HTML, ARIA labels
- [ ] Dark mode works
- [ ] Keyboard navigable
