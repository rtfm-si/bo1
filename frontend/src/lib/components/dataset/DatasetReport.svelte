<script lang="ts">
	/**
	 * DatasetReport - Renders a generated report with sections and embedded charts
	 *
	 * Follows pyramid principle structure:
	 * 1. Executive Summary
	 * 2. Key Findings
	 * 3. Detailed Analysis
	 * 4. Recommendations
	 * 5. Data Notes
	 */
	import type { DatasetReportResponse, DatasetFavourite, ReportSection } from '$lib/api/types';
	import ChartRenderer from './ChartRenderer.svelte';
	import ChartModal from './ChartModal.svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	interface Props {
		report: DatasetReportResponse;
		favourites?: DatasetFavourite[];
		datasetName?: string;
	}

	let { report, favourites = [], datasetName = 'Dataset' }: Props = $props();

	// Create a map of favourite IDs to favourites for chart rendering
	const favouriteMap = $derived(
		new Map(favourites.map((f) => [f.id, f]))
	);

	// Modal state
	let modalOpen = $state(false);
	let modalFigureJson = $state<Record<string, unknown> | null>(null);
	let modalTitle = $state('');

	function handleExpandChart(favId: string) {
		const fav = favouriteMap.get(favId);
		if (fav?.figure_json) {
			modalFigureJson = fav.figure_json as Record<string, unknown>;
			modalTitle = fav.title || 'Chart';
			modalOpen = true;
		}
	}

	function getSectionIcon(sectionType: string): string {
		switch (sectionType) {
			case 'key_findings':
				return 'M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z';
			case 'analysis':
				return 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z';
			case 'recommendations':
				return 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'data_notes':
				return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
			default:
				return 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z';
		}
	}

	function getSectionColor(sectionType: string): string {
		switch (sectionType) {
			case 'key_findings':
				return 'text-warning-500';
			case 'analysis':
				return 'text-brand-500';
			case 'recommendations':
				return 'text-success-500';
			case 'data_notes':
				return 'text-neutral-500';
			default:
				return 'text-brand-500';
		}
	}

	function formatDate(dateString: string): string {
		const date = new Date(dateString);
		return date.toLocaleDateString('en-US', {
			year: 'numeric',
			month: 'long',
			day: 'numeric',
			hour: 'numeric',
			minute: '2-digit'
		});
	}
</script>

<article class="max-w-4xl mx-auto">
	<!-- Report Header -->
	<header class="mb-8">
		<div class="flex items-center gap-2 text-sm text-neutral-500 dark:text-neutral-400 mb-2">
			<span>{datasetName}</span>
			<span>-</span>
			<span>Generated {formatDate(report.created_at)}</span>
		</div>
		<h1 class="text-3xl font-bold text-neutral-900 dark:text-white mb-4">
			{report.title}
		</h1>
	</header>

	<!-- Executive Summary -->
	{#if report.executive_summary}
		<section class="mb-8 p-6 bg-brand-50 dark:bg-brand-900/20 rounded-lg border border-brand-200 dark:border-brand-800">
			<h2 class="text-lg font-semibold text-brand-800 dark:text-brand-200 mb-3 flex items-center gap-2">
				<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z" />
				</svg>
				Executive Summary
			</h2>
			<p class="text-brand-900 dark:text-brand-100 text-lg leading-relaxed">
				{report.executive_summary}
			</p>
		</section>
	{/if}

	<!-- Report Sections -->
	{#if report.sections}
		{#each report.sections as section, index (index)}
			<section class="mb-8">
				<h2 class="text-xl font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
					<svg class="w-5 h-5 {getSectionColor(section.section_type)}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getSectionIcon(section.section_type)} />
					</svg>
					{section.title}
				</h2>

				<!-- Section Content -->
				<div class="prose prose-neutral dark:prose-invert max-w-none">
					<MarkdownContent content={section.content} />
				</div>

				<!-- Referenced Charts -->
				{#if section.chart_refs && section.chart_refs.length > 0}
					<div class="mt-6 grid gap-4 {section.chart_refs.length > 1 ? 'md:grid-cols-2' : ''}">
						{#each section.chart_refs as chartRef}
							{@const fav = favouriteMap.get(chartRef)}
							{#if fav?.figure_json}
								<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
									<div class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
										{fav.title || 'Chart'}
									</div>
									<ChartRenderer
										figureJson={fav.figure_json}
										title=""
										viewMode="simple"
										height={220}
										onExpand={() => handleExpandChart(chartRef)}
									/>
								</div>
							{/if}
						{/each}
					</div>
				{/if}
			</section>
		{/each}
	{/if}

	<!-- Report Footer -->
	<footer class="mt-12 pt-6 border-t border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center justify-between text-sm text-neutral-500 dark:text-neutral-400">
			<div>
				Based on {report.favourite_ids.length} favourited item{report.favourite_ids.length !== 1 ? 's' : ''}
			</div>
			{#if report.model_used}
				<div class="flex items-center gap-2">
					<span>Generated by</span>
					<span class="font-mono text-xs bg-neutral-100 dark:bg-neutral-700 px-2 py-1 rounded">
						{report.model_used}
					</span>
				</div>
			{/if}
		</div>
	</footer>
</article>

<!-- Chart Modal -->
<ChartModal
	bind:open={modalOpen}
	figureJson={modalFigureJson}
	title={modalTitle}
/>

<style>
	@media print {
		article {
			max-width: 100%;
		}
		section {
			break-inside: avoid;
		}
	}
</style>
