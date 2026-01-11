<script lang="ts">
	/**
	 * InsightCard - Individual insight display with actions
	 *
	 * Displays a single insight from objective analysis with:
	 * - Objective tag (if linked)
	 * - Headline + narrative
	 * - Chart visualization (if present)
	 * - Recommendation callout
	 * - Action buttons with feedback
	 */
	import { fly, fade } from 'svelte/transition';
	import type { ObjectiveInsight } from '$lib/api/types';
	import ChartRenderer from '$lib/components/dataset/ChartRenderer.svelte';

	interface Props {
		insight: ObjectiveInsight;
		onAddToReport?: () => void;
		onCreateAction?: () => void;
		onExploreMore?: () => void;
		onShareWithBoard?: () => void;
	}

	let { insight, onAddToReport, onCreateAction, onExploreMore, onShareWithBoard }: Props = $props();

	// Action feedback states
	let addingToReport = $state(false);
	let creatingAction = $state(false);
	let addedToReport = $state(false);
	let actionCreated = $state(false);
	let sharingWithBoard = $state(false);
	let sharedWithBoard = $state(false);

	function getConfidenceColor(confidence: string): string {
		switch (confidence) {
			case 'high':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300';
			case 'medium':
				return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300';
			case 'low':
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
			default:
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
		}
	}

	function getPerformanceColor(performance: string): string {
		switch (performance) {
			case 'top_performer':
				return 'bg-success-100 text-success-700 dark:bg-success-900/30 dark:text-success-300';
			case 'above_average':
				return 'bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300';
			case 'average':
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
			case 'below_average':
				return 'bg-warning-100 text-warning-700 dark:bg-warning-900/30 dark:text-warning-300';
			default:
				return 'bg-neutral-100 text-neutral-600 dark:bg-neutral-700 dark:text-neutral-400';
		}
	}

	function formatPerformance(performance: string): string {
		switch (performance) {
			case 'top_performer':
				return 'Top Performer';
			case 'above_average':
				return 'Above Average';
			case 'average':
				return 'Average';
			case 'below_average':
				return 'Below Average';
			default:
				return performance;
		}
	}

	function formatNumber(value: number): string {
		if (value >= 1000000) {
			return `${(value / 1000000).toFixed(1)}M`;
		} else if (value >= 1000) {
			return `${(value / 1000).toFixed(1)}K`;
		}
		return value.toLocaleString();
	}

	// Calculate benchmark progress percentage for visual bar
	const benchmarkProgress = $derived.by(() => {
		if (!insight.benchmark_comparison) return null;
		const { your_value, industry_median, industry_top_quartile } = insight.benchmark_comparison;
		if (industry_median === null) return null;

		// Normalize to 0-100 where median is 50% and top quartile is 75%
		const topQ = industry_top_quartile ?? industry_median * 1.5;
		const range = topQ - (industry_median * 0.5);
		const normalized = ((your_value - (industry_median * 0.5)) / range) * 100;
		return Math.min(100, Math.max(0, normalized));
	});

	// Get figure_json from visualization for ChartRenderer
	const figureJson = $derived.by(() => {
		if (!insight.visualization?.figure_json) return null;
		return insight.visualization.figure_json as { data?: unknown[]; layout?: Record<string, unknown> };
	});

	async function handleAddToReport() {
		if (addingToReport || addedToReport) return;
		addingToReport = true;
		try {
			onAddToReport?.();
			addedToReport = true;
			// Reset after 2 seconds
			setTimeout(() => {
				addedToReport = false;
			}, 2000);
		} finally {
			addingToReport = false;
		}
	}

	async function handleCreateAction() {
		if (creatingAction || actionCreated) return;
		creatingAction = true;
		try {
			onCreateAction?.();
			actionCreated = true;
			// Reset after 2 seconds
			setTimeout(() => {
				actionCreated = false;
			}, 2000);
		} finally {
			creatingAction = false;
		}
	}

	async function handleShareWithBoard() {
		if (sharingWithBoard || sharedWithBoard) return;
		sharingWithBoard = true;
		try {
			onShareWithBoard?.();
			sharedWithBoard = true;
			// Reset after 2 seconds
			setTimeout(() => {
				sharedWithBoard = false;
			}, 2000);
		} finally {
			sharingWithBoard = false;
		}
	}
</script>

<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-5 transition-shadow hover:shadow-md">
	<!-- Header with objective tag -->
	<div class="flex items-start justify-between mb-3">
		<div class="flex items-center gap-2 flex-wrap">
			{#if insight.objective_name}
				<span class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium bg-brand-100 text-brand-700 dark:bg-brand-900/30 dark:text-brand-300">
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
					</svg>
					{insight.objective_name}
				</span>
			{/if}
			<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {getConfidenceColor(insight.confidence)}">
				{insight.confidence} confidence
			</span>
		</div>
	</div>

	<!-- Headline -->
	<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">
		{insight.headline}
	</h3>

	<!-- Narrative -->
	<p class="text-neutral-600 dark:text-neutral-400 text-sm leading-relaxed mb-4">
		{insight.narrative}
	</p>

	<!-- Visualization (if present) -->
	{#if figureJson}
		<div class="mb-4 -mx-2">
			<ChartRenderer
				{figureJson}
				title={insight.visualization?.title || ''}
				height={200}
				viewMode="simple"
			/>
		</div>
	{/if}

	<!-- Benchmark Comparison Section -->
	{#if insight.benchmark_comparison}
		<div class="mb-4 p-3 bg-neutral-50 dark:bg-neutral-900/50 rounded-lg border border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-2 mb-2">
				<svg class="w-4 h-4 text-neutral-500 dark:text-neutral-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
				</svg>
				<span class="text-xs font-medium text-neutral-600 dark:text-neutral-400">Industry Comparison</span>
			</div>

			<!-- Values comparison -->
			<div class="flex items-center justify-between mb-2">
				<div class="text-sm">
					<span class="font-semibold text-neutral-900 dark:text-white">{insight.benchmark_comparison.your_value}{insight.benchmark_comparison.unit}</span>
					<span class="text-neutral-500 dark:text-neutral-400 mx-1">vs</span>
					<span class="text-neutral-600 dark:text-neutral-300">
						{insight.benchmark_comparison.industry_median}{insight.benchmark_comparison.unit} median
					</span>
				</div>
				<span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium {getPerformanceColor(insight.benchmark_comparison.performance)}">
					{formatPerformance(insight.benchmark_comparison.performance)}
				</span>
			</div>

			<!-- Progress bar -->
			{#if benchmarkProgress !== null}
				<div class="relative h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
					<!-- Median marker at 50% -->
					<div class="absolute top-0 bottom-0 w-0.5 bg-neutral-400 dark:bg-neutral-500" style="left: 50%"></div>
					<!-- Top quartile marker at 75% -->
					{#if insight.benchmark_comparison.industry_top_quartile}
						<div class="absolute top-0 bottom-0 w-0.5 bg-success-400 dark:bg-success-500" style="left: 75%"></div>
					{/if}
					<!-- Your value indicator -->
					<div
						class="absolute top-0 bottom-0 rounded-full transition-all duration-300 {insight.benchmark_comparison.performance === 'top_performer' ? 'bg-success-500' : insight.benchmark_comparison.performance === 'above_average' ? 'bg-brand-500' : insight.benchmark_comparison.performance === 'below_average' ? 'bg-warning-500' : 'bg-neutral-400'}"
						style="width: {benchmarkProgress}%"
					></div>
				</div>
				<div class="flex justify-between text-xs text-neutral-500 dark:text-neutral-400 mt-1">
					<span>Below avg</span>
					<span>Median</span>
					<span>Top 25%</span>
				</div>
			{/if}
		</div>
	{/if}

	<!-- Impact Model Section -->
	{#if insight.impact_model}
		<div class="mb-4 p-3 bg-success-50 dark:bg-success-900/20 rounded-lg border border-success-200 dark:border-success-800">
			<div class="flex items-center gap-2 mb-2">
				<svg class="w-4 h-4 text-success-600 dark:text-success-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
				<span class="text-xs font-medium text-success-700 dark:text-success-300">Potential Impact</span>
			</div>
			<p class="text-sm text-success-700 dark:text-success-300 mb-2">{insight.impact_model.narrative}</p>
			<div class="flex gap-4">
				<div class="text-center">
					<div class="text-lg font-bold text-success-600 dark:text-success-400">
						${formatNumber(insight.impact_model.monthly_impact)}
					</div>
					<div class="text-xs text-success-600 dark:text-success-400">/month</div>
				</div>
				<div class="text-center">
					<div class="text-lg font-bold text-success-600 dark:text-success-400">
						${formatNumber(insight.impact_model.annual_impact)}
					</div>
					<div class="text-xs text-success-600 dark:text-success-400">/year</div>
				</div>
			</div>
			{#if insight.impact_model.assumptions && insight.impact_model.assumptions.length > 0}
				<details class="mt-2">
					<summary class="text-xs text-success-600 dark:text-success-400 cursor-pointer hover:underline">View assumptions</summary>
					<ul class="mt-1 text-xs text-success-600 dark:text-success-400 list-disc list-inside">
						{#each insight.impact_model.assumptions as assumption}
							<li>{assumption}</li>
						{/each}
					</ul>
				</details>
			{/if}
		</div>
	{/if}

	<!-- Recommendation callout -->
	{#if insight.recommendation}
		<div class="mb-4 p-3 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
			<div class="flex items-start gap-2">
				<svg class="w-4 h-4 text-brand-600 dark:text-brand-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
				</svg>
				<span class="text-sm text-brand-700 dark:text-brand-300">
					<strong>Recommendation:</strong> {insight.recommendation}
				</span>
			</div>
		</div>
	{/if}

	<!-- Follow-up questions -->
	{#if insight.follow_up_questions && insight.follow_up_questions.length > 0}
		<div class="mb-4">
			<p class="text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-2">Explore further:</p>
			<div class="flex flex-wrap gap-2">
				{#each insight.follow_up_questions.slice(0, 3) as question}
					<button
						onclick={() => onExploreMore?.()}
						class="text-xs px-2.5 py-1 rounded-full bg-neutral-100 dark:bg-neutral-700 text-neutral-600 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600 transition-colors"
					>
						{question}
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Action buttons -->
	<div class="flex items-center gap-2 pt-3 border-t border-neutral-100 dark:border-neutral-700">
		{#if onAddToReport}
			<button
				onclick={handleAddToReport}
				disabled={addingToReport}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
					{addedToReport
						? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
						: 'bg-neutral-100 dark:bg-neutral-700 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-200 dark:hover:bg-neutral-600'}
					disabled:opacity-50 disabled:cursor-not-allowed"
				aria-label={addedToReport ? 'Added to report' : 'Add to report'}
			>
				{#if addingToReport}
					<svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				{:else if addedToReport}
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					Added
				{:else}
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
					</svg>
					Add to Report
				{/if}
			</button>
		{/if}
		{#if onCreateAction}
			<button
				onclick={handleCreateAction}
				disabled={creatingAction}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
					{actionCreated
						? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
						: 'bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 hover:bg-brand-200 dark:hover:bg-brand-900/50'}
					disabled:opacity-50 disabled:cursor-not-allowed"
				aria-label={actionCreated ? 'Action created' : 'Create action'}
			>
				{#if creatingAction}
					<svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				{:else if actionCreated}
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					Created
				{:else}
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
					</svg>
					Create Action
				{/if}
			</button>
		{/if}
		{#if onExploreMore}
			<button
				onclick={onExploreMore}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md text-neutral-600 dark:text-neutral-400 hover:text-neutral-900 dark:hover:text-white hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
				aria-label="Explore more about this insight"
			>
				<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				</svg>
				Explore More
			</button>
		{/if}
		{#if onShareWithBoard}
			<button
				onclick={handleShareWithBoard}
				disabled={sharingWithBoard}
				class="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-all duration-200
					{sharedWithBoard
						? 'bg-success-100 dark:bg-success-900/30 text-success-700 dark:text-success-300'
						: 'bg-purple-100 dark:bg-purple-900/30 text-purple-700 dark:text-purple-300 hover:bg-purple-200 dark:hover:bg-purple-900/50'}
					disabled:opacity-50 disabled:cursor-not-allowed"
				aria-label={sharedWithBoard ? 'Shared with board' : 'Share with board'}
			>
				{#if sharingWithBoard}
					<svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
						<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
						<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
					</svg>
				{:else if sharedWithBoard}
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
					</svg>
					Shared
				{:else}
					<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
					</svg>
					Share with Board
				{/if}
			</button>
		{/if}
	</div>
</div>
