<script lang="ts">
	/**
	 * Market Trends - Trend forecasts and market analysis
	 *
	 * - TrendSummaryCard (AI-generated industry summary with timeframe)
	 * - Market Trends (real-time trend refresh)
	 */
	import { onMount } from 'svelte';
	import { apiClient, getCsrfToken, type MarketTrend } from '$lib/api/client';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import Breadcrumb from '$lib/components/ui/Breadcrumb.svelte';
	import TrendSummaryCard from '$lib/components/context/TrendSummaryCard.svelte';

	// Trend Summary types
	interface TrendSummary {
		summary: string;
		key_trends: string[];
		opportunities: string[];
		threats: string[];
		generated_at: string;
		industry: string;
		timeframe?: string;
		available_timeframes?: string[];
	}

	type Timeframe = 'now' | '3m' | '12m' | '24m';

	// UI state
	let isLoading = $state(true);

	// Market Trends state
	let marketTrends = $state<MarketTrend[]>([]);
	let isRefreshingTrends = $state(false);
	let trendsError = $state<string | null>(null);

	// Trend Summary state (AI-generated industry summary with timeframe support)
	let trendSummary = $state<TrendSummary | null>(null);
	let trendSummaryStale = $state(false);
	let trendSummaryNeedsIndustry = $state(false);
	let isLoadingTrendSummary = $state(false);
	let isRefreshingTrendSummary = $state(false);
	let trendSummaryError = $state<string | null>(null);
	let selectedTimeframe = $state<Timeframe>('now');
	let availableTimeframes = $state<string[]>(['now', '3m']);
	let forecastUpgradePrompt = $state<string | null>(null);
	let canRefreshNow = $state(true);
	let refreshBlockedReason = $state<string | null>(null);

	onMount(async () => {
		try {
			await loadTrendSummary();
		} finally {
			isLoading = false;
		}
	});

	// Trend Forecast functions (with timeframe support)
	async function loadTrendForecast(timeframe: Timeframe = selectedTimeframe) {
		isLoadingTrendSummary = true;
		trendSummaryError = null;
		forecastUpgradePrompt = null;
		try {
			const endpoint = timeframe === 'now'
				? '/api/v1/context/trends/summary'
				: `/api/v1/context/trends/forecast?timeframe=${timeframe}`;
			const response = await fetch(endpoint, {
				credentials: 'include'
			});
			const data = await response.json();
			if (data.success) {
				trendSummary = data.summary;
				trendSummaryStale = data.stale;
				trendSummaryNeedsIndustry = data.needs_industry;
				availableTimeframes = timeframe === 'now'
					? ['now', ...(data.available_timeframes || ['3m'])]
					: data.available_timeframes || ['now', '3m'];
				forecastUpgradePrompt = data.upgrade_prompt || null;
				canRefreshNow = data.can_refresh_now ?? true;
				refreshBlockedReason = data.refresh_blocked_reason ?? null;
			} else if (data.upgrade_prompt) {
				forecastUpgradePrompt = data.upgrade_prompt;
				availableTimeframes = data.available_timeframes || ['now', '3m'];
			} else {
				trendSummaryError = data.error || 'Failed to load trend forecast';
			}
		} catch (error) {
			console.error('Failed to load trend forecast:', error);
			trendSummaryError = error instanceof Error ? error.message : 'Failed to load trend forecast';
		} finally {
			isLoadingTrendSummary = false;
		}
	}

	const loadTrendSummary = () => loadTrendForecast(selectedTimeframe);

	async function handleRefreshTrendForecast() {
		isRefreshingTrendSummary = true;
		trendSummaryError = null;
		try {
			const endpoint = selectedTimeframe === 'now'
				? '/api/v1/context/trends/summary/refresh'
				: `/api/v1/context/trends/forecast/refresh?timeframe=${selectedTimeframe}`;
			const csrfToken = getCsrfToken();
			const headers: Record<string, string> = {};
			if (csrfToken) {
				headers['X-CSRF-Token'] = csrfToken;
			}
			const response = await fetch(endpoint, {
				method: 'POST',
				credentials: 'include',
				headers
			});
			const data = await response.json();
			if (data.success && data.summary) {
				trendSummary = data.summary;
				trendSummaryStale = false;
				availableTimeframes = selectedTimeframe === 'now'
					? ['now', ...(data.available_timeframes || ['3m'])]
					: data.available_timeframes || ['now', '3m'];
				forecastUpgradePrompt = null;
			} else if (response.status === 403) {
				trendSummaryError = data.detail || 'Upgrade required to access this timeframe.';
			} else {
				trendSummaryError = data.error || 'Failed to refresh trend forecast';
			}
		} catch (error) {
			console.error('Failed to refresh trend forecast:', error);
			trendSummaryError = error instanceof Error ? error.message : 'Failed to refresh trend forecast';
		} finally {
			isRefreshingTrendSummary = false;
		}
	}

	async function handleTimeframeChange(newTimeframe: Timeframe) {
		if (newTimeframe === selectedTimeframe) return;
		selectedTimeframe = newTimeframe;
		await loadTrendForecast(newTimeframe);
	}

	async function handleRefreshTrends() {
		isRefreshingTrends = true;
		trendsError = null;

		try {
			const response = await apiClient.refreshTrends();
			if (response.success) {
				marketTrends = response.trends;
			} else {
				trendsError = response.error || 'Failed to fetch trends';
			}
		} catch (error) {
			trendsError = error instanceof Error ? error.message : 'Failed to fetch trends';
		} finally {
			isRefreshingTrends = false;
		}
	}
</script>

<svelte:head>
	<title>Market Trends - Board of One</title>
</svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
	<!-- Breadcrumb -->
	<div class="mb-6">
		<Breadcrumb
			items={[
				{ label: 'Dashboard', href: '/dashboard' },
				{ label: 'Reports', href: '/reports' },
				{ label: 'Trends', href: '/reports/trends' }
			]}
		/>
	</div>

	{#if isLoading}
		<div class="flex items-center justify-center py-12">
			<div class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"></div>
		</div>
	{:else}
		<div class="space-y-6">
			<!-- Header -->
			<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
				<div class="flex items-center gap-3">
					<span class="text-2xl">📈</span>
					<div>
						<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
							Market Trends
						</h2>
						<p class="text-slate-600 dark:text-slate-400">
							AI-powered trend forecasts and market intelligence for your industry.
						</p>
					</div>
				</div>
			</div>

			<!-- Trend Forecast Section -->
			<TrendSummaryCard
				summary={trendSummary}
				isStale={trendSummaryStale}
				needsIndustry={trendSummaryNeedsIndustry}
				isLoading={isLoadingTrendSummary}
				isRefreshing={isRefreshingTrendSummary}
				error={trendSummaryError}
				{selectedTimeframe}
				{availableTimeframes}
				upgradePrompt={forecastUpgradePrompt}
				canRefresh={canRefreshNow}
				refreshBlockedReason={refreshBlockedReason}
				onRefresh={handleRefreshTrendForecast}
				onTimeframeChange={handleTimeframeChange}
			/>

			<!-- Market Trends Section -->
			<div class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
				<div class="flex items-center justify-between mb-4">
					<div class="flex items-center gap-3">
						<span class="text-2xl">📊</span>
						<h3 class="text-lg font-semibold text-slate-900 dark:text-white">
							Live Market Trends
						</h3>
					</div>
					<Button
						variant="outline"
						size="sm"
						onclick={handleRefreshTrends}
						disabled={isRefreshingTrends}
						loading={isRefreshingTrends}
					>
						{isRefreshingTrends ? 'Refreshing...' : 'Refresh Trends'}
					</Button>
				</div>

				{#if trendsError}
					<Alert variant="warning" class="mb-4">
						{trendsError}
					</Alert>
				{/if}

				{#if marketTrends.length > 0}
					<div class="space-y-4">
						{#each marketTrends as trend, index}
							{@const hasAISummary = trend.summary && trend.key_points}
							<div class="p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg border border-slate-200 dark:border-slate-600">
								<!-- Headline -->
								<h4 class="font-medium text-slate-900 dark:text-white mb-2">{trend.trend}</h4>

								{#if hasAISummary}
									<!-- AI Summary -->
									<p class="text-sm text-slate-700 dark:text-slate-300 mb-3">{trend.summary}</p>

									<!-- Key Points (collapsible) -->
									<details class="group">
										<summary class="text-xs font-medium text-brand-600 dark:text-brand-400 cursor-pointer hover:underline flex items-center gap-1">
											<svg class="w-3 h-3 transition-transform group-open:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
											</svg>
											Key Takeaways
										</summary>
										<ul class="mt-2 space-y-1 pl-4 text-sm text-slate-600 dark:text-slate-400">
											{#each trend.key_points || [] as point}
												<li class="flex items-start gap-2">
													<span class="text-brand-500 mt-0.5">•</span>
													<span>{point}</span>
												</li>
											{/each}
										</ul>
									</details>

									<!-- AI indicator + Source -->
									<div class="flex items-center justify-between mt-3 pt-2 border-t border-slate-200 dark:border-slate-600">
										<span class="text-xs text-slate-500 dark:text-slate-400 flex items-center gap-1">
											<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
												<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
											</svg>
											Summarized by AI
										</span>
										{#if trend.source_url}
											<a
												href={trend.source_url}
												target="_blank"
												rel="noopener noreferrer"
												class="text-xs text-brand-600 dark:text-brand-400 hover:underline"
											>
												{trend.source || 'Read full article'} →
											</a>
										{/if}
									</div>
								{:else}
									<!-- Fallback: Original search snippet style -->
									{#if trend.source_url}
										<a
											href={trend.source_url}
											target="_blank"
											rel="noopener noreferrer"
											class="text-xs text-brand-600 dark:text-brand-400 hover:underline mt-1 inline-block"
										>
											{trend.source || 'Source'} →
										</a>
									{/if}
								{/if}
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-sm text-slate-500 dark:text-slate-400">
						Click "Refresh Trends" to fetch the latest market trends for your industry.
						Make sure you've set your industry in <a href="/context/overview" class="text-brand-600 dark:text-brand-400 hover:underline">Context → Overview</a> first.
					</p>
				{/if}
			</div>

			<!-- Info Box -->
			<div class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
				<div class="flex gap-3">
					<svg
						class="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5"
						fill="none"
						stroke="currentColor"
						viewBox="0 0 24 24"
					>
						<path
							stroke-linecap="round"
							stroke-linejoin="round"
							stroke-width="2"
							d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
						/>
					</svg>
					<div class="text-sm text-blue-900 dark:text-blue-200">
						<p class="font-semibold mb-1">Using trends effectively</p>
						<ul class="text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
							<li>Set your industry in <a href="/context/overview" class="underline">Context → Overview</a> for relevant forecasts</li>
							<li>Use timeframe selector to see predictions for different horizons</li>
							<li>Trends inform your Board meetings for better recommendations</li>
						</ul>
					</div>
				</div>
			</div>
		</div>
	{/if}
</div>
