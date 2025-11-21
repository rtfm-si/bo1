<script lang="ts">
	/**
	 * PhaseTable Event Component
	 * Displays phase cost breakdown in a table
	 */
	import type { PhaseCostBreakdownEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: PhaseCostBreakdownEvent;
	}

	let { event }: Props = $props();

	const formatCost = (cost: number): string => {
		return `$${cost.toFixed(4)}`;
	};

	const formatPhase = (phase: string): string => {
		return phase
			.split('_')
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	};

	const calculatePercentage = (phaseCost: number, totalCost: number): string => {
		return ((phaseCost / totalCost) * 100).toFixed(1);
	};

	const sortedPhases = $derived(
		Object.entries(event.data.phase_costs).sort((a, b) => b[1] - a[1])
	);
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between">
		<h3 class="text-lg font-semibold text-neutral-900 dark:text-neutral-100">
			Phase Cost Breakdown
		</h3>
		<Badge variant="info" size="lg">
			Total: {formatCost(event.data.total_cost)}
		</Badge>
	</div>

	<div class="overflow-x-auto">
		<table class="w-full text-sm">
			<thead>
				<tr
					class="border-b border-neutral-200 dark:border-neutral-700 text-neutral-600 dark:text-neutral-400"
				>
					<th class="text-left py-2 px-3 font-semibold">Phase</th>
					<th class="text-right py-2 px-3 font-semibold">Cost</th>
					<th class="text-right py-2 px-3 font-semibold">Percentage</th>
					<th class="text-right py-2 px-3 font-semibold">Visual</th>
				</tr>
			</thead>
			<tbody>
				{#each sortedPhases as [phase, cost]}
					{@const percentage = calculatePercentage(cost, event.data.total_cost)}
					<tr
						class="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
					>
						<td class="py-2 px-3 text-neutral-900 dark:text-neutral-100">
							{formatPhase(phase)}
						</td>
						<td class="text-right py-2 px-3 font-mono text-neutral-900 dark:text-neutral-100">
							{formatCost(cost)}
						</td>
						<td class="text-right py-2 px-3 text-neutral-700 dark:text-neutral-300">
							{percentage}%
						</td>
						<td class="text-right py-2 px-3">
							<div class="w-full max-w-[100px] ml-auto">
								<div
									class="h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden"
								>
									<div
										class="h-full bg-brand-500 dark:bg-brand-400 rounded-full"
										style="width: {percentage}%"
									></div>
								</div>
							</div>
						</td>
					</tr>
				{/each}
			</tbody>
		</table>
	</div>
</div>
