<script lang="ts">
	import { onMount } from 'svelte';
	import { Loader2, AlertCircle, TrendingUp, TrendingDown, Gauge, Settings2, Info } from 'lucide-svelte';
	import { adminApi, type CacheMetricsResponse } from '$lib/api/admin';
	import StatCard from '$lib/components/ui/StatCard.svelte';

	let data = $state<CacheMetricsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	async function loadMetrics() {
		loading = true;
		error = null;
		try {
			data = await adminApi.getResearchCacheMetrics();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load cache metrics';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadMetrics();
	});

	function getHitRateTrend(rate1d: number, rate7d: number): 'up' | 'down' | 'stable' {
		const diff = rate1d - rate7d;
		if (diff > 5) return 'up';
		if (diff < -5) return 'down';
		return 'stable';
	}

	function getConfidenceColor(confidence: string): string {
		switch (confidence) {
			case 'high':
				return 'text-success-600 dark:text-success-400';
			case 'medium':
				return 'text-warning-600 dark:text-warning-400';
			case 'low':
				return 'text-neutral-500 dark:text-neutral-400';
			default:
				return 'text-neutral-500';
		}
	}
</script>

<div class="mb-8">
	<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Cache Hit Rate Metrics</h2>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<Loader2 class="w-6 h-6 text-neutral-400 animate-spin" />
			<span class="ml-2 text-neutral-600 dark:text-neutral-400">Loading cache metrics...</span>
		</div>
	{:else if error}
		<div
			class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4"
		>
			<div class="flex items-center gap-2 text-error-700 dark:text-error-400">
				<AlertCircle class="w-5 h-5" />
				<span>{error}</span>
			</div>
			<button
				onclick={() => loadMetrics()}
				class="mt-2 text-sm text-error-600 dark:text-error-400 hover:underline"
			>
				Retry
			</button>
		</div>
	{:else if data}
		<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
			<!-- Hit Rate Trends Card -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Gauge class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Hit Rate by Period</h3>
				</div>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<div>
							<span class="text-sm text-neutral-600 dark:text-neutral-400">Last 24 hours</span>
							<div class="flex items-center gap-2">
								<span class="text-2xl font-semibold text-neutral-900 dark:text-white"
									>{data.hit_rate_1d.toFixed(1)}%</span
								>
								{#if getHitRateTrend(data.hit_rate_1d, data.hit_rate_7d) === 'up'}
									<TrendingUp class="w-4 h-4 text-success-500" />
								{:else if getHitRateTrend(data.hit_rate_1d, data.hit_rate_7d) === 'down'}
									<TrendingDown class="w-4 h-4 text-error-500" />
								{/if}
							</div>
						</div>
						<span class="text-sm text-neutral-500"
							>{data.cache_hits_1d}/{data.total_queries_1d} queries</span
						>
					</div>
					<div class="flex items-center justify-between">
						<div>
							<span class="text-sm text-neutral-600 dark:text-neutral-400">Last 7 days</span>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">
								{data.hit_rate_7d.toFixed(1)}%
							</p>
						</div>
						<span class="text-sm text-neutral-500"
							>{data.cache_hits_7d}/{data.total_queries_7d} queries</span
						>
					</div>
					<div class="flex items-center justify-between pt-2 border-t border-neutral-200 dark:border-neutral-700">
						<div>
							<span class="text-sm text-neutral-600 dark:text-neutral-400">Last 30 days</span>
							<p class="text-xl font-semibold text-neutral-900 dark:text-white">
								{data.hit_rate_30d.toFixed(1)}%
							</p>
						</div>
						<span class="text-sm text-neutral-500"
							>{data.cache_hits_30d}/{data.total_queries_30d} queries</span
						>
					</div>
				</div>
			</div>

			<!-- Threshold Recommendation Card -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-accent-100 dark:bg-accent-900/30 rounded-lg">
						<Settings2 class="w-6 h-6 text-accent-600 dark:text-accent-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Threshold Recommendation
					</h3>
				</div>
				<div class="space-y-4">
					<div class="flex items-center justify-between">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Current Threshold</span>
						<span class="text-lg font-mono font-semibold text-neutral-900 dark:text-white"
							>{data.current_threshold.toFixed(2)}</span
						>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Recommended</span>
						<span
							class="text-lg font-mono font-semibold {data.recommended_threshold !== data.current_threshold
								? 'text-warning-600 dark:text-warning-400'
								: 'text-success-600 dark:text-success-400'}"
						>
							{data.recommended_threshold.toFixed(2)}
						</span>
					</div>
					<div class="flex items-center justify-between">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Avg Similarity on Hit</span
						>
						<span class="text-sm font-mono text-neutral-700 dark:text-neutral-300"
							>{data.avg_similarity_on_hit.toFixed(3)}</span
						>
					</div>
					<div
						class="mt-4 p-3 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg flex items-start gap-2"
					>
						<Info class="w-4 h-4 text-neutral-500 mt-0.5 flex-shrink-0" />
						<div>
							<span class={`text-xs font-medium ${getConfidenceColor(data.recommendation_confidence)}`}>
								{data.recommendation_confidence.toUpperCase()} confidence
							</span>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">
								{data.recommendation_reason}
							</p>
						</div>
					</div>
				</div>
			</div>
		</div>

		<!-- Miss Distribution Chart (if has data) -->
		{#if data.miss_distribution && data.miss_distribution.length > 0}
			<div
				class="mt-6 bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<h3 class="text-md font-semibold text-neutral-900 dark:text-white mb-4">
					Near-Miss Similarity Distribution (0.70 - 0.85)
				</h3>
				<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
					Shows queries that almost matched but fell below the similarity threshold. High counts in
					upper buckets suggest lowering the threshold.
				</p>
				<div class="flex items-end gap-2 h-32">
					{#each data.miss_distribution as bucket, i (bucket.bucket)}
						{@const maxCount = Math.max(...data.miss_distribution.map((b) => b.count), 1)}
						{@const height = (bucket.count / maxCount) * 100}
						<div
							class="flex-1 flex flex-col items-center gap-1"
							title={`${bucket.range_start.toFixed(2)} - ${bucket.range_end.toFixed(2)}: ${bucket.count} queries`}
						>
							<span class="text-xs text-neutral-500">{bucket.count}</span>
							<div class="w-full flex flex-col items-center h-20">
								<div
									class="w-full max-w-12 bg-brand-500 dark:bg-brand-400 rounded-t"
									style="height: {height}%"
								></div>
							</div>
							<span class="text-xs text-neutral-500 truncate max-w-full">
								{bucket.range_start.toFixed(2)}
							</span>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Summary Stats -->
		<div class="mt-6 grid grid-cols-1 md:grid-cols-3 gap-4">
			<StatCard size="sm" label="Cached Results" value={data.total_cached_results.toLocaleString()} />
			<StatCard size="sm" label="Cost Savings (30d)" value={'$' + data.cost_savings_30d.toFixed(2)} />
			<StatCard size="sm" label="Total Queries (30d)" value={data.total_queries_30d.toLocaleString()} />
		</div>
	{:else}
		<p class="text-neutral-500 dark:text-neutral-400 text-center py-8">No cache data available</p>
	{/if}
</div>
