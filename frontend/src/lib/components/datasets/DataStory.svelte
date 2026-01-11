<script lang="ts">
	/**
	 * DataStory - Main narrative display component
	 *
	 * Displays the AI-generated data story with:
	 * - Opening hook that references North Star
	 * - Objective sections with linked insights
	 * - Data quality summary
	 * - Unexpected findings
	 * - Next steps and suggested questions
	 */
	import { fly, fade, slide } from 'svelte/transition';
	import type {
		ObjectiveDataStory,
		ObjectiveInsight,
		ObjectiveAnalysisMode,
		DataQualityIssue,
		DatasetFixResponse
	} from '$lib/api/types';
	import InsightCard from './InsightCard.svelte';
	import DataQualityNotice from './DataQualityNotice.svelte';

	interface Props {
		datasetId: string;
		dataStory?: ObjectiveDataStory | null;
		insights: ObjectiveInsight[];
		analysisMode: ObjectiveAnalysisMode;
		dataQualityIssues?: DataQualityIssue[];
		loading?: boolean;
		onAddToReport?: (insight: ObjectiveInsight) => void;
		onCreateAction?: (insight: ObjectiveInsight) => void;
		onExploreMore?: (insight: ObjectiveInsight) => void;
		onShareWithBoard?: (insight: ObjectiveInsight) => void;
		onAskQuestion?: (question: string) => void;
		onDataFixed?: (result: DatasetFixResponse) => void;
	}

	let {
		datasetId,
		dataStory = null,
		insights,
		analysisMode,
		dataQualityIssues = [],
		loading = false,
		onAddToReport,
		onCreateAction,
		onExploreMore,
		onShareWithBoard,
		onAskQuestion,
		onDataFixed
	}: Props = $props();

	// Helper to get insights for a section
	function getInsightsForSection(insightIds: string[]): ObjectiveInsight[] {
		return insightIds
			.map((id) => insights.find((i) => i.id === id))
			.filter((i): i is ObjectiveInsight => i !== undefined);
	}

	// Get insights not in any section (for open exploration mode)
	const unlinkedInsights = $derived.by(() => {
		if (!dataStory || analysisMode !== 'open_exploration') return insights;
		const linkedIds = new Set(dataStory.objective_sections.flatMap((s) => s.insight_ids));
		return insights.filter((i) => !linkedIds.has(i.id));
	});
</script>

<!-- Skeleton Loader for Loading State -->
{#if loading}
	<div class="space-y-6 animate-pulse" in:fade={{ duration: 200 }}>
		<!-- Opening Hook Skeleton -->
		<div class="bg-gradient-to-r from-neutral-100 to-neutral-50 dark:from-neutral-800 dark:to-neutral-800/50 rounded-xl p-6 border border-neutral-200 dark:border-neutral-700">
			<div class="h-6 w-32 bg-neutral-200 dark:bg-neutral-700 rounded mb-3"></div>
			<div class="space-y-2">
				<div class="h-4 w-full bg-neutral-200 dark:bg-neutral-700 rounded"></div>
				<div class="h-4 w-3/4 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
			</div>
		</div>

		<!-- Insight Cards Skeleton -->
		{#each [1, 2] as _, i (i)}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-5">
				<div class="flex items-center gap-2 mb-3">
					<div class="h-6 w-24 bg-neutral-200 dark:bg-neutral-700 rounded-full"></div>
					<div class="h-5 w-20 bg-neutral-200 dark:bg-neutral-700 rounded"></div>
				</div>
				<div class="h-5 w-3/4 bg-neutral-200 dark:bg-neutral-700 rounded mb-3"></div>
				<div class="space-y-2 mb-4">
					<div class="h-4 w-full bg-neutral-100 dark:bg-neutral-700/50 rounded"></div>
					<div class="h-4 w-5/6 bg-neutral-100 dark:bg-neutral-700/50 rounded"></div>
				</div>
				<div class="flex gap-2 pt-3 border-t border-neutral-100 dark:border-neutral-700">
					<div class="h-8 w-24 bg-neutral-100 dark:bg-neutral-700 rounded-md"></div>
					<div class="h-8 w-24 bg-neutral-100 dark:bg-neutral-700 rounded-md"></div>
				</div>
			</div>
		{/each}

		<!-- Next Steps Skeleton -->
		<div class="bg-white dark:bg-neutral-800 rounded-lg p-5 border border-neutral-200 dark:border-neutral-700">
			<div class="h-5 w-40 bg-neutral-200 dark:bg-neutral-700 rounded mb-3"></div>
			<div class="space-y-2">
				{#each [1, 2, 3] as _, i (i)}
					<div class="flex items-center gap-3">
						<div class="w-5 h-5 rounded-full bg-neutral-200 dark:bg-neutral-700"></div>
						<div class="h-4 flex-1 bg-neutral-100 dark:bg-neutral-700/50 rounded"></div>
					</div>
				{/each}
			</div>
		</div>
	</div>
{:else}
<div class="space-y-6" in:fade={{ duration: 300 }}>
	<!-- Opening Hook -->
	{#if dataStory?.opening_hook}
		<div class="bg-gradient-to-r from-brand-50 to-brand-100/50 dark:from-brand-900/30 dark:to-brand-900/10 rounded-xl p-6 border border-brand-200 dark:border-brand-800" in:fly={{ y: -10, duration: 300 }}>
			<h2 class="text-xl font-semibold text-brand-900 dark:text-brand-100 mb-2">
				Your Data Story
			</h2>
			<p class="text-lg text-brand-700 dark:text-brand-300 leading-relaxed">
				{dataStory.opening_hook}
			</p>
		</div>
	{:else if insights.length > 0}
		<div class="bg-gradient-to-r from-brand-50 to-brand-100/50 dark:from-brand-900/30 dark:to-brand-900/10 rounded-xl p-6 border border-brand-200 dark:border-brand-800" in:fly={{ y: -10, duration: 300 }}>
			<h2 class="text-xl font-semibold text-brand-900 dark:text-brand-100">
				{analysisMode === 'objective_focused' ? 'Objective-Aligned Analysis' : 'Data Exploration Results'}
			</h2>
			<p class="text-brand-600 dark:text-brand-400 mt-1">
				{insights.length} insight{insights.length !== 1 ? 's' : ''} generated from your data
			</p>
		</div>
	{/if}

	<!-- Data Quality Notice (if issues exist) -->
	{#if dataQualityIssues.length > 0}
		<DataQualityNotice {datasetId} issues={dataQualityIssues} onFixed={onDataFixed} />
	{:else if dataStory?.data_quality_summary}
		<div class="bg-neutral-50 dark:bg-neutral-800/50 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
			<div class="flex items-start gap-3">
				<svg class="w-5 h-5 text-neutral-500 dark:text-neutral-400 mt-0.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
				</svg>
				<div>
					<p class="text-sm font-medium text-neutral-700 dark:text-neutral-300">Data Quality</p>
					<p class="text-sm text-neutral-600 dark:text-neutral-400">{dataStory.data_quality_summary}</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Objective Sections -->
	{#if dataStory?.objective_sections && dataStory.objective_sections.length > 0}
		{#each dataStory.objective_sections as section, i}
			<div class="space-y-4">
				<!-- Section header -->
				<div class="flex items-center gap-3">
					<span class="flex items-center justify-center w-7 h-7 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400 text-sm font-semibold">
						{i + 1}
					</span>
					<div class="flex-1">
						<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
							{section.objective_name}
						</h3>
						{#if section.key_metric}
							<p class="text-sm text-brand-600 dark:text-brand-400">
								Key metric: {section.key_metric}
							</p>
						{/if}
					</div>
				</div>

				<!-- Section summary -->
				{#if section.summary}
					<p class="text-neutral-600 dark:text-neutral-400 pl-10">
						{section.summary}
					</p>
				{/if}

				<!-- Section insights -->
				{#if section.insight_ids.length > 0}
					<div class="grid gap-4 pl-10">
						{#each getInsightsForSection(section.insight_ids) as insight (insight.id)}
							<InsightCard
								{insight}
								onAddToReport={() => onAddToReport?.(insight)}
								onCreateAction={() => onCreateAction?.(insight)}
								onExploreMore={() => onExploreMore?.(insight)}
								onShareWithBoard={() => onShareWithBoard?.(insight)}
							/>
						{/each}
					</div>
				{/if}

				<!-- Section action -->
				{#if section.recommended_action}
					<div class="pl-10">
						<div class="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-brand-50 dark:bg-brand-900/20 border border-brand-200 dark:border-brand-800">
							<svg class="w-4 h-4 text-brand-600 dark:text-brand-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
								<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7l5 5m0 0l-5 5m5-5H6" />
							</svg>
							<span class="text-sm font-medium text-brand-700 dark:text-brand-300">
								{section.recommended_action}
							</span>
						</div>
					</div>
				{/if}
			</div>
		{/each}
	{/if}

	<!-- Unlinked insights (for open exploration or when no sections) -->
	{#if unlinkedInsights.length > 0 && (!dataStory?.objective_sections || dataStory.objective_sections.length === 0)}
		<div class="space-y-4">
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white">
				{analysisMode === 'open_exploration' ? 'Discoveries' : 'Insights'}
			</h3>
			<div class="grid gap-4">
				{#each unlinkedInsights as insight (insight.id)}
					<InsightCard
						{insight}
						onAddToReport={() => onAddToReport?.(insight)}
						onCreateAction={() => onCreateAction?.(insight)}
						onExploreMore={() => onExploreMore?.(insight)}
						onShareWithBoard={() => onShareWithBoard?.(insight)}
					/>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Unexpected Finding -->
	{#if dataStory?.unexpected_finding}
		<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-5 border border-purple-200 dark:border-purple-800">
			<div class="flex items-start gap-3">
				<div class="p-2 rounded-lg bg-purple-100 dark:bg-purple-900/40">
					<svg class="w-5 h-5 text-purple-600 dark:text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
					</svg>
				</div>
				<div class="flex-1">
					<div class="flex items-center gap-2 mb-1">
						<h4 class="text-sm font-semibold text-purple-800 dark:text-purple-200">
							Unexpected Finding
						</h4>
						{#if dataStory.unexpected_finding.should_investigate}
							<span class="px-2 py-0.5 rounded text-xs font-medium bg-purple-200 dark:bg-purple-800 text-purple-700 dark:text-purple-300">
								Worth investigating
							</span>
						{/if}
					</div>
					<p class="text-sm font-medium text-purple-700 dark:text-purple-300 mb-1">
						{dataStory.unexpected_finding.headline}
					</p>
					<p class="text-sm text-purple-600 dark:text-purple-400">
						{dataStory.unexpected_finding.narrative}
					</p>
				</div>
			</div>
		</div>
	{/if}

	<!-- Next Steps -->
	{#if dataStory?.next_steps && dataStory.next_steps.length > 0}
		<div class="bg-white dark:bg-neutral-800 rounded-lg p-5 border border-neutral-200 dark:border-neutral-700">
			<h4 class="text-sm font-semibold text-neutral-900 dark:text-white mb-3">
				Recommended Next Steps
			</h4>
			<ol class="space-y-2">
				{#each dataStory.next_steps as step, i}
					<li class="flex items-start gap-3">
						<span class="flex items-center justify-center w-5 h-5 rounded-full bg-brand-100 dark:bg-brand-900/40 text-brand-600 dark:text-brand-400 text-xs font-medium flex-shrink-0">
							{i + 1}
						</span>
						<span class="text-sm text-neutral-700 dark:text-neutral-300">{step}</span>
					</li>
				{/each}
			</ol>
		</div>
	{/if}

	<!-- Empty state -->
	{#if !dataStory && insights.length === 0}
		<div class="text-center py-12" in:fade={{ duration: 200, delay: 100 }}>
			<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
			</svg>
			<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">No insights yet</h3>
			<p class="text-sm text-neutral-600 dark:text-neutral-400">
				Run an analysis to generate insights aligned with your objectives.
			</p>
		</div>
	{/if}
</div>
{/if}
