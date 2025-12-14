<script lang="ts">
	/**
	 * Spinner Component - Loading indicator with smooth rotation
	 * Used for loading states, typing indicators, and async operations
	 */

	// Props
	interface Props {
		size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
		variant?: 'brand' | 'accent' | 'neutral';
		ariaLabel?: string;
		class?: string;
	}

	let {
		size = 'md',
		variant = 'brand',
		ariaLabel = 'Loading',
		class: className = ''
	}: Props = $props();

	// Variant styles
	const variants = {
		brand: 'text-brand-600 dark:text-brand-400',
		accent: 'text-accent-600 dark:text-accent-400',
		neutral: 'text-neutral-500 dark:text-neutral-400',
	};

	// Size styles (width and height)
	const sizes = {
		xs: 'w-3 h-3',
		sm: 'w-4 h-4',
		md: 'w-6 h-6',
		lg: 'w-8 h-8',
		xl: 'w-12 h-12',
	};

	// Compute classes
	const classes = $derived([
		'animate-spin',
		variants[variant],
		sizes[size],
		className
	].filter(Boolean).join(' '));
</script>

<svg
	class={classes}
	xmlns="http://www.w3.org/2000/svg"
	fill="none"
	viewBox="0 0 24 24"
	aria-label={ariaLabel}
	role="status"
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
