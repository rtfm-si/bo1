<script lang="ts">
	/**
	 * Industry Benchmarks Tab - Compare your metrics against industry standards
	 * Extracted from /reports/benchmarks for use in tabbed interface
	 *
	 * Features:
	 * - Tier-based limits (Free: 3, Starter: 5, Pro: unlimited)
	 * - Percentile ranking visualization
	 * - Category filtering (growth, retention, efficiency, engagement)
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type {
		IndustryInsight,
		BenchmarkComparison,
		BenchmarkCategory
	} from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';
	import BenchmarkRangeBar from '$lib/components/benchmarks/BenchmarkRangeBar.svelte';
	import BenchmarkHistory from '$lib/components/benchmarks/BenchmarkHistory.svelte';
	import BenchmarkRefreshBanner from '$lib/components/benchmarks/BenchmarkRefreshBanner.svelte';

	// State
	let isLoading = $state(true);
	let insights = $state<IndustryInsight[]>([]);
	let comparisons = $state<BenchmarkComparison[]>([]);
	let industry = $state('');
	let tier = $state('free');
	let lockedCount = $state(0);
	let upgradePrompt = $state<string | null>(null);
	let error = $state<string | null>(null);

	// Filter state
	let selectedCategory = $state<BenchmarkCategory | 'all'>('all');
	let showComparison = $state(true);

	const categories: { value: BenchmarkCategory | 'all'; label: string; icon: string }[] = [
		{ value: 'all', label: 'All Categories', icon: '📊' },
		{ value: 'growth', label: 'Growth', icon: '📈' },
		{ value: 'retention', label: 'Retention', icon: '🔄' },
		{ value: 'efficiency', label: 'Efficiency', icon: '⚡' },
		{ value: 'engagement', label: 'Engagement', icon: '👥' }
	];

	onMount(async () => {
		await loadData();
	});

	async function loadData() {
		isLoading = true;
		error = null;

		try {
			// Load insights and comparison in parallel
			const [insightsRes, comparisonRes] = await Promise.all([
				apiClient.getIndustryBenchmarks({ insightType: 'benchmark' }),
				apiClient.compareBenchmarks()
			]);

			industry = insightsRes.industry;
			insights = insightsRes.insights ?? [];
			tier = insightsRes.user_tier;
			lockedCount = insightsRes.locked_count;
			upgradePrompt = insightsRes.upgrade_prompt || null;
			comparisons = comparisonRes.comparisons ?? [];
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to load benchmarks';
		} finally {
			isLoading = false;
		}
	}

	// Filter benchmarks by category
	let filteredInsights = $derived(
		selectedCategory === 'all'
			? insights
			: insights.filter((i) => {
					const content = i.content as { category?: string };
					return content.category === selectedCategory;
				})
	);

	// Get comparison data for a benchmark
	function getComparison(metricName: string): BenchmarkComparison | undefined {
		return comparisons.find((c) => c.metric_name === metricName);
	}

	// Get status color
	function getStatusColor(status: string): string {
		switch (status) {
			case 'top_performer':
				return 'text-green-600 dark:text-green-400 bg-green-100 dark:bg-green-900/30';
			case 'above_average':
				return 'text-emerald-600 dark:text-emerald-400 bg-emerald-100 dark:bg-emerald-900/30';
			case 'average':
				return 'text-yellow-600 dark:text-yellow-400 bg-yellow-100 dark:bg-yellow-900/30';
			case 'below_average':
				return 'text-red-600 dark:text-red-400 bg-red-100 dark:bg-red-900/30';
			case 'locked':
				return 'text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700';
			default:
				return 'text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700';
		}
	}

	// Get status label (human-friendly)
	function getStatusLabel(status: string): string {
		switch (status) {
			case 'top_performer':
				return 'Excellent';
			case 'above_average':
				return 'Good';
			case 'average':
				return 'Typical';
			case 'below_average':
				return 'Needs Attention';
			case 'locked':
				return 'Upgrade to View';
			default:
				return 'No Data';
		}
	}

	// Get category badge color
	function getCategoryColor(category: string): string {
		switch (category) {
			case 'growth':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			case 'retention':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
			case 'efficiency':
				return 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400';
			case 'engagement':
				return 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400';
			default:
				return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
		}
	}

	// Get tier badge color
	function getTierBadgeColor(t: string): string {
		switch (t) {
			case 'pro':
			case 'enterprise':
				return 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400';
			case 'starter':
				return 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400';
			default:
				return 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300';
		}
	}

	// Format relative time (e.g., "3 days ago", "2 months ago")
	function formatRelativeTime(isoTimestamp: string | undefined): string | null {
		if (!isoTimestamp) return null;
		try {
			const date = new Date(isoTimestamp);
			const now = new Date();
			const diffMs = now.getTime() - date.getTime();
			const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

			if (diffDays < 1) return 'today';
			if (diffDays === 1) return '1 day ago';
			if (diffDays < 7) return `${diffDays} days ago`;
			if (diffDays < 14) return '1 week ago';
			if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
			if (diffDays < 60) return '1 month ago';
			if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
			return `${Math.floor(diffDays / 365)} year${Math.floor(diffDays / 365) > 1 ? 's' : ''} ago`;
		} catch {
			return null;
		}
	}
</script>

<div class="space-y-6">
{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<div
			class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"
		></div>
	</div>
{:else}
	<!-- Monthly Check-in Banner -->
	<BenchmarkRefreshBanner />

	<!-- Header -->
	<div
		class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6"
	>
		<div class="flex items-center justify-between mb-4">
			<div class="flex items-center gap-3">
				<span class="text-2xl">📊</span>
				<div>
					<h2 class="text-lg font-semibold text-slate-900 dark:text-white">
						Industry Benchmarks
					</h2>
					<p class="text-sm text-slate-600 dark:text-slate-400">
						Compare your metrics against {industry || 'your industry'} standards
					</p>
				</div>
			</div>
			<div class="flex items-center gap-3">
				<span class={`text-xs px-2 py-1 rounded-full font-medium ${getTierBadgeColor(tier)}`}>
					{tier.charAt(0).toUpperCase() + tier.slice(1)} Plan
				</span>
				{#if lockedCount > 0}
					<span class="text-sm text-slate-500 dark:text-slate-400">
						{insights.length - lockedCount}/{insights.length} unlocked
					</span>
				{/if}
			</div>
		</div>

		<!-- Tier limits info -->
		<div
			class="flex items-center gap-2 text-sm text-slate-600 dark:text-slate-400 bg-slate-50 dark:bg-slate-700/50 rounded-lg px-3 py-2"
		>
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path
					stroke-linecap="round"
					stroke-linejoin="round"
					stroke-width="2"
					d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
				/>
			</svg>
			<span>
				{#if tier === 'free'}
					Free plan includes <strong>3 benchmark metrics</strong>.
					<a href="/settings/billing" class="text-brand-600 dark:text-brand-400 hover:underline">
						Upgrade to Starter
					</a> for 5, or Pro for unlimited.
				{:else if tier === 'starter'}
					Starter plan includes <strong>5 benchmark metrics</strong>.
					<a href="/settings/billing" class="text-brand-600 dark:text-brand-400 hover:underline">
						Upgrade to Pro
					</a> for unlimited access.
				{:else}
					You have <strong>unlimited access</strong> to all benchmark metrics.
				{/if}
			</span>
		</div>
	</div>

	<!-- Alerts -->
	{#if error}
		<Alert variant="error">{error}</Alert>
	{/if}

	{#if upgradePrompt && lockedCount > 0}
		<Alert variant="info">{upgradePrompt}</Alert>
	{/if}

	<!-- Category filters -->
	<div class="flex flex-wrap gap-2">
		{#each categories as cat}
			<button
				type="button"
				onclick={() => (selectedCategory = cat.value)}
				class="px-3 py-1.5 rounded-full text-sm font-medium transition-colors {selectedCategory ===
				cat.value
					? 'bg-brand-600 text-white'
					: 'bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-600'}"
			>
				{cat.icon} {cat.label}
			</button>
		{/each}
	</div>

	<!-- Toggle view -->
	<div class="flex items-center gap-4">
		<label class="flex items-center gap-2 cursor-pointer">
			<input type="checkbox" bind:checked={showComparison} class="rounded border-slate-300" />
			<span class="text-sm text-slate-600 dark:text-slate-400">Show my metrics comparison</span>
		</label>
	</div>

	<!-- Benchmarks grid -->
	{#if filteredInsights.length > 0}
		<div class="grid gap-4 md:grid-cols-2">
			{#each filteredInsights as benchmark (benchmark.id)}
				{@const content = benchmark.content as {
					title?: string;
					description?: string;
					metric_name?: string;
					metric_unit?: string;
					category?: string;
					p25?: number;
					p50?: number;
					p75?: number;
					sample_size?: number;
				}}
				{@const comparison = getComparison(content.metric_name || '')}
				<div
					class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 {benchmark.locked
						? 'opacity-75'
						: ''}"
				>
					<!-- Header -->
					<div class="flex items-start justify-between mb-3">
						<div>
							<h3 class="font-semibold text-slate-900 dark:text-white">
								{content.title || content.metric_name}
							</h3>
							<p class="text-sm text-slate-500 dark:text-slate-400">{content.description}</p>
						</div>
						{#if content.category}
							<span
								class={`text-xs px-2 py-1 rounded-full font-medium ${getCategoryColor(content.category)}`}
							>
								{content.category}
							</span>
						{/if}
					</div>

					{#if benchmark.locked}
						<!-- Locked state -->
						<div
							class="bg-slate-50 dark:bg-slate-700/50 rounded-lg p-4 flex items-center justify-center gap-2"
						>
							<svg class="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path
									stroke-linecap="round"
									stroke-linejoin="round"
									stroke-width="2"
									d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"
								/>
							</svg>
							<span class="text-sm text-slate-500 dark:text-slate-400">
								<a
									href="/settings/billing"
									class="text-brand-600 dark:text-brand-400 hover:underline"
								>
									Upgrade to unlock
								</a>
							</span>
						</div>
					{:else}
						<!-- 2-column layout: Industry vs You -->
						<div class="grid grid-cols-1 md:grid-cols-2 gap-4 md:gap-6">
							<!-- Left column: Industry Range -->
							<div class="space-y-2">
								<div class="flex items-center gap-2 mb-3">
									<span class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400">Industry</span>
									{#if content.sample_size}
										<span class="text-xs text-slate-400">(n={content.sample_size})</span>
									{/if}
								</div>
								<BenchmarkRangeBar
									rangeMin={content.p25 ?? 0}
									rangeMedian={content.p50 ?? 0}
									rangeMax={content.p75 ?? 0}
									unit={content.metric_unit}
								/>
							</div>

							<!-- Right column: Your Value -->
							<div class="space-y-2 md:border-l md:border-slate-200 md:dark:border-slate-700 md:pl-6">
								<div class="text-xs font-semibold uppercase tracking-wide text-slate-500 dark:text-slate-400 mb-3">You</div>
								{#if showComparison && comparison}
									{#if comparison.user_value !== null && comparison.user_value !== undefined}
										<!-- User has a value set -->
										<div class="flex flex-col items-center justify-center py-2">
											<div class="text-3xl font-bold text-slate-900 dark:text-white">
												{comparison.user_value}{content.metric_unit === '%' ? '%' : ''}{content.metric_unit && content.metric_unit !== '%' ? ` ${content.metric_unit}` : ''}
											</div>
											<div class="mt-2 flex items-center gap-2">
												<span
													class={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(comparison.status)}`}
												>
													{getStatusLabel(comparison.status)}
												</span>
											</div>
											{#if comparison.user_value_updated_at}
												{@const relativeTime = formatRelativeTime(comparison.user_value_updated_at)}
												{#if relativeTime}
													<span class="text-xs text-slate-400 mt-2" title="When you last updated this value">
														Updated {relativeTime}
													</span>
												{/if}
											{/if}
											<!-- Historical values -->
											{#if comparison.history && comparison.history.length > 0}
												<div class="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
													<div class="text-xs text-slate-400 dark:text-slate-500 mb-1">History</div>
													<BenchmarkHistory
														history={comparison.history}
														unit={content.metric_unit}
													/>
												</div>
											{/if}
										</div>
									{:else}
										<!-- User hasn't set a value - prominent empty state -->
										<div class="flex flex-col items-center justify-center py-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
											<div class="text-3xl font-bold text-slate-300 dark:text-slate-600 mb-2">—</div>
											<span class="text-sm text-slate-500 dark:text-slate-400 mb-3">Not Set</span>
											<a
												href="/context/metrics#{content.category || 'metrics'}"
												class="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium text-white bg-brand-600 hover:bg-brand-700 rounded-md transition-colors"
											>
												<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
													<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
												</svg>
												Set My Value
											</a>
										</div>
									{/if}
								{:else}
									<!-- Comparison toggle is off -->
									<div class="flex flex-col items-center justify-center py-4 text-slate-400 dark:text-slate-500">
										<span class="text-sm">Enable comparison above</span>
									</div>
								{/if}
							</div>
						</div>
					{/if}
				</div>
			{/each}
		</div>
	{:else}
		<!-- Empty state -->
		<div
			class="bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center"
		>
			<div class="text-4xl mb-4">📊</div>
			<h3 class="text-lg font-semibold text-slate-900 dark:text-white mb-2">
				No benchmarks available
			</h3>
			<p class="text-slate-600 dark:text-slate-400 mb-4">
				{#if industry === 'Unknown'}
					Set your industry in
					<a
						href="/context"
						class="text-brand-600 dark:text-brand-400 hover:underline"
					>
						Business Context
					</a>
					to see relevant benchmarks.
				{:else}
					No benchmarks found for {selectedCategory === 'all' ? 'this industry' : `the ${selectedCategory} category`}.
				{/if}
			</p>
		</div>
	{/if}

	<!-- Info Box -->
	<div
		class="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4"
	>
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
				<p class="font-semibold mb-1">How to Read This</p>
				<ul class="text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
					<li><strong>Industry</strong> shows the range of values across businesses in your sector</li>
					<li><strong>You</strong> shows your current value and how you compare</li>
					<li><strong>Bottom 25%</strong> &mdash; lowest performers &bull; <strong>Typical</strong> &mdash; industry midpoint &bull; <strong>Top 25%</strong> &mdash; best performers</li>
					<li>
						Add your metrics in
						<a
							href="/context/metrics"
							class="text-blue-700 dark:text-blue-400 hover:underline"
						>
							Context &rarr; Metrics
						</a>
						to see where you stand
					</li>
				</ul>
			</div>
		</div>
	</div>
{/if}
</div>
