<script lang="ts">
	/**
	 * BoCard - Canonical card wrapper
	 * Wraps Card.svelte with standardized Bo1 API
	 */
	import Card from './Card.svelte';
	import type { Snippet } from 'svelte';

	interface Props {
		variant?: 'default' | 'bordered' | 'elevated';
		padding?: 'none' | 'sm' | 'md' | 'lg';
		class?: string;
		children?: Snippet;
		header?: Snippet;
		footer?: Snippet;
	}

	let {
		variant = 'bordered',
		padding = 'md',
		class: className,
		children,
		header,
		footer,
	}: Props = $props();
</script>

<Card {variant} {padding} class={className}>
	{#snippet header()}
		{@render header?.()}
	{/snippet}
	{@render children?.()}
	{#snippet footer()}
		{@render footer?.()}
	{/snippet}
</Card>
