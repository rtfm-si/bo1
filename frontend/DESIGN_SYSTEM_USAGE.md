# Design System Usage Guide

**Board of One Frontend Design System v2.0**

Complete guide to using the Board of One design system with teal brand color (`#00C8B3`), progressive disclosure patterns, and three theme variants.

## Table of Contents

1. [Quick Start](#quick-start)
2. [Color Palette](#color-palette)
3. [Component Library](#component-library)
4. [Progressive Disclosure Components](#progressive-disclosure-components)
5. [Theme System](#theme-system)
6. [Design Tokens](#design-tokens)
7. [Accessibility](#accessibility)
8. [Best Practices](#best-practices)

---

## Quick Start

### Import Components

```svelte
<script lang="ts">
  import { Button, Card, Input, Badge, Alert } from '$lib/components/ui';
  import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';
</script>
```

### Basic Example

```svelte
<Card variant="bordered">
  <h2 slot="header">Welcome to Board of One</h2>

  <p>This is a card component with a header slot.</p>

  <Input
    label="Email"
    type="email"
    placeholder="your@email.com"
    required
  />

  <div slot="footer" class="flex gap-2">
    <Button variant="brand">Submit</Button>
    <Button variant="ghost">Cancel</Button>
  </div>
</Card>
```

---

## Color Palette

### Brand Color Rationale

**Primary: `#00C8B3` (Teal)**
- Psychology: Trust, clarity, professionalism, analytical thinking
- Use cases: Primary buttons, links, active states, brand identity
- Contrast: Excellent readability on white (AAA) and dark backgrounds (AA)

**Accent: `#ff6b47` (Coral)**
- Theory: Complementary to teal on color wheel (warm vs. cool)
- Psychology: Energy, action, warmth, approachability
- Use cases: Secondary CTAs, highlights, attention-grabbing elements

**Semantic Colors**:
- Success: `#10b05e` (green aligned with teal)
- Warning: `#f59e0b` (amber)
- Error: `#ef4444` (red-orange harmonizing with coral)
- Info: `#06b6d4` (cyan, lighter teal variant)

**Neutral**: Cool grays with subtle teal tint for visual consistency.

### Using Colors

```html
<!-- Brand teal -->
<div class="bg-brand-500 text-white">Primary action</div>
<div class="bg-brand-50 text-brand-700 dark:bg-brand-900 dark:text-brand-300">Light background</div>

<!-- Coral accent -->
<Button variant="accent">Secondary CTA</Button>

<!-- Semantic -->
<Badge variant="success">Active</Badge>
<Alert variant="error">Failed</Alert>
```

---

## Component Library

### Button Component

**Variants**: `brand`, `accent`, `secondary`, `ghost`, `danger`
**Sizes**: `sm`, `md`, `lg`

```svelte
<script lang="ts">
  import { Button } from '$lib/components/ui';

  let loading = false;

  async function handleSubmit() {
    loading = true;
    // Perform async operation
    await new Promise(resolve => setTimeout(resolve, 2000));
    loading = false;
  }
</script>

<!-- Variants -->
<Button variant="brand">Brand Button</Button>
<Button variant="accent">Accent Button</Button>
<Button variant="secondary">Secondary Button</Button>
<Button variant="ghost">Ghost Button</Button>
<Button variant="danger">Danger Button</Button>

<!-- Sizes -->
<Button size="sm">Small</Button>
<Button size="md">Medium</Button>
<Button size="lg">Large</Button>

<!-- Loading State -->
<Button variant="brand" {loading} on:click={handleSubmit}>
  {loading ? 'Processing...' : 'Submit'}
</Button>

<!-- Disabled -->
<Button disabled>Disabled</Button>
```

---

### Card Component

**Variants**: `default`, `bordered`, `elevated`
**Padding**: `none`, `sm`, `md`, `lg`
**Slots**: `header`, `default`, `footer`

```svelte
<script lang="ts">
  import { Card, Button } from '$lib/components/ui';
</script>

<!-- Basic Card -->
<Card>
  <p>This is a basic card with default styling.</p>
</Card>

<!-- Card with Slots -->
<Card variant="bordered">
  <h3 slot="header" class="text-xl font-bold">Card Title</h3>

  <p>This is the main content area.</p>

  <div slot="footer" class="flex justify-end gap-2">
    <Button variant="secondary" size="sm">Cancel</Button>
    <Button variant="brand" size="sm">Save</Button>
  </div>
</Card>

<!-- Elevated Card -->
<Card variant="elevated" padding="lg">
  <p>This card has a shadow and large padding.</p>
</Card>

<!-- No Padding (for images) -->
<Card padding="none">
  <img src="/hero.jpg" alt="Hero" class="w-full rounded-t-lg" />
  <div class="p-6">
    <h3>Image Card</h3>
    <p>Content with custom padding</p>
  </div>
</Card>
```

---

### Input Component

**Types**: `text`, `email`, `password`, `number`, `tel`, `url`

```svelte
<script lang="ts">
  import { Input, Button } from '$lib/components/ui';

  let email = '';
  let password = '';
  let errors: Record<string, string> = {};

  function validateForm() {
    errors = {};

    if (!email.includes('@')) {
      errors.email = 'Please enter a valid email address';
    }

    if (password.length < 8) {
      errors.password = 'Password must be at least 8 characters';
    }
  }
</script>

<!-- Basic Input -->
<Input
  label="Email"
  type="email"
  placeholder="your@email.com"
  bind:value={email}
  required
/>

<!-- Input with Error -->
<Input
  label="Password"
  type="password"
  placeholder="Enter password"
  bind:value={password}
  error={errors.password}
  required
/>

<!-- Input with Helper Text -->
<Input
  label="Username"
  type="text"
  placeholder="johndoe"
  helperText="Must be unique and at least 3 characters"
/>

<!-- Disabled Input -->
<Input
  label="User ID"
  type="text"
  value="user-12345"
  disabled
/>

<!-- Number Input -->
<Input
  label="Age"
  type="number"
  placeholder="18"
/>
```

---

### Badge Component

**Variants**: `success`, `warning`, `error`, `info`, `neutral`
**Sizes**: `sm`, `md`, `lg`

```svelte
<script lang="ts">
  import { Badge } from '$lib/components/ui';
</script>

<!-- Status Badges -->
<Badge variant="success">Active</Badge>
<Badge variant="warning">Pending</Badge>
<Badge variant="error">Failed</Badge>
<Badge variant="info">In Progress</Badge>
<Badge variant="neutral">Draft</Badge>

<!-- Sizes -->
<Badge size="sm">Small</Badge>
<Badge size="md">Medium</Badge>
<Badge size="lg">Large</Badge>

<!-- Usage in Context -->
<div class="flex items-center gap-2">
  <h3>Session Status:</h3>
  <Badge variant="success">Completed</Badge>
</div>
```

---

### Alert Component

**Variants**: `success`, `warning`, `error`, `info`
**Dismissable**: `true` | `false`

```svelte
<script lang="ts">
  import { Alert } from '$lib/components/ui';

  let showAlert = true;
</script>

<!-- Success Alert -->
<Alert variant="success" title="Success!">
  Your deliberation has been created successfully.
</Alert>

<!-- Warning Alert -->
<Alert variant="warning" title="Warning">
  This action cannot be undone. Please proceed with caution.
</Alert>

<!-- Error Alert -->
<Alert variant="error" title="Error">
  Failed to connect to the API. Please try again later.
</Alert>

<!-- Info Alert -->
<Alert variant="info">
  New features are available! Check out the latest updates.
</Alert>

<!-- Dismissable Alert -->
{#if showAlert}
  <Alert
    variant="info"
    dismissable
    on:dismiss={() => showAlert = false}
  >
    This alert can be dismissed by clicking the X button.
  </Alert>
{/if}
```

---

## Progressive Disclosure Components

### ProgressBar

Visual progress indicator with animations for stage tracking and loading states.

```svelte
<script>
  import { ProgressBar } from '$lib/components/ui';
  let progress = 65;
</script>

<!-- Basic progress -->
<ProgressBar value={progress} variant="brand" showLabel />

<!-- Different sizes -->
<ProgressBar value={75} variant="accent" size="sm" />
<ProgressBar value={100} variant="success" size="lg" />

<!-- Indeterminate loading -->
<ProgressBar indeterminate variant="brand" />
```

**Props**: `value` (0-100), `variant`, `size`, `animated`, `indeterminate`, `showLabel`

---

### Spinner

Loading indicator with smooth rotation for async operations.

```svelte
<Spinner size="md" variant="brand" ariaLabel="Loading session" />
```

**Sizes**: `xs`, `sm`, `md`, `lg`, `xl`

---

### Avatar

User/persona profile picture with fallback initials and status indicators.

```svelte
<Avatar name="Maria Chen" size="md" status="typing" />
<Avatar name="Board of One" src="/logo.png" size="lg" />
```

**Status**: `online`, `offline`, `typing`

---

### Tooltip

Hover-triggered contextual information.

```svelte
<Tooltip text="Marketing Strategy & Consumer Behavior" position="top">
  <Badge>MARIA</Badge>
</Tooltip>
```

---

### Modal

Accessible dialog overlay with focus trap and scroll lock.

```svelte
<script>
  let showModal = false;
</script>

<Button on:click={() => showModal = true}>Open Details</Button>

<Modal bind:open={showModal} title="Session Details" size="md">
  <p>Modal content...</p>

  <div slot="footer">
    <Button variant="ghost" on:click={() => showModal = false}>Cancel</Button>
    <Button variant="brand">Confirm</Button>
  </div>
</Modal>
```

**Features**: ESC to close, backdrop click, focus trap, scroll lock

---

### Dropdown

Accessible select with keyboard navigation and search.

```svelte
<script>
  import type { DropdownItem } from '$lib/components/ui';

  const items: DropdownItem[] = [
    { value: 'light', label: 'Light Theme', icon: '☀️' },
    { value: 'dark', label: 'Dark Theme', icon: '🌙' },
  ];
  let selected = 'light';
</script>

<Dropdown {items} bind:value={selected} searchable />
```

---

### Tabs

Multi-section content with keyboard navigation.

```svelte
<script>
  import type { Tab } from '$lib/components/ui';

  const tabs: Tab[] = [
    { id: 'overview', label: 'Overview', icon: '📊' },
    { id: 'contributions', label: 'Contributions', icon: '💬' },
  ];
  let activeTab = 'overview';
</script>

<Tabs {tabs} bind:activeTab>
  <div slot="overview">Overview content</div>
  <div slot="contributions">Contributions feed</div>
</Tabs>
```

---

### Toast

Temporary notification message with auto-dismiss.

```svelte
<script>
  let toasts = [];

  function showToast(type, message) {
    toasts = [...toasts, { id: Date.now(), type, message }];
  }
</script>

<!-- Toast container (fixed position) -->
<div class="fixed top-4 right-4 z-[1100] space-y-2">
  {#each toasts as toast (toast.id)}
    <Toast
      type={toast.type}
      message={toast.message}
      on:dismiss={() => toasts = toasts.filter(t => t.id !== toast.id)}
    />
  {/each}
</div>

<!-- Trigger -->
<Button on:click={() => showToast('success', 'Session started!')}>
  Show Toast
</Button>
```

---

### InsightFlag

Live insight indicator for risk/opportunity/tension/alignment.

```svelte
<InsightFlag
  type="risk"
  message="Market volatility detected in Q4 projections"
  dismissable
  pulse
/>

<InsightFlag
  type="opportunity"
  message="Strategic alignment with AI trends"
/>
```

**Types**: `risk`, `opportunity`, `tension`, `alignment`

---

### ContributionCard

Expert contribution display with avatar, expertise, and confidence badge.

```svelte
<script>
  import type { Persona } from '$lib/components/ui';

  const persona: Persona = {
    name: 'Maria Chen',
    code: 'MARIA',
    expertise: 'Marketing Strategy & Consumer Behavior'
  };
</script>

<ContributionCard
  {persona}
  content="I recommend a phased rollout strategy..."
  timestamp={new Date()}
  confidence="high"
>
  <div slot="actions">
    <Button size="sm" variant="ghost">View Analysis</Button>
  </div>
</ContributionCard>
```

---

## Theme System

### Theme Switcher Component

```svelte
<script lang="ts">
  import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';
</script>

<!-- Add to navbar or header -->
<nav class="flex items-center justify-between p-4">
  <h1>Board of One</h1>
  <ThemeSwitcher />
</nav>
```

### Initialize Theme in Root Layout

```svelte
<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { themeStore } from '$lib/stores/theme';
  import '../app.css';

  onMount(() => {
    // Initialize theme on app load
    themeStore.initialize();
  });
</script>

<slot />
```

### Programmatically Change Theme

```svelte
<script lang="ts">
  import { themeStore } from '$lib/stores/theme';
  import { Button } from '$lib/components/ui';
</script>

<Button on:click={() => themeStore.setTheme('dark')}>
  Switch to Dark Mode
</Button>

<Button on:click={() => themeStore.setTheme('light')}>
  Switch to Light Mode
</Button>

<Button on:click={() => themeStore.setTheme('ocean')}>
  Switch to Ocean Theme
</Button>
```

### Available Themes

- **Light** (`light`) - Clean, bright interface
- **Dark** (`dark`) - Dark mode for low-light environments
- **Ocean** (`ocean`) - Deep blue theme with cyan accents

---

## Design Tokens

### Using Design Tokens in Tailwind

Design tokens are automatically integrated into Tailwind CSS. Use semantic color names:

```svelte
<!-- Semantic Colors (RECOMMENDED) -->
<div class="bg-brand-600 text-white">Brand color</div>
<div class="bg-accent-500 text-white">Accent color</div>
<div class="bg-success-600 text-white">Success color</div>
<div class="bg-warning-500 text-neutral-900">Warning color</div>
<div class="bg-error-600 text-white">Error color</div>
<div class="bg-info-600 text-white">Info color</div>
<div class="bg-neutral-100 text-neutral-900">Neutral color</div>

<!-- Dark Mode Support -->
<div class="bg-brand-600 dark:bg-brand-400">
  Auto-adjusts in dark mode
</div>

<!-- Spacing (4px grid) -->
<div class="p-4 m-2 gap-3">
  <!-- p-4 = 16px, m-2 = 8px, gap-3 = 12px -->
</div>

<!-- Typography -->
<h1 class="text-4xl font-bold">Large Heading</h1>
<p class="text-base font-normal">Body text</p>
<span class="text-sm font-medium">Small text</span>

<!-- Shadows -->
<div class="shadow-sm">Subtle shadow</div>
<div class="shadow-md">Medium shadow</div>
<div class="shadow-lg">Large shadow</div>

<!-- Border Radius -->
<div class="rounded-md">Medium rounded corners</div>
<div class="rounded-lg">Large rounded corners</div>
<div class="rounded-full">Fully rounded</div>
```

### Importing Tokens in TypeScript

```typescript
import { colors, spacing, typography } from '$lib/design/tokens';

// Access specific token values
const brandColor = colors.brand[600]; // '#0284c7'
const largePadding = spacing[8]; // '2rem' (32px)
const headingSize = typography.fontSize['4xl']; // ['2.25rem', { lineHeight: '2.5rem' }]
```

---

## Complete Page Example

```svelte
<!-- src/routes/(app)/example/+page.svelte -->
<script lang="ts">
  import { Button, Card, Input, Badge, Alert } from '$lib/components/ui';
  import ThemeSwitcher from '$lib/components/ThemeSwitcher.svelte';

  let email = '';
  let password = '';
  let showSuccess = false;

  async function handleLogin() {
    // Mock login
    showSuccess = true;
    setTimeout(() => showSuccess = false, 3000);
  }
</script>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-950 p-8">
  <!-- Header -->
  <header class="flex items-center justify-between mb-8">
    <div class="flex items-center gap-3">
      <h1 class="text-3xl font-bold">Board of One</h1>
      <Badge variant="info">Beta</Badge>
    </div>
    <ThemeSwitcher />
  </header>

  <!-- Success Alert -->
  {#if showSuccess}
    <Alert variant="success" dismissable on:dismiss={() => showSuccess = false}>
      Login successful! Redirecting...
    </Alert>
  {/if}

  <!-- Login Card -->
  <div class="max-w-md mx-auto">
    <Card variant="bordered">
      <h2 slot="header" class="text-2xl font-bold">Sign In</h2>

      <form on:submit|preventDefault={handleLogin} class="space-y-4">
        <Input
          label="Email"
          type="email"
          placeholder="your@email.com"
          bind:value={email}
          required
        />

        <Input
          label="Password"
          type="password"
          placeholder="Enter password"
          bind:value={password}
          required
        />

        <div slot="footer" class="flex flex-col gap-3">
          <Button type="submit" variant="brand" size="lg" class="w-full">
            Sign In
          </Button>
          <Button variant="ghost" size="md" class="w-full">
            Forgot Password?
          </Button>
        </div>
      </form>
    </Card>
  </div>
</div>
```

---

## Accessibility

All components include comprehensive accessibility features:

### Keyboard Navigation

- **Buttons**: Enter/Space to activate
- **Modals**: ESC to close, Tab for focus trap
- **Dropdowns**: Arrow keys, Enter to select, ESC to close
- **Tabs**: Arrow keys (left/right), Home/End
- **Tooltips**: Keyboard focus triggers

### ARIA Labels

```svelte
<!-- Spinner -->
<Spinner ariaLabel="Loading deliberation results" />

<!-- Button (icon-only) -->
<Button variant="ghost" ariaLabel="Close modal">×</Button>

<!-- Progress -->
<ProgressBar value={65} ariaLabel="Session progress: 65%" />
```

### Screen Reader Support

```svelte
<!-- Status updates -->
<div role="status" aria-live="polite">
  <InsightFlag type="risk" message="Alert" />
</div>

<!-- Loading states -->
<div role="status" aria-busy="true">
  <Spinner ariaLabel="Loading" />
</div>
```

---

## Best Practices

### 1. Use Semantic Color Names

❌ **Don't use**: `primary`, `secondary`
✅ **Use**: `brand`, `accent`, `success`, `warning`, `error`

```svelte
<!-- BAD -->
<Button variant="primary">Submit</Button>

<!-- GOOD -->
<Button variant="brand">Submit</Button>
```

### 2. Always Support Dark Mode

```svelte
<!-- Always provide dark mode alternatives -->
<div class="bg-white dark:bg-neutral-900">
  <p class="text-neutral-900 dark:text-neutral-100">
    Content that works in both modes
  </p>
</div>
```

### 3. Use Component Library Over Utility Classes

```svelte
<!-- BAD -->
<button class="px-4 py-2 bg-brand-600 text-white rounded-md hover:bg-brand-700">
  Submit
</button>

<!-- GOOD -->
<Button variant="brand">Submit</Button>
```

### 4. Leverage TypeScript for Type Safety

```svelte
<script lang="ts">
  import type { ComponentProps } from 'svelte';
  import { Button } from '$lib/components/ui';

  // Type-safe button props
  let buttonProps: ComponentProps<Button> = {
    variant: 'brand',
    size: 'md',
    disabled: false
  };
</script>

<Button {...buttonProps}>Submit</Button>
```

### 5. Accessibility First

```svelte
<!-- Always provide ARIA labels for icon-only buttons -->
<Button variant="ghost" ariaLabel="Close dialog">
  <svg><!-- X icon --></svg>
</Button>

<!-- Use semantic HTML -->
<form on:submit|preventDefault={handleSubmit}>
  <Input label="Email" type="email" required />
  <Button type="submit">Submit</Button>
</form>
```

---

## Troubleshooting

### Theme Not Applying

Make sure you initialize the theme in your root layout:

```svelte
<!-- src/routes/+layout.svelte -->
<script lang="ts">
  import { onMount } from 'svelte';
  import { themeStore } from '$lib/stores/theme';

  onMount(() => {
    themeStore.initialize();
  });
</script>
```

### Tailwind Classes Not Working

Verify your `tailwind.config.js` imports the design tokens:

```javascript
import { colors, spacing, typography } from './src/lib/design/tokens';
```

### Dark Mode Not Working

Ensure `darkMode: 'class'` is set in `tailwind.config.js` and the theme system applies the `dark` class to `<html>`.

---

## Resources

- Design Tokens: `/Users/si/projects/bo1/frontend/src/lib/design/tokens.ts`
- Theme System: `/Users/si/projects/bo1/frontend/src/lib/design/themes.ts`
- Components: `/Users/si/projects/bo1/frontend/src/lib/components/ui/`
- Tailwind Config: `/Users/si/projects/bo1/frontend/tailwind.config.js`
- Global Styles: `/Users/si/projects/bo1/frontend/src/app.css`
