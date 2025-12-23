<script lang="ts">
	import { CheckCircle, Loader, XCircle, Clock } from 'lucide-svelte';

	type SubProblemStatus = 'complete' | 'in_progress' | 'failed' | 'pending';

	interface Props {
		status: SubProblemStatus;
		showLabel?: boolean;
	}

	let { status, showLabel = true }: Props = $props();

	const statusConfig = {
		complete: {
			label: 'Complete',
			icon: CheckCircle,
			bgClass: 'bg-success-100 dark:bg-success-900/40',
			textClass: 'text-success-700 dark:text-success-400',
			iconClass: 'text-success-600 dark:text-success-400',
		},
		in_progress: {
			label: 'In Progress',
			icon: Loader,
			bgClass: 'bg-warning-100 dark:bg-warning-900/40',
			textClass: 'text-warning-700 dark:text-warning-400',
			iconClass: 'text-warning-600 dark:text-warning-400 animate-spin',
		},
		failed: {
			label: 'Failed',
			icon: XCircle,
			bgClass: 'bg-error-100 dark:bg-error-900/40',
			textClass: 'text-error-700 dark:text-error-400',
			iconClass: 'text-error-600 dark:text-error-400',
		},
		pending: {
			label: 'Pending',
			icon: Clock,
			bgClass: 'bg-slate-100 dark:bg-slate-700',
			textClass: 'text-slate-600 dark:text-slate-400',
			iconClass: 'text-slate-500 dark:text-slate-400',
		},
	} as const;

	const config = $derived(statusConfig[status]);
	const Icon = $derived(statusConfig[status].icon);
</script>

<span
	class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium {config.bgClass} {config.textClass}"
	role="status"
	aria-label="Focus area status: {config.label}"
>
	<Icon size={14} class={config.iconClass} aria-hidden="true" />
	{#if showLabel}
		<span>{config.label}</span>
	{/if}
</span>
