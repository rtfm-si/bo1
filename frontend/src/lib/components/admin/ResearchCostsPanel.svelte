<script lang="ts">
	import { onMount } from 'svelte';
	import { Search, Loader2, AlertCircle } from 'lucide-svelte';
	import { adminApi, type ResearchCostsResponse } from '$lib/api/admin';
	import { preferredCurrency } from '$lib/stores/preferences';
	import { formatCurrency } from '$lib/utils/currency';

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
			<!-- Brave Costs -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
						<Search class="w-6 h-6 text-orange-600 dark:text-orange-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Brave Search</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Total Cost</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white"
							>{fmtCurrency(data.brave.amount_usd)}</span
						>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Queries</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
							>{data.brave.query_count.toLocaleString()}</span
						>
					</div>
					{#if data.brave.query_count > 0}
						<div class="flex justify-between items-center">
							<span class="text-sm text-neutral-600 dark:text-neutral-400">Avg/Query</span>
							<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
								>{fmtCurrency(data.brave.amount_usd / data.brave.query_count)}</span
							>
						</div>
					{/if}
				</div>
			</div>

			<!-- Tavily Costs -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-purple-100 dark:bg-purple-900/30 rounded-lg">
						<Search class="w-6 h-6 text-purple-600 dark:text-purple-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Tavily</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Total Cost</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white"
							>{fmtCurrency(data.tavily.amount_usd)}</span
						>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Queries</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
							>{data.tavily.query_count.toLocaleString()}</span
						>
					</div>
					{#if data.tavily.query_count > 0}
						<div class="flex justify-between items-center">
							<span class="text-sm text-neutral-600 dark:text-neutral-400">Avg/Query</span>
							<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
								>{fmtCurrency(data.tavily.amount_usd / data.tavily.query_count)}</span
							>
						</div>
					{/if}
				</div>
			</div>

			<!-- Period Summary -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
			>
				<div class="flex items-center gap-3 mb-4">
					<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
						<Search class="w-6 h-6 text-brand-600 dark:text-brand-400" />
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">Total Research</h3>
				</div>
				<div class="space-y-2">
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">Today</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
							>{fmtCurrency(data.by_period.today)}</span
						>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">This Week</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
							>{fmtCurrency(data.by_period.week)}</span
						>
					</div>
					<div class="flex justify-between items-center">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">This Month</span>
						<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300"
							>{fmtCurrency(data.by_period.month)}</span
						>
					</div>
					<div class="flex justify-between items-center pt-2 border-t border-neutral-200 dark:border-neutral-700">
						<span class="text-sm text-neutral-600 dark:text-neutral-400">All Time</span>
						<span class="text-lg font-semibold text-neutral-900 dark:text-white"
							>{fmtCurrency(data.total_usd)}</span
						>
					</div>
				</div>
			</div>
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
