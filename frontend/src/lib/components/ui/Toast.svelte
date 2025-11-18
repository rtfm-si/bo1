<script lang="ts">
	/**
	 * Toast Component - Temporary notification message
	 * Used for session events, errors, confirmations
	 */

	import { onMount } from 'svelte';
	import { createEventDispatcher } from 'svelte';

	// Props
	export let type: 'success' | 'error' | 'warning' | 'info' = 'info';
	export let message: string;
	export let duration = 5000; // ms (0 = no auto-dismiss)
	export let dismissable = true;

	const dispatch = createEventDispatcher();

	// State
	let visible = false;
	let timeoutId: ReturnType<typeof setTimeout> | null = null;

	// Type styles
	const typeStyles = {
		success: {
			bg: 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800',
			text: 'text-success-800 dark:text-success-200',
			icon: '✓',
		},
		error: {
			bg: 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800',
			text: 'text-error-800 dark:text-error-200',
			icon: '✕',
		},
		warning: {
			bg: 'bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800',
			text: 'text-warning-800 dark:text-warning-200',
			icon: '⚠',
		},
		info: {
			bg: 'bg-info-50 dark:bg-info-900/20 border-info-200 dark:border-info-800',
			text: 'text-info-800 dark:text-info-200',
			icon: 'ℹ',
		},
	};

	// Dismiss handler
	function dismiss() {
		visible = false;
		if (timeoutId) clearTimeout(timeoutId);
		setTimeout(() => {
			dispatch('dismiss');
		}, 300); // Wait for exit animation
	}

	// Auto-dismiss
	onMount(() => {
		visible = true;
		if (duration > 0) {
			timeoutId = setTimeout(dismiss, duration);
		}

		return () => {
			if (timeoutId) clearTimeout(timeoutId);
		};
	});

	$: style = typeStyles[type];
	$: containerClasses = [
		'flex items-start gap-3 p-4 rounded-lg border shadow-lg',
		'transform transition-all duration-300 ease-smooth',
		visible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0',
		style.bg,
	].join(' ');
</script>

<div class={containerClasses} role="alert">
	<!-- Icon -->
	<div class={['text-xl', style.text].join(' ')}>
		{style.icon}
	</div>

	<!-- Message -->
	<div class={['flex-1 text-sm font-medium', style.text].join(' ')}>
		{message}
	</div>

	<!-- Dismiss button -->
	{#if dismissable}
		<button
			type="button"
			class={['text-lg leading-none hover:opacity-70 transition-opacity', style.text].join(' ')}
			on:click={dismiss}
			aria-label="Dismiss"
		>
			×
		</button>
	{/if}
</div>
