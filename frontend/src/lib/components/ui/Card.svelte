<script lang="ts">
	/**
	 * Card Component - shadcn-svelte wrapper with backward-compatible API
	 * Preserves variant, padding, and slot-based header/footer
	 */
	import { Card as ShadcnCard, CardHeader, CardContent, CardFooter } from './shadcn/card';
	import type { Snippet } from 'svelte';
	import { paddingClasses } from './utils';

	// Props matching the legacy API
	interface Props {
		variant?: 'default' | 'bordered' | 'elevated';
		padding?: 'none' | 'sm' | 'md' | 'lg';
		class?: string;
		children?: Snippet;
		header?: Snippet;
		footer?: Snippet;
	}

	let {
		variant = 'default',
		padding = 'md',
		class: customClass = '',
		children,
		header,
		footer
	}: Props = $props();

	// Variant styles
	const variantClasses = {
		default: '',
		bordered: 'border-2',
		elevated: 'shadow-lg',
	};

	const variantClass = $derived(variantClasses[variant] ?? '');
	const padClass = $derived(paddingClasses(padding));
</script>

<ShadcnCard class="{variantClass} {padClass} {customClass}">
	{#if header}
		<CardHeader class="p-0 mb-4">
			{@render header()}
		</CardHeader>
	{/if}

	<CardContent class="p-0">
		{@render children?.()}
	</CardContent>

	{#if footer}
		<CardFooter class="p-0 mt-4">
			{@render footer()}
		</CardFooter>
	{/if}
</ShadcnCard>
