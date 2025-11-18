<script lang="ts">
	/**
	 * InsightFlag Component - Live insight indicator during deliberation
	 * Used for risk/opportunity/tension/alignment notifications
	 */

	import { createEventDispatcher } from 'svelte';

	// Props
	export let type: 'risk' | 'opportunity' | 'tension' | 'alignment';
	export let message: string;
	export let dismissable = true;
	export let pulse = false;

	const dispatch = createEventDispatcher();

	// Type configurations
	const typeConfig = {
		risk: {
			icon: '⚠',
			bg: 'bg-error-50 dark:bg-error-900/20',
			border: 'border-error-300 dark:border-error-700',
			text: 'text-error-800 dark:text-error-200',
			accent: 'bg-error-500',
		},
		opportunity: {
			icon: '✦',
			bg: 'bg-success-50 dark:bg-success-900/20',
			border: 'border-success-300 dark:border-success-700',
			text: 'text-success-800 dark:text-success-200',
			accent: 'bg-success-500',
		},
		tension: {
			icon: '⚡',
			bg: 'bg-warning-50 dark:bg-warning-900/20',
			border: 'border-warning-300 dark:border-warning-700',
			text: 'text-warning-800 dark:text-warning-200',
			accent: 'bg-warning-500',
		},
		alignment: {
			icon: '◆',
			bg: 'bg-brand-50 dark:bg-brand-900/20',
			border: 'border-brand-300 dark:border-brand-700',
			text: 'text-brand-800 dark:text-brand-200',
			accent: 'bg-brand-500',
		},
	};

	function dismiss() {
		dispatch('dismiss');
	}

	$: config = typeConfig[type];
	$: containerClasses = [
		'flex items-start gap-3 p-3 rounded-lg border-l-4 shadow-md',
		'transform transition-all duration-400 ease-smooth',
		'animate-slideInFromLeft',
		pulse ? 'animate-pulse' : '',
		config.bg,
		config.border,
	].join(' ');
</script>

<div class={containerClasses} role="status" aria-live="polite">
	<!-- Accent bar indicator -->
	<div class={['w-1 h-full rounded-full', config.accent].join(' ')}></div>

	<!-- Icon -->
	<div class={['text-2xl leading-none', config.text].join(' ')}>
		{config.icon}
	</div>

	<!-- Content -->
	<div class="flex-1">
		<div class={['text-sm font-semibold uppercase tracking-wide mb-1', config.text].join(' ')}>
			{type}
		</div>
		<div class={['text-sm', config.text].join(' ')}>
			{message}
		</div>
	</div>

	<!-- Dismiss button -->
	{#if dismissable}
		<button
			type="button"
			class={['text-lg leading-none hover:opacity-70 transition-opacity', config.text].join(' ')}
			on:click={dismiss}
			aria-label="Dismiss insight"
		>
			×
		</button>
	{/if}
</div>
