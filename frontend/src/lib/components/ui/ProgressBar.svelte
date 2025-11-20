<script lang="ts">
	/**
	 * ProgressBar Component - Visual progress indicator with animations
	 * Used for stage progress, loading states, and deliberation advancement
	 */

	// Props
	interface Props {
		value?: number; // 0-100
		variant?: 'brand' | 'accent' | 'success';
		size?: 'sm' | 'md' | 'lg';
		animated?: boolean;
		indeterminate?: boolean;
		showLabel?: boolean;
		ariaLabel?: string;
	}

	let {
		value = 0,
		variant = 'brand',
		size = 'md',
		animated = true,
		indeterminate = false,
		showLabel = false,
		ariaLabel
	}: Props = $props();

	// Clamp value between 0-100
	const clampedValue = $derived(Math.min(100, Math.max(0, value)));

	// Variant styles for the filled portion
	const variants = {
		brand:
			'bg-brand-600 dark:bg-brand-500',
		accent:
			'bg-accent-600 dark:bg-accent-500',
		success:
			'bg-success-600 dark:bg-success-500',
	};

	// Size styles
	const sizes = {
		sm: 'h-1',
		md: 'h-2',
		lg: 'h-3',
	};

	// Container classes
	const containerClasses = $derived([
		'w-full bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden',
		sizes[size],
	].join(' '));

	// Bar classes
	const barClasses = $derived([
		'h-full rounded-full',
		variants[variant],
		animated ? 'transition-all duration-300 ease-smooth' : '',
		indeterminate ? 'animate-pulse' : '',
	].join(' '));
</script>

<div class="w-full">
	<div
		class={containerClasses}
		role="progressbar"
		aria-valuenow={indeterminate ? undefined : clampedValue}
		aria-valuemin={indeterminate ? undefined : 0}
		aria-valuemax={indeterminate ? undefined : 100}
		aria-label={ariaLabel}
	>
		<div
			class={barClasses}
			style="width: {indeterminate ? '100%' : `${clampedValue}%`}"
		></div>
	</div>
	{#if showLabel && !indeterminate}
		<div class="mt-1 text-xs text-neutral-600 dark:text-neutral-400 text-right">
			{Math.round(clampedValue)}%
		</div>
	{/if}
</div>
