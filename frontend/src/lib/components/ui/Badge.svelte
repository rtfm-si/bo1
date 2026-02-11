<script lang="ts">
	/**
	 * Badge Component - thin shadcn-svelte wrapper
	 * Passes variant/size straight through to shadcn Badge
	 */
	import { Badge as ShadcnBadge } from './shadcn/badge';
	import type { BadgeVariant, BadgeSize } from './shadcn/badge';
	import type { Snippet } from 'svelte';

	// Props
	interface Props {
		variant?: 'brand' | 'success' | 'warning' | 'error' | 'info' | 'neutral';
		size?: 'sm' | 'md' | 'lg';
		class?: string;
		children?: Snippet;
	}

	let {
		variant = 'neutral',
		size = 'md',
		class: className = '',
		children
	}: Props = $props();
</script>

<ShadcnBadge
	variant={variant as BadgeVariant}
	size={size as BadgeSize}
	class={className}
>
	{@render children?.()}
</ShadcnBadge>
