<script lang="ts">
	/**
	 * InsightsPreview - Displays dataset insights as compact preview
	 *
	 * Shows headline metrics, top insights, and suggested questions.
	 * Clicking a suggested question triggers the parent to submit it.
	 */
	import type { DatasetInsightsResponse } from '$lib/api/types';
	import { TrendingUp, TrendingDown, AlertCircle, Lightbulb, Search, BarChart3 } from 'lucide-svelte';
	import MarkdownContent from '$lib/components/ui/MarkdownContent.svelte';

	// Props
	let {
		insights,
		onQuestionClick
	}: {
		insights: DatasetInsightsResponse;
		onQuestionClick: (question: string) => void;
	} = $props();

	// Limit displays
	const maxMetrics = 4;
	const maxInsights = 3;
	const maxQuestions = 4;

	// Get insight type icon
	function getInsightIcon(type: string) {
		switch (type) {
			case 'trend':
				return TrendingUp;
			case 'anomaly':
				return AlertCircle;
			case 'pattern':
				return BarChart3;
			default:
				return Lightbulb;
		}
	}

	// Get severity color
	function getSeverityClass(severity: string) {
		switch (severity) {
			case 'critical':
				return 'text-error-600 dark:text-error-400 bg-error-50 dark:bg-error-900/20';
			case 'high':
				return 'text-warning-600 dark:text-warning-400 bg-warning-50 dark:bg-warning-900/20';
			case 'medium':
				return 'text-brand-600 dark:text-brand-400 bg-brand-50 dark:bg-brand-900/20';
			default:
				return 'text-neutral-600 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-800';
		}
	}
</script>

<div class="space-y-4 p-4 bg-gradient-to-br from-brand-50/50 to-neutral-50 dark:from-brand-950/20 dark:to-neutral-900 rounded-lg border border-brand-200/50 dark:border-brand-800/30">
	<!-- Headline Metrics -->
	{#if insights.insights.headline_metrics.length > 0}
		<div>
			<h4 class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">
				Key Metrics
			</h4>
			<div class="grid grid-cols-2 gap-2">
				{#each insights.insights.headline_metrics.slice(0, maxMetrics) as metric (metric.label)}
					<div class="bg-white dark:bg-neutral-800 rounded-md p-2 border border-neutral-200 dark:border-neutral-700">
						<div class="flex items-center justify-between">
							<span class="text-xs text-neutral-500 dark:text-neutral-400 truncate">{metric.label}</span>
							{#if metric.trend}
								{#if metric.trend.includes('up') || metric.trend.includes('increase')}
									<TrendingUp class="w-3 h-3 text-success-500" />
								{:else if metric.trend.includes('down') || metric.trend.includes('decrease')}
									<TrendingDown class="w-3 h-3 text-error-500" />
								{/if}
							{/if}
						</div>
						<div class="text-sm font-semibold text-neutral-900 dark:text-white mt-0.5">{metric.value}</div>
						{#if metric.context}
							<div class="text-[10px] text-neutral-400 dark:text-neutral-500 mt-0.5 truncate">{metric.context}</div>
						{/if}
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Top Insights -->
	{#if insights.insights.insights.length > 0}
		<div>
			<h4 class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">
				Notable Patterns
			</h4>
			<div class="space-y-1.5">
				{#each insights.insights.insights.slice(0, maxInsights) as insight (insight.headline)}
					{@const Icon = getInsightIcon(insight.type)}
					<div class="flex items-start gap-2 p-2 bg-white dark:bg-neutral-800 rounded-md border border-neutral-200 dark:border-neutral-700">
						<span class={`p-1 rounded ${getSeverityClass(insight.severity)}`}>
							<Icon class="w-3 h-3" />
						</span>
						<div class="flex-1 min-w-0">
							<div class="text-xs font-medium text-neutral-900 dark:text-white">{insight.headline}</div>
							<div class="text-[10px] text-neutral-500 dark:text-neutral-400 mt-0.5 line-clamp-2">
								<MarkdownContent content={insight.detail} class="text-[10px]" />
							</div>
						</div>
					</div>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Suggested Questions -->
	{#if insights.insights.suggested_questions.length > 0}
		<div>
			<h4 class="text-xs font-medium text-neutral-500 dark:text-neutral-400 uppercase tracking-wide mb-2">
				Explore Your Data
			</h4>
			<div class="flex flex-wrap gap-1.5">
				{#each insights.insights.suggested_questions.slice(0, maxQuestions) as sq (sq.question)}
					<button
						type="button"
						onclick={() => onQuestionClick(sq.question)}
						class="inline-flex items-center gap-1 px-2 py-1 text-xs bg-white dark:bg-neutral-800 text-brand-700 dark:text-brand-300 border border-brand-200 dark:border-brand-700 rounded-full hover:bg-brand-50 dark:hover:bg-brand-900/30 hover:border-brand-300 dark:hover:border-brand-600 transition-colors cursor-pointer"
						title={sq.why_relevant}
					>
						<Search class="w-3 h-3 opacity-50" />
						<span class="truncate max-w-[180px]">{sq.question}</span>
					</button>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Brief Summary -->
	{#if insights.insights.narrative_summary}
		<div class="text-xs text-neutral-600 dark:text-neutral-400 italic border-t border-neutral-200 dark:border-neutral-700 pt-3">
			<MarkdownContent content={insights.insights.narrative_summary} class="text-xs" />
		</div>
	{/if}
</div>
