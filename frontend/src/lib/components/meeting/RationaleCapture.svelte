<script lang="ts">
	/**
	 * RationaleCapture - Structured rationale form for decision recording
	 */
	import type { OptionCard } from '$lib/api/sse-events';
	import { BoButton } from '$lib/components/ui';

	interface Props {
		option: OptionCard;
		dissenting_views: string[];
		submitting?: boolean;
		onsubmit: (rationale: DecisionRationale) => void;
		onback: () => void;
	}

	export interface DecisionRationale {
		tradeoffs_accepted: string[];
		concerns_overridden: string[];
		confidence: number;
		free_text: string | null;
	}

	let { option, dissenting_views, submitting = false, onsubmit, onback }: Props = $props();

	// Form state
	let tradeoffsAccepted = $state<Set<string>>(new Set());
	let concernsOverridden = $state<Set<string>>(new Set());
	let confidence = $state(70);
	let freeText = $state('');

	function handleSubmit() {
		onsubmit({
			tradeoffs_accepted: [...tradeoffsAccepted],
			concerns_overridden: [...concernsOverridden],
			confidence,
			free_text: freeText.trim() || null
		});
	}

	function toggleTradeoff(t: string) {
		const next = new Set(tradeoffsAccepted);
		if (next.has(t)) next.delete(t);
		else next.add(t);
		tradeoffsAccepted = next;
	}

	function toggleConcern(c: string) {
		const next = new Set(concernsOverridden);
		if (next.has(c)) next.delete(c);
		else next.add(c);
		concernsOverridden = next;
	}
</script>

<div class="space-y-5">
	<!-- Selected option summary -->
	<div class="p-4 rounded-lg bg-brand-50 dark:bg-brand-950 border border-brand-200 dark:border-brand-800">
		<p class="text-sm font-medium text-brand-700 dark:text-brand-300">Selected Option</p>
		<p class="text-base font-semibold text-neutral-900 dark:text-neutral-100 mt-1">{option.label}</p>
	</div>

	<!-- Tradeoffs acceptance -->
	{#if option.tradeoffs.length > 0}
		<div>
			<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
				I accept these tradeoffs
			</label>
			<div class="space-y-2">
				{#each option.tradeoffs as tradeoff}
					<label class="flex items-start gap-2 cursor-pointer">
						<input
							type="checkbox"
							checked={tradeoffsAccepted.has(tradeoff)}
							onchange={() => toggleTradeoff(tradeoff)}
							class="mt-0.5 rounded border-neutral-300 dark:border-neutral-600 text-brand-600 focus:ring-brand-500"
						/>
						<span class="text-sm text-neutral-600 dark:text-neutral-400">{tradeoff}</span>
					</label>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Dissenting views override -->
	{#if dissenting_views.length > 0}
		<div>
			<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
				I've considered and override these concerns
			</label>
			<div class="space-y-2">
				{#each dissenting_views as concern}
					<label class="flex items-start gap-2 cursor-pointer">
						<input
							type="checkbox"
							checked={concernsOverridden.has(concern)}
							onchange={() => toggleConcern(concern)}
							class="mt-0.5 rounded border-neutral-300 dark:border-neutral-600 text-brand-600 focus:ring-brand-500"
						/>
						<span class="text-sm text-neutral-600 dark:text-neutral-400">{concern}</span>
					</label>
				{/each}
			</div>
		</div>
	{/if}

	<!-- Confidence slider -->
	<div>
		<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
			How confident are you in this decision?
			<span class="ml-2 text-brand-600 dark:text-brand-400 font-semibold">{confidence}%</span>
		</label>
		<input
			type="range"
			min="0"
			max="100"
			bind:value={confidence}
			class="w-full h-2 rounded-full appearance-none cursor-pointer bg-neutral-200 dark:bg-neutral-700 accent-brand-500"
		/>
		<div class="flex justify-between text-xs text-neutral-400 mt-1">
			<span>Not sure</span>
			<span>Very confident</span>
		</div>
	</div>

	<!-- Free text -->
	<div>
		<label class="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
			Additional notes <span class="text-neutral-400">(optional)</span>
		</label>
		<textarea
			bind:value={freeText}
			rows="3"
			maxlength="2000"
			placeholder="Any additional reasoning or context..."
			class="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-900 px-3 py-2 text-sm text-neutral-900 dark:text-neutral-100 placeholder:text-neutral-400 focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
		></textarea>
	</div>

	<!-- Actions -->
	<div class="flex items-center gap-3 pt-2">
		<BoButton variant="outline" onclick={onback}>Back</BoButton>
		<BoButton variant="brand" onclick={handleSubmit} disabled={submitting} loading={submitting}>Confirm Decision</BoButton>
	</div>
</div>
