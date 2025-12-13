<script lang="ts">
	/**
	 * UsageMeter Component - Display usage progress for tier limits
	 * Shows current usage, limit, and visual progress bar
	 */
	import type { UsageMetric } from '$lib/api/types';

	interface Props {
		metric: UsageMetric;
		label?: string;
		showReset?: boolean;
		compact?: boolean;
	}

	let { metric, label, showReset = true, compact = false }: Props = $props();

	// Calculate percentage (handle unlimited -1)
	const isUnlimited = $derived(metric.limit === -1);
	const percentage = $derived(
		isUnlimited ? 0 : Math.min(100, (metric.current / metric.limit) * 100)
	);

	// Determine color based on usage level
	const colorClass = $derived.by(() => {
		if (isUnlimited) return 'bg-brand-500';
		if (percentage >= 90) return 'bg-error-500';
		if (percentage >= 75) return 'bg-warning-500';
		return 'bg-brand-500';
	});

	// Format reset time
	const resetText = $derived.by(() => {
		if (!metric.reset_at) return null;
		const reset = new Date(metric.reset_at);
		const now = new Date();
		const diff = reset.getTime() - now.getTime();
		if (diff < 0) return 'soon';
		const hours = Math.floor(diff / (1000 * 60 * 60));
		const days = Math.floor(hours / 24);
		if (days > 0) return `${days}d`;
		return `${hours}h`;
	});

	// Metric display name mapping
	const metricLabels: Record<string, string> = {
		meetings_created: 'Meetings',
		datasets_uploaded: 'Datasets',
		mentor_chats: 'Mentor Chats',
		api_calls: 'API Calls'
	};

	const displayLabel = $derived(label || metricLabels[metric.metric] || metric.metric);
</script>

{#if compact}
	<!-- Compact inline display -->
	<div class="flex items-center gap-2 text-sm">
		<span class="text-neutral-600 dark:text-neutral-400">{displayLabel}:</span>
		{#if isUnlimited}
			<span class="text-brand-600 dark:text-brand-400 font-medium">{metric.current}</span>
			<span class="text-neutral-500 dark:text-neutral-500">/ unlimited</span>
		{:else}
			<span
				class="font-medium"
				class:text-error-600={percentage >= 90}
				class:dark:text-error-400={percentage >= 90}
				class:text-warning-600={percentage >= 75 && percentage < 90}
				class:dark:text-warning-400={percentage >= 75 && percentage < 90}
				class:text-neutral-700={percentage < 75}
				class:dark:text-neutral-200={percentage < 75}
			>
				{metric.current} / {metric.limit}
			</span>
			{#if showReset && resetText}
				<span class="text-neutral-500 dark:text-neutral-500 text-xs">
					resets in {resetText}
				</span>
			{/if}
		{/if}
	</div>
{:else}
	<!-- Full display with progress bar -->
	<div class="space-y-1">
		<div class="flex items-center justify-between text-sm">
			<span class="text-neutral-700 dark:text-neutral-300 font-medium">{displayLabel}</span>
			<span class="text-neutral-600 dark:text-neutral-400">
				{#if isUnlimited}
					{metric.current} used
				{:else}
					{metric.current} / {metric.limit}
				{/if}
			</span>
		</div>

		<!-- Progress bar -->
		<div class="h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
			{#if isUnlimited}
				<!-- Striped pattern for unlimited -->
				<div
					class="h-full bg-brand-500/30 rounded-full"
					style="width: 100%; background-image: repeating-linear-gradient(45deg, transparent, transparent 4px, rgba(var(--color-brand-500) / 0.3) 4px, rgba(var(--color-brand-500) / 0.3) 8px);"
				></div>
			{:else}
				<div
					class="h-full rounded-full transition-all duration-300 {colorClass}"
					style="width: {percentage}%"
				></div>
			{/if}
		</div>

		<!-- Footer with remaining and reset -->
		<div class="flex items-center justify-between text-xs text-neutral-500 dark:text-neutral-500">
			{#if isUnlimited}
				<span>Unlimited</span>
			{:else}
				<span>{metric.remaining} remaining</span>
			{/if}
			{#if showReset && resetText}
				<span>Resets in {resetText}</span>
			{/if}
		</div>
	</div>
{/if}
