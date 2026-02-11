<script lang="ts">
	/**
	 * AnalysisGallery - Grid of chart thumbnails with modal expand
	 * Supports both PNG charts (chart_url) and Plotly specs (chart_spec)
	 */
	import type { DatasetAnalysis, ChartSpec, ChartResultResponse } from '$lib/api/types';
	import { apiClient } from '$lib/api/client';
	import ChartRenderer from './ChartRenderer.svelte';

	import { formatDate } from '$lib/utils/time-formatting';
	let {
		analyses,
		datasetId,
		loading = false,
		error = null
	}: {
		analyses: DatasetAnalysis[];
		datasetId: string;
		loading?: boolean;
		error?: string | null;
	} = $props();

	let selectedAnalysis: DatasetAnalysis | null = $state(null);
	let chartPreviewData: ChartResultResponse | null = $state(null);
	let chartPreviewLoading = $state(false);
	let chartPreviewError: string | null = $state(null);

	async function handleAnalysisClick(analysis: DatasetAnalysis) {
		selectedAnalysis = analysis;
		chartPreviewData = null;
		chartPreviewError = null;

		// Always fetch chart preview if we have chart_spec (auto-load for better UX)
		if (analysis.chart_spec) {
			chartPreviewLoading = true;
			try {
				const result = await apiClient.previewChart(datasetId, analysis.chart_spec as ChartSpec);
				chartPreviewData = result;
			} catch (err) {
				chartPreviewError = err instanceof Error ? err.message : 'Failed to load chart';
			} finally {
				chartPreviewLoading = false;
			}
		}
	}

	function closeModal() {
		selectedAnalysis = null;
		chartPreviewData = null;
		chartPreviewError = null;
	}


	function getChartTypeIcon(chartType: string | undefined): string {
		switch (chartType) {
			case 'line':
				return 'M3 3v18h18M8 17l4-8 4 4 3-6';
			case 'bar':
				return 'M18 20V10M12 20V4M6 20v-6';
			case 'pie':
				return 'M21.21 15.89A10 10 0 1 1 8 2.83M22 12A10 10 0 0 0 12 2v10z';
			case 'scatter':
				return 'M12 12m-1 0a1 1 0 1 0 2 0 a1 1 0 1 0 -2 0M6 8m-1 0a1 1 0 1 0 2 0 a1 1 0 1 0 -2 0M16 6m-1 0a1 1 0 1 0 2 0 a1 1 0 1 0 -2 0M18 14m-1 0a1 1 0 1 0 2 0 a1 1 0 1 0 -2 0M8 16m-1 0a1 1 0 1 0 2 0 a1 1 0 1 0 -2 0';
			default:
				return 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z';
		}
	}
</script>

<!-- Loading state -->
{#if loading}
	<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
		{#each [1, 2, 3, 4] as _}
			<div class="aspect-[4/3] bg-neutral-100 dark:bg-neutral-700 rounded-lg animate-pulse"></div>
		{/each}
	</div>

<!-- Error state -->
{:else if error}
	<div class="p-4 bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg text-error-700 dark:text-error-400 text-sm">
		{error}
	</div>

<!-- Empty state -->
{:else if analyses.length === 0}
	<div class="text-center py-8 text-neutral-500 dark:text-neutral-400">
		<svg class="w-12 h-12 mx-auto mb-3 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
		</svg>
		<p class="text-sm">No analysis history yet</p>
		<p class="text-xs mt-1">Charts generated from questions will appear here</p>
	</div>

<!-- Gallery grid - full width on mobile for better visibility -->
{:else}
	<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
		{#each analyses as analysis}
			<button
				type="button"
				onclick={() => handleAnalysisClick(analysis)}
				class="group relative aspect-[4/3] bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden hover:border-brand-300 dark:hover:border-brand-600 transition-colors text-left"
			>
				{#if analysis.chart_url}
					<img
						src={analysis.chart_url}
						alt={analysis.title || 'Chart'}
						class="w-full h-[60%] object-contain bg-neutral-50 dark:bg-neutral-900"
					/>
				{:else}
					<div class="w-full h-[60%] flex items-center justify-center bg-neutral-50 dark:bg-neutral-900">
						<svg class="w-8 h-8 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d={getChartTypeIcon(analysis.chart_spec?.chart_type)} />
						</svg>
					</div>
				{/if}

				<!-- Info section - always visible -->
				<div class="absolute bottom-0 inset-x-0 bg-white dark:bg-neutral-800 border-t border-neutral-200 dark:border-neutral-700 p-2">
					<p class="text-neutral-900 dark:text-white text-xs font-medium truncate">
						{analysis.title || analysis.chart_spec?.chart_type || 'Analysis'}
					</p>
					{#if analysis.chart_spec}
						<p class="text-[10px] text-neutral-500 dark:text-neutral-400 truncate mt-0.5">
							{analysis.chart_spec.y_field} by {analysis.chart_spec.x_field}
						</p>
					{/if}
					<div class="flex items-center gap-2 mt-0.5">
						{#if analysis.chart_spec?.chart_type}
							<span class="text-[10px] px-1.5 py-0.5 rounded bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 capitalize">
								{analysis.chart_spec.chart_type}
							</span>
						{/if}
						<span class="text-neutral-500 dark:text-neutral-400 text-[10px]">
							{formatDate(analysis.created_at)}
						</span>
					</div>
				</div>
			</button>
		{/each}
	</div>
{/if}

<!-- Modal for expanded view -->
{#if selectedAnalysis}
	<div
		class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
		role="dialog"
		aria-modal="true"
		aria-label="Analysis detail"
		tabindex="-1"
		onclick={closeModal}
		onkeydown={(e) => e.key === 'Escape' && closeModal()}
	>
		<!-- svelte-ignore a11y_no_static_element_interactions a11y_click_events_have_key_events -->
		<div
			class="bg-white dark:bg-neutral-800 rounded-lg shadow-xl max-w-4xl w-full max-h-[90vh] overflow-hidden"
			onclick={(e) => e.stopPropagation()}
			onkeydown={(e) => e.stopPropagation()}
			role="dialog"
			aria-modal="true"
			tabindex="-1"
		>
			<!-- Header -->
			<div class="flex items-center justify-between p-4 border-b border-neutral-200 dark:border-neutral-700">
				<div>
					<h3 class="font-medium text-neutral-900 dark:text-white">
						{selectedAnalysis.title || 'Analysis'}
					</h3>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">
						{formatDate(selectedAnalysis.created_at)}
					</p>
				</div>
				<button
					type="button"
					onclick={closeModal}
					class="p-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
					aria-label="Close"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Chart content -->
			<div class="p-4 bg-neutral-50 dark:bg-neutral-900">
				{#if selectedAnalysis.chart_url}
					<!-- PNG chart from /chart endpoint -->
					<img
						src={selectedAnalysis.chart_url}
						alt={selectedAnalysis.title || 'Chart'}
						class="max-w-full max-h-[60vh] mx-auto"
					/>
				{:else if chartPreviewLoading}
					<!-- Loading state for Plotly chart -->
					<div class="flex items-center justify-center h-64">
						<div class="text-center">
							<svg class="w-8 h-8 mx-auto mb-2 animate-spin text-brand-500" fill="none" viewBox="0 0 24 24">
								<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
								<path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
							</svg>
							<p class="text-sm text-neutral-500">Loading chart...</p>
						</div>
					</div>
				{:else if chartPreviewError}
					<!-- Error state -->
					<div class="flex items-center justify-center h-48 text-error-500">
						<p class="text-sm">{chartPreviewError}</p>
					</div>
				{:else if chartPreviewData}
					<!-- Plotly chart from Q&A -->
					<div class="min-h-[300px]">
						<ChartRenderer
							figureJson={chartPreviewData.figure_json}
							chartSpec={selectedAnalysis.chart_spec as ChartSpec}
							viewMode="detail"
							width={700}
							height={400}
						/>
					</div>
				{:else}
					<div class="flex items-center justify-center h-48 text-neutral-400">
						Chart not available
					</div>
				{/if}
			</div>

			<!-- Chart spec details -->
			{#if selectedAnalysis.chart_spec}
				<div class="p-4 border-t border-neutral-200 dark:border-neutral-700">
					<dl class="grid grid-cols-2 gap-2 text-sm">
						<div>
							<dt class="text-neutral-500 dark:text-neutral-400">Chart Type</dt>
							<dd class="font-medium text-neutral-900 dark:text-white capitalize">
								{selectedAnalysis.chart_spec.chart_type}
							</dd>
						</div>
						<div>
							<dt class="text-neutral-500 dark:text-neutral-400">X Axis</dt>
							<dd class="font-medium text-neutral-900 dark:text-white">
								{selectedAnalysis.chart_spec.x_field}
							</dd>
						</div>
						<div>
							<dt class="text-neutral-500 dark:text-neutral-400">Y Axis</dt>
							<dd class="font-medium text-neutral-900 dark:text-white">
								{selectedAnalysis.chart_spec.y_field}
							</dd>
						</div>
						{#if selectedAnalysis.chart_spec.group_field}
							<div>
								<dt class="text-neutral-500 dark:text-neutral-400">Group By</dt>
								<dd class="font-medium text-neutral-900 dark:text-white">
									{selectedAnalysis.chart_spec.group_field}
								</dd>
							</div>
						{/if}
					</dl>
				</div>
			{/if}
		</div>
	</div>
{/if}
