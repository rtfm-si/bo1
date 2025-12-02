<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { MetaSynthesisCompleteEvent } from '$lib/api/sse-events';

	interface ActionItem {
		action: string;
		rationale: string;
		priority: 'critical' | 'high' | 'medium' | 'low';
		timeline: string;
		success_metrics: string[];
		risks: string[];
	}

	interface ActionPlanData {
		problem_statement: string;
		sub_problems_addressed: string[];
		recommended_actions: ActionItem[];
		synthesis_summary: string;
	}

	interface Props {
		event: MetaSynthesisCompleteEvent;
		subProblemIndex?: number;
	}

	let { event, subProblemIndex }: Props = $props();

	// Parse action plan from event data
	const actionPlan = $derived.by((): ActionPlanData | null => {
		try {
			// Try to parse as JSON first
			const synthesis = event.data.synthesis as string;

			// Look for JSON structure in the synthesis
			const jsonMatch = synthesis.match(/\{[\s\S]*"recommended_actions"[\s\S]*\}/);
			if (jsonMatch) {
				return JSON.parse(jsonMatch[0]) as ActionPlanData;
			}

			return null;
		} catch (error) {
			console.error('Failed to parse action plan:', error);
			return null;
		}
	});

	function getPriorityConfig(priority: 'critical' | 'high' | 'medium' | 'low') {
		return eventTokens.actionPriority[priority];
	}

	/**
	 * Filter actions for a specific sub-problem by parsing rationale text.
	 * Returns actions that mention the sub-problem number in their rationale.
	 * If no sub-problem index is provided, returns all actions.
	 */
	function filterActionsForSubProblem(actions: ActionItem[], subProblemIdx: number | undefined): ActionItem[] {
		if (subProblemIdx === undefined) {
			return actions; // Show all actions if no filter
		}

		return actions.filter(action => {
			// Match patterns like "sub-problem 1", "sub-problem 2", "(sub-problem 1)"
			const match = action.rationale.match(/sub-problem\s*(\d+)/gi);
			if (!match) {
				return true; // Show actions without sub-problem reference in all tabs
			}
			// Check if any match corresponds to the current sub-problem (1-indexed)
			return match.some(m => parseInt(m.replace(/\D/g, '')) === subProblemIdx + 1);
		});
	}

	// Filtered actions for current sub-problem (if applicable)
	const filteredActions = $derived.by(() => {
		if (!actionPlan) return [];
		return filterActionsForSubProblem(actionPlan.recommended_actions, subProblemIndex);
	});
</script>

{#if actionPlan}
	<div
		class="bg-neutral-50 dark:bg-neutral-900/50 rounded-xl p-6 border-2 border-neutral-300 dark:border-neutral-700"
	>
		<!-- Header -->
		<div class="mb-6">
			<div class="mb-3">
				<h2 class="text-[1.875rem] font-semibold leading-tight text-neutral-900 dark:text-white">Action Plan</h2>
			</div>
			<p class="text-[0.875rem] font-medium text-neutral-700 dark:text-neutral-300">
				{actionPlan.problem_statement}
			</p>
		</div>

		<!-- Synthesis Summary -->
		{#if actionPlan.synthesis_summary}
			<div class="mb-6 p-4 bg-white dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
				<h3 class="text-[1.25rem] font-medium leading-snug text-neutral-800 dark:text-neutral-100 mb-2">
					Executive Summary
				</h3>
				<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300">
					{actionPlan.synthesis_summary}
				</p>
			</div>
		{/if}

		<!-- Recommended Actions -->
		<div class="space-y-5 mb-6">
			<h3 class="text-xl sm:text-2xl font-semibold leading-tight text-neutral-900 dark:text-white">
				Recommended Actions
				{#if subProblemIndex !== undefined && filteredActions.length < actionPlan.recommended_actions.length}
					<span class="block sm:inline text-sm font-normal text-neutral-600 dark:text-neutral-400 mt-1 sm:mt-0 sm:ml-2">
						({filteredActions.length} of {actionPlan.recommended_actions.length} for this focus area)
					</span>
				{/if}
			</h3>
			{#each filteredActions as action, index (index)}
				{@const priorityConfig = getPriorityConfig(action.priority)}
				<div
					class="rounded-xl border-2 overflow-hidden {priorityConfig.bg} {priorityConfig.border}"
				>
					<!-- Action Header -->
					<div class="p-5 sm:p-6">
						<!-- Priority & Timeline badges -->
						<div class="flex flex-wrap items-center gap-2 mb-4">
							<span class="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-full {priorityConfig.badge}">
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 21v-4m0 0V5a2 2 0 012-2h6.5l1 1H21l-3 6 3 6h-8.5l-1-1H5a2 2 0 00-2 2zm9-13.5V9" />
								</svg>
								{priorityConfig.label}
							</span>
							<span class="inline-flex items-center gap-1.5 text-xs font-semibold px-3 py-1.5 rounded-full bg-neutral-200 text-neutral-700 dark:bg-neutral-700 dark:text-neutral-200">
								<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
									<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
								</svg>
								{action.timeline}
							</span>
						</div>

						<!-- Action Title -->
						<h4 class="text-base sm:text-lg font-semibold leading-snug {priorityConfig.text} mb-4">
							{action.action}
						</h4>

						<!-- Rationale -->
						<div class="bg-white/50 dark:bg-neutral-800/50 rounded-lg p-4 mb-4">
							<h5 class="text-xs font-semibold uppercase tracking-wide text-neutral-500 dark:text-neutral-400 mb-2">
								Rationale
							</h5>
							<p class="text-sm leading-relaxed text-neutral-700 dark:text-neutral-300">
								{action.rationale}
							</p>
						</div>

						<!-- Success Metrics & Risks Grid -->
						<div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
							<!-- Success Metrics -->
							<div class="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
								<h5 class="text-xs font-semibold uppercase tracking-wide text-green-700 dark:text-green-300 mb-3 flex items-center gap-2">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
									</svg>
									Success Metrics
								</h5>
								<ul class="space-y-2">
									{#each action.success_metrics as metric (metric)}
										<li class="flex items-start gap-2 text-sm text-green-800 dark:text-green-200 leading-relaxed">
											<span class="text-green-500 dark:text-green-400 mt-0.5 flex-shrink-0">✓</span>
											<span>{metric}</span>
										</li>
									{/each}
								</ul>
							</div>

							<!-- Risks -->
							<div class="bg-amber-50 dark:bg-amber-900/20 rounded-lg p-4">
								<h5 class="text-xs font-semibold uppercase tracking-wide text-amber-700 dark:text-amber-300 mb-3 flex items-center gap-2">
									<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
										<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
									</svg>
									Risks to Consider
								</h5>
								<ul class="space-y-2">
									{#each action.risks as risk (risk)}
										<li class="flex items-start gap-2 text-sm text-amber-800 dark:text-amber-200 leading-relaxed">
											<span class="text-amber-500 dark:text-amber-400 mt-0.5 flex-shrink-0">⚠</span>
											<span>{risk}</span>
										</li>
									{/each}
								</ul>
							</div>
						</div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Sub-problems Reference -->
		{#if actionPlan.sub_problems_addressed && actionPlan.sub_problems_addressed.length > 0}
			<div class="pt-4 border-t border-neutral-300 dark:border-neutral-600">
				<p class="text-[0.75rem] text-neutral-600 dark:text-neutral-400">
					<span class="font-semibold">Analysis based on:</span>
					{actionPlan.sub_problems_addressed.length} focus area{actionPlan.sub_problems_addressed.length !== 1 ? 's' : ''} deliberated
					({actionPlan.sub_problems_addressed.join(', ')})
				</p>
			</div>
		{/if}
	</div>
{:else}
	<!-- Fallback: Show synthesis as prose if not structured -->
	<div class="bg-neutral-50 dark:bg-neutral-900/50 rounded-lg p-4 border border-neutral-200 dark:border-neutral-700">
		<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300 whitespace-pre-wrap">
			{event.data.synthesis}
		</p>
	</div>
{/if}
