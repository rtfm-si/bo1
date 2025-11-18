<script lang="ts">
	/**
	 * Button Component - Reusable button with variants and sizes
	 */

	// Props
	export let variant: 'brand' | 'accent' | 'secondary' | 'ghost' | 'danger' = 'brand';
	export let size: 'sm' | 'md' | 'lg' = 'md';
	export let type: 'button' | 'submit' | 'reset' = 'button';
	export let disabled = false;
	export let loading = false;
	export let ariaLabel: string | undefined = undefined;

	// Variant styles
	const variants = {
		brand:
			'bg-brand-600 text-white hover:bg-brand-700 focus:ring-brand-500 dark:bg-brand-500 dark:hover:bg-brand-600',
		accent:
			'bg-accent-600 text-white hover:bg-accent-700 focus:ring-accent-500 dark:bg-accent-500 dark:hover:bg-accent-600',
		secondary:
			'bg-neutral-200 text-neutral-900 hover:bg-neutral-300 focus:ring-neutral-500 dark:bg-neutral-700 dark:text-neutral-100 dark:hover:bg-neutral-600',
		ghost:
			'bg-transparent text-neutral-700 hover:bg-neutral-100 focus:ring-neutral-500 dark:text-neutral-300 dark:hover:bg-neutral-800',
		danger:
			'bg-error-600 text-white hover:bg-error-700 focus:ring-error-500 dark:bg-error-500 dark:hover:bg-error-600',
	};

	// Size styles
	const sizes = {
		sm: 'px-3 py-1.5 text-sm',
		md: 'px-4 py-2 text-base',
		lg: 'px-6 py-3 text-lg',
	};

	// Compute classes
	$: classes = [
		'inline-flex items-center justify-center gap-2',
		'font-medium rounded-md',
		'transition-colors duration-200',
		'focus:outline-none focus:ring-2 focus:ring-offset-2',
		'disabled:opacity-50 disabled:cursor-not-allowed',
		variants[variant],
		sizes[size],
	].join(' ');
</script>

<button
	{type}
	disabled={disabled || loading}
	class={classes}
	aria-label={ariaLabel}
	on:click
>
	{#if loading}
		<svg
			class="animate-spin h-5 w-5"
			xmlns="http://www.w3.org/2000/svg"
			fill="none"
			viewBox="0 0 24 24"
		>
			<circle
				class="opacity-25"
				cx="12"
				cy="12"
				r="10"
				stroke="currentColor"
				stroke-width="4"
			/>
			<path
				class="opacity-75"
				fill="currentColor"
				d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
			/>
		</svg>
	{/if}
	<slot />
</button>
