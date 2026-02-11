<script lang="ts">
	import { onMount } from 'svelte';
	import { Globe, RefreshCw, Users, Eye, MousePointerClick, TrendingUp } from 'lucide-svelte';
	import Button from '$lib/components/ui/Button.svelte';
	import Alert from '$lib/components/ui/Alert.svelte';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import { formatDate } from '$lib/utils/time-formatting';
	import {
		adminApi,
		type LandingPageMetricsResponse
	} from '$lib/api/admin';

	// State
	let metrics = $state<LandingPageMetricsResponse | null>(null);
	let loading = $state(true);
	let error = $state<string | null>(null);
	let selectedDays = $state(30);

	// Derived date range
	const dateRange = $derived(() => {
		const end = new Date();
		const start = new Date();
		start.setDate(start.getDate() - selectedDays);
		return {
			start_date: start.toISOString().split('T')[0],
			end_date: end.toISOString().split('T')[0]
		};
	});

	// Chart scaling
	let maxViews = $state(1);

	async function loadData() {
		try {
			loading = true;
			const range = dateRange();
			metrics = await adminApi.getLandingPageMetrics({
				start_date: range.start_date,
				end_date: range.end_date
			});
			error = null;

			// Calculate max for chart scaling
			if (metrics.daily_stats.length > 0) {
				maxViews = Math.max(...metrics.daily_stats.map((d) => d.total_views), 1);
			}
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load analytics';
		} finally {
			loading = false;
		}
	}


	function formatDuration(ms: number | null): string {
		if (!ms) return '-';
		const seconds = Math.round(ms / 1000);
		if (seconds < 60) return `${seconds}s`;
		const minutes = Math.floor(seconds / 60);
		const remainingSeconds = seconds % 60;
		return `${minutes}m ${remainingSeconds}s`;
	}

	function getBarHeight(value: number): number {
		if (maxViews === 0) return 0;
		return (value / maxViews) * 100;
	}

	function getCountryName(code: string): string {
		try {
			const regionNames = new Intl.DisplayNames(['en'], { type: 'region' });
			return regionNames.of(code) || code;
		} catch {
			return code;
		}
	}

	onMount(() => {
		loadData();
	});

	// Reload when days change
	$effect(() => {
		if (selectedDays) {
			loadData();
		}
	});
</script>

<svelte:head>
	<title>Landing Page Analytics - Admin</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="Landing Page Analytics" icon={Globe}>
		{#snippet actions()}
			<select
				bind:value={selectedDays}
				class="px-3 py-2 text-sm border border-neutral-300 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
			>
				<option value={7}>Last 7 days</option>
				<option value={30}>Last 30 days</option>
				<option value={90}>Last 90 days</option>
			</select>
			<Button variant="secondary" size="sm" onclick={loadData}>
				<RefreshCw class="w-4 h-4" />
				Refresh
			</Button>
		{/snippet}
	</AdminPageHeader>

	<!-- Main Content -->
	<main class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-8">
		{#if error}
			<Alert variant="error" class="mb-6">{error}</Alert>
		{/if}

		{#if loading}
			<div class="flex items-center justify-center py-12">
				<RefreshCw class="w-8 h-8 text-brand-600 animate-spin" />
			</div>
		{:else if metrics}
			<!-- Summary Cards -->
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Unique Visitors</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{metrics.funnel.unique_visitors.toLocaleString()}
							</p>
						</div>
						<div class="p-3 bg-brand-100 dark:bg-brand-900/30 rounded-lg">
							<Users class="w-6 h-6 text-brand-600 dark:text-brand-400" />
						</div>
					</div>
				</div>

				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Total Page Views</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{metrics.daily_stats.reduce((sum, d) => sum + d.total_views, 0).toLocaleString()}
							</p>
						</div>
						<div class="p-3 bg-success-100 dark:bg-success-900/30 rounded-lg">
							<Eye class="w-6 h-6 text-success-600 dark:text-success-400" />
						</div>
					</div>
				</div>

				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Signup Clicks</p>
							<p class="text-2xl font-semibold text-neutral-900 dark:text-white">
								{metrics.funnel.signup_clicks}
							</p>
							<p class="text-xs text-neutral-500 mt-1">
								{metrics.funnel.click_through_rate}% CTR
							</p>
						</div>
						<div class="p-3 bg-warning-100 dark:bg-warning-900/30 rounded-lg">
							<MousePointerClick class="w-6 h-6 text-warning-600 dark:text-warning-400" />
						</div>
					</div>
				</div>

				<div
					class="bg-white dark:bg-neutral-800 rounded-lg p-6 border border-neutral-200 dark:border-neutral-700"
				>
					<div class="flex items-center justify-between">
						<div>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-1">Bounce Rate</p>
							<p
								class="text-2xl font-semibold {metrics.bounce_rate.bounce_rate > 70
									? 'text-error-600 dark:text-error-400'
									: metrics.bounce_rate.bounce_rate > 50
										? 'text-warning-600 dark:text-warning-400'
										: 'text-success-600 dark:text-success-400'}"
							>
								{metrics.bounce_rate.bounce_rate}%
							</p>
						</div>
						<div class="p-3 bg-info-100 dark:bg-info-900/30 rounded-lg">
							<TrendingUp class="w-6 h-6 text-info-600 dark:text-info-400" />
						</div>
					</div>
				</div>
			</div>

			<!-- Conversion Funnel -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8"
			>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
					Conversion Funnel
				</h2>
				<div class="grid grid-cols-4 gap-4">
					<div class="text-center p-4 bg-brand-50 dark:bg-brand-900/20 rounded-lg">
						<p class="text-3xl font-bold text-brand-600 dark:text-brand-400">
							{metrics.funnel.unique_visitors}
						</p>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Visitors</p>
					</div>
					<div class="text-center p-4 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg relative">
						<div class="absolute left-0 top-1/2 -tranneutral-x-1/2 -tranneutral-y-1/2 text-neutral-400">
							→
						</div>
						<p class="text-3xl font-bold text-neutral-900 dark:text-white">
							{metrics.funnel.signup_clicks}
						</p>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Signup Clicks</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1">
							{metrics.funnel.click_through_rate}% CTR
						</p>
					</div>
					<div class="text-center p-4 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg relative">
						<div class="absolute left-0 top-1/2 -tranneutral-x-1/2 -tranneutral-y-1/2 text-neutral-400">
							→
						</div>
						<p class="text-3xl font-bold text-neutral-900 dark:text-white">
							{metrics.funnel.signup_completions}
						</p>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Completions</p>
						<p class="text-xs text-brand-600 dark:text-brand-400 mt-1">
							{metrics.funnel.completion_rate}% completion
						</p>
					</div>
					<div class="text-center p-4 bg-success-50 dark:bg-success-900/20 rounded-lg relative">
						<div class="absolute left-0 top-1/2 -tranneutral-x-1/2 -tranneutral-y-1/2 text-neutral-400">
							→
						</div>
						<p
							class="text-3xl font-bold {metrics.funnel.overall_conversion_rate >= 5
								? 'text-success-600 dark:text-success-400'
								: metrics.funnel.overall_conversion_rate >= 2
									? 'text-warning-600 dark:text-warning-400'
									: 'text-error-600 dark:text-error-400'}"
						>
							{metrics.funnel.overall_conversion_rate}%
						</p>
						<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">Overall Rate</p>
					</div>
				</div>
			</div>

			<div class="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
				<!-- Daily Views Chart -->
				{#if metrics.daily_stats.length > 0}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							Daily Page Views
						</h3>
						<div class="h-40 flex items-end gap-1">
							{#each metrics.daily_stats as day, i (day.date)}
								<div class="flex-1 flex flex-col items-center gap-1 min-w-0">
									<div
										class="w-full bg-brand-500 dark:bg-brand-400 rounded-t transition-all hover:bg-brand-600 dark:hover:bg-brand-300"
										style="height: {getBarHeight(day.total_views)}%"
										title="{formatDate(day.date)}: {day.total_views} views ({day.unique_visitors} unique)"
									></div>
									{#if i % Math.ceil(metrics.daily_stats.length / 7) === 0 || i === metrics.daily_stats.length - 1}
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

				<!-- Geo Breakdown -->
				{#if metrics.geo_breakdown.length > 0}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							Visitors by Country
						</h3>
						<div class="space-y-3 max-h-60 overflow-y-auto">
							{#each metrics.geo_breakdown.slice(0, 10) as country (country.country)}
								{@const maxVisitors = metrics.geo_breakdown[0]?.visitors || 1}
								<div class="flex items-center gap-3">
									<span class="w-8 text-lg" title={getCountryName(country.country)}>
										{country.country}
									</span>
									<div class="flex-1">
										<div class="h-6 bg-neutral-100 dark:bg-neutral-700 rounded-full overflow-hidden">
											<div
												class="h-full bg-brand-500 dark:bg-brand-400 rounded-full transition-all"
												style="width: {(country.visitors / maxVisitors) * 100}%"
											></div>
										</div>
									</div>
									<span class="text-sm font-medium text-neutral-700 dark:text-neutral-300 w-16 text-right">
										{country.visitors}
									</span>
								</div>
							{/each}
						</div>
					</div>
				{:else}
					<div
						class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
					>
						<h3 class="text-base font-semibold text-neutral-900 dark:text-white mb-4">
							Visitors by Country
						</h3>
						<EmptyState title="No geo data available yet" icon={Globe} />
					</div>
				{/if}
			</div>

			<!-- Engagement Metrics -->
			<div
				class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6"
			>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
					Engagement Metrics
				</h2>
				<div class="grid grid-cols-2 md:grid-cols-4 gap-6">
					<div class="text-center">
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Avg. Time on Page</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white mt-1">
							{formatDuration(
								metrics.daily_stats.length > 0
									? metrics.daily_stats.reduce((sum, d) => sum + (d.avg_duration_ms || 0), 0) /
											metrics.daily_stats.filter((d) => d.avg_duration_ms).length || 0
									: null
							)}
						</p>
					</div>
					<div class="text-center">
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Avg. Scroll Depth</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white mt-1">
							{#if metrics.daily_stats.some((d) => d.avg_scroll_depth)}
								{Math.round(
									metrics.daily_stats.reduce((sum, d) => sum + (d.avg_scroll_depth || 0), 0) /
										metrics.daily_stats.filter((d) => d.avg_scroll_depth).length
								)}%
							{:else}
								-
							{/if}
						</p>
					</div>
					<div class="text-center">
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Total Sessions</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white mt-1">
							{metrics.bounce_rate.total_sessions}
						</p>
					</div>
					<div class="text-center">
						<p class="text-sm text-neutral-600 dark:text-neutral-400">Bounced Sessions</p>
						<p class="text-xl font-semibold text-neutral-900 dark:text-white mt-1">
							{metrics.bounce_rate.bounced_sessions}
						</p>
					</div>
				</div>
			</div>
		{/if}
	</main>
</div>
