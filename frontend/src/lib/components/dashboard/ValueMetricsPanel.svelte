<script lang="ts">
	import { apiClient } from '$lib/api/client';
	import type { ValueMetricsResponse, ValueMetric } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { onMount } from 'svelte';
	import { formatCompactRelativeTime } from '$lib/utils/time-formatting';

	// Fetch value metrics
	const metricsData = useDataFetch(() => apiClient.getValueMetrics());

	// Expose fetch method for parent component to trigger refresh
	export function refresh() {
		metricsData.fetch();
	}

	// Derived state
	const metrics = $derived<ValueMetric[]>((metricsData.data?.metrics ?? []) as ValueMetric[]);
	const hasContext = $derived(metricsData.data?.has_context ?? false);
	const hasHistory = $derived(metricsData.data?.has_history ?? false);
	const isLoading = $derived(metricsData.isLoading);
	const hasMetrics = $derived(metrics.length > 0);

	// Format display value
	function formatValue(value: string | number | null): string {
		if (value === null || value === undefined) return '—';
		return String(value);
	}

	// Format change percent
	function formatChange(changePercent: number | null): string {
		if (changePercent === null || changePercent === undefined) return '';
		const sign = changePercent >= 0 ? '+' : '';
		return `${sign}${changePercent.toFixed(1)}%`;
	}

	// Get trend icon path
	function getTrendIcon(direction: string): string {
		switch (direction) {
			case 'improving':
				return 'M5 10l7-7m0 0l7 7m-7-7v18'; // Up arrow
			case 'worsening':
				return 'M19 14l-7 7m0 0l-7-7m7 7V3'; // Down arrow
			case 'stable':
				return 'M4 12h16'; // Horizontal line
			default:
				return 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01'; // Question mark
		}
	}

	// Get trend color classes based on is_positive_change
	function getTrendClasses(metric: ValueMetric): { bg: string; text: string; icon: string } {
		// If insufficient data or null, use neutral
		if (metric.trend_direction === 'insufficient_data' || metric.is_positive_change === null) {
			return {
				bg: 'bg-neutral-100 dark:bg-neutral-700',
				text: 'text-neutral-600 dark:text-neutral-400',
				icon: 'text-neutral-500 dark:text-neutral-400'
			};
		}

		// Stable trends
		if (metric.trend_direction === 'stable') {
			return {
				bg: 'bg-neutral-100 dark:bg-neutral-700',
				text: 'text-neutral-600 dark:text-neutral-400',
				icon: 'text-neutral-500 dark:text-neutral-400'
			};
		}

		// Good change (green)
		if (metric.is_positive_change) {
			return {
				bg: 'bg-success-100 dark:bg-success-900/30',
				text: 'text-success-700 dark:text-success-400',
				icon: 'text-success-600 dark:text-success-400'
			};
		}

		// Bad change (red)
		return {
			bg: 'bg-error-100 dark:bg-error-900/30',
			text: 'text-error-700 dark:text-error-400',
			icon: 'text-error-600 dark:text-error-400'
		};
	}

	onMount(() => {
		metricsData.fetch();
	});
</script>

<!-- Only show panel if user has context -->
{#if hasContext || isLoading}
	<div class="bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg">
		<div class="p-4 border-b border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
					</svg>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Key Metrics</h2>
				</div>
				<a
					href="/context/overview"
					class="text-xs text-neutral-500 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors"
				>
					Edit context
				</a>
			</div>
		</div>

		{#if isLoading}
			<!-- Loading skeleton -->
			<div class="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
				{#each [1, 2, 3, 4, 5] as idx (idx)}
					<div class="animate-pulse">
						<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-16 mb-2"></div>
						<div class="h-6 bg-neutral-200 dark:bg-neutral-700 rounded w-20 mb-1"></div>
						<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-12"></div>
					</div>
				{/each}
			</div>
		{:else if !hasMetrics}
			<!-- Empty state - prompt to set up context -->
			<div class="p-6 text-center">
				<svg class="w-12 h-12 mx-auto mb-3 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
				<p class="text-sm text-neutral-500 dark:text-neutral-400 mb-3">
					Add your business metrics to track improvements over time.
				</p>
				<a
					href="/context/overview"
					class="inline-flex items-center px-3 py-1.5 text-sm font-medium text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20 rounded-lg hover:bg-brand-100 dark:hover:bg-brand-900/30 transition-colors"
				>
					<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					Set up business context
				</a>
			</div>
		{:else}
			<!-- Metrics grid -->
			<div class="p-4 grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
				{#each metrics as metric (metric.name)}
					{@const colors = getTrendClasses(metric)}
					<div class="flex flex-col">
						<!-- Label -->
						<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1 truncate" title={metric.label}>
							{metric.label}
						</span>

						<!-- Value -->
						<span class="text-lg font-semibold text-neutral-900 dark:text-white truncate" title={formatValue(metric.current_value)}>
							{formatValue(metric.current_value)}
						</span>

						<!-- Trend indicator -->
						{#if metric.change_percent !== null && metric.trend_direction !== 'insufficient_data'}
							<div class="flex items-center gap-1 mt-1">
								<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded {colors.bg} {colors.text}">
									<svg class="w-3 h-3 mr-0.5 {colors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getTrendIcon(metric.trend_direction)} />
									</svg>
									{formatChange(metric.change_percent)}
								</span>
							</div>
						{:else if metric.trend_direction === 'insufficient_data'}
							<span class="text-xs text-neutral-400 dark:text-neutral-500 mt-1">
								No trend data
							</span>
						{:else}
							<span class="inline-flex items-center gap-1 text-xs text-neutral-400 dark:text-neutral-500 mt-1">
								<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 12h16" />
								</svg>
								Stable
							</span>
						{/if}

						<!-- Last updated -->
						{#if metric.last_updated}
							<span class="text-xs text-neutral-400 dark:text-neutral-500 mt-0.5" title="Last updated">
								{formatCompactRelativeTime(metric.last_updated)}
							</span>
						{/if}
					</div>
				{/each}
			</div>

			{#if !hasHistory}
				<div class="px-4 pb-4">
					<p class="text-xs text-neutral-400 dark:text-neutral-500 text-center">
						Trend data will appear as your metrics are updated over time.
					</p>
				</div>
			{/if}
		{/if}
	</div>
{/if}
