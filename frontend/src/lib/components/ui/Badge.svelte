<script lang="ts">
	/**
	 * Badge Component - Small status indicator
	 */

	import type { Snippet } from 'svelte';

	// Props
	interface Props {
		variant?: 'brand' | 'success' | 'warning' | 'error' | 'info' | 'neutral';
		size?: 'sm' | 'md' | 'lg';
		children?: Snippet;
	}

	let {
		variant = 'neutral',
		size = 'md',
		children
	}: Props = $props();

	// Variant styles
	const variants = {
		brand:
			'bg-brand-100 text-brand-800 dark:bg-brand-900 dark:text-brand-200',
		success:
			'bg-success-100 text-success-800 dark:bg-success-900 dark:text-success-200',
		warning:
			'bg-warning-100 text-warning-800 dark:bg-warning-900 dark:text-warning-200',
		error: 'bg-error-100 text-error-800 dark:bg-error-900 dark:text-error-200',
		info: 'bg-info-100 text-info-800 dark:bg-info-900 dark:text-info-200',
		neutral:
			'bg-neutral-100 text-neutral-800 dark:bg-neutral-800 dark:text-neutral-200',
	};

	// Size styles
	const sizes = {
		sm: 'px-2 py-0.5 text-xs',
		md: 'px-2.5 py-1 text-sm',
		lg: 'px-3 py-1.5 text-base',
	};

	// Compute classes
	const classes = $derived([
		'inline-flex items-center gap-1',
		'font-medium rounded-full',
		variants[variant],
		sizes[size],
	].join(' '));
</script>

<span class={classes}>
	{@render children?.()}
</span>
