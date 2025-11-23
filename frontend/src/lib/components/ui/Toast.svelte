<script lang="ts">
	/**
	 * Toast Component - Temporary notification message
	 * Used for session events, errors, confirmations
	 */

	import { onMount } from 'svelte';
	import { CheckCircle, AlertCircle, Info, X } from 'lucide-svelte';
	import type { ComponentType } from 'svelte';

	// Props
	interface Props {
		type?: 'success' | 'error' | 'warning' | 'info';
		message: string;
		duration?: number; // ms (0 = no auto-dismiss)
		dismissable?: boolean;
		ondismiss?: () => void;
	}

	let {
		type = 'info',
		message,
		duration = 5000,
		dismissable = true,
		ondismiss
	}: Props = $props();

	// State
	let visible = $state(false);
	let timeoutId: ReturnType<typeof setTimeout> | null = null;

	// Type styles
	const typeStyles: Record<string, { bg: string; text: string; icon: ComponentType }> = {
		success: {
			bg: 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800',
			text: 'text-success-800 dark:text-success-200',
			icon: CheckCircle,
		},
		error: {
			bg: 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800',
			text: 'text-error-800 dark:text-error-200',
			icon: AlertCircle,
		},
		warning: {
			bg: 'bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800',
			text: 'text-warning-800 dark:text-warning-200',
			icon: AlertCircle,
		},
		info: {
			bg: 'bg-info-50 dark:bg-info-900/20 border-info-200 dark:border-info-800',
			text: 'text-info-800 dark:text-info-200',
			icon: Info,
		},
	};

	// Dismiss handler
	function dismiss() {
		visible = false;
		if (timeoutId) clearTimeout(timeoutId);
		setTimeout(() => {
			ondismiss?.();
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

	const style = $derived(typeStyles[type]);
	const containerClasses = $derived([
		'flex items-start gap-3 p-4 rounded-lg border shadow-lg',
		'transform transition-all duration-300 ease-smooth',
		visible ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0',
		style.bg,
	].join(' '));
</script>

<div class={containerClasses} role="alert">
	<!-- Icon -->
	<div class={style.text}>
		{#if type === 'success'}
			<CheckCircle size={20} />
		{:else if type === 'error' || type === 'warning'}
			<AlertCircle size={20} />
		{:else}
			<Info size={20} />
		{/if}
	</div>

	<!-- Message -->
	<div class={['flex-1 text-sm font-medium', style.text].join(' ')}>
		{message}
	</div>

	<!-- Dismiss button -->
	{#if dismissable}
		<button
			type="button"
			class={['hover:opacity-70 transition-opacity', style.text].join(' ')}
			onclick={dismiss}
			aria-label="Dismiss"
		>
			<X size={18} />
		</button>
	{/if}
</div>
