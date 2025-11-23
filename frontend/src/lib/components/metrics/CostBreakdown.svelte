<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent, PhaseCostBreakdownEvent } from '$lib/api/sse-events';

	interface Props {
		events: SSEEvent[];
	}

	let { events }: Props = $props();

	// Extract cost breakdown from events
	const costData = $derived.by(() => {
		const costEvent = events.find(
			(e) => e.event_type === 'phase_cost_breakdown'
		) as PhaseCostBreakdownEvent | undefined;

		if (!costEvent) {
			return null;
		}

		const phaseCosts = costEvent.data.phase_costs;
		const totalCost = costEvent.data.total_cost;

		// Convert to array and sort by cost (descending)
		const phases = Object.entries(phaseCosts)
			.map(([phase, cost]) => ({
				phase: formatPhaseName(phase),
				cost: cost,
				percentage: totalCost > 0 ? (cost / totalCost) * 100 : 0,
			}))
			.sort((a, b) => b.cost - a.cost);

		return {
			phases,
			totalCost,
		};
	});

	function formatPhaseName(phase: string): string {
		return phase
			.split('_')
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function getPhaseColor(index: number): string {
		const colors = [
			eventTokens.charts.cost.primary,
			eventTokens.charts.cost.secondary,
		];
		return colors[index % colors.length];
	}
</script>

{#if costData}
	<div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
		<!-- Header -->
		<div class="flex items-center justify-between mb-4">
			<h3 class="text-sm font-semibold text-slate-900 dark:text-white flex items-center gap-2">
				<span>💰</span>
				Cost Breakdown
			</h3>
			<div class="text-right">
				<p class="text-xs text-slate-500 dark:text-slate-400">Total Cost</p>
				<p class="text-lg font-bold text-brand-600 dark:text-brand-400">
					${costData.totalCost.toFixed(4)}
				</p>
			</div>
		</div>

		<!-- Phase Breakdown -->
		<div class="space-y-3">
			{#each costData.phases as phase, index (phase.phase)}
				<div>
					<!-- Phase Name and Cost -->
					<div class="flex items-center justify-between mb-1">
						<span class="text-xs font-medium text-slate-700 dark:text-slate-300">
							{phase.phase}
						</span>
						<span class="text-xs font-semibold text-slate-900 dark:text-white">
							${phase.cost.toFixed(4)}
							<span class="text-slate-500 dark:text-slate-400 ml-1">
								({phase.percentage.toFixed(1)}%)
							</span>
						</span>
					</div>

					<!-- Progress Bar -->
					<div class="w-full bg-slate-100 dark:bg-slate-700 rounded-full h-2 overflow-hidden">
						<div
							class="h-full rounded-full transition-all duration-500"
							style="width: {phase.percentage}%; background-color: {getPhaseColor(index)}"
						></div>
					</div>
				</div>
			{/each}
		</div>

		<!-- Cost Efficiency Note -->
		<div class="mt-4 pt-3 border-t border-slate-200 dark:border-slate-700">
			<p class="text-xs text-slate-500 dark:text-slate-400">
				Cost optimized through prompt caching and Haiku summarization
			</p>
		</div>
	</div>
{:else}
	<div class="bg-slate-50 dark:bg-slate-900/50 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
		<p class="text-xs text-slate-500 dark:text-slate-400 text-center">
			Cost breakdown will appear after deliberation
		</p>
	</div>
{/if}
