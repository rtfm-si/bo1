<script lang="ts">
	import { onMount } from 'svelte';
	import {
		BarChart3,
		Download,
		RefreshCw,
		DollarSign,
		Calendar,
		Users,
		TrendingUp,
		PieChart,
		Server,
		Plus,
		Zap
	} from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import {
		adminApi,
		type CostSummaryResponse,
		type UserCostsResponse,
		type DailyCostsResponse,
		type CostsByProviderResponse,
		type FixedCostsResponse,
		type PerUserCostResponse,
		type UnifiedCacheMetricsResponse
	} from '$lib/api/admin';

	// State
	let summary = $state<CostSummaryResponse | null>(null);
	let userCosts = $state<UserCostsResponse | null>(null);
	let dailyCosts = $state<DailyCostsResponse | null>(null);
	let providerCosts = $state<CostsByProviderResponse | null>(null);
	let fixedCosts = $state<FixedCostsResponse | null>(null);
	let perUserCosts = $state<PerUserCostResponse | null>(null);
	let cacheMetrics = $state<UnifiedCacheMetricsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let activeTab = $state<'overview' | 'providers' | 'fixed'>('overview');

	// Chart state
	let chartMaxValue = $state(0);

	// Provider colors
	const providerColors: Record<string, string> = {
		anthropic: 'bg-orange-500',
		voyage: 'bg-blue-500',
		brave: 'bg-red-500',
		tavily: 'bg-green-500',
		openai: 'bg-emerald-500'
	};

	async function loadData() {
		try {
			loading = true;
			const [summaryData, usersData, dailyData, providerData, fixedData, perUserData, cacheData] =
				await Promise.all([
					adminApi.getCostSummary(),
					adminApi.getUserCosts({ limit: 10 }),
					adminApi.getDailyCosts(),
					adminApi.getCostsByProvider(30),
					adminApi.getFixedCosts(),
					adminApi.getPerUserCosts({ days: 30, limit: 20 }),
					adminApi.getUnifiedCacheMetrics().catch(() => null)
				]);
			summary = summaryData;
			userCosts = usersData;
			dailyCosts = dailyData;
			providerCosts = providerData;
			fixedCosts = fixedData;
			perUserCosts = perUserData;
			cacheMetrics = cacheData;
			error = null;

			// Calculate max for chart scaling
			if (dailyData.days.length > 0) {
				chartMaxValue = Math.max(...dailyData.days.map((d) => d.total_cost));
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load cost data';
		} finally {
			loading = false;
		}
	}

	function formatPercent(value: number): string {
		return `${(value * 100).toFixed(1)}%`;
	}

	async function seedFixedCosts() {
		try {
			const result = await adminApi.seedFixedCosts();
			fixedCosts = result;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to seed fixed costs';
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

		let csv = 'Type,Date/User,Cost,Sessions\n';

		for (const day of dailyCosts.days) {
			csv += `Daily,${day.date},${day.total_cost.toFixed(4)},${day.session_count}\n`;
		}

		for (const user of userCosts.users) {
			csv += `User,${user.email || user.user_id},${user.total_cost.toFixed(4)},${user.session_count}\n`;
		}

		const blob = new Blob([csv], { type: 'text/csv' });
		const url = URL.createObjectURL(blob);
		const a = document.createElement('a');
		a.href = url;
		a.download = `cost-report-${new Date().toISOString().split('T')[0]}.csv`;
		a.click();
		URL.revokeObjectURL(url);
	}

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
						<svg
							class="w-5 h-5 text-neutral-600 dark:text-neutral-400"
							fill="none"
							stroke="currentColor"
							viewBox="0 0 24 24"
						>
							<path
								stroke-linecap="round"
								stroke-linejoin="round"
								stroke-width="2"
								d="M10 19l-7-7m0 0l7-7m-7 7h18"
							/>
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
					<Button
						variant="brand"
						size="sm"
						onclick={downloadCsv}
						disabled={!userCosts || !dailyCosts}
					>
						<Download class="w-4 h-4" />
						Export CSV
					</Button>
				</div>
			</div>

			<!-- Tabs -->
			<div class="flex gap-4 mt-4">
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab ===
					'overview'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'overview')}
				>
					Overview
				</button>
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab ===
					'providers'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'providers')}
				>
					By Provider
				</button>
				<button
					class="px-4 py-2 text-sm font-medium rounded-lg transition-colors {activeTab === 'fixed'
						? 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-400'
						: 'text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-700'}"
					onclick={() => (activeTab = 'fixed')}
				>
					Fixed Costs
				</button>
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
		{:else if activeTab === 'overview' && summary}
			<!-- Summary Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Today</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.today)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_today} sessions</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<DollarSign class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Week</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.this_week)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_week} sessions</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Calendar class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">This Month</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.this_month)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_month} sessions</p>
						</div>
						<div class="p-3 bg-amber-100 dark:bg-amber-900/30 rounded-lg">
							<TrendingUp class="w-6 h-6 text-amber-600 dark:text-amber-400" />
						</div>
					</div>
				</div>
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">All Time</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(summary.all_time)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">{summary.session_count_total} sessions</p>
						</div>
						<div class="p-3 bg-neutral-100 dark:bg-neutral-700 rounded-lg">
							<BarChart3 class="w-6 h-6 text-neutral-600 dark:text-neutral-400" />
						</div>
					</div>
				</div>
			</div>

			<!-- Per-User Average Card -->
			{#if perUserCosts}
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 mb-8"
				>
					<div class="flex items-center justify-between">
						<div class="flex items-center gap-3">
							<Users class="w-5 h-5 text-brand-600" />
							<h3 class="text-lg font-medium text-neutral-900 dark:text-white">
								Average Cost Per User
							</h3>
						</div>
						<div class="text-right">
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(perUserCosts.overall_avg)}
							</p>
							<p class="text-sm text-neutral-500">
								{perUserCosts.total_users} active users (30d)
							</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Cache Performance Card -->
			{#if cacheMetrics}
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700 mb-8"
				>
					<div class="flex items-center gap-3 mb-4">
						<Zap class="w-5 h-5 text-amber-500" />
						<h3 class="text-lg font-medium text-neutral-900 dark:text-white">
							Cache Performance (24h)
						</h3>
					</div>

					<div class="grid grid-cols-1 md:grid-cols-4 gap-4">
						<!-- Prompt Cache -->
						<div class="p-4 bg-orange-50 dark:bg-orange-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">Prompt Cache</p>
							<p class="text-xl font-semibold text-orange-600 dark:text-orange-400">
								{formatPercent(cacheMetrics.prompt.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.prompt.hits.toLocaleString()} / {cacheMetrics.prompt.total.toLocaleString()}
							</p>
						</div>

						<!-- Research Cache -->
						<div class="p-4 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">Research Cache</p>
							<p class="text-xl font-semibold text-blue-600 dark:text-blue-400">
								{formatPercent(cacheMetrics.research.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.research.hits.toLocaleString()} / {cacheMetrics.research.total.toLocaleString()}
							</p>
						</div>

						<!-- LLM Cache -->
						<div class="p-4 bg-green-50 dark:bg-green-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">LLM Cache</p>
							<p class="text-xl font-semibold text-green-600 dark:text-green-400">
								{formatPercent(cacheMetrics.llm.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.llm.hits.toLocaleString()} / {cacheMetrics.llm.total.toLocaleString()}
							</p>
						</div>

						<!-- Aggregate -->
						<div class="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
							<p class="text-xs text-neutral-500 mb-1">Aggregate</p>
							<p class="text-xl font-semibold text-brand-600 dark:text-brand-400">
								{formatPercent(cacheMetrics.aggregate.hit_rate)}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{cacheMetrics.aggregate.total_hits.toLocaleString()} / {cacheMetrics.aggregate.total_requests.toLocaleString()}
							</p>
						</div>
					</div>
				</div>
			{/if}

			<!-- Daily Costs Chart -->
			{#if dailyCosts && dailyCosts.days.length > 0}
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8"
				>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
						Daily Costs (Last 30 Days)
					</h2>
					<div class="h-48 flex items-end gap-1">
						{#each dailyCosts.days as day, i (day.date)}
							<div class="flex-1 flex flex-col items-center gap-1 min-w-0">
								<div
									class="w-full bg-brand-500 dark:bg-brand-400 rounded-t transition-all hover:bg-brand-600 dark:hover:bg-brand-300"
									style="height: {getBarHeight(day.total_cost)}%"
									title="{formatDate(day.date)}: {formatCurrency(day.total_cost)} ({day.session_count} sessions)"
								></div>
								{#if i % 5 === 0 || i === dailyCosts.days.length - 1}
									<span
										class="text-xs text-neutral-500 transform -rotate-45 origin-top-left whitespace-nowrap"
									>
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
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
				>
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Top Users by Cost
						</h2>
					</div>
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Rank</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>User</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Sessions</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Total Cost</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wider"
									>Avg/Session</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each userCosts.users as user, i (user.user_id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
									<td class="px-6 py-4">
										<span
											class="inline-flex items-center justify-center w-6 h-6 rounded-full text-xs font-medium {i ===
											0
												? 'bg-amber-100 text-amber-800 dark:bg-amber-900/30 dark:text-amber-400'
												: i === 1
													? 'bg-neutral-200 text-neutral-800 dark:bg-neutral-600 dark:text-neutral-300'
													: i === 2
														? 'bg-amber-700/20 text-amber-700 dark:bg-amber-800/30 dark:text-amber-500'
														: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400'}"
										>
											{i + 1}
										</span>
									</td>
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<Users class="w-4 h-4 text-neutral-400" />
											<span
												class="text-sm text-neutral-900 dark:text-white truncate max-w-[200px]"
												title={user.email || user.user_id}
											>
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
											{formatCurrency(
												user.session_count > 0 ? user.total_cost / user.session_count : 0
											)}
										</span>
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			{/if}
		{:else if activeTab === 'providers' && providerCosts}
			<!-- Provider Breakdown -->
			<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
				<!-- Provider Pie Chart (visual representation) -->
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
				>
					<div class="flex items-center gap-2 mb-4">
						<PieChart class="w-5 h-5 text-brand-600" />
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Cost Distribution by Provider
						</h2>
					</div>

					<div class="space-y-4">
						{#each providerCosts.providers as provider (provider.provider)}
							<div>
								<div class="flex justify-between text-sm mb-1">
									<span class="text-neutral-700 dark:text-neutral-300 capitalize"
										>{provider.provider}</span
									>
									<span class="text-neutral-900 dark:text-white font-medium">
										{formatCurrency(provider.amount_usd)} ({provider.percentage}%)
									</span>
								</div>
								<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
									<div
										class="{providerColors[provider.provider] ||
											'bg-neutral-500'} h-full rounded-full transition-all"
										style="width: {provider.percentage}%"
									></div>
								</div>
								<p class="text-xs text-neutral-500 mt-1">
									{provider.request_count.toLocaleString()} requests
								</p>
							</div>
						{/each}
					</div>

					<div class="mt-6 pt-4 border-t border-neutral-200 dark:border-neutral-700">
						<div class="flex justify-between">
							<span class="text-neutral-600 dark:text-neutral-400">Total (30d)</span>
							<span class="text-lg font-semibold text-neutral-900 dark:text-white">
								{formatCurrency(providerCosts.total_usd)}
							</span>
						</div>
					</div>
				</div>

				<!-- Provider Table -->
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 overflow-hidden"
				>
					<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Provider Details</h2>
					</div>
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Provider</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Requests</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Cost</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Avg/Request</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each providerCosts.providers as provider (provider.provider)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
									<td class="px-6 py-4">
										<div class="flex items-center gap-2">
											<div
												class="w-3 h-3 rounded-full {providerColors[provider.provider] ||
													'bg-neutral-500'}"
											></div>
											<span class="text-sm font-medium text-neutral-900 dark:text-white capitalize">
												{provider.provider}
											</span>
										</div>
									</td>
									<td class="px-6 py-4 text-right text-sm text-neutral-700 dark:text-neutral-300">
										{provider.request_count.toLocaleString()}
									</td>
									<td class="px-6 py-4 text-right text-sm font-medium text-neutral-900 dark:text-white">
										{formatCurrency(provider.amount_usd)}
									</td>
									<td class="px-6 py-4 text-right text-sm text-neutral-600 dark:text-neutral-400">
										{formatCurrency(
											provider.request_count > 0
												? provider.amount_usd / provider.request_count
												: 0
										)}
									</td>
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{:else if activeTab === 'fixed' && fixedCosts}
			<!-- Fixed Costs -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
			>
				<div
					class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700 flex items-center justify-between"
				>
					<div class="flex items-center gap-2">
						<Server class="w-5 h-5 text-brand-600" />
						<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
							Fixed Infrastructure Costs
						</h2>
					</div>
					{#if fixedCosts.costs.length === 0}
						<Button variant="secondary" size="sm" onclick={seedFixedCosts}>
							<Plus class="w-4 h-4" />
							Seed Defaults
						</Button>
					{/if}
				</div>

				{#if fixedCosts.costs.length === 0}
					<div class="p-8 text-center">
						<Server class="w-12 h-12 text-neutral-400 mx-auto mb-4" />
						<p class="text-neutral-600 dark:text-neutral-400">No fixed costs configured</p>
						<p class="text-sm text-neutral-500 mt-1">Click "Seed Defaults" to add common entries</p>
					</div>
				{:else}
					<table class="w-full">
						<thead class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Provider</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Description</th
								>
								<th
									class="px-6 py-3 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Category</th
								>
								<th
									class="px-6 py-3 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
									>Monthly Cost</th
								>
							</tr>
						</thead>
						<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
							{#each fixedCosts.costs as cost (cost.id)}
								<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-700/50">
									<td class="px-6 py-4">
										<span class="text-sm font-medium text-neutral-900 dark:text-white capitalize">
											{cost.provider}
										</span>
									</td>
									<td class="px-6 py-4 text-sm text-neutral-700 dark:text-neutral-300">
										{cost.description}
									</td>
									<td class="px-6 py-4">
										<span
											class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300 capitalize"
										>
											{cost.category}
										</span>
									</td>
									<td class="px-6 py-4 text-right text-sm font-medium text-neutral-900 dark:text-white">
										{formatCurrency(cost.monthly_amount_usd)}
									</td>
								</tr>
							{/each}
						</tbody>
						<tfoot class="bg-neutral-50 dark:bg-neutral-700">
							<tr>
								<td colspan="3" class="px-6 py-4 text-sm font-medium text-neutral-900 dark:text-white">
									Total Monthly Fixed Costs
								</td>
								<td class="px-6 py-4 text-right text-lg font-semibold text-neutral-900 dark:text-white">
									{formatCurrency(fixedCosts.monthly_total)}
								</td>
							</tr>
						</tfoot>
					</table>
				{/if}

				<!-- Fixed vs Variable Comparison -->
				{#if summary && fixedCosts.costs.length > 0}
					<div class="p-6 border-t border-neutral-200 dark:border-neutral-700">
						<h3 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-4">
							Fixed vs Variable (This Month)
						</h3>
						<div class="grid grid-cols-2 gap-4">
							<div class="p-4 bg-neutral-50 dark:bg-neutral-700 rounded-lg">
								<p class="text-xs text-neutral-500 mb-1">Fixed Costs</p>
								<p class="text-xl font-semibold text-neutral-900 dark:text-white">
									{formatCurrency(fixedCosts.monthly_total)}
								</p>
							</div>
							<div class="p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
								<p class="text-xs text-neutral-500 mb-1">Variable Costs (API)</p>
								<p class="text-xl font-semibold text-brand-700 dark:text-brand-400">
									{formatCurrency(summary.this_month)}
								</p>
							</div>
						</div>
						<div class="mt-4 p-4 bg-neutral-100 dark:bg-neutral-600 rounded-lg">
							<div class="flex justify-between items-center">
								<span class="text-sm text-neutral-600 dark:text-neutral-300"
									>Estimated Total Monthly</span
								>
								<span class="text-xl font-bold text-neutral-900 dark:text-white">
									{formatCurrency(fixedCosts.monthly_total + summary.this_month)}
								</span>
							</div>
						</div>
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
