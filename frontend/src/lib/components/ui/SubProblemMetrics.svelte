<script lang="ts">
	/**
	 * SubProblemMetrics Component
	 * Shows micro-metrics for a sub-problem: experts, convergence, round, duration
	 */
	interface Props {
		expertCount: number;
		convergencePercent: number;
		currentRound: number;
		maxRounds: number;
		duration: string;
		status: 'pending' | 'active' | 'voting' | 'synthesis' | 'complete' | 'blocked';
	}

	let { expertCount, convergencePercent, currentRound, maxRounds, duration, status }: Props = $props();

	function getStatusBadge(status: Props['status']) {
		const badges = {
			complete: { color: 'bg-[hsl(142,76%,95%)] text-[hsl(142,76%,36%)] dark:bg-[hsl(142,76%,20%)] dark:text-[hsl(142,76%,60%)]', label: 'Complete' },
			active: { color: 'bg-brand-100 text-brand-700 dark:bg-brand-900 dark:text-brand-300', label: 'Active' },
			voting: { color: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300', label: 'Voting' },
			synthesis: { color: 'bg-neutral-100 text-neutral-700 dark:bg-neutral-800 dark:text-neutral-300', label: 'Synthesis' },
			blocked: { color: 'bg-[hsl(38,92%,95%)] text-[hsl(38,92%,50%)] dark:bg-[hsl(38,92%,20%)] dark:text-[hsl(38,92%,70%)]', label: 'Blocked' },
			pending: { color: 'bg-neutral-100 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-400', label: 'Pending' },
		};
		return badges[status];
	}

	const badge = $derived(getStatusBadge(status));
</script>

<div class="grid grid-cols-2 md:grid-cols-4 gap-4">
	<div>
		<div class="text-[0.75rem] font-normal leading-normal text-neutral-500 dark:text-neutral-400">Experts</div>
		<div class="text-[0.875rem] font-semibold text-neutral-900 dark:text-white">{expertCount}</div>
	</div>
	<div>
		<div class="text-[0.75rem] font-normal leading-normal text-neutral-500 dark:text-neutral-400">Convergence</div>
		<div class="text-[0.875rem] font-semibold text-neutral-900 dark:text-white">{convergencePercent}%</div>
	</div>
	<div>
		<div class="text-[0.75rem] font-normal leading-normal text-neutral-500 dark:text-neutral-400">Round</div>
		<div class="text-[0.875rem] font-semibold text-neutral-900 dark:text-white">{currentRound}/{maxRounds}</div>
	</div>
	<div>
		<div class="text-[0.75rem] font-normal leading-normal text-neutral-500 dark:text-neutral-400">Status</div>
		<div>
			<span class="inline-flex items-center px-2 py-0.5 rounded text-[0.75rem] font-medium {badge.color}">
				{badge.label}
			</span>
		</div>
	</div>
</div>
