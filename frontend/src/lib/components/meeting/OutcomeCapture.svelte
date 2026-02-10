<script lang="ts">
	/**
	 * OutcomeCapture - Records what happened after a decision
	 * Used within DecisionGate after a decision is submitted.
	 */
	import { apiClient } from '$lib/api/client';
	import { BoButton } from '$lib/components/ui';
	import type { DecisionOutcomeResponse } from '$lib/api/types';

	interface Props {
		sessionId: string;
		existingOutcome?: DecisionOutcomeResponse | null;
		onsubmitted?: (outcome: DecisionOutcomeResponse) => void;
	}

	let { sessionId, existingOutcome = null, onsubmitted }: Props = $props();

	type OutcomeStatus = 'successful' | 'partially_successful' | 'unsuccessful' | 'too_early';

	let outcomeStatus = $state<OutcomeStatus>(
		(existingOutcome?.outcome_status as OutcomeStatus) ?? 'successful'
	);
	let outcomeNotes = $state(existingOutcome?.outcome_notes ?? '');
	let surpriseFactor = $state(existingOutcome?.surprise_factor ?? 3);
	let lessonsLearned = $state(existingOutcome?.lessons_learned ?? '');
	let whatWouldChange = $state(existingOutcome?.what_would_change ?? '');
	let submitting = $state(false);
	let error = $state('');

	const statusOptions: { value: OutcomeStatus; label: string }[] = [
		{ value: 'successful', label: 'Successful' },
		{ value: 'partially_successful', label: 'Partially Successful' },
		{ value: 'unsuccessful', label: 'Unsuccessful' },
		{ value: 'too_early', label: 'Too Early to Tell' }
	];

	const surpriseLabels = ['Expected', 'Slightly surprising', 'Somewhat surprising', 'Quite surprising', 'Totally unexpected'];

	async function handleSubmit() {
		submitting = true;
		error = '';
		try {
			const outcome = await apiClient.submitDecisionOutcome(sessionId, {
				outcome_status: outcomeStatus,
				outcome_notes: outcomeNotes.trim() || null,
				surprise_factor: surpriseFactor,
				lessons_learned: lessonsLearned.trim() || null,
				what_would_change: whatWouldChange.trim() || null
			});
			onsubmitted?.(outcome);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to save outcome';
			console.error('Failed to submit outcome:', e);
		} finally {
			submitting = false;
		}
	}
</script>

<div class="space-y-5">
	<h4 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
		{existingOutcome ? 'Update Outcome' : 'Record Outcome'}
	</h4>

	<!-- Outcome status -->
	<div>
		<p class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
			How did it turn out?
		</p>
		<div class="flex flex-wrap gap-2">
			{#each statusOptions as opt (opt.value)}
				<button
					type="button"
					class="px-3 py-1.5 text-sm rounded-full border transition-colors {outcomeStatus === opt.value
						? 'bg-brand-100 dark:bg-brand-900 border-brand-300 dark:border-brand-700 text-brand-700 dark:text-brand-300'
						: 'border-neutral-300 dark:border-neutral-600 text-neutral-600 dark:text-neutral-400 hover:border-neutral-400'}"
					onclick={() => (outcomeStatus = opt.value)}
				>
					{opt.label}
				</button>
			{/each}
		</div>
	</div>

	<!-- Surprise factor slider -->
	<div>
		<label for="surprise-factor" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
			How surprising was this outcome?
		</label>
		<div class="flex items-center gap-3">
			<input
				id="surprise-factor"
				type="range"
				min="1"
				max="5"
				bind:value={surpriseFactor}
				class="flex-1 h-2 bg-neutral-200 dark:bg-neutral-700 rounded-lg appearance-none cursor-pointer accent-brand-600"
			/>
			<span class="text-sm text-neutral-600 dark:text-neutral-400 w-40 text-right">
				{surpriseFactor} — {surpriseLabels[surpriseFactor - 1]}
			</span>
		</div>
	</div>

	<!-- What happened -->
	<div>
		<label for="outcome-notes" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
			What happened?
		</label>
		<textarea
			id="outcome-notes"
			bind:value={outcomeNotes}
			rows="3"
			class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			placeholder="Describe the actual outcome..."
		></textarea>
	</div>

	<!-- Lessons learned -->
	<div>
		<label for="lessons-learned" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
			Lessons learned
		</label>
		<textarea
			id="lessons-learned"
			bind:value={lessonsLearned}
			rows="2"
			class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			placeholder="What did you learn from this?"
		></textarea>
	</div>

	<!-- What would you change -->
	<div>
		<label for="what-would-change" class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-1">
			What would you do differently?
		</label>
		<textarea
			id="what-would-change"
			bind:value={whatWouldChange}
			rows="2"
			class="w-full px-3 py-2 rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-900 dark:text-neutral-100 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500"
			placeholder="Knowing what you know now..."
		></textarea>
	</div>

	{#if error}
		<p class="text-sm text-error-600 dark:text-error-400">{error}</p>
	{/if}

	<div class="flex justify-end">
		<BoButton variant="brand" onclick={handleSubmit} disabled={submitting}>
			{submitting ? 'Saving...' : existingOutcome ? 'Update Outcome' : 'Record Outcome'}
		</BoButton>
	</div>
</div>
