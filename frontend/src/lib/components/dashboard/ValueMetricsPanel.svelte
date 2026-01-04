<script lang="ts">
	/**
	 * Key Metrics Widget - Dashboard summary of user's prioritized metrics
	 *
	 * Features:
	 * - Shows "Focus Now" metrics prominently with trend indicators
	 * - Compact card design with visual hierarchy
	 * - Industry benchmark comparison when available
	 * - Clear empty state with CTA to configure metrics
	 * - Loading skeleton for smooth experience
	 */
	import { apiClient } from '$lib/api/client';
	import type { KeyMetricDisplay, MetricHistoryPoint } from '$lib/api/types';
	import { useDataFetch } from '$lib/utils/useDataFetch.svelte';
	import { onMount } from 'svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { formatCurrency, isMonetaryMetric, type CurrencyCode } from '$lib/utils/currency';

	// Generate sparkline SVG path from history data (Stephen Few style - minimal, data-dense)
	function generateSparklinePath(history: MetricHistoryPoint[] | undefined, width: number, height: number): { path: string; hasData: boolean; trend: 'up' | 'down' | 'stable' } {
		if (!history || history.length < 2) {
			return { path: '', hasData: false, trend: 'stable' };
		}

		// Filter to only points with numeric values
		const validPoints = history.filter((p) => p.value !== null) as { value: number; recorded_at: string }[];
		if (validPoints.length < 2) {
			return { path: '', hasData: false, trend: 'stable' };
		}

		const values = validPoints.map((p) => p.value);
		const minVal = Math.min(...values);
		const maxVal = Math.max(...values);
		const range = maxVal - minVal || 1;

		// Scale points to SVG coordinates (with padding)
		const padding = 2;
		const points = validPoints.map((p, i) => ({
			x: padding + (i / (validPoints.length - 1)) * (width - 2 * padding),
			y: height - padding - ((p.value - minVal) / range) * (height - 2 * padding)
		}));

		// Build SVG path
		const path = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');

		// Determine trend from first vs last value
		const firstVal = values[0];
		const lastVal = values[values.length - 1];
		const trend = lastVal > firstVal * 1.05 ? 'up' : lastVal < firstVal * 0.95 ? 'down' : 'stable';

		return { path, hasData: true, trend };
	}

	// Get sparkline color based on trend
	function getSparklineColor(trend: 'up' | 'down' | 'stable'): string {
		switch (trend) {
			case 'up':
				return 'text-success-500 dark:text-success-400';
			case 'down':
				return 'text-error-500 dark:text-error-400';
			default:
				return 'text-neutral-400 dark:text-neutral-500';
		}
	}

	// Fetch key metrics from context API
	const metricsData = useDataFetch(() => apiClient.getKeyMetrics());

	// Expose fetch method for parent component to trigger refresh
	export function refresh() {
		metricsData.fetch();
	}

	// Derived state
	const metrics = $derived<KeyMetricDisplay[]>(metricsData.data?.metrics ?? []);
	const isLoading = $derived(metricsData.isLoading);
	const hasMetrics = $derived(metrics.length > 0);

	// Filter to show "now" (Focus Now) metrics prominently, with a few "later" as secondary
	const focusMetrics = $derived(metrics.filter((m) => m.importance === 'now').slice(0, 4));
	const secondaryMetrics = $derived(metrics.filter((m) => m.importance === 'later').slice(0, 2));
	const hasAnyMetrics = $derived(focusMetrics.length > 0 || secondaryMetrics.length > 0);

	// Format display value with appropriate scaling (currency-aware)
	function formatValue(value: string | number | null, metricName?: string): string {
		if (value === null || value === undefined) return '—';

		// Check if this is a monetary metric
		const isMoney = metricName && isMonetaryMetric(metricName);

		if (typeof value === 'number') {
			if (isMoney) {
				return formatCurrency(value, $preferredCurrency as CurrencyCode, {
					abbreviated: Math.abs(value) >= 1_000,
					decimals: Math.abs(value) >= 1_000 ? 1 : 0
				});
			}
			if (Math.abs(value) >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
			if (Math.abs(value) >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
			return value.toLocaleString();
		}
		return String(value);
	}

	// Get icon for trend direction
	function getTrendIcon(trend: string): string {
		switch (trend) {
			case 'up':
				return 'M5 10l7-7m0 0l7 7m-7-7v18';
			case 'down':
				return 'M19 14l-7 7m0 0l-7-7m7 7V3';
			case 'stable':
				return 'M4 12h16';
			default:
				return 'M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01';
		}
	}

	// Get color classes for trend
	function getTrendClasses(trend: string): { bg: string; text: string; icon: string } {
		switch (trend) {
			case 'up':
				return {
					bg: 'bg-success-100 dark:bg-success-900/30',
					text: 'text-success-700 dark:text-success-400',
					icon: 'text-success-600 dark:text-success-400'
				};
			case 'down':
				return {
					bg: 'bg-error-100 dark:bg-error-900/30',
					text: 'text-error-700 dark:text-error-400',
					icon: 'text-error-600 dark:text-error-400'
				};
			case 'stable':
				return {
					bg: 'bg-info-100 dark:bg-info-900/30',
					text: 'text-info-700 dark:text-info-400',
					icon: 'text-info-600 dark:text-info-400'
				};
			default:
				return {
					bg: 'bg-neutral-100 dark:bg-neutral-700',
					text: 'text-neutral-600 dark:text-neutral-400',
					icon: 'text-neutral-500 dark:text-neutral-400'
				};
		}
	}

	// Get icon for metric category
	function getCategoryIcon(category: string): string {
		switch (category) {
			case 'user':
				return 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z';
			case 'competitor':
				return 'M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z';
			case 'industry':
				return 'M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4';
			default:
				return 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z';
		}
	}

	onMount(() => {
		metricsData.fetch();
	});
</script>

<BoCard class="overflow-hidden">
	<!-- Header -->
	<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between">
		<div class="flex items-center gap-2">
			<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
			</svg>
			<h2 class="text-base font-semibold text-neutral-900 dark:text-white">Key Metrics</h2>
			{#if focusMetrics.length > 0}
				<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded-full bg-error-100 dark:bg-error-900/30 text-error-700 dark:text-error-400">
					{focusMetrics.length} focus
				</span>
			{/if}
		</div>
		<a
			href="/context/metrics"
			class="text-xs text-neutral-500 dark:text-neutral-400 hover:text-brand-600 dark:hover:text-brand-400 transition-colors flex items-center gap-1"
		>
			View all
			<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
			</svg>
		</a>
	</div>

	{#if isLoading}
		<!-- Loading skeleton -->
		<div class="p-4">
			<div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
				{#each [1, 2, 3, 4] as idx (idx)}
					<div class="animate-pulse space-y-2">
						<div class="flex items-center gap-1.5">
							<div class="w-4 h-4 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
							<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-16"></div>
						</div>
						<div class="h-7 bg-neutral-200 dark:bg-neutral-700 rounded w-20"></div>
						<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-14"></div>
					</div>
				{/each}
			</div>
		</div>
	{:else if !hasAnyMetrics}
		<!-- Empty state -->
		<div class="p-6 text-center">
			<div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-neutral-100 dark:bg-neutral-700 mb-3">
				<svg class="w-6 h-6 text-neutral-400 dark:text-neutral-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
			</div>
			<h3 class="text-sm font-medium text-neutral-900 dark:text-white mb-1">
				Track what matters
			</h3>
			<p class="text-xs text-neutral-500 dark:text-neutral-400 mb-4 max-w-xs mx-auto">
				Configure your key metrics to see trends, industry comparisons, and focus areas at a glance.
			</p>
			<a
				href="/context/metrics"
				class="inline-flex items-center px-3 py-1.5 text-sm font-medium text-white bg-brand-600 rounded-lg hover:bg-brand-700 transition-colors"
			>
				<svg class="w-4 h-4 mr-1.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
				</svg>
				Configure Metrics
			</a>
		</div>
	{:else}
		<!-- Metrics grid -->
		<div class="p-4">
			<!-- Focus Now metrics (prominent) -->
			{#if focusMetrics.length > 0}
				<div class="grid grid-cols-2 sm:grid-cols-4 gap-4">
					{#each focusMetrics as metric (metric.metric_key)}
						{@const colors = getTrendClasses(metric.trend)}
						{@const sparkline = generateSparklinePath(metric.history, 48, 20)}
						<div class="group relative flex flex-col p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
							<!-- Category icon + name -->
							<div class="flex items-center gap-1.5 mb-2">
								<svg class="w-3.5 h-3.5 text-neutral-400 dark:text-neutral-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getCategoryIcon(metric.category)} />
								</svg>
								<span class="text-xs font-medium text-neutral-500 dark:text-neutral-400 truncate" title={metric.name}>
									{metric.name}
								</span>
							</div>

							<!-- Value + Sparkline row -->
							<div class="flex items-center gap-2 mb-1">
								<div class="flex items-baseline gap-1">
									<span class="text-xl font-bold text-neutral-900 dark:text-white">
										{formatValue(metric.value, metric.name)}
									</span>
									{#if metric.unit}
										<span class="text-xs text-neutral-500 dark:text-neutral-400">{metric.unit}</span>
									{/if}
								</div>
								<!-- Sparkline (Stephen Few style) -->
								{#if sparkline.hasData}
									<svg viewBox="0 0 48 20" class="w-12 h-5 flex-shrink-0 {getSparklineColor(sparkline.trend)}">
										<path
											d={sparkline.path}
											fill="none"
											stroke="currentColor"
											stroke-width="1.5"
											stroke-linecap="round"
											stroke-linejoin="round"
										/>
									</svg>
								{/if}
							</div>

							<!-- Trend indicator -->
							<div class="flex items-center gap-2 mt-auto">
								{#if metric.trend_change}
									<span class="inline-flex items-center px-1.5 py-0.5 text-xs font-medium rounded {colors.bg} {colors.text}">
										<svg class="w-3 h-3 mr-0.5 {colors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getTrendIcon(metric.trend)} />
										</svg>
										{metric.trend_change}
									</span>
								{:else if metric.trend !== 'unknown'}
									<span class="inline-flex items-center gap-0.5 text-xs {colors.text}">
										<svg class="w-3 h-3 {colors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
											<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getTrendIcon(metric.trend)} />
										</svg>
										{metric.trend === 'up' ? 'Up' : metric.trend === 'down' ? 'Down' : 'Stable'}
									</span>
								{/if}
							</div>

							<!-- Industry benchmark (shown on hover or always if available) -->
							{#if metric.benchmark_value}
								<div class="mt-2 pt-2 border-t border-neutral-200 dark:border-neutral-700">
									<div class="flex items-center justify-between text-xs">
										<span class="text-neutral-500 dark:text-neutral-400">Industry</span>
										<span class="font-medium text-neutral-600 dark:text-neutral-300">{formatValue(metric.benchmark_value, metric.name)}</span>
									</div>
									{#if metric.percentile}
										<div class="mt-1.5 h-1.5 bg-neutral-200 dark:bg-neutral-600 rounded-full overflow-hidden">
											<div
												class="h-full bg-brand-500 rounded-full transition-all duration-300"
												style="width: {metric.percentile}%"
											></div>
										</div>
										<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
											{metric.percentile}th percentile
										</p>
									{/if}
								</div>
							{/if}
						</div>
					{/each}
				</div>
			{/if}

			<!-- Secondary metrics (compact row) -->
			{#if secondaryMetrics.length > 0}
				<div class="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700">
					<p class="text-xs text-neutral-400 dark:text-neutral-500 mb-2">Track Later</p>
					<div class="flex flex-wrap gap-3">
						{#each secondaryMetrics as metric (metric.metric_key)}
							{@const colors = getTrendClasses(metric.trend)}
							{@const sparkline = generateSparklinePath(metric.history, 32, 14)}
							<div class="flex items-center gap-2 px-2.5 py-1.5 rounded-md bg-neutral-50 dark:bg-neutral-800/50">
								<span class="text-xs text-neutral-500 dark:text-neutral-400">{metric.name}:</span>
								<span class="text-sm font-medium text-neutral-900 dark:text-white">{formatValue(metric.value, metric.name)}</span>
								{#if sparkline.hasData}
									<svg viewBox="0 0 32 14" class="w-8 h-3.5 {getSparklineColor(sparkline.trend)}">
										<path d={sparkline.path} fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" />
									</svg>
								{:else if metric.trend !== 'unknown'}
									<svg class="w-3 h-3 {colors.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getTrendIcon(metric.trend)} />
									</svg>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	{/if}
</BoCard>
