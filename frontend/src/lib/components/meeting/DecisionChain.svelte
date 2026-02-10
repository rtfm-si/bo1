<script lang="ts">
	/**
	 * DecisionChain - Visual chain: Decision → Actions → Outcome
	 * Shows the complete lifecycle of a decision.
	 */
	import type { UserDecisionResponse, DecisionOutcomeResponse } from '$lib/api/types';
	import { CheckCircle2, Circle, Clock } from 'lucide-svelte';

	interface ChainAction {
		id: string;
		title: string;
		status: string;
	}

	interface Props {
		decision: UserDecisionResponse;
		actions?: ChainAction[];
		outcome?: DecisionOutcomeResponse | null;
	}

	let { decision, actions = [], outcome = null }: Props = $props();

	const outcomeStatusLabel: Record<string, string> = {
		successful: 'Successful',
		partially_successful: 'Partially Successful',
		unsuccessful: 'Unsuccessful',
		too_early: 'Too Early to Tell'
	};

	const outcomeStatusColor: Record<string, string> = {
		successful: 'text-success-600 dark:text-success-400',
		partially_successful: 'text-warning-600 dark:text-warning-400',
		unsuccessful: 'text-error-600 dark:text-error-400',
		too_early: 'text-neutral-500 dark:text-neutral-400'
	};

	const actionStatusBadge: Record<string, string> = {
		pending: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400',
		in_progress: 'bg-brand-100 dark:bg-brand-900 text-brand-700 dark:text-brand-300',
		completed: 'bg-success-100 dark:bg-success-900 text-success-700 dark:text-success-300',
		cancelled: 'bg-neutral-100 dark:bg-neutral-800 text-neutral-500 dark:text-neutral-500'
	};
</script>

<div class="space-y-3">
	<p class="text-xs font-medium uppercase tracking-wider text-neutral-500 dark:text-neutral-400">
		Decision Chain
	</p>

	<!-- Decision node -->
	<div class="flex items-start gap-3">
		<div class="flex flex-col items-center">
			<CheckCircle2 class="w-5 h-5 text-brand-600 dark:text-brand-400" />
			{#if actions.length > 0 || outcome}
				<div class="w-px h-4 bg-neutral-300 dark:bg-neutral-600"></div>
			{/if}
		</div>
		<div class="text-sm">
			<span class="font-medium text-neutral-900 dark:text-neutral-100">Decision:</span>
			<span class="text-neutral-700 dark:text-neutral-300">{decision.chosen_option_label}</span>
		</div>
	</div>

	<!-- Actions node -->
	{#if actions.length > 0}
		<div class="flex items-start gap-3">
			<div class="flex flex-col items-center">
				<Circle class="w-5 h-5 text-neutral-400 dark:text-neutral-500" />
				{#if outcome}
					<div class="w-px h-4 bg-neutral-300 dark:bg-neutral-600"></div>
				{/if}
			</div>
			<div class="text-sm">
				<span class="font-medium text-neutral-900 dark:text-neutral-100">Actions:</span>
				<div class="mt-1 flex flex-wrap gap-1.5">
					{#each actions.slice(0, 5) as action (action.id)}
						<span class="inline-flex items-center px-2 py-0.5 rounded text-xs {actionStatusBadge[action.status] ?? actionStatusBadge.pending}">
							{action.title?.slice(0, 40) ?? 'Action'}{(action.title?.length ?? 0) > 40 ? '...' : ''}
						</span>
					{/each}
					{#if actions.length > 5}
						<span class="text-xs text-neutral-500">+{actions.length - 5} more</span>
					{/if}
				</div>
			</div>
		</div>
	{/if}

	<!-- Outcome node -->
	{#if outcome}
		<div class="flex items-start gap-3">
			<div class="flex flex-col items-center">
				{#if outcome.outcome_status === 'successful'}
					<CheckCircle2 class="w-5 h-5 text-success-500" />
				{:else if outcome.outcome_status === 'too_early'}
					<Clock class="w-5 h-5 text-neutral-400" />
				{:else}
					<Circle class="w-5 h-5 {outcomeStatusColor[outcome.outcome_status] ?? 'text-neutral-400'}" />
				{/if}
			</div>
			<div class="text-sm">
				<span class="font-medium text-neutral-900 dark:text-neutral-100">Outcome:</span>
				<span class="{outcomeStatusColor[outcome.outcome_status] ?? 'text-neutral-600'}">
					{outcomeStatusLabel[outcome.outcome_status] ?? outcome.outcome_status}
				</span>
				{#if outcome.outcome_notes}
					<p class="mt-1 text-xs text-neutral-600 dark:text-neutral-400 line-clamp-2">
						{outcome.outcome_notes}
					</p>
				{/if}
			</div>
		</div>
	{:else}
		<div class="flex items-start gap-3">
			<div class="flex flex-col items-center">
				<Circle class="w-5 h-5 text-neutral-300 dark:text-neutral-600" />
			</div>
			<div class="text-sm text-neutral-500 dark:text-neutral-400 italic">
				Outcome not yet recorded
			</div>
		</div>
	{/if}
</div>
