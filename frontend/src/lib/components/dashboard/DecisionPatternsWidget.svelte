<script lang="ts">
	/**
	 * DecisionPatternsWidget - Dashboard widget showing decision-making patterns.
	 * Displays confidence calibration, outcome breakdown, bias alerts.
	 */
	import { onMount } from 'svelte';
	import { apiClient } from '$lib/api/client';
	import type { DecisionPatternsResponse } from '$lib/api/types';
	import { AlertTriangle, BarChart3, Target } from 'lucide-svelte';

	let patterns = $state<DecisionPatternsResponse | null>(null);
	let isLoading = $state(true);
	let error = $state<string | null>(null);

	onMount(async () => {
		try {
			patterns = await apiClient.getDecisionPatterns();
		} catch (e) {
			error = 'Failed to load';
			console.error(e);
		} finally {
			isLoading = false;
		}
	});

	const OUTCOME_LABELS: Record<string, { label: string; color: string }> = {
		successful: { label: 'Successful', color: 'bg-success-100 text-success-800 dark:bg-success-900/30 dark:text-success-200' },
		partially_successful: { label: 'Partial', color: 'bg-warning-100 text-warning-800 dark:bg-warning-900/30 dark:text-warning-200' },
		unsuccessful: { label: 'Unsuccessful', color: 'bg-error-100 text-error-800 dark:bg-error-900/30 dark:text-error-200' },
		too_early: { label: 'Too Early', color: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300' },
	};

	const SEVERITY_COLORS: Record<string, string> = {
		high: 'border-error-300 bg-error-50 dark:border-error-700 dark:bg-error-900/20',
		medium: 'border-warning-300 bg-warning-50 dark:border-warning-700 dark:bg-warning-900/20',
		low: 'border-neutral-300 bg-neutral-50 dark:border-neutral-700 dark:bg-neutral-900/20',
	};
</script>

{#if isLoading}
	<div class="bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-200 dark:border-neutral-700">
		<div class="animate-pulse flex items-center gap-3">
			<div class="w-10 h-10 bg-neutral-200 dark:bg-neutral-700 rounded-lg"></div>
			<div class="flex-1 space-y-2">
				<div class="h-4 bg-neutral-200 dark:bg-neutral-700 rounded w-3/4"></div>
				<div class="h-3 bg-neutral-200 dark:bg-neutral-700 rounded w-1/2"></div>
			</div>
		</div>
	</div>
{:else if error || !patterns}
	<!-- Silent fail — don't show widget if no data -->
{:else if !patterns.has_enough_data}
	<div class="bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-200 dark:border-neutral-700">
		<div class="flex items-center gap-3">
			<div class="w-10 h-10 bg-neutral-100 dark:bg-neutral-700 rounded-lg flex items-center justify-center">
				<BarChart3 class="w-5 h-5 text-neutral-400" />
			</div>
			<div class="flex-1 min-w-0">
				<p class="font-medium text-neutral-900 dark:text-white text-sm">Decision Patterns</p>
				<p class="text-xs text-neutral-500 dark:text-neutral-400 mt-0.5">
					{patterns.total_decisions} of 3 decisions needed for insights
				</p>
			</div>
		</div>
	</div>
{:else}
	<div class="bg-white dark:bg-neutral-800 rounded-xl p-4 border border-neutral-200 dark:border-neutral-700 space-y-4">
		<div class="flex items-center gap-3">
			<div class="w-10 h-10 bg-brand-100 dark:bg-brand-900/50 rounded-lg flex items-center justify-center flex-shrink-0">
				<BarChart3 class="w-5 h-5 text-brand-600 dark:text-brand-400" />
			</div>
			<div class="flex-1 min-w-0">
				<p class="font-medium text-neutral-900 dark:text-white text-sm">Decision Patterns</p>
				<p class="text-xs text-neutral-500 dark:text-neutral-400">
					{patterns.total_decisions} decisions analyzed
				</p>
			</div>
		</div>

		<!-- Confidence Calibration -->
		{#if patterns.confidence_calibration.success_rate !== null}
			<div class="flex items-center gap-2">
				<Target class="w-4 h-4 text-neutral-400 flex-shrink-0" />
				<div class="flex-1">
					<div class="flex items-center justify-between text-xs mb-1">
						<span class="text-neutral-600 dark:text-neutral-400">Success rate</span>
						<span class="font-medium text-neutral-900 dark:text-white">
							{Math.round(patterns.confidence_calibration.success_rate * 100)}%
						</span>
					</div>
					<div class="h-1.5 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
						<div
							class="h-full bg-success-500 rounded-full transition-all"
							style="width: {Math.round(patterns.confidence_calibration.success_rate * 100)}%"
						></div>
					</div>
				</div>
			</div>
		{/if}

		<!-- Outcome Breakdown -->
		{#if Object.keys(patterns.outcome_breakdown).length > 0}
			<div class="flex flex-wrap gap-1.5">
				{#each Object.entries(patterns.outcome_breakdown) as [status, count] (status)}
					{@const meta = OUTCOME_LABELS[status] ?? { label: status, color: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-300' }}
					<span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium {meta.color}">
						{meta.label}: {count}
					</span>
				{/each}
			</div>
		{/if}

		<!-- Matrix usage -->
		{#if patterns.matrix_usage_pct !== null}
			<p class="text-xs text-neutral-500 dark:text-neutral-400">
				Decision matrix used in {Math.round(patterns.matrix_usage_pct)}% of decisions
			</p>
		{/if}

		<!-- Constraint accuracy -->
		{#if patterns.constraint_accuracy}
			{@const ca = patterns.constraint_accuracy}
			<div class="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-400">
				<span>Constraints: {ca.violations_chosen} violation{ca.violations_chosen !== 1 ? 's' : ''} chosen</span>
				{#if ca.violations_chosen > 0}
					<span class="text-neutral-400 dark:text-neutral-600">&middot;</span>
					<span>{ca.violations_successful} succeeded</span>
				{/if}
				{#if ca.tensions_chosen > 0}
					<span class="text-neutral-400 dark:text-neutral-600">&middot;</span>
					<span>{ca.tensions_chosen} tension{ca.tensions_chosen !== 1 ? 's' : ''}</span>
				{/if}
			</div>
		{/if}

		<!-- Monthly trend sparkline -->
		{#if patterns.monthly_trends.length > 1}
			<div>
				<p class="text-xs text-neutral-500 dark:text-neutral-400 mb-1">Monthly success rate</p>
				<div class="flex items-end gap-0.5 h-8">
					{#each patterns.monthly_trends as trend (trend.month)}
						{@const rate = trend.success_rate ?? 0}
						{@const pct = Math.max(rate * 100, 4)}
						<div
							class="flex-1 rounded-sm transition-all {rate >= 0.7 ? 'bg-success-400 dark:bg-success-600' : rate >= 0.4 ? 'bg-warning-400 dark:bg-warning-600' : 'bg-error-400 dark:bg-error-600'}"
							style="height: {pct}%"
							title="{trend.month}: {trend.success_rate !== null ? Math.round(trend.success_rate * 100) + '%' : 'N/A'} ({trend.total_decisions} decisions)"
						></div>
					{/each}
				</div>
			</div>
		{/if}

		<!-- Bias Flags -->
		{#if patterns.bias_flags.length > 0}
			<div class="space-y-2">
				{#each patterns.bias_flags as flag (flag.bias_type)}
					<div class="flex items-start gap-2 p-2 rounded-lg border {SEVERITY_COLORS[flag.severity] ?? SEVERITY_COLORS.low}">
						<AlertTriangle class="w-3.5 h-3.5 text-warning-500 flex-shrink-0 mt-0.5" />
						<p class="text-xs text-neutral-700 dark:text-neutral-300">{flag.description}</p>
					</div>
				{/each}
			</div>
		{/if}
	</div>
{/if}
