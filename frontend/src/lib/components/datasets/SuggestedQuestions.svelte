<script lang="ts">
	/**
	 * SuggestedQuestions - Mode-aware question suggestions
	 *
	 * Displays clickable question chips based on analysis mode:
	 * - Objective-Focused: Questions derived from objectives + data
	 * - Open Exploration: Questions about patterns, outliers, segments
	 */
	import type { ObjectiveAnalysisMode } from '$lib/api/types';

	interface Props {
		analysisMode: ObjectiveAnalysisMode;
		suggestedQuestions?: string[];
		objectives?: string[];
		dataColumns?: string[];
		onAskQuestion: (question: string) => void;
	}

	let {
		analysisMode,
		suggestedQuestions = [],
		objectives = [],
		dataColumns = [],
		onAskQuestion
	}: Props = $props();

	// Generate objective-based questions if none provided
	const objectiveQuestions = $derived.by(() => {
		if (suggestedQuestions.length > 0) return [];
		if (analysisMode !== 'objective_focused' || objectives.length === 0) return [];

		return objectives.slice(0, 3).map((obj) => {
			const objLower = obj.toLowerCase();
			if (objLower.includes('churn') || objLower.includes('retention')) {
				return `What factors are driving ${obj.toLowerCase()}?`;
			}
			if (objLower.includes('revenue') || objLower.includes('mrr') || objLower.includes('sales')) {
				return `Which segments contribute most to ${obj.toLowerCase()}?`;
			}
			if (objLower.includes('growth') || objLower.includes('increase')) {
				return `What opportunities exist for ${obj.toLowerCase()}?`;
			}
			return `What does the data reveal about ${obj.toLowerCase()}?`;
		});
	});

	// Generate exploration questions if none provided
	const explorationQuestions = $derived.by(() => {
		if (suggestedQuestions.length > 0) return [];
		if (analysisMode !== 'open_exploration') return [];

		const questions: string[] = [];

		// Column-based suggestions
		if (dataColumns.length > 0) {
			const numericCols = dataColumns.filter((c) =>
				['amount', 'total', 'count', 'revenue', 'price', 'quantity', 'value'].some((k) =>
					c.toLowerCase().includes(k)
				)
			);
			const catCols = dataColumns.filter((c) =>
				['category', 'type', 'status', 'segment', 'region', 'channel'].some((k) =>
					c.toLowerCase().includes(k)
				)
			);

			if (numericCols.length > 0) {
				questions.push(`What's the distribution of ${numericCols[0]}?`);
			}
			if (catCols.length > 0 && numericCols.length > 0) {
				questions.push(`How does ${numericCols[0]} vary by ${catCols[0]}?`);
			}
		}

		// Generic exploration questions
		questions.push('What patterns stand out in this data?');
		questions.push('Are there any outliers I should investigate?');
		questions.push('What segments exist in this data?');

		return questions.slice(0, 4);
	});

	// Combined questions list
	const displayQuestions = $derived(
		suggestedQuestions.length > 0
			? suggestedQuestions
			: [...objectiveQuestions, ...explorationQuestions].slice(0, 4)
	);

	// Group label based on mode
	const groupLabel = $derived(
		analysisMode === 'objective_focused'
			? 'Based on your objectives'
			: 'Explore the data'
	);
</script>

{#if displayQuestions.length > 0}
	<div class="space-y-3">
		<div class="flex items-center gap-2">
			<svg class="w-4 h-4 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				{#if analysisMode === 'objective_focused'}
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
				{:else}
					<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
				{/if}
			</svg>
			<span class="text-sm font-medium text-neutral-600 dark:text-neutral-400">
				{groupLabel}
			</span>
		</div>

		<div class="flex flex-wrap gap-2">
			{#each displayQuestions as question, i (i)}
				<button
					onclick={() => onAskQuestion(question)}
					class="text-sm px-4 py-2 rounded-lg bg-white dark:bg-neutral-700 border border-neutral-200 dark:border-neutral-600 text-neutral-700 dark:text-neutral-200 hover:border-brand-400 dark:hover:border-brand-500 hover:bg-brand-50 dark:hover:bg-brand-900/20 hover:text-brand-700 dark:hover:text-brand-300 transition-colors text-left shadow-sm"
				>
					{question}
				</button>
			{/each}
		</div>
	</div>
{/if}
