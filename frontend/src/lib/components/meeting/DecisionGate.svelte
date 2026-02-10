<script lang="ts">
	/**
	 * DecisionGate - Main decision capture component
	 * Renders after synthesis when session is completed and options are extracted.
	 * States: selecting → rationale → submitted
	 */
	import type { OptionCard } from '$lib/api/sse-events';
	import { apiClient } from '$lib/api/client';
	import { BoButton } from '$lib/components/ui';
	import OptionComparisonCard from './OptionComparisonCard.svelte';
	import RationaleCapture, { type DecisionRationale } from './RationaleCapture.svelte';
	import DecisionMatrix from './DecisionMatrix.svelte';
	import OutcomeCapture from './OutcomeCapture.svelte';
	import DecisionChain from './DecisionChain.svelte';
	import { Scale, CheckCircle2, AlertTriangle } from 'lucide-svelte';
	import type { UserDecisionResponse, DecisionOutcomeResponse } from '$lib/api/types';

	interface Props {
		sessionId: string;
		options: OptionCard[];
		dissenting_views: string[];
		premortemText?: string;
	}

	let { sessionId, options, dissenting_views, premortemText = '' }: Props = $props();

	type GateState = 'selecting' | 'rationale' | 'submitted';

	let gateState = $state<GateState>('selecting');
	let selectedOptionId = $state<string | null>(null);
	let showMatrix = $state(false);
	let submitting = $state(false);
	let existingDecision = $state<UserDecisionResponse | null>(null);
	let matrixSnapshot = $state<Record<string, unknown> | null>(null);
	let existingOutcome = $state<DecisionOutcomeResponse | null>(null);
	let showOutcomeForm = $state(false);
	let sessionActions = $state<{ id: string; title: string; status: string }[]>([]);

	const selectedOption = $derived(options.find((o) => o.id === selectedOptionId) ?? null);

	// Constraint violation detection
	const violatedConstraints = $derived.by(() => {
		if (!selectedOption?.constraint_alignment) return [];
		return Object.entries(selectedOption.constraint_alignment)
			.filter(([, status]) => status === 'violation')
			.map(([desc]) => desc);
	});
	const selectedHasViolations = $derived(violatedConstraints.length > 0);
	let violationAcknowledged = $state(false);

	// Reset acknowledgment when option changes
	$effect(() => {
		selectedOptionId;
		violationAcknowledged = false;
	});

	// Decision is old enough for outcome recording (>7 days)
	const isOldEnoughForOutcome = $derived.by(() => {
		if (!existingDecision) return false;
		const created = new Date(existingDecision.created_at);
		const now = new Date();
		const daysDiff = (now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24);
		return daysDiff >= 7;
	});

	// Fetch existing decision on mount
	$effect(() => {
		loadExistingDecision();
	});

	async function loadExistingDecision() {
		try {
			const decision = await apiClient.getDecision(sessionId);
			if (decision) {
				existingDecision = decision;
				selectedOptionId = decision.chosen_option_id;
				gateState = 'submitted';
				// Load outcome and actions in parallel
				const [outcome, actionsResp] = await Promise.all([
					apiClient.getDecisionOutcome(sessionId).catch(() => null),
					apiClient.getSessionActions(sessionId).catch(() => null)
				]);
				existingOutcome = outcome;
				sessionActions = (actionsResp?.tasks ?? []).map((t) => ({
					id: t.id,
					title: t.title,
					status: t.status
				}));
			}
		} catch {
			// No existing decision, stay in selecting state
		}
	}

	function selectOption(optionId: string) {
		selectedOptionId = optionId;
	}

	function proceedToRationale() {
		if (selectedOptionId) {
			gateState = 'rationale';
		}
	}

	function applyMatrixWinner(optionId: string) {
		selectedOptionId = optionId;
		showMatrix = false;
	}

	async function submitDecision(rationale: DecisionRationale) {
		if (!selectedOption) return;

		submitting = true;
		try {
			const enrichedRationale: Record<string, unknown> = {
				...(rationale as unknown as Record<string, unknown>)
			};
			if (premortemText.trim()) {
				enrichedRationale.pre_mortem = premortemText.trim();
			}
			if (selectedOption.constraint_alignment) {
				enrichedRationale.constraint_alignment = selectedOption.constraint_alignment;
			}
			if (violationAcknowledged && violatedConstraints.length > 0) {
				enrichedRationale.constraints_violated_acknowledged = violatedConstraints;
			}
			const decision = await apiClient.submitDecision(sessionId, {
				chosen_option_id: selectedOption.id,
				chosen_option_label: selectedOption.label,
				chosen_option_description: selectedOption.description,
				rationale: enrichedRationale,
				matrix_snapshot: matrixSnapshot,
				decision_source: matrixSnapshot ? 'matrix' : 'direct'
			});
			existingDecision = decision;
			gateState = 'submitted';
		} catch (e) {
			console.error('Failed to submit decision:', e);
		} finally {
			submitting = false;
		}
	}

	function handleOutcomeSubmitted(outcome: DecisionOutcomeResponse) {
		existingOutcome = outcome;
		showOutcomeForm = false;
	}
</script>

<div id="decision-gate" class="mt-8">
	<div class="border-t-2 border-brand-200 dark:border-brand-800 pt-6">
		<!-- Header -->
		<div class="flex items-center gap-3 mb-6">
			<div
				class="w-10 h-10 rounded-full bg-brand-100 dark:bg-brand-900 flex items-center justify-center"
			>
				<Scale class="w-5 h-5 text-brand-600 dark:text-brand-400" />
			</div>
			<div>
				<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
					What's Your Decision?
				</h3>
				<p class="text-sm text-neutral-500 dark:text-neutral-400">
					{gateState === 'submitted'
						? 'Your decision has been recorded'
						: 'Review the options and make your choice'}
				</p>
			</div>
		</div>

		{#if gateState === 'selecting'}
			<!-- Option cards grid -->
			<div class="grid gap-4 {options.length <= 3 ? 'sm:grid-cols-3' : 'sm:grid-cols-2 lg:grid-cols-3'}">
				{#each options as option (option.id)}
					<OptionComparisonCard
						{option}
						selected={selectedOptionId === option.id}
						onclick={() => selectOption(option.id)}
					/>
				{/each}
			</div>

			<!-- Decision Matrix toggle -->
			<div class="mt-4">
				<button
					type="button"
					class="text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 dark:hover:text-brand-300 flex items-center gap-1.5"
					onclick={() => (showMatrix = !showMatrix)}
				>
					<Scale class="w-4 h-4" />
					{showMatrix ? 'Hide' : 'Use'} Decision Matrix
				</button>
				{#if showMatrix}
					<div class="mt-4 p-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
						<DecisionMatrix {options} onapply={applyMatrixWinner} />
					</div>
				{/if}
			</div>

			<!-- Proceed button -->
			{#if selectedOptionId}
				{#if selectedHasViolations && !violationAcknowledged}
					<div class="mt-4 p-3 rounded-lg border border-warning-300 dark:border-warning-700 bg-warning-50 dark:bg-warning-900/20">
						<div class="flex items-start gap-2">
							<AlertTriangle class="w-4 h-4 text-warning-600 dark:text-warning-400 flex-shrink-0 mt-0.5" />
							<div class="flex-1">
								<p class="text-sm font-medium text-warning-800 dark:text-warning-200">
									This option has constraint violations
								</p>
								<ul class="mt-1 text-xs text-warning-700 dark:text-warning-300 space-y-0.5">
									{#each violatedConstraints as constraint}
										<li>&bull; {constraint}</li>
									{/each}
								</ul>
								<label class="mt-2 flex items-center gap-2 cursor-pointer">
									<input type="checkbox" bind:checked={violationAcknowledged} class="rounded border-warning-400" />
									<span class="text-xs text-warning-800 dark:text-warning-200">I understand and want to proceed</span>
								</label>
							</div>
						</div>
					</div>
				{/if}
				<div class="mt-4 flex justify-end">
					<BoButton variant="brand" onclick={proceedToRationale} disabled={selectedHasViolations && !violationAcknowledged}>
						Continue with "{selectedOption?.label}"
					</BoButton>
				</div>
			{/if}
		{:else if gateState === 'rationale' && selectedOption}
			<RationaleCapture
				option={selectedOption}
				{dissenting_views}
				{submitting}
				onsubmit={submitDecision}
				onback={() => (gateState = 'selecting')}
			/>
		{:else if gateState === 'submitted' && existingDecision}
			<!-- Confirmation view -->
			<div class="p-6 rounded-xl border border-success-200 dark:border-success-800 bg-success-50 dark:bg-success-950">
				<div class="flex items-start gap-3">
					<CheckCircle2 class="w-6 h-6 text-success-500 flex-shrink-0 mt-0.5" />
					<div class="flex-1">
						<h4 class="text-base font-semibold text-success-800 dark:text-success-200">
							Decision Recorded
						</h4>
						<p class="mt-1 text-sm text-success-700 dark:text-success-300">
							<strong>{existingDecision.chosen_option_label}</strong>
						</p>
						{#if existingDecision.chosen_option_description}
							<p class="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
								{existingDecision.chosen_option_description}
							</p>
						{/if}
						<button
							type="button"
							class="mt-3 text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 underline"
							onclick={() => (gateState = 'selecting')}
						>
							Change decision
						</button>
					</div>
				</div>
			</div>

			<!-- Decision Chain visualization -->
			<div class="mt-6 p-4 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
				<DecisionChain
					decision={existingDecision}
					actions={sessionActions}
					outcome={existingOutcome}
				/>
			</div>

			<!-- Outcome recording -->
			{#if showOutcomeForm}
				<div class="mt-6 p-5 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800">
					<OutcomeCapture
						{sessionId}
						{existingOutcome}
						onsubmitted={handleOutcomeSubmitted}
					/>
				</div>
			{:else if existingOutcome}
				<div class="mt-4 flex justify-end">
					<button
						type="button"
						class="text-sm text-brand-600 dark:text-brand-400 hover:text-brand-700 underline"
						onclick={() => (showOutcomeForm = true)}
					>
						Update outcome
					</button>
				</div>
			{:else if isOldEnoughForOutcome}
				<div class="mt-4 flex justify-end">
					<BoButton variant="secondary" onclick={() => (showOutcomeForm = true)}>
						Record Outcome
					</BoButton>
				</div>
			{/if}
		{/if}
	</div>
</div>
