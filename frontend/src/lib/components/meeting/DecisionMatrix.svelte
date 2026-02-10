<script lang="ts">
	/**
	 * DecisionMatrix - Interactive weighted scoring matrix
	 */
	import type { OptionCard } from '$lib/api/sse-events';
	import { BoButton } from '$lib/components/ui';
	import {
		getDefaultCriteria,
		computeWeightedScores,
		computeSensitivity,
		getWinner,
		type Criterion
	} from '$lib/utils/decision-matrix';
	import { Trophy, Info } from 'lucide-svelte';

	interface Props {
		options: OptionCard[];
		onapply: (optionId: string) => void;
	}

	let { options, onapply }: Props = $props();

	let criteria = $state<Criterion[]>(getDefaultCriteria());

	const scores = $derived(computeWeightedScores(options, criteria));
	const winnerId = $derived(getWinner(scores));
	const sensitivity = $derived(computeSensitivity(options, criteria));

	function updateWeight(key: string, value: number) {
		criteria = criteria.map((c) => (c.key === key ? { ...c, weight: value } : c));
	}

	const winnerOption = $derived(options.find((o) => o.id === winnerId));
</script>

<div class="space-y-4">
	<!-- Criteria weight sliders -->
	<div>
		<h4 class="text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-3">
			Adjust Criteria Weights
		</h4>
		<div class="space-y-3">
			{#each criteria as criterion}
				<div class="flex items-center gap-3">
					<span class="w-28 text-sm text-neutral-600 dark:text-neutral-400 flex-shrink-0">
						{criterion.label}
					</span>
					<input
						type="range"
						min="0"
						max="5"
						step="0.5"
						value={criterion.weight}
						oninput={(e) => updateWeight(criterion.key, parseFloat(e.currentTarget.value))}
						class="flex-1 h-2 rounded-full appearance-none cursor-pointer bg-neutral-200 dark:bg-neutral-700 accent-brand-500"
					/>
					<span class="w-8 text-xs text-neutral-500 text-right">{criterion.weight}</span>
				</div>
			{/each}
		</div>
	</div>

	<!-- Score table -->
	<div class="overflow-x-auto">
		<table class="w-full text-sm">
			<thead>
				<tr class="border-b border-neutral-200 dark:border-neutral-700">
					<th class="text-left py-2 pr-4 font-medium text-neutral-600 dark:text-neutral-400">
						Option
					</th>
					{#each criteria as c}
						<th class="text-center py-2 px-2 font-medium text-neutral-600 dark:text-neutral-400 text-xs">
							{c.label}
						</th>
					{/each}
					<th class="text-center py-2 pl-4 font-semibold text-neutral-900 dark:text-neutral-100">
						Score
					</th>
				</tr>
			</thead>
			<tbody>
				{#each options as option}
					{@const isWinner = option.id === winnerId}
					<tr
						class="border-b border-neutral-100 dark:border-neutral-800 {isWinner
							? 'bg-brand-50 dark:bg-brand-950'
							: ''}"
					>
						<td class="py-2 pr-4 font-medium text-neutral-900 dark:text-neutral-100">
							<div class="flex items-center gap-1.5">
								{#if isWinner}
									<Trophy class="w-4 h-4 text-brand-500" />
								{/if}
								{option.label}
							</div>
						</td>
						{#each criteria as c}
							{@const raw = option.criteria_scores?.[c.key] ?? 0.5}
							<td class="text-center py-2 px-2">
								<span
									class="inline-block w-8 h-8 leading-8 rounded text-xs font-medium {raw >= 0.7
										? 'bg-success-100 text-success-700 dark:bg-success-900 dark:text-success-300'
										: raw >= 0.4
											? 'bg-warning-100 text-warning-700 dark:bg-warning-900 dark:text-warning-300'
											: 'bg-error-100 text-error-700 dark:bg-error-900 dark:text-error-300'}"
								>
									{Math.round(raw * 10)}
								</span>
							</td>
						{/each}
						<td class="text-center py-2 pl-4 font-bold text-neutral-900 dark:text-neutral-100">
							{Math.round((scores[option.id] ?? 0) * 100)}
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>

	<!-- Sensitivity analysis -->
	{#if sensitivity.length > 0}
		<div class="p-3 rounded-lg bg-neutral-50 dark:bg-neutral-800 border border-neutral-200 dark:border-neutral-700">
			<div class="flex items-center gap-1.5 mb-2">
				<Info class="w-4 h-4 text-neutral-500" />
				<span class="text-xs font-medium text-neutral-600 dark:text-neutral-400"
					>Sensitivity Analysis</span
				>
			</div>
			<ul class="space-y-1">
				{#each sensitivity as s}
					<li class="text-xs text-neutral-500 dark:text-neutral-400">
						If you weight <strong>{s.criterion}</strong> by +{s.flip_delta},
						<strong>{s.new_winner}</strong> wins
					</li>
				{/each}
			</ul>
		</div>
	{/if}

	<!-- Apply winner -->
	{#if winnerOption}
		<div class="flex justify-end pt-2">
			<BoButton variant="brand" onclick={() => onapply(winnerId)}>
				Apply Winner: {winnerOption.label}
			</BoButton>
		</div>
	{/if}
</div>
