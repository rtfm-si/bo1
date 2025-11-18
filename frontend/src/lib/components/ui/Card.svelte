<script lang="ts">
	/**
	 * Card Component - Container for content with variants
	 */

	// Props
	export let variant: 'default' | 'bordered' | 'elevated' = 'default';
	export let padding: 'none' | 'sm' | 'md' | 'lg' = 'md';

	// Variant styles (use CSS variables for theme support)
	const variants = {
		default: '',
		bordered: 'border',
		elevated: 'shadow-lg',
	};

	// Padding styles
	const paddings = {
		none: '',
		sm: 'p-4',
		md: 'p-6',
		lg: 'p-8',
	};

	// Compute classes
	$: classes = ['rounded-lg', variants[variant], paddings[padding]].join(' ');
</script>

<div
	class={classes}
	style="background-color: var(--color-surface); border-color: var(--color-border);"
>
	{#if $$slots.header}
		<div class="mb-4">
			<slot name="header" />
		</div>
	{/if}

	<slot />

	{#if $$slots.footer}
		<div class="mt-4">
			<slot name="footer" />
		</div>
	{/if}
</div>
