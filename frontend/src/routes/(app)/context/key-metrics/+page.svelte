<script lang="ts">
	/**
	 * Key Metrics - "Metrics You Need to Know"
	 *
	 * Shows user's prioritized key metrics with:
	 * - Current values and trends (pendulum indicators)
	 * - 3 sections: Focus Now, Track Later, Monitor
	 * - Benchmark comparison when available
	 * - Suggestions from insights panel
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { KeyMetricsResponse, KeyMetricDisplay, MetricImportance } from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';
	import Spinner from '$lib/components/ui/Spinner.svelte';
	import MetricSuggestions from '$lib/components/context/MetricSuggestions.svelte';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { formatCurrency, isMonetaryMetric, type CurrencyCode } from '$lib/utils/currency';

	// State
	let metricsResponse = $state<KeyMetricsResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let suggestionsKey = $state(0);

	onMount(async () => {
		await loadMetrics();
	});

	function handleSuggestionApplied() {
		// Reload metrics after a suggestion is applied
		loadMetrics();
		// Force re-mount of suggestions component to refresh
		suggestionsKey++;
	}

	async function loadMetrics() {
		isLoading = true;
		error = null;

		try {
			metricsResponse = await apiClient.getKeyMetrics();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load key metrics';
			console.error('Failed to load key metrics:', e);
		} finally {
			isLoading = false;
		}
	}

	function formatValue(value: string | number | null, metricName?: string): string {
		if (value === null) return '-';

		// Check if this is a monetary metric
		const isMoney = metricName && isMonetaryMetric(metricName);

		if (typeof value === 'number') {
			if (isMoney) {
				return formatCurrency(value, $preferredCurrency as CurrencyCode, {
					abbreviated: Math.abs(value) >= 1_000,
					decimals: Math.abs(value) >= 1_000 ? 1 : 0
				});
			}
			if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
			if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
			return value.toLocaleString();
		}
		return value;
	}

	function getTrendIcon(trend: string): string {
		switch (trend) {
			case 'up':
				return '↑';
			case 'down':
				return '↓';
			case 'stable':
				return '→';
			default:
				return '•';
		}
	}

	function getTrendColor(trend: string): string {
		switch (trend) {
			case 'up':
				return 'text-green-600 dark:text-green-400';
			case 'down':
				return 'text-red-600 dark:text-red-400';
			case 'stable':
				return 'text-blue-600 dark:text-blue-400';
			default:
				return 'text-neutral-400';
		}
	}

	function getImportanceLabel(importance: MetricImportance): string {
		switch (importance) {
			case 'now':
				return 'Focus Now';
			case 'later':
				return 'Track Later';
			case 'monitor':
				return 'Monitor';
		}
	}

	function getImportanceColor(importance: MetricImportance): string {
		switch (importance) {
			case 'now':
				return 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300';
			case 'later':
				return 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-300';
			case 'monitor':
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400';
		}
	}

	function filterByImportance(
		metrics: KeyMetricDisplay[] | undefined,
		importance: MetricImportance
	): KeyMetricDisplay[] {
		if (!metrics) return [];
		return metrics.filter((m) => m.importance === importance);
	}

	// Computed
	let nowMetrics = $derived(filterByImportance(metricsResponse?.metrics, 'now'));
	let laterMetrics = $derived(filterByImportance(metricsResponse?.metrics, 'later'));
	let monitorMetrics = $derived(filterByImportance(metricsResponse?.metrics, 'monitor'));
	let hasMetrics = $derived(
		nowMetrics.length > 0 || laterMetrics.length > 0 || monitorMetrics.length > 0
	);
</script>

<svelte:head>
	<title>Key Metrics | Bo1</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
	<!-- Header -->
	<div class="flex items-center justify-between">
		<div>
			<h1 class="text-2xl font-bold text-neutral-900 dark:text-neutral-100">
				Metrics You Need to Know
			</h1>
			<p class="mt-1 text-sm text-neutral-500 dark:text-neutral-400">
				Your prioritized key metrics with trends and benchmarks
			</p>
		</div>
	</div>

	<!-- Metric Suggestions Panel (above metrics) -->
	{#key suggestionsKey}
		<MetricSuggestions onapplied={handleSuggestionApplied} />
	{/key}

	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<Spinner size="lg" />
		</div>
	{:else if error}
		<Alert variant="error">
			<p>{error}</p>
			<BoButton variant="outline" size="sm" class="mt-2" onclick={loadMetrics}>Retry</BoButton>
		</Alert>
	{:else if !hasMetrics}
		<!-- Empty state -->
		<BoCard>
			<div class="text-center py-12">
				<div class="text-4xl mb-4">📊</div>
				<h3 class="text-lg font-medium text-neutral-900 dark:text-neutral-100 mb-2">
					No metrics tracked yet
				</h3>
				<p class="text-neutral-500 dark:text-neutral-400 mb-4 max-w-md mx-auto">
					Add metrics from your Context settings to start tracking them here. You'll see trends
					and benchmark comparisons.
				</p>
				<a
					href="/context/metrics"
					class="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-brand-600 rounded-md hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2"
				>
					Set Up Metrics
				</a>
			</div>
		</BoCard>
	{:else}
		<!-- Focus Now Section -->
		{#if nowMetrics.length > 0}
			<section>
				<div class="flex items-center gap-2 mb-3">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Focus Now</h2>
					<span class="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full {getImportanceColor('now')}">{nowMetrics.length}</span>
				</div>
				<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{#each nowMetrics as metric (metric.metric_key)}
						<BoCard class="hover:shadow-md transition-shadow">
							<div class="p-4">
								<div class="flex items-start justify-between mb-2">
									<h3 class="font-medium text-neutral-900 dark:text-neutral-100">{metric.name}</h3>
									<span
										class="text-lg font-bold {getTrendColor(metric.trend)}"
										title={metric.trend_change || metric.trend}
									>
										{getTrendIcon(metric.trend)}
									</span>
								</div>
								<div class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-1">
									{formatValue(metric.value, metric.name)}
									{#if metric.unit}
										<span class="text-sm font-normal text-neutral-500">{metric.unit}</span>
									{/if}
								</div>
								{#if metric.trend_change}
									<p class="text-sm {getTrendColor(metric.trend)}">{metric.trend_change}</p>
								{/if}
								{#if metric.benchmark_value}
									<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-2">
										Industry: {formatValue(metric.benchmark_value, metric.name)}
									</p>
								{/if}
							</div>
						</BoCard>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Track Later Section -->
		{#if laterMetrics.length > 0}
			<section>
				<div class="flex items-center gap-2 mb-3">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Track Later</h2>
					<span class="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full {getImportanceColor('later')}">{laterMetrics.length}</span>
				</div>
				<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
					{#each laterMetrics as metric (metric.metric_key)}
						<BoCard class="hover:shadow-md transition-shadow opacity-90">
							<div class="p-4">
								<div class="flex items-start justify-between mb-2">
									<h3 class="font-medium text-neutral-900 dark:text-neutral-100">{metric.name}</h3>
									<span class="text-lg font-bold {getTrendColor(metric.trend)}">
										{getTrendIcon(metric.trend)}
									</span>
								</div>
								<div class="text-2xl font-bold text-neutral-900 dark:text-neutral-100 mb-1">
									{formatValue(metric.value, metric.name)}
									{#if metric.unit}
										<span class="text-sm font-normal text-neutral-500">{metric.unit}</span>
									{/if}
								</div>
								{#if metric.trend_change}
									<p class="text-sm {getTrendColor(metric.trend)}">{metric.trend_change}</p>
								{/if}
							</div>
						</BoCard>
					{/each}
				</div>
			</section>
		{/if}

		<!-- Monitor Section -->
		{#if monitorMetrics.length > 0}
			<section>
				<div class="flex items-center gap-2 mb-3">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">Monitor</h2>
					<span class="inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full {getImportanceColor('monitor')}">{monitorMetrics.length}</span>
				</div>
				<div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
					{#each monitorMetrics as metric (metric.metric_key)}
						<BoCard class="opacity-75">
							<div class="p-3">
								<div class="flex items-center justify-between mb-1">
									<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300">
										{metric.name}
									</h3>
									<span class="text-sm {getTrendColor(metric.trend)}">
										{getTrendIcon(metric.trend)}
									</span>
								</div>
								<div class="text-lg font-bold text-neutral-900 dark:text-neutral-100">
									{formatValue(metric.value, metric.name)}
									{#if metric.unit}
										<span class="text-xs font-normal text-neutral-500">{metric.unit}</span>
									{/if}
								</div>
							</div>
						</BoCard>
					{/each}
				</div>
			</section>
		{/if}
	{/if}
</div>
