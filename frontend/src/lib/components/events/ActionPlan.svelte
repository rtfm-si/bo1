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
		<div class="space-y-4 mb-6">
			<h3 class="text-[1.5rem] font-semibold leading-tight text-neutral-900 dark:text-white">
				Recommended Actions
				{#if subProblemIndex !== undefined && filteredActions.length < actionPlan.recommended_actions.length}
					<span class="text-[0.875rem] font-normal text-neutral-600 dark:text-neutral-400">
						({filteredActions.length} of {actionPlan.recommended_actions.length} for this focus area)
					</span>
				{/if}
			</h3>
			{#each filteredActions as action, index (index)}
				{@const priorityConfig = getPriorityConfig(action.priority)}
				<div
					class="p-4 rounded-lg border-2 {priorityConfig.bg} {priorityConfig.border}"
				>
					<!-- Action Header -->
					<div class="flex items-start justify-between gap-3 mb-3">
						<div class="flex-1">
							<div class="flex items-center gap-2 mb-2">
								<span class="text-[0.75rem] font-bold px-2 py-1 rounded {priorityConfig.badge}">
									{priorityConfig.label}
								</span>
								<span class="text-[0.75rem] font-semibold px-2 py-1 rounded bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300">
									{action.timeline}
								</span>
							</div>
							<p class="text-[0.875rem] font-semibold {priorityConfig.text}">
								{action.action}
							</p>
						</div>
					</div>

					<!-- Rationale -->
					<div class="mb-3">
						<p class="text-[0.75rem] font-medium text-neutral-600 dark:text-neutral-400 mb-1">
							Rationale
						</p>
						<p class="text-[0.875rem] font-normal leading-relaxed text-neutral-700 dark:text-neutral-300">
							{action.rationale}
						</p>
					</div>

					<!-- Success Metrics & Risks Grid -->
					<div class="grid grid-cols-1 md:grid-cols-2 gap-3">
						<!-- Success Metrics -->
						<div>
							<p class="text-[0.75rem] font-medium text-neutral-600 dark:text-neutral-400 mb-2">
								Success Metrics
							</p>
							<ul class="space-y-1">
								{#each action.success_metrics as metric (metric)}
									<li class="text-[0.75rem] text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5">
										<span class="text-neutral-500 dark:text-neutral-400 mt-0.5">•</span>
										<span>{metric}</span>
									</li>
								{/each}
							</ul>
						</div>

						<!-- Risks -->
						<div>
							<p class="text-[0.75rem] font-medium text-neutral-600 dark:text-neutral-400 mb-2">
								Risks to Consider
							</p>
							<ul class="space-y-1">
								{#each action.risks as risk (risk)}
									<li class="text-[0.75rem] text-neutral-700 dark:text-neutral-300 flex items-start gap-1.5">
										<span class="text-neutral-500 dark:text-neutral-400 mt-0.5">•</span>
										<span>{risk}</span>
									</li>
								{/each}
							</ul>
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
