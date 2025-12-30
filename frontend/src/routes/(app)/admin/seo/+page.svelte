<script lang="ts">
	/**
	 * Admin SEO Analytics Page
	 *
	 * Displays global SEO content performance metrics:
	 * - Summary stats (views, clicks, signups, CTR, signup rate)
	 * - Time-based metrics (today, week, month)
	 * - Top articles by views
	 * - Top articles by conversion rate
	 * - Blog post CTR & cost performance
	 */
	import { onMount } from 'svelte';
	import { Button } from '$lib/components/ui';
	import { RefreshCw, Eye, MousePointer, UserPlus, TrendingUp, BarChart3, PoundSterling, ExternalLink } from 'lucide-svelte';
	import {
		adminApi,
		type AdminSeoAnalyticsResponse,
		type SeoTopArticle,
		type BlogPerformanceResponse
	} from '$lib/api/admin';

	// State
	let analytics = $state<AdminSeoAnalyticsResponse | null>(null);
	let blogPerf = $state<BlogPerformanceResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);
	let sortBy = $state<'views' | 'ctr' | 'cost_per_click' | 'roi'>('views');

	// Load data
	async function loadData() {
		isLoading = true;
		error = null;
		try {
			const [analyticsData, perfData] = await Promise.all([
				adminApi.getSeoAnalytics(10),
				adminApi.getBlogPerformance(50, sortBy)
			]);
			analytics = analyticsData;
			blogPerf = perfData;
		} catch (err) {
			error = err instanceof Error ? err.message : 'Failed to load SEO analytics';
		} finally {
			isLoading = false;
		}
	}

	// Load just blog performance (for sort changes)
	async function loadBlogPerf() {
		try {
			blogPerf = await adminApi.getBlogPerformance(50, sortBy);
		} catch {
			// Silent fail for sort changes
		}
	}

	// Format percentage
	function formatPercent(value: number): string {
		return (value * 100).toFixed(2) + '%';
	}

	// Format number with commas
	function formatNumber(value: number): string {
		return value.toLocaleString();
	}

	// Format currency
	function formatCurrency(value: number): string {
		return '£' + value.toFixed(4);
	}

	// Handle sort change
	function handleSortChange(newSort: 'views' | 'ctr' | 'cost_per_click' | 'roi') {
		sortBy = newSort;
		loadBlogPerf();
	}

	onMount(() => {
		loadData();
	});
</script>

<svelte:head>
	<title>SEO Analytics - Admin - Board of One</title>
</svelte:head>

<div class="min-h-screen bg-neutral-50 dark:bg-neutral-900">
	<!-- Header -->
	<header class="bg-white dark:bg-neutral-800 border-b border-neutral-200 dark:border-neutral-700">
		<div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
			<div class="flex items-center justify-between">
				<div class="flex items-center gap-4">
					<a
						href="/admin"
						class="p-2 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded-lg transition-colors duration-200"
						aria-label="Back to admin dashboard"
					>
						<svg class="w-5 h-5 text-neutral-600 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 19l-7-7m0 0l7-7m-7 7h18" />
						</svg>
					</a>
					<div>
						<h1 class="text-2xl font-semibold text-neutral-900 dark:text-white">
							SEO Content Analytics
						</h1>
						<p class="text-sm text-neutral-500 dark:text-neutral-400">
							Track blog article performance and conversions
						</p>
					</div>
				</div>
				<Button variant="secondary" size="sm" onclick={loadData} disabled={isLoading}>
					{#snippet children()}
						<RefreshCw class="w-4 h-4 {isLoading ? 'animate-spin' : ''}" />
						Refresh
					{/snippet}
				</Button>
			</div>
		</div>
	</header>

	<!-- Main Content -->
	<main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
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
							<div class="h-8 bg-neutral-200 dark:bg-neutral-700 rounded w-16 mb-2"></div>
							<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-24"></div>
						</div>
					{/each}
				</div>
			</div>
		{:else if analytics}
			<!-- Summary Cards -->
			<div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<BarChart3 class="w-5 h-5 text-neutral-400" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Total Articles</span>
					</div>
					<div class="text-2xl font-bold text-neutral-900 dark:text-white">
						{formatNumber(analytics.summary.total_articles)}
					</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<Eye class="w-5 h-5 text-blue-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Total Views</span>
					</div>
					<div class="text-2xl font-bold text-neutral-900 dark:text-white">
						{formatNumber(analytics.summary.total_views)}
					</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<MousePointer class="w-5 h-5 text-amber-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Total Clicks</span>
					</div>
					<div class="text-2xl font-bold text-neutral-900 dark:text-white">
						{formatNumber(analytics.summary.total_clicks)}
					</div>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">
						CTR: {formatPercent(analytics.summary.overall_ctr)}
					</div>
				</div>

				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
					<div class="flex items-center gap-2 mb-2">
						<UserPlus class="w-5 h-5 text-success-500" />
						<span class="text-sm text-neutral-500 dark:text-neutral-400">Total Signups</span>
					</div>
					<div class="text-2xl font-bold text-neutral-900 dark:text-white">
						{formatNumber(analytics.summary.total_signups)}
					</div>
					<div class="text-sm text-neutral-500 dark:text-neutral-400">
						Rate: {formatPercent(analytics.summary.overall_signup_rate)}
					</div>
				</div>
			</div>

			<!-- Time-based Stats -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4 mb-8">
				<h2 class="text-lg font-medium text-neutral-900 dark:text-white mb-4">Views Over Time</h2>
				<div class="grid grid-cols-3 gap-4">
					<div class="text-center">
						<div class="text-3xl font-bold text-neutral-900 dark:text-white">
							{formatNumber(analytics.summary.views_today)}
						</div>
						<div class="text-sm text-neutral-500 dark:text-neutral-400">Today</div>
					</div>
					<div class="text-center">
						<div class="text-3xl font-bold text-neutral-900 dark:text-white">
							{formatNumber(analytics.summary.views_this_week)}
						</div>
						<div class="text-sm text-neutral-500 dark:text-neutral-400">This Week</div>
					</div>
					<div class="text-center">
						<div class="text-3xl font-bold text-neutral-900 dark:text-white">
							{formatNumber(analytics.summary.views_this_month)}
						</div>
						<div class="text-sm text-neutral-500 dark:text-neutral-400">This Month</div>
					</div>
				</div>
			</div>

			<!-- Top Articles Tables -->
			<div class="grid md:grid-cols-2 gap-6">
				<!-- Top by Views -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-medium text-neutral-900 dark:text-white flex items-center gap-2">
							<Eye class="w-5 h-5 text-blue-500" />
							Top Articles by Views
						</h2>
					</div>
					<div class="overflow-x-auto">
						{#if analytics.top_by_views.length === 0}
							<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
								No article data yet
							</div>
						{:else}
							<table class="w-full">
								<thead class="bg-neutral-50 dark:bg-neutral-900">
									<tr>
										<th class="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Article</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Views</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">CTR</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
									{#each analytics.top_by_views as article}
										<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
											<td class="px-4 py-3">
												<div class="font-medium text-neutral-900 dark:text-white truncate max-w-xs">
													{article.title}
												</div>
												{#if article.user_email}
													<div class="text-xs text-neutral-500 dark:text-neutral-400">
														{article.user_email}
													</div>
												{/if}
											</td>
											<td class="px-4 py-3 text-right text-neutral-900 dark:text-white">
												{formatNumber(article.views)}
											</td>
											<td class="px-4 py-3 text-right text-neutral-500 dark:text-neutral-400">
												{formatPercent(article.ctr)}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						{/if}
					</div>
				</div>

				<!-- Top by Conversion -->
				<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
						<h2 class="text-lg font-medium text-neutral-900 dark:text-white flex items-center gap-2">
							<TrendingUp class="w-5 h-5 text-success-500" />
							Top Articles by Conversion
						</h2>
						<p class="text-xs text-neutral-500 dark:text-neutral-400">Min 10 views required</p>
					</div>
					<div class="overflow-x-auto">
						{#if analytics.top_by_conversion.length === 0}
							<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
								No articles with 10+ views yet
							</div>
						{:else}
							<table class="w-full">
								<thead class="bg-neutral-50 dark:bg-neutral-900">
									<tr>
										<th class="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Article</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Signups</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Rate</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
									{#each analytics.top_by_conversion as article}
										<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
											<td class="px-4 py-3">
												<div class="font-medium text-neutral-900 dark:text-white truncate max-w-xs">
													{article.title}
												</div>
												{#if article.user_email}
													<div class="text-xs text-neutral-500 dark:text-neutral-400">
														{article.user_email}
													</div>
												{/if}
											</td>
											<td class="px-4 py-3 text-right text-neutral-900 dark:text-white">
												{formatNumber(article.signups)}
											</td>
											<td class="px-4 py-3 text-right">
												<span class="text-success-600 dark:text-success-400 font-medium">
													{formatPercent(article.signup_rate)}
												</span>
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						{/if}
					</div>
				</div>
			</div>

			<!-- Blog Post Performance with Cost ROI -->
			{#if blogPerf}
				<div class="mt-8 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
					<div class="px-4 py-3 border-b border-neutral-200 dark:border-neutral-700">
						<div class="flex items-center justify-between">
							<div>
								<h2 class="text-lg font-medium text-neutral-900 dark:text-white flex items-center gap-2">
									<PoundSterling class="w-5 h-5 text-brand-500" />
									Blog Post ROI Performance
								</h2>
								<p class="text-xs text-neutral-500 dark:text-neutral-400">
									CTR and cost metrics for published blog posts
								</p>
							</div>
							<div class="flex items-center gap-2">
								<span class="text-xs text-neutral-500">Sort:</span>
								<select
									class="text-sm border border-neutral-300 dark:border-neutral-600 rounded px-2 py-1 bg-white dark:bg-neutral-700 text-neutral-900 dark:text-white"
									value={sortBy}
									onchange={(e) => handleSortChange(e.currentTarget.value as 'views' | 'ctr' | 'cost_per_click' | 'roi')}
								>
									<option value="views">Views</option>
									<option value="ctr">CTR</option>
									<option value="roi">Best ROI</option>
								</select>
							</div>
						</div>

						<!-- Summary Stats -->
						<div class="mt-4 grid grid-cols-4 gap-4 text-center">
							<div>
								<div class="text-xl font-bold text-neutral-900 dark:text-white">
									{formatNumber(blogPerf.total_views)}
								</div>
								<div class="text-xs text-neutral-500">Total Views</div>
							</div>
							<div>
								<div class="text-xl font-bold text-neutral-900 dark:text-white">
									{formatNumber(blogPerf.total_clicks)}
								</div>
								<div class="text-xs text-neutral-500">Total Clicks</div>
							</div>
							<div>
								<div class="text-xl font-bold text-brand-600 dark:text-brand-400">
									{blogPerf.overall_ctr.toFixed(2)}%
								</div>
								<div class="text-xs text-neutral-500">Overall CTR</div>
							</div>
							<div>
								<div class="text-xl font-bold text-neutral-900 dark:text-white">
									£{blogPerf.total_cost.toFixed(2)}
								</div>
								<div class="text-xs text-neutral-500">Total Cost</div>
							</div>
						</div>
					</div>

					<div class="overflow-x-auto">
						{#if blogPerf.posts.length === 0}
							<div class="p-8 text-center text-neutral-500 dark:text-neutral-400">
								No published blog posts yet
							</div>
						{:else}
							<table class="w-full">
								<thead class="bg-neutral-50 dark:bg-neutral-900">
									<tr>
										<th class="px-4 py-2 text-left text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Post</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Views</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Clicks</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">CTR</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">Cost</th>
										<th class="px-4 py-2 text-right text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase">£/Click</th>
									</tr>
								</thead>
								<tbody class="divide-y divide-neutral-200 dark:divide-neutral-700">
									{#each blogPerf.posts as post}
										<tr class="hover:bg-neutral-50 dark:hover:bg-neutral-900/50">
											<td class="px-4 py-3">
												<a
													href="/blog/{post.slug}"
													target="_blank"
													class="font-medium text-neutral-900 dark:text-white hover:text-brand-600 dark:hover:text-brand-400 flex items-center gap-1 truncate max-w-xs"
												>
													{post.title}
													<ExternalLink class="w-3 h-3 flex-shrink-0" />
												</a>
												{#if post.last_viewed_at}
													<div class="text-xs text-neutral-500 dark:text-neutral-400">
														Last view: {new Date(post.last_viewed_at).toLocaleDateString()}
													</div>
												{/if}
											</td>
											<td class="px-4 py-3 text-right text-neutral-900 dark:text-white">
												{formatNumber(post.view_count)}
											</td>
											<td class="px-4 py-3 text-right text-neutral-900 dark:text-white">
												{formatNumber(post.click_through_count)}
											</td>
											<td class="px-4 py-3 text-right">
												<span class="{post.ctr_percent >= 5 ? 'text-success-600 dark:text-success-400' : post.ctr_percent >= 2 ? 'text-amber-600 dark:text-amber-400' : 'text-neutral-500'} font-medium">
													{post.ctr_percent.toFixed(2)}%
												</span>
											</td>
											<td class="px-4 py-3 text-right text-neutral-500 dark:text-neutral-400">
												£{post.generation_cost.toFixed(2)}
											</td>
											<td class="px-4 py-3 text-right">
												{#if post.click_through_count > 0}
													<span class="{post.cost_per_click <= 0.10 ? 'text-success-600 dark:text-success-400' : post.cost_per_click <= 0.50 ? 'text-amber-600 dark:text-amber-400' : 'text-error-600 dark:text-error-400'} font-medium">
														£{post.cost_per_click.toFixed(4)}
													</span>
												{:else}
													<span class="text-neutral-400">-</span>
												{/if}
											</td>
										</tr>
									{/each}
								</tbody>
							</table>
						{/if}
					</div>
				</div>
			{/if}
		{:else}
			<!-- Empty State -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-12 text-center">
				<div class="mx-auto w-12 h-12 bg-neutral-100 dark:bg-neutral-700 rounded-full flex items-center justify-center mb-4">
					<BarChart3 class="w-6 h-6 text-neutral-400" />
				</div>
				<h3 class="text-lg font-medium text-neutral-900 dark:text-white mb-2">
					No analytics data
				</h3>
				<p class="text-neutral-600 dark:text-neutral-400">
					Analytics data will appear once articles start receiving views.
				</p>
			</div>
		{/if}
	</main>
</div>
