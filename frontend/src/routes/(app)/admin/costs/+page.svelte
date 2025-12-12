<script lang="ts">
	import { onMount } from 'svelte';
	import { BarChart3, Download, RefreshCw, DollarSign, Calendar, Users, TrendingUp } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import { adminApi, type CostSummaryResponse, type UserCostsResponse, type DailyCostsResponse } from '$lib/api/admin';

	// State
	let summary = $state<CostSummaryResponse | null>(null);
	let userCosts = $state<UserCostsResponse | null>(null);
	let dailyCosts = $state<DailyCostsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);

	// Chart state
	let chartCanvas = $state<HTMLCanvasElement | null>(null);
	let chartMaxValue = $state(0);

	async function loadData() {
		try {
			loading = true;
			const [summaryData, usersData, dailyData] = await Promise.all([
				adminApi.getCostSummary(),
				adminApi.getUserCosts({ limit: 10 }),
				adminApi.getDailyCosts()
			]);
			summary = summaryData;
			userCosts = usersData;
			dailyCosts = dailyData;
			error = null;

			// Calculate max for chart scaling
			if (dailyData.days.length > 0) {
				chartMaxValue = Math.max(...dailyData.days.map(d => d.total_cost));
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load cost data';
		} finally {
			loading = false;
		}
	}

	function formatCurrency(value: number): string {
		return `$${value.toFixed(2)}`;
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	function downloadCsv() {
		if (!userCosts || !dailyCosts) return;

		// Build CSV content
		let csv = 'Type,Date/User,Cost,Sessions\n';

		// Daily costs
		for (const day of dailyCosts.days) {
			csv += `Daily,${day.date},${day.total_cost.toFixed(4)},${day.session_count}\n`;
		}

		// User costs
		for (const user of userCosts.users) {
			csv += `User,${user.email || user.user_id},${user.total_cost.toFixed(4)},${user.session_count}\n`;
		}

		// Download
		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `cost-report-${new Date().toISOString().split('T')[0]}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

	// Calculate bar height percentage
	function getBarHeight(value: number): number {
		if (chartMaxValue === 0) return 0;
		return (value / chartMaxValue) * 100;
	}

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>Cost Analytics - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
						aria-label="Back to admin"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div class="flex items-center gap-3">
						<BarChart3 class="w-6 h-6 text-success-600 dark:text-success-400" />
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">Cost Analytics</h1>
					</div>
				</div>
				<div class="flex items-center gap-3">
					<Button variant="secondary" size="sm" onclick={loadData}>
						<RefreshCw class="w-4 h-4" />
						Refresh
					</Button>
					<Button variant="brand" size="sm" onclick={downloadCsv} disabled={!userCosts || !dailyCosts}>
						<Download class="w-4 h-4" />
						Export CSV
					</Button>
				</div>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if summary}
			<!-- Summary Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Today</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{formatCurrency(summary.today)}</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_today} sessions</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<DollarSign class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Week</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{formatCurrency(summary.this_week)}</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_week} sessions</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Calendar class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Month</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{formatCurrency(summary.this_month)}</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_month} sessions</p>
						</div>
						<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
							<TrendingUp class="w-6 h-6 text-amber-600 dark:text-amber-400" />
						</div>
					</div>
				</div>
				<div class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700">
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">All Time</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">{formatCurrency(summary.all_time)}</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_total} sessions</p>
						</div>
						<div class="p-3 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
							<BarChart3 class="w-6 h-6 text-neutral-600 dark:text-neutral-400" />
						</div>
					</div>
				</div>
			</div>

			<!-- Daily Costs Chart -->
			{#if dailyCosts && dailyCosts.days.length > 0}
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">Daily Costs (Last 30 Days)</h2>
					<div class="h-48 flex items-end gap-1">
						{#each dailyCosts.days as day, i (day.date)}
							<div class="flex-1 flex flex-col items-center gap-1 min-w-0">
								<div
									class="w-full bg-brand-500 dark:bg-brand-400 rounded-t transition-all hover:bg-brand-600 dark:hover:bg-brand-300"
									style="height: {getBarHeight(day.total_cost)}%"
									title="{formatDate(day.date)}: {formatCurrency(day.total_cost)} ({day.session_count} sessions)"
								></div>
								{#if i % 5 === 0 || i === dailyCosts.days.length - 1}
									<span class="text-xs text-neutral-500 transform -rotate-45 origin-top-left whitespace-nowrap">
										{formatDate(day.date)}
									</span>
								{/if}
							</div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- Top Users Table -->
			{#if userCosts && userCosts.users.length > 0}
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden">
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Top Users by Cost</h2>
					</div>
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Rank</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">User</th>
								<th class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Sessions</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Total Cost</th>
								<th class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">Avg/Session</th>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each userCosts.users as user, i (user.user_id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
									<td class="px-6 py-4">
										<span class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium {
											i === 0 ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400' :
											i === 1 ? 'bg-neutral-200 text-neutral-800 dark:bg-neutral-600 dark:text-neutral-300' :
											i === 2 ? 'bg-amber-700/20 text-amber-700 dark:bg-amber-800/30 dark:text-amber-500' :
											'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400'
										}">
											{i + 1}
										</span>
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<Users class="w-4 h-4 text-neutral-400" />
											<span class="text-sm text-neutral-900 dark:text-white truncate max-w-[200px]" title={user.email || user.user_id}>
												{user.email || user.user_id}
											</span>
										</div>
									</td>
									<td class="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300">
										{user.session_count}
									</td>
									<td class="px-6 py-4 text-right">
										<span class="text-sm font-medium text-neutral-900 dark:text-white">
											{formatCurrency(user.total_cost)}
										</span>
									</td>
									<td class="px-6 py-4 text-right">
										<span class="text-sm text-neutral-600 dark:text-neutral-400">
											{formatCurrency(user.session_count > 0 ? user.total_cost / user.session_count : 0)}
										</span>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{/if}
	</main>
</div>
