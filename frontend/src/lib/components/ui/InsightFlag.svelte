<script lang="ts">
	/**
	 * InsightFlag Component - Live insight indicator during deliberation
	 * Used for risk/opportunity/tension/alignment notifications
	 */
	import { AlertCircle, CheckCircle, Target, X } from 'lucide-svelte';
	import type { ComponentType } from 'svelte';

	// Props
	interface Props {
		type: 'risk' | 'opportunity' | 'tension' | 'alignment';
		message: string;
		dismissable?: boolean;
		pulse?: boolean;
		ondismiss?: () => void;
	}

	let {
		type,
		message,
		dismissable = true,
		pulse = false,
		ondismiss
	}: Props = $props();

	// Type configurations
	const typeConfig: Record<string, { icon: ComponentType; bg: string; border: string; text: string; accent: string }> = {
		risk: {
			icon: AlertCircle,
			bg: 'bg-error-50 dark:bg-error-900/20',
			border: 'border-error-300 dark:border-error-700',
			text: 'text-error-800 dark:text-error-200',
			accent: 'bg-error-500',
		},
		opportunity: {
			icon: CheckCircle,
			bg: 'bg-success-50 dark:bg-success-900/20',
			border: 'border-success-300 dark:border-success-700',
			text: 'text-success-800 dark:text-success-200',
			accent: 'bg-success-500',
		},
		tension: {
			icon: AlertCircle,
			bg: 'bg-warning-50 dark:bg-warning-900/20',
			border: 'border-warning-300 dark:border-warning-700',
			text: 'text-warning-800 dark:text-warning-200',
			accent: 'bg-warning-500',
		},
		alignment: {
			icon: Target,
			bg: 'bg-brand-50 dark:bg-brand-900/20',
			border: 'border-brand-300 dark:border-brand-700',
			text: 'text-brand-800 dark:text-brand-200',
			accent: 'bg-brand-500',
		},
	};

	function dismiss() {
		ondismiss?.();
	}

	const config = $derived(typeConfig[type]);
	const containerClasses = $derived([
		'flex items-start gap-3 p-3 rounded-lg border-l-4 shadow-md',
		'transform transition-all duration-400 ease-smooth',
		'animate-slideInFromLeft',
		pulse ? 'animate-pulse' : '',
		config.bg,
		config.border,
	].join(' '));
</script>

<div class={containerClasses} role="status" aria-live="polite">
	<!-- Accent bar indicator -->
	<div class={['w-1 h-full rounded-full', config.accent].join(' ')}></div>

	<!-- Icon -->
	<div class={config.text}>
		{#if type === 'risk' || type === 'tension'}
			<AlertCircle size={20} />
		{:else if type === 'opportunity'}
			<CheckCircle size={20} />
		{:else}
			<Target size={20} />
		{/if}
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
			class={['hover:opacity-70 transition-opacity', config.text].join(' ')}
			onclick={dismiss}
			aria-label="Dismiss insight"
		>
			<X size={18} />
		</button>
	{/if}
</div>
