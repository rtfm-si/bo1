<script lang="ts">
	/**
	 * Card Component - shadcn-svelte wrapper
	 * Adds slot-based header/footer on top of shadcn Card
	 */
	import { Card as ShadcnCard, CardHeader, CardContent, CardFooter } from './shadcn/card';
	import type { CardVariant, CardPadding } from './shadcn/card';
	import type { Snippet } from 'svelte';

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
		class: customClass = '',
		children,
		header,
		footer
	}: Props = $props();
</script>

<ShadcnCard variant={variant as CardVariant} padding={padding as CardPadding} class={customClass}>
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
