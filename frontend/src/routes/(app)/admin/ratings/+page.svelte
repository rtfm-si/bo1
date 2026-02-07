<script lang="ts">
	/**
	 * Admin Ratings Page - View user satisfaction ratings (thumbs up/down)
	 * Shows metrics and recent negative ratings for triage
	 */
	import { onMount } from 'svelte';
	import { Button, Badge } from '$lib/components/ui';
	import AdminPageHeader from '$lib/components/admin/AdminPageHeader.svelte';
	import EmptyState from '$lib/components/ui/EmptyState.svelte';
	import { RefreshCw, ThumbsUp, ThumbsDown, TrendingUp, Users, Calendar, ExternalLink } from 'lucide-svelte';
	import { apiClient } from '$lib/api/client';
	import type { RatingMetricsResponse, RatingTrendItem, NegativeRatingItem } from '$lib/api/types';

	// State
	let metrics = $state<RatingMetricsResponse | null>(null);
	let trend = $state<RatingTrendItem[]>([]);
	let negativeRatings = $state<NegativeRatingItem[]>([]);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let metricsDays = $state(30);
	let trendDays = $state(7);

	// Load data
	async function loadData() {
		isLoading = true;
		error = null;
		try {
			const [metricsData, trendData, negativeData] = await Promise.all([
				apiClient.getRatingMetrics(metricsDays),
				apiClient.getRatingTrend(trendDays),
				apiClient.getNegativeRatings(10)
			]);
			metrics = metricsData;
			trend = trendData;
			negativeRatings = negativeData.items;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load rating data';
		} finally {
			isLoading = false;
		}
	}

	// Format date
	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: '2-digit',
			minute: '2-digit'
		});
	}

	// Format short date for trend
	function formatShortDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
	}

	// Get entity link
	function getEntityLink(item: NegativeRatingItem): string {
		if (item.entity_type === 'meeting') {
			return `/meeting/${item.entity_id}`;
		}
		return `/actions/${item.entity_id}`;
	}

	onMount(() => {
		loadData();
	});

	// Reload when period changes
	$effect(() => {
		if (!isLoading) {
			void metricsDays;
			void trendDays;
			loadData();
		}
	});
</script>

<svelte:head>
	<title>User Ratings - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<AdminPageHeader title="User Ratings">
		{#snippet actions()}
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
			<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-4 mb-6">
				<p class="text-error-800 dark:text-error-200">{error}</p>
				<Button variant="secondary" size="sm" onclick={loadData} class="mt-2">
					{#snippet children()}Retry{/snippet}
				</Button>
			</div>
		{/if}

		<!-- Loading State -->
		{#if isLoading}
			<div class="space-y-6">
				<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
					{#each [1, 2, 3, 4] as _}
						<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 animate-pulse">
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2 mb-2"></div>
							<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-2/3"></div>
						</div>
					{/each}
				</div>
			</div>
		{:else if metrics}
			<!-- Metrics Cards -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<Users class="w-5 h-5 text-neutral-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Total Ratings</span>
					</div>
					<div class="text-2xl font-bold text-neutral-900 dark:text-white">{metrics.total}</div>
					<div class="text-xs text-neutral-400 mt-1">Last {metrics.period_days} days</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<TrendingUp class="w-5 h-5 text-success-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Satisfaction</span>
					</div>
					<div class="text-2xl font-bold text-success-600 dark:text-success-400">{metrics.thumbs_up_pct}%</div>
					<div class="text-xs text-neutral-400 mt-1">{metrics.thumbs_up} positive</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<ThumbsUp class="w-5 h-5 text-success-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Thumbs Up</span>
					</div>
					<div class="text-2xl font-bold text-success-600 dark:text-success-400">{metrics.thumbs_up}</div>
					<div class="text-xs text-neutral-400 mt-1">
						Meetings: {metrics.by_type.meeting.up} | Actions: {metrics.by_type.action.up}
					</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<ThumbsDown class="w-5 h-5 text-error-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Thumbs Down</span>
					</div>
					<div class="text-2xl font-bold text-error-600 dark:text-error-400">{metrics.thumbs_down}</div>
					<div class="text-xs text-neutral-400 mt-1">
						Meetings: {metrics.by_type.meeting.down} | Actions: {metrics.by_type.action.down}
					</div>
				</div>
			</div>

			<!-- Trend Chart (Simple) -->
			{#if trend.length > 0}
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6 mb-8">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4">
						Daily Trend (Last {trendDays} Days)
					</h2>
					<div class="flex items-end gap-2 h-32">
						{#each trend as day}
							{@const maxHeight = 100}
							{@const maxTotal = Math.max(...trend.map(t => t.total))}
							{@const upHeight = maxTotal > 0 ? (day.up / maxTotal) * maxHeight : 0}
							{@const downHeight = maxTotal > 0 ? (day.down / maxTotal) * maxHeight : 0}
							<div class="flex-1 flex flex-col items-center gap-1">
								<div class="w-full flex flex-col items-center">
									<div
										class="w-full max-w-8 bg-success-500 rounded-t"
										style="height: {upHeight}px"
										title="{day.up} thumbs up"
									></div>
									<div
										class="w-full max-w-8 bg-error-500 rounded-b"
										style="height: {downHeight}px"
										title="{day.down} thumbs down"
									></div>
								</div>
								<span class="text-xs text-neutral-500 dark:text-neutral-400 transform -rotate-45 origin-center whitespace-nowrap">
									{formatShortDate(day.date)}
								</span>
							</div>
						{/each}
					</div>
					<div class="flex items-center justify-center gap-6 mt-4 text-sm">
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 bg-success-500 rounded"></div>
							<span class="text-neutral-600 dark:text-neutral-400">Thumbs Up</span>
						</div>
						<div class="flex items-center gap-2">
							<div class="w-3 h-3 bg-error-500 rounded"></div>
							<span class="text-neutral-600 dark:text-neutral-400">Thumbs Down</span>
						</div>
					</div>
				</div>
			{/if}

			<!-- Recent Negative Ratings -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
				<div class="px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">
						Recent Negative Ratings
					</h2>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">
						Latest thumbs-down ratings for triage
					</p>
				</div>

				{#if negativeRatings.length === 0}
					<EmptyState
						title="No negative ratings"
						description="All recent feedback has been positive!"
						icon={ThumbsUp}
					/>
				{:else}
					<div class="divide-y divide-neutral-200 dark:divide-neutral-700">
						{#each negativeRatings as item}
							<div class="px-6 py-4 hover:bg-neutral-50 dark:hover:bg-neutral-700/50 transition-colors">
								<div class="flex items-start justify-between gap-4">
									<div class="flex-1 min-w-0">
										<div class="flex items-center gap-2 mb-1">
											<Badge variant={item.entity_type === 'meeting' ? 'info' : 'warning'}>
												{item.entity_type}
											</Badge>
											{#if item.entity_title}
												<span class="text-sm font-medium text-neutral-900 dark:text-white truncate">
													{item.entity_title}
												</span>
											{:else}
												<span class="text-sm text-neutral-500 dark:text-neutral-400 font-mono">
													{item.entity_id.slice(0, 8)}...
												</span>
											{/if}
										</div>
										{#if item.comment}
											<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-2">
												"{item.comment}"
											</p>
										{/if}
										<div class="flex items-center gap-4 text-xs text-neutral-500 dark:text-neutral-500">
											<span class="flex items-center gap-1">
												<Calendar class="w-3 h-3" />
												{formatDate(item.created_at)}
											</span>
											{#if item.user_email}
												<span>{item.user_email}</span>
											{/if}
										</div>
									</div>
									<a
										href={getEntityLink(item)}
										class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors"
										title="View {item.entity_type}"
									>
										<ExternalLink class="w-4 h-4 text-neutral-500" />
									</a>
								</div>
							</div>
						{/each}
					</div>
				{/if}
			</div>
		{/if}
	</main>
</div>
