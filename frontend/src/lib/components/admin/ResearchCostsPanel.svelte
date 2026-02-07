<script lang="ts">
	import { onMount } from 'svelte';
	import { Search, Loader2, AlertCircle } from 'lucide-svelte';
	import { adminApi, type ResearchCostsResponse } from '$lib/api/admin';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { formatCurrency } from '$lib/utils/currency';
	import { StatCard, StatCardRow } from '$lib/components/ui';

	let data = $state<ResearchCostsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Format currency using user's preferred currency
	function fmtCurrency(amount: number): string {
		return formatCurrency(amount, $preferredCurrency);
	}

	async function loadResearchCosts() {
		loading = true;
		error = null;
		try {
			data = await adminApi.getResearchCosts();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load research costs';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		loadResearchCosts();
	});

	// Calculate max for bar chart scaling
	function getMaxDailyTotal(): number {
		if (!data?.daily_trend) return 1;
		const max = Math.max(...data.daily_trend.map((d) => d.total), 0.001);
		return max;
	}
</script>

<div class="mb-8">
	<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Research Costs</h2>

	{#if loading}
		<div class="flex items-center justify-center py-8">
			<Loader2 class="w-6 h-6 text-neutral-400 animate-spin" />
			<span class="ml-2 text-neutral-600 dark:text-neutral-400">Loading research costs...</span>
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
				onclick={() => loadResearchCosts()}
				class="mt-2 text-sm text-error-600 dark:text-error-400 hover:underline"
			>
				Retry
			</button>
		</div>
	{:else if data}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
			<StatCard label="Brave Search" icon={Search} iconColorClass="text-orange-600 dark:text-orange-400" iconBgClass="bg-orange-100 dark:bg-orange-900/30">
				<StatCardRow label="Total Cost" value={fmtCurrency(data.brave.amount_usd)} prominent />
				<StatCardRow label="Queries" value={data.brave.query_count.toLocaleString()} />
				{#if data.brave.query_count > 0}
					<StatCardRow label="Avg/Query" value={fmtCurrency(data.brave.amount_usd / data.brave.query_count)} />
				{/if}
			</StatCard>

			<StatCard label="Tavily" icon={Search} iconColorClass="text-purple-600 dark:text-purple-400" iconBgClass="bg-purple-100 dark:bg-purple-900/30">
				<StatCardRow label="Total Cost" value={fmtCurrency(data.tavily.amount_usd)} prominent />
				<StatCardRow label="Queries" value={data.tavily.query_count.toLocaleString()} />
				{#if data.tavily.query_count > 0}
					<StatCardRow label="Avg/Query" value={fmtCurrency(data.tavily.amount_usd / data.tavily.query_count)} />
				{/if}
			</StatCard>

			<StatCard label="Total Research" icon={Search} iconColorClass="text-brand-600 dark:text-brand-400" iconBgClass="bg-brand-100 dark:bg-brand-900/30">
				<StatCardRow label="Today" value={fmtCurrency(data.by_period.today)} />
				<StatCardRow label="This Week" value={fmtCurrency(data.by_period.week)} />
				<StatCardRow label="This Month" value={fmtCurrency(data.by_period.month)} />
				<div class="pt-2 border-t border-neutral-200 dark:border-neutral-700">
					<StatCardRow label="All Time" value={fmtCurrency(data.total_usd)} prominent />
				</div>
			</StatCard>
		</div>

		<!-- Daily Trend Chart (7 days) -->
		{#if data.daily_trend && data.daily_trend.length > 0}
			<div
				class="mt-6 bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<h3 class="text-md font-semibold text-neutral-900 dark:text-white mb-4">
					Daily Trend (Last 7 Days)
				</h3>
				<div class="flex items-end gap-2 h-32">
					{#each data.daily_trend as day (day.date)}
						{@const maxTotal = getMaxDailyTotal()}
						{@const braveHeight = maxTotal > 0 ? (day.brave / maxTotal) * 100 : 0}
						{@const tavilyHeight = maxTotal > 0 ? (day.tavily / maxTotal) * 100 : 0}
						<div class="flex-1 flex flex-col items-center gap-1" title={`${day.date}: ${fmtCurrency(day.total)}`}>
							<div class="w-full flex flex-col items-center h-24">
								<div
									class="w-full max-w-8 bg-purple-500 dark:bg-purple-400 rounded-t"
									style="height: {tavilyHeight}%"
								></div>
								<div
									class="w-full max-w-8 bg-orange-500 dark:bg-orange-400 rounded-b"
									style="height: {braveHeight}%"
								></div>
							</div>
							<span class="text-xs text-neutral-500 dark:text-neutral-400 truncate max-w-full">
								{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short' })}
							</span>
						</div>
					{/each}
				</div>
				<div class="flex justify-center gap-6 mt-4 text-xs">
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 bg-orange-500 rounded"></div>
						<span class="text-neutral-600 dark:text-neutral-400">Brave</span>
					</div>
					<div class="flex items-center gap-2">
						<div class="w-3 h-3 bg-purple-500 rounded"></div>
						<span class="text-neutral-600 dark:text-neutral-400">Tavily</span>
					</div>
				</div>
			</div>
		{/if}

		<!-- No Data State -->
		{#if data.total_queries === 0}
			<div class="mt-6 text-center py-8 text-neutral-500 dark:text-neutral-400">
				No research queries recorded yet.
			</div>
		{/if}
	{/if}
</div>
