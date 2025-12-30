<script lang="ts">
	/**
	 * DataInsightsPanel - Structured business intelligence display
	 *
	 * Renders AI-generated insights in an actionable, scannable format.
	 */
	import type {
		DatasetInsights,
		HeadlineMetric,
		Insight,
		InsightSeverity,
		DataQualityScore,
		SuggestedQuestion
	} from '$lib/api/types';
	import { ShimmerSkeleton } from '$lib/components/ui/loading';

	interface Props {
		insights: DatasetInsights | null;
		loading?: boolean;
		error?: string | null;
		onQuestionClick?: (question: string) => void;
		onRefresh?: () => void;
	}

	let {
		insights,
		loading = false,
		error = null,
		onQuestionClick,
		onRefresh
	}: Props = $props();

	// Severity styling
	function getSeverityClasses(severity: InsightSeverity): string {
		switch (severity) {
			case 'positive':
				return 'bg-success-50 dark:bg-success-900/20 border-success-200 dark:border-success-800 text-success-800 dark:text-success-200';
			case 'warning':
				return 'bg-warning-50 dark:bg-warning-900/20 border-warning-200 dark:border-warning-800 text-warning-800 dark:text-warning-200';
			case 'critical':
				return 'bg-error-50 dark:bg-error-900/20 border-error-200 dark:border-error-800 text-error-800 dark:text-error-200';
			default:
				return 'bg-neutral-50 dark:bg-neutral-800 border-neutral-200 dark:border-neutral-700 text-neutral-700 dark:text-neutral-300';
		}
	}

	function getSeverityIcon(severity: InsightSeverity): string {
		switch (severity) {
			case 'positive':
				return 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z';
			case 'warning':
				return 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z';
			case 'critical':
				return 'M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z';
			default:
				return 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z';
		}
	}

	function getTypeLabel(type: string): string {
		const labels: Record<string, string> = {
			trend: 'Trend',
			pattern: 'Pattern',
			anomaly: 'Anomaly',
			risk: 'Risk',
			opportunity: 'Opportunity',
			benchmark: 'Benchmark'
		};
		return labels[type] || type;
	}

	function getDomainLabel(domain: string): string {
		const labels: Record<string, string> = {
			ecommerce: 'E-commerce',
			saas: 'SaaS',
			services: 'Services',
			marketing: 'Marketing',
			finance: 'Finance',
			operations: 'Operations',
			hr: 'HR',
			product: 'Product',
			unknown: 'General'
		};
		return labels[domain] || domain;
	}

	function getQualityColor(score: number): string {
		if (score >= 80) return 'text-success-600 dark:text-success-400';
		if (score >= 60) return 'text-warning-600 dark:text-warning-400';
		return 'text-error-600 dark:text-error-400';
	}

	function getQualityBg(score: number): string {
		if (score >= 80) return 'bg-success-500';
		if (score >= 60) return 'bg-warning-500';
		return 'bg-error-500';
	}
</script>

{#if loading}
	<div class="space-y-4">
		<ShimmerSkeleton type="card" />
		<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
			{#each Array(4) as _}
				<ShimmerSkeleton type="card" />
			{/each}
		</div>
		<ShimmerSkeleton type="card" />
	</div>
{:else if error}
	<div class="bg-error-50 dark:bg-error-900/20 border border-error-200 dark:border-error-800 rounded-lg p-6">
		<div class="flex items-center gap-3">
			<svg class="w-6 h-6 text-error-600 dark:text-error-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
			</svg>
			<div>
				<h3 class="font-semibold text-error-900 dark:text-error-200">Failed to load insights</h3>
				<p class="text-sm text-error-700 dark:text-error-300">{error}</p>
			</div>
		</div>
		{#if onRefresh}
			<button
				onclick={onRefresh}
				class="mt-4 px-4 py-2 bg-error-600 hover:bg-error-700 text-white rounded-lg text-sm font-medium transition-colors"
			>
				Try Again
			</button>
		{/if}
	</div>
{:else if insights}
	<div class="space-y-6">
		<!-- Data Identity Card -->
		<div class="bg-gradient-to-r from-brand-50 to-brand-100 dark:from-brand-900/30 dark:to-brand-800/20 rounded-lg border border-brand-200 dark:border-brand-800 p-6">
			<div class="flex items-start justify-between">
				<div class="flex-1">
					<div class="flex items-center gap-2 mb-2">
						<span class="px-2 py-0.5 text-xs font-medium rounded-full bg-brand-200 dark:bg-brand-800 text-brand-800 dark:text-brand-200">
							{getDomainLabel(insights.identity.domain)}
						</span>
						{#if insights.identity.time_range}
							<span class="text-xs text-neutral-500 dark:text-neutral-400">
								{insights.identity.time_range}
							</span>
						{/if}
					</div>
					<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-1">
						{insights.identity.entity_type}
					</h3>
					<p class="text-sm text-neutral-600 dark:text-neutral-300">
						{insights.identity.description}
					</p>
				</div>
				{#if onRefresh}
					<button
						onclick={onRefresh}
						class="p-2 text-neutral-500 hover:text-neutral-700 dark:text-neutral-400 dark:hover:text-neutral-200 transition-colors"
						title="Regenerate insights"
					>
						<svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
							<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
						</svg>
					</button>
				{/if}
			</div>
		</div>

		<!-- Headline Metrics -->
		{#if insights.headline_metrics.length > 0}
			<div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
				{#each insights.headline_metrics as metric (metric.label)}
					<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-4">
						<div class="text-xs text-neutral-500 dark:text-neutral-400 mb-1">{metric.label}</div>
						<div class="text-xl font-bold text-neutral-900 dark:text-white">{metric.value}</div>
						{#if metric.context}
							<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">{metric.context}</div>
						{/if}
						{#if metric.trend}
							<div class="text-xs mt-1 {metric.is_good === true ? 'text-success-600 dark:text-success-400' : metric.is_good === false ? 'text-error-600 dark:text-error-400' : 'text-neutral-500'}">
								{metric.trend}
							</div>
						{/if}
					</div>
				{/each}
			</div>
		{/if}

		<!-- Key Insights -->
		{#if insights.insights.length > 0}
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
					</svg>
					Key Insights
				</h3>
				<div class="space-y-3">
					{#each insights.insights as insight (insight.headline)}
						<div class="rounded-lg border p-4 {getSeverityClasses(insight.severity)}">
							<div class="flex items-start gap-3">
								<svg class="w-5 h-5 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d={getSeverityIcon(insight.severity)} />
								</svg>
								<div class="flex-1 min-w-0">
									<div class="flex items-center gap-2 mb-1">
										<span class="text-xs font-medium opacity-70">{getTypeLabel(insight.type)}</span>
									</div>
									<h4 class="font-semibold">{insight.headline}</h4>
									<p class="text-sm mt-1 opacity-90">{insight.detail}</p>
									{#if insight.action}
										<p class="text-sm mt-2 font-medium">
											<span class="opacity-70">Action:</span> {insight.action}
										</p>
									{/if}
								</div>
							</div>
						</div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Data Quality + Suggested Questions Row -->
		<div class="grid md:grid-cols-2 gap-6">
			<!-- Data Quality Card -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
					</svg>
					Data Quality
				</h3>

				<!-- Score Ring -->
				<div class="flex items-center gap-6 mb-4">
					<div class="relative w-20 h-20">
						<svg class="w-20 h-20 transform -rotate-90">
							<circle
								cx="40"
								cy="40"
								r="36"
								stroke="currentColor"
								stroke-width="8"
								fill="transparent"
								class="text-neutral-200 dark:text-neutral-700"
							/>
							<circle
								cx="40"
								cy="40"
								r="36"
								stroke="currentColor"
								stroke-width="8"
								fill="transparent"
								stroke-dasharray={36 * 2 * Math.PI}
								stroke-dashoffset={36 * 2 * Math.PI * (1 - insights.quality.overall_score / 100)}
								class="{getQualityBg(insights.quality.overall_score)}"
								stroke-linecap="round"
							/>
						</svg>
						<div class="absolute inset-0 flex items-center justify-center">
							<span class="text-xl font-bold {getQualityColor(insights.quality.overall_score)}">{insights.quality.overall_score}</span>
						</div>
					</div>
					<div class="flex-1 space-y-2">
						<div class="flex justify-between text-sm">
							<span class="text-neutral-600 dark:text-neutral-400">Completeness</span>
							<span class="font-medium">{insights.quality.completeness}%</span>
						</div>
						<div class="flex justify-between text-sm">
							<span class="text-neutral-600 dark:text-neutral-400">Consistency</span>
							<span class="font-medium">{insights.quality.consistency}%</span>
						</div>
						{#if insights.quality.freshness !== null}
							<div class="flex justify-between text-sm">
								<span class="text-neutral-600 dark:text-neutral-400">Freshness</span>
								<span class="font-medium">{insights.quality.freshness}%</span>
							</div>
						{/if}
					</div>
				</div>

				<!-- Issues & Suggestions -->
				{#if insights.quality.issues.length > 0 || insights.quality.missing_data.length > 0}
					<div class="border-t border-neutral-200 dark:border-neutral-700 pt-4 mt-4">
						{#if insights.quality.issues.length > 0}
							<div class="mb-3">
								<h4 class="text-xs font-medium text-warning-600 dark:text-warning-400 mb-1">Issues</h4>
								<ul class="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
									{#each insights.quality.issues as issue}
										<li class="flex items-start gap-2">
											<span class="text-warning-500 mt-1">-</span>
											{issue}
										</li>
									{/each}
								</ul>
							</div>
						{/if}
						{#if insights.quality.suggestions.length > 0}
							<div>
								<h4 class="text-xs font-medium text-brand-600 dark:text-brand-400 mb-1">Suggestions</h4>
								<ul class="text-sm text-neutral-600 dark:text-neutral-400 space-y-1">
									{#each insights.quality.suggestions as suggestion}
										<li class="flex items-start gap-2">
											<span class="text-brand-500 mt-1">+</span>
											{suggestion}
										</li>
									{/each}
								</ul>
							</div>
						{/if}
					</div>
				{/if}
			</div>

			<!-- Suggested Questions -->
			<div class="bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-6">
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-4 flex items-center gap-2">
					<svg class="w-5 h-5 text-brand-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
					</svg>
					Explore Further
				</h3>
				<div class="space-y-3">
					{#each insights.suggested_questions as sq (sq.question)}
						<button
							onclick={() => onQuestionClick?.(sq.question)}
							class="w-full text-left p-3 rounded-lg border border-neutral-200 dark:border-neutral-700 hover:border-brand-300 dark:hover:border-brand-700 hover:bg-brand-50 dark:hover:bg-brand-900/20 transition-colors group"
						>
							<div class="font-medium text-neutral-900 dark:text-white group-hover:text-brand-700 dark:group-hover:text-brand-300">
								{sq.question}
							</div>
							<div class="text-xs text-neutral-500 dark:text-neutral-400 mt-1">
								{sq.why_relevant}
							</div>
						</button>
					{/each}
				</div>
			</div>
		</div>
	</div>
{:else}
	<div class="bg-neutral-50 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700 p-8 text-center">
		<svg class="w-12 h-12 mx-auto text-neutral-400 dark:text-neutral-500 mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
		</svg>
		<h3 class="text-lg font-semibold text-neutral-900 dark:text-white mb-2">No Insights Yet</h3>
		<p class="text-sm text-neutral-600 dark:text-neutral-400 mb-4">
			Generate a profile to unlock AI-powered business insights for this dataset.
		</p>
	</div>
{/if}
