<script lang="ts">
	/**
	 * InsightsTab - AI-generated insights, suggested questions, and next steps
	 */
	import type { DatasetInsights, DatasetInvestigation } from '$lib/api/types';
	import DataInsightsPanel from '../DataInsightsPanel.svelte';

	interface Props {
		datasetId: string;
		insights: DatasetInsights | null;
		investigation: DatasetInvestigation | null;
		loading: boolean;
		error: string | null;
		onQuestionClick: (question: string) => void;
		onRefresh: () => void;
	}

	let { datasetId, insights, investigation, loading, error, onQuestionClick, onRefresh }: Props = $props();

	// Generate LLM-powered suggestions based on investigation
	const suggestedNextSteps = $derived(() => {
		if (!investigation) return [];

		const steps: { title: string; description: string; action?: string }[] = [];

		// Based on data quality
		const qualityScore = investigation.data_quality?.overall_score ?? 100;
		if (qualityScore < 80) {
			steps.push({
				title: 'Improve Data Quality',
				description: `Your data quality score is ${qualityScore}%. Consider addressing missing values and inconsistencies.`,
				action: 'Show quality issues'
			});
		}

		// Based on correlations
		const leakage = investigation.correlations?.potential_leakage ?? [];
		if (leakage.length > 0) {
			steps.push({
				title: 'Review Correlated Columns',
				description: `Found ${leakage.length} highly correlated column pairs that may indicate redundancy or data leakage.`,
				action: 'View correlations'
			});
		}

		// Based on time series readiness
		if (investigation.time_series_readiness?.is_ready) {
			steps.push({
				title: 'Explore Time Trends',
				description: `Your data is time-series ready with ${investigation.time_series_readiness.detected_frequency || 'detected'} frequency.`,
				action: 'Create trend chart'
			});
		}

		// Based on segmentation
		const opportunities = investigation.segmentation_suggestions?.opportunities ?? [];
		if (opportunities.length > 0) {
			steps.push({
				title: 'Segment Your Data',
				description: `Found ${opportunities.length} segmentation opportunities to explore patterns across dimensions.`,
				action: 'View segments'
			});
		}

		return steps;
	});
</script>

<div class="space-y-6">
	<!-- LLM-Generated Insights -->
	<DataInsightsPanel
		{insights}
		{datasetId}
		{loading}
		{error}
		{onQuestionClick}
		{onRefresh}
	/>

	<!-- Suggested Next Steps -->
	{#if suggestedNextSteps().length > 0}
		<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
			<div class="flex items-center gap-3 mb-4">
				<span class="p-2 rounded-lg bg-amber-100 dark:bg-amber-900/30">
					<svg class="w-5 h-5 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
					</svg>
				</span>
				<div>
					<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Suggested Next Steps</h2>
					<p class="text-sm text-neutral-500 dark:text-neutral-400">AI-powered recommendations based on your data</p>
				</div>
			</div>

			<div class="space-y-3">
				{#each suggestedNextSteps() as step}
					<div class="p-4 bg-neutral-50 dark:bg-neutral-700/50 rounded-lg flex items-start justify-between gap-4">
						<div>
							<h3 class="font-medium text-neutral-900 dark:text-white">{step.title}</h3>
							<p class="text-sm text-neutral-600 dark:text-neutral-400 mt-1">{step.description}</p>
						</div>
						{#if step.action}
							<button
								onclick={() => onQuestionClick(step.action ?? '')}
								class="flex-shrink-0 px-3 py-1.5 text-sm font-medium rounded-lg bg-brand-100 dark:bg-brand-900/30 text-brand-700 dark:text-brand-300 hover:bg-brand-200 dark:hover:bg-brand-900/50 transition-colors"
							>
								{step.action}
							</button>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Quick Questions -->
	<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
		<div class="flex items-center gap-3 mb-4">
			<span class="p-2 rounded-lg bg-blue-100 dark:bg-blue-900/30">
				<svg class="w-5 h-5 text-blue-600 dark:text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
				</svg>
			</span>
			<div>
				<h2 class="text-lg font-semibold text-neutral-900 dark:text-white">Ask a Question</h2>
				<p class="text-sm text-neutral-500 dark:text-neutral-400">Get instant answers about your data</p>
			</div>
		</div>

		<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
			{#each [
				'What are the main trends in this data?',
				'Which columns have the most missing values?',
				'Are there any outliers I should investigate?',
				'What segments show interesting patterns?',
				'How can I improve data quality?',
				'What correlations exist between metrics?'
			] as question}
				<button
					onclick={() => onQuestionClick(question)}
					class="text-left p-3 rounded-lg border border-neutral-200 dark:border-neutral-600 hover:border-brand-300 dark:hover:border-brand-600 hover:bg-brand-50 dark:hover:bg-brand-900/10 transition-colors group"
				>
					<span class="text-sm text-neutral-700 dark:text-neutral-300 group-hover:text-brand-700 dark:group-hover:text-brand-300">
						{question}
					</span>
				</button>
			{/each}
		</div>
	</div>
</div>
