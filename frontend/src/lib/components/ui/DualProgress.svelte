<script lang="ts">
	/**
	 * DualProgress Component
	 * Shows overall meeting progress + per-round progress during discussion phases
	 */
	interface Props {
		// Overall progress
		currentSubProblem: number;
		totalSubProblems: number;
		currentPhase: string | null;

		// Round progress (only during discussion)
		currentRound: number | null;
		maxRounds: number | null;
		contributionsReceived: number;
		expectedContributions: number;
	}

	let {
		currentSubProblem,
		totalSubProblems,
		currentPhase,
		currentRound,
		maxRounds,
		contributionsReceived,
		expectedContributions,
	}: Props = $props();

	const isDiscussionPhase = $derived(
		currentPhase === 'initial_round' || currentPhase === 'discussion'
	);

	const roundProgress = $derived(
		currentRound && maxRounds ? Math.min((currentRound / maxRounds) * 100, 100) : 0
	);

	const contributionProgress = $derived(
		expectedContributions > 0 ? Math.min((contributionsReceived / expectedContributions) * 100, 100) : 0
	);

	const overallProgress = $derived.by(() => {
		if (!currentPhase) return 0;

		// Phase-based progress
		const phaseProgress: Record<string, number> = {
			decomposition: 10,
			persona_selection: 20,
			initial_round: 35,
			discussion: 50,
			voting: 75,
			synthesis: 90,
			complete: 100,
		};

		const baseProgress = phaseProgress[currentPhase] || 0;

		// Add micro-progress within discussion phase
		if (isDiscussionPhase && currentRound && maxRounds) {
			const roundBonus = (roundProgress / 100) * 25; // Up to 25% bonus for rounds
			return Math.min(baseProgress + roundBonus, 75); // Cap at voting phase start
		}

		return baseProgress;
	});

	function formatPhase(phase: string | null): string {
		if (!phase) return 'Initializing';
		return phase
			.split('_')
			.map(word => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}
</script>

<div class="space-y-3">
	<!-- Overall Meeting Progress -->
	<div>
		<div class="flex items-center justify-between mb-1">
			<span class="text-sm font-medium text-slate-700 dark:text-slate-300">
				{#if totalSubProblems > 1 && currentSubProblem > 0}
					Sub-problem {currentSubProblem} of {totalSubProblems}
				{:else}
					Meeting Progress
				{/if}
			</span>
			<span class="text-xs text-slate-600 dark:text-slate-400">
				{formatPhase(currentPhase)}
			</span>
		</div>
		<div class="w-full bg-slate-200 dark:bg-slate-700 rounded-full h-2.5 overflow-hidden">
			<div
				class="bg-gradient-to-r from-blue-500 to-blue-600 h-2.5 rounded-full transition-all duration-500 ease-out"
				style="width: {overallProgress}%"
			></div>
		</div>
		<div class="flex items-center justify-between mt-1">
			<span class="text-xs text-slate-500 dark:text-slate-400">
				{overallProgress.toFixed(0)}% complete
			</span>
		</div>
	</div>

	<!-- Round Progress (only during discussion) -->
	{#if isDiscussionPhase && currentRound && maxRounds}
		<div class="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-3 border border-purple-200 dark:border-purple-800">
			<div class="flex items-center justify-between mb-2">
				<span class="text-sm font-semibold text-purple-900 dark:text-purple-100 flex items-center gap-2">
					<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
						<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
					</svg>
					Round {currentRound} of {maxRounds}
				</span>
				<span class="text-xs text-purple-700 dark:text-purple-300 font-medium">
					{contributionsReceived}/{expectedContributions} experts
				</span>
			</div>
			<div class="w-full bg-purple-200 dark:bg-purple-800 rounded-full h-2 mb-1 overflow-hidden">
				<div
					class="bg-gradient-to-r from-purple-500 to-purple-600 h-2 rounded-full transition-all duration-300 ease-out"
					style="width: {contributionProgress}%"
				></div>
			</div>
			<div class="flex items-center justify-between text-xs text-purple-600 dark:text-purple-400">
				<span>Contribution progress</span>
				<span>{contributionProgress.toFixed(0)}%</span>
			</div>
		</div>
	{/if}
</div>
