<script lang="ts">
	/**
	 * Admin GSC Analytics Page
	 *
	 * Displays Google Search Console metrics:
	 * - Connection status and site info
	 * - Overview metrics (impressions, clicks, CTR, position)
	 * - Per-decision search performance
	 * - Manual sync controls
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import {
		RefreshCw,
		Search,
		MousePointer,
		TrendingUp,
		BarChart3,
		ExternalLink,
		AlertCircle,
		CheckCircle2
	} from 'lucide-svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import {
		adminApi,
		type GSCOverviewResponse,
		type GSCDecisionsResponse,
		type GSCSyncResponse
	} from '$lib/api/admin';

	// State
	let overview = $state<GSCOverviewResponse | null>(null);
	let decisions = $state<GSCDecisionsResponse | null>(null);
	let isLoading = $state(true);
	let isSyncing = $state(false);
	let error = $state<string | null>(null);
	let syncResult = $state<GSCSyncResponse | null>(null);
	let sortBy = $state<'impressions' | 'clicks' | 'ctr' | 'position'>('impressions');

	// Load data
	async function loadData() {
		isLoading = true;
		error = null;
		try {
			const [overviewData, decisionsData] = await Promise.all([
				adminApi.getGscOverview(30),
				adminApi.getGscDecisions(50, 0, sortBy)
			]);
			overview = overviewData;
			decisions = decisionsData;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load GSC data';
		} finally {
			isLoading = false;
		}
	}

	// Sync GSC data
	async function handleSync(historical: boolean = false) {
		isSyncing = true;
		syncResult = null;
		try {
			if (historical) {
				syncResult = await adminApi.syncGscHistorical(90);
			} else {
				syncResult = await adminApi.syncGsc();
			}
			// Reload data after sync
			await loadData();
		} catch (err) {
			error = err instanceof Error ? err.message : 'Sync failed';
		} finally {
			isSyncing = false;
		}
	}

	// Handle sort change
	async function handleSortChange(newSort: 'impressions' | 'clicks' | 'ctr' | 'position') {
		sortBy = newSort;
		try {
			decisions = await adminApi.getGscDecisions(50, 0, sortBy);
		} catch {
			// Silent fail for sort changes
		}
	}

	// Format number with commas
	function formatNumber(value: number): string {
		return value.toLocaleString();
	}

	// Format percentage
	function formatPercent(value: number): string {
		return (value * 100).toFixed(2) + '%';
	}

	// Format position
	function formatPosition(value: number | null): string {
		if (value === null) return '-';
		return value.toFixed(1);
	}

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>GSC Analytics - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Google Search Console">
		{#snippet actions()}
			<Button
				variant="secondary"
				size="sm"
				onclick={() => handleSync(true)}
				disabled={isSyncing || !overview?.connected}
			>
				{#snippet children()}
					<RefreshCw class="w-4 h-4 {isSyncing ? 'animate-spin' : ''}" />
					Sync 90 Days
				{/snippet}
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={() => handleSync(false)}
				disabled={isSyncing || !overview?.connected}
			>
				{#snippet children()}
					<RefreshCw class="w-4 h-4 {isSyncing ? 'animate-spin' : ''}" />
					Sync Recent
				{/snippet}
			</Button>
			<Button variant="secondary" size="sm" onclick={loadData} disabled={isLoading}>
				{#snippet children()}
					<RefreshCw class="w-4 h-4 {isLoading ? 'animate-spin' : ''}" />
					Refresh
				{/snippet}
			</Button>
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		<!-- Error State -->
		{#if error}
			<div
				class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6"
			>
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={loadData} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		<!-- Sync Result -->
		{#if syncResult}
			<div
				class="bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-800 rounded-lg p-4 mb-6"
			>
				<div class="flex items-center gap-2">
					<CheckCircle2 class="w-5 h-5 text-success-600" />
					<span class="font-medium text-success-800 dark:text-success-200">Sync Complete</span>
				</div>
				<p class="text-sm text-success-700 dark:text-success-300 mt-1">
					Fetched {syncResult.pages_fetched} pages, matched {syncResult.decisions_matched}{' '}
					decisions, created {syncResult.snapshots_created} snapshots
				</p>
			</div>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="space-y-6">
				<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
					{#each [1, 2, 3, 4] as _}
						<div
							class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 animate-pulse"
						>
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-16 mb-2"></div>
							<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-24"></div>
						</div>
					{/each}
				</div>
			</div>
		{:else if overview}
			<!-- Connection Status -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 mb-6"
			>
				<div class="flex items-center justify-between">
					<div class="flex items-center gap-3">
						{#if overview.connected}
							<div class="w-3 h-3 bg-success-500 rounded-full"></div>
							<span class="font-medium text-neutral-900 dark:text-white">Connected</span>
							<span class="text-neutral-500 dark:text-neutral-400">
								{overview.site_url}
							</span>
						{:else}
							<div class="w-3 h-3 bg-error-500 rounded-full"></div>
							<span class="font-medium text-neutral-900 dark:text-white">Not Connected</span>
						{/if}
					</div>
					{#if overview.last_sync}
						<span class="text-sm text-neutral-500 dark:text-neutral-400">
							Last sync: {new Date(overview.last_sync).toLocaleString()}
						</span>
					{/if}
					<a
						href="/admin/integrations"
						class="text-sm text-brand-600 hover:text-brand-700 dark:text-brand-400"
					>
						Manage Connection
					</a>
				</div>
			</div>

			{#if !overview.connected}
				<!-- Not Connected State -->
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center"
				>
					<div
						class="mx-auto w-12 h-12 bg-neutral-100 dark:bg-neutral-700 rounded-full flex items-center justify-center mb-4"
					>
						<AlertCircle class="w-6 h-6 text-neutral-400" />
					</div>
					<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
						Google Search Console Not Connected
					</h3>
					<p class="text-neutral-600 dark:text-neutral-400 mb-4">
						Connect your GSC account to view search performance data.
					</p>
					<a href="/admin/integrations">
						<Button variant="brand" size="sm">
							{#snippet children()}Connect GSC{/snippet}
						</Button>
					</a>
				</div>
			{:else}
				<!-- Overview Cards -->
				<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
					>
						<div class="flex items-center gap-2 mb-2">
							<Search class="w-5 h-5 text-info-500" />
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Impressions</span>
						</div>
						<div class="text-2xl font-bold text-neutral-900 dark:text-white">
							{formatNumber(overview.total_impressions)}
						</div>
					</div>

					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
					>
						<div class="flex items-center gap-2 mb-2">
							<MousePointer class="w-5 h-5 text-warning-500" />
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Clicks</span>
						</div>
						<div class="text-2xl font-bold text-neutral-900 dark:text-white">
							{formatNumber(overview.total_clicks)}
						</div>
					</div>

					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
					>
						<div class="flex items-center gap-2 mb-2">
							<TrendingUp class="w-5 h-5 text-success-500" />
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Avg CTR</span>
						</div>
						<div class="text-2xl font-bold text-neutral-900 dark:text-white">
							{formatPercent(overview.avg_ctr)}
						</div>
					</div>

					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4"
					>
						<div class="flex items-center gap-2 mb-2">
							<BarChart3 class="w-5 h-5 text-purple-500" />
							<span class="text-sm text-neutral-500 dark:text-neutral-400">Avg Position</span>
						</div>
						<div class="text-2xl font-bold text-neutral-900 dark:text-white">
							{formatPosition(overview.avg_position)}
						</div>
					</div>
				</div>

				<!-- Date Range Info -->
				{#if overview.earliest_date && overview.latest_date}
					<div
						class="bg-neutral-100 dark:bg-neutral-800 rounded-lg px-4 py-2 mb-6 text-sm text-neutral-600 dark:text-neutral-400"
					>
						Data range: {overview.earliest_date} to {overview.latest_date} ({overview.decision_count}{' '}
						decisions tracked)
					</div>
				{/if}

				<!-- Decisions Table -->
				{#if decisions}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700"
					>
						<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
							<div class="flex items-center justify-between">
								<h2 class="text-lg font-medium text-neutral-900 dark:text-white">
									Decision Search Performance
								</h2>
								<div class="flex items-center gap-2">
									<span class="text-xs text-neutral-500">Sort:</span>
									<select
										class="text-sm border border-neutral-300 dark:border-neutral-600 rounded px-2 py-1 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
										bind:value={sortBy}
										onchange={() => handleSortChange(sortBy)}
									>
										<option value="impressions">Impressions</option>
										<option value="clicks">Clicks</option>
										<option value="ctr">CTR</option>
										<option value="position">Position</option>
									</select>
								</div>
							</div>
						</div>

						<div class="overflow-x-auto">
							{#if decisions.decisions.length === 0}
								<EmptyState title="No search data yet" description='Click "Sync" to fetch data from GSC.' icon={Search} />
							{:else}
								<table class="w-full">
									<thead class="bg-neutral-50 dark:bg-neutral-900">
										<tr>
											<th
												class="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
												>Decision</th
											>
											<th
												class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
												>Impressions</th
											>
											<th
												class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
												>Clicks</th
											>
											<th
												class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
												>CTR</th
											>
											<th
												class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase"
												>Position</th
											>
										</tr>
									</thead>
									<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
										{#each decisions.decisions as decision}
											<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
												<td class="px-4 py-3">
													<a
														href="/decisions/{decision.slug}"
														target="_blank"
														class="font-medium text-neutral-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400 flex items-center gap-1"
													>
														<span class="truncate max-w-xs">{decision.title}</span>
														<ExternalLink class="w-3 h-3 flex-shrink-0" />
													</a>
													<div class="text-xs text-neutral-500 dark:text-neutral-400">
														{decision.category}
													</div>
												</td>
												<td class="px-4 py-3 text-right text-neutral-900 dark:text-white">
													{formatNumber(decision.impressions)}
												</td>
												<td class="px-4 py-3 text-right text-neutral-900 dark:text-white">
													{formatNumber(decision.clicks)}
												</td>
												<td class="px-4 py-3 text-right">
													<span
														class="{decision.ctr >= 0.05
															? 'text-success-600 dark:text-success-400'
															: decision.ctr >= 0.02
																? 'text-warning-600 dark:text-warning-400'
																: 'text-neutral-500'} font-medium"
													>
														{formatPercent(decision.ctr)}
													</span>
												</td>
												<td class="px-4 py-3 text-right">
													<span
														class="{decision.position !== null && decision.position <= 10
															? 'text-success-600 dark:text-success-400'
															: decision.position !== null && decision.position <= 20
																? 'text-warning-600 dark:text-warning-400'
																: 'text-neutral-500'} font-medium"
													>
														{formatPosition(decision.position)}
													</span>
												</td>
											</tr>
										{/each}
									</tbody>
								</table>
							{/if}
						</div>
					</div>
				{/if}
			{/if}
		{:else}
			<!-- Empty State -->
			<EmptyState title="No GSC data available" description="Connect GSC and sync data to see search performance." icon={BarChart3} />
		{/if}
	</main>
</div>
