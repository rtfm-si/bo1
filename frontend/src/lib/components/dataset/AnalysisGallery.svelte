<script lang="ts">
	/**
	 * AnalysisGallery - Grid of chart thumbnails with modal expand
	 */
	import type { DatasetAnalysis } from '$lib/api/types';
	import BoCard from '$lib/components/ui/BoCard.svelte';
	import BoButton from '$lib/components/ui/BoButton.svelte';

	let {
		analyses,
		loading = false,
		error = null
	}: {
		analyses: DatasetAnalysis[];
		loading?: boolean;
		error?: string | null;
	} = $props();

	let selectedAnalysis: DatasetAnalysis | null = $state(null);

	function formatDate(timestamp: string): string {
		const date = new Date(timestamp);
		return date.toLocaleDateString('en-US', {
			month: 'short',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
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

<!-- Gallery grid -->
{:else}
	<div class="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
		{#each analyses as analysis}
			<button
				type="button"
				onclick={() => selectedAnalysis = analysis}
				class="group aspect-[4/3] bg-white dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700 rounded-lg overflow-hidden hover:border-brand-300 dark:hover:border-brand-600 transition-colors text-left"
			>
				{#if analysis.chart_url}
					<img
						src={analysis.chart_url}
						alt={analysis.title || 'Chart'}
						class="w-full h-full object-contain bg-neutral-50 dark:bg-neutral-900"
					/>
				{:else}
					<div class="w-full h-full flex items-center justify-center bg-neutral-50 dark:bg-neutral-900">
						<svg class="w-8 h-8 text-neutral-300 dark:text-neutral-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d={getChartTypeIcon(analysis.chart_spec?.chart_type)} />
						</svg>
					</div>
				{/if}

				<!-- Overlay with title -->
				<div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/60 to-transparent p-2 opacity-0 group-hover:opacity-100 transition-opacity">
					<p class="text-white text-xs font-medium truncate">
						{analysis.title || analysis.chart_spec?.chart_type || 'Analysis'}
					</p>
					<p class="text-white/70 text-xs">
						{formatDate(analysis.created_at)}
					</p>
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
		onclick={() => selectedAnalysis = null}
		onkeydown={(e) => e.key === 'Escape' && (selectedAnalysis = null)}
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
					onclick={() => selectedAnalysis = null}
					class="p-2 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-300"
					aria-label="Close"
				>
					<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
					</svg>
				</button>
			</div>

			<!-- Chart image -->
			<div class="p-4 bg-neutral-50 dark:bg-neutral-900">
				{#if selectedAnalysis.chart_url}
					<img
						src={selectedAnalysis.chart_url}
						alt={selectedAnalysis.title || 'Chart'}
						class="max-w-full max-h-[60vh] mx-auto"
					/>
				{:else}
					<div class="flex items-center justify-center h-48 text-neutral-400">
						Chart image not available
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
