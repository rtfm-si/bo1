<script lang="ts">
	/**
	 * Industry Benchmarks - Compare your metrics against industry standards
	 *
	 * Features:
	 * - Tier-based limits (Free: 3, Starter: 5, Pro: unlimited)
	 * - Percentile ranking visualization
	 * - Category filtering (growth, retention, efficiency, engagement)
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type {
		IndustryInsightsResponse,
		IndustryInsight,
		BenchmarkComparisonResponse,
		BenchmarkComparison,
		BenchmarkCategory
	} from '$lib/api/types';
	import Alert from '$lib/components/ui/Alert.svelte';

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
			insights = insightsRes.insights;
			tier = insightsRes.user_tier;
			lockedCount = insightsRes.locked_count;
			upgradePrompt = insightsRes.upgrade_prompt || null;
			comparisons = comparisonRes.comparisons;
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

	// Format percentile display
	function formatPercentile(percentile: number | undefined): string {
		if (percentile === undefined) return 'N/A';
		return `${Math.round(percentile)}th`;
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

	// Get status label
	function getStatusLabel(status: string): string {
		switch (status) {
			case 'top_performer':
				return 'Top Performer';
			case 'above_average':
				return 'Above Average';
			case 'average':
				return 'Average';
			case 'below_average':
				return 'Below Average';
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

	// Calculate progress bar width for percentile visualization
	function getPercentileBarWidth(percentile: number | undefined): string {
		if (percentile === undefined) return '0%';
		return `${Math.min(100, Math.max(0, percentile))}%`;
	}
</script>

<svelte:head>
	<title>Industry Benchmarks - Board of One</title>
</svelte:head>

{#if isLoading}
	<div class="flex items-center justify-center py-12">
		<div
			class="animate-spin h-8 w-8 border-4 border-brand-600 border-t-transparent rounded-full"
		></div>
	</div>
{:else}
	<div class="space-y-6">
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
							<!-- Percentile visualization -->
							<div class="space-y-3">
								<!-- Benchmark values -->
								<div class="flex items-center justify-between text-sm">
									<div class="flex gap-4">
										<div>
											<span class="text-slate-500 dark:text-slate-400">P25:</span>
											<span class="font-medium text-slate-700 dark:text-slate-200">
												{content.p25}{content.metric_unit === '%' ? '%' : ` ${content.metric_unit}`}
											</span>
										</div>
										<div>
											<span class="text-slate-500 dark:text-slate-400">Median:</span>
											<span class="font-medium text-slate-700 dark:text-slate-200">
												{content.p50}{content.metric_unit === '%' ? '%' : ` ${content.metric_unit}`}
											</span>
										</div>
										<div>
											<span class="text-slate-500 dark:text-slate-400">P75:</span>
											<span class="font-medium text-slate-700 dark:text-slate-200">
												{content.p75}{content.metric_unit === '%' ? '%' : ` ${content.metric_unit}`}
											</span>
										</div>
									</div>
									{#if content.sample_size}
										<span class="text-xs text-slate-400">n={content.sample_size}</span>
									{/if}
								</div>

								<!-- User comparison -->
								{#if showComparison && comparison}
									<div
										class="border-t border-slate-100 dark:border-slate-700 pt-3 mt-3 space-y-2"
									>
										<div class="flex items-center justify-between">
											<div class="flex items-center gap-2">
												<span class="text-sm text-slate-600 dark:text-slate-300">Your value:</span>
												{#if comparison.user_value !== undefined && comparison.user_value !== null}
													<span class="font-semibold text-slate-900 dark:text-white">
														{comparison.user_value}{content.metric_unit === '%'
															? '%'
															: ` ${content.metric_unit}`}
													</span>
												{:else}
													<span class="text-sm text-slate-400 italic">Not set</span>
												{/if}
											</div>
											<span
												class={`text-xs px-2 py-1 rounded-full font-medium ${getStatusColor(comparison.status)}`}
											>
												{getStatusLabel(comparison.status)}
											</span>
										</div>

										{#if comparison.percentile !== undefined && comparison.percentile !== null}
											<!-- Percentile bar -->
											<div class="space-y-1">
												<div class="flex items-center justify-between text-xs">
													<span class="text-slate-500 dark:text-slate-400">Your percentile</span>
													<span class="font-medium text-slate-700 dark:text-slate-200">
														{formatPercentile(comparison.percentile)} percentile
													</span>
												</div>
												<div
													class="h-2 bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden"
												>
													<div
														class="h-full rounded-full transition-all duration-500 {comparison.percentile >=
														75
															? 'bg-green-500'
															: comparison.percentile >= 50
																? 'bg-emerald-500'
																: comparison.percentile >= 25
																	? 'bg-yellow-500'
																	: 'bg-red-500'}"
														style="width: {getPercentileBarWidth(comparison.percentile)}"
													></div>
												</div>
												<!-- Percentile markers -->
												<div class="flex justify-between text-xs text-slate-400">
													<span>0</span>
													<span>25</span>
													<span>50</span>
													<span>75</span>
													<span>100</span>
												</div>
											</div>
										{/if}
									</div>
								{/if}
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
							href="/settings/context"
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
					<p class="font-semibold mb-1">About Industry Benchmarks</p>
					<ul class="text-blue-800 dark:text-blue-300 space-y-1 list-disc list-inside">
						<li>Benchmarks show P25, median (P50), and P75 for key metrics in your industry</li>
						<li>Your metrics are compared to show your percentile ranking</li>
						<li>
							Add your metrics in
							<a
								href="/settings/context/metrics"
								class="text-blue-700 dark:text-blue-400 hover:underline"
							>
								Context &rarr; Metrics
							</a>
							to see comparisons
						</li>
						<li>Benchmarks help our AI experts calibrate advice to industry standards</li>
					</ul>
				</div>
			</div>
		</div>
	</div>
{/if}
