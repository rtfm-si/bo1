<script lang="ts">
	/**
	 * Card Component - Container for content with variants
	 */

	import type { Snippet } from 'svelte';
	import { paddingClasses } from './utils';

	// Props
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
		class: customClass,
		children,
		header,
		footer
	}: Props = $props();

	// Variant styles (use CSS variables for theme support)
	const variants = {
		default: '',
		bordered: 'border',
		elevated: 'shadow-lg',
	};

	// Compute classes using design token utilities
	const classes = $derived([
		'rounded-lg',
		variants[variant],
		paddingClasses(padding),
		customClass
	].filter(Boolean).join(' '));
</script>

<div
	class={classes}
	style="background-color: var(--color-surface); border-color: var(--color-border);"
>
	{#if header}
		<div class="mb-4">
			{@render header()}
		</div>
	{/if}

	{@render children?.()}

	{#if footer}
		<div class="mt-4">
			{@render footer()}
		</div>
	{/if}
</div>
