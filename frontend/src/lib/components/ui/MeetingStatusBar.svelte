<script lang="ts">
	import { eventTokens, PHASE_PROGRESS_MAP } from '$lib/design/tokens';

	interface Props {
		currentPhase: string | null;
		currentRound: number | null;
		maxRounds: number;
		subProblemProgress: { current: number; total: number } | null;
	}

	let { currentPhase = null, currentRound = null, maxRounds = 10, subProblemProgress }: Props = $props();

	// Calculate phase progress percentage
	const phaseProgress = $derived.by(() => {
		if (!currentPhase) return 0;

		const baseProgress = PHASE_PROGRESS_MAP[currentPhase as keyof typeof PHASE_PROGRESS_MAP] || 0;

		// Add round-based progress within discussion phase
		if (currentPhase === 'discussion' && currentRound) {
			const roundProgress = Math.min((currentRound / maxRounds) * 30, 30);
			return Math.min(baseProgress + roundProgress, 100);
		}

		return baseProgress;
	});

	function getPhaseEmoji(phase: string | null): string {
		// Removed emojis for cleaner professional UI
		return '';
	}

	function formatPhase(phase: string | null): string {
		if (!phase) return 'Initializing';
		return phase
			.split('_')
			.map((word) => word.charAt(0).toUpperCase() + word.slice(1))
			.join(' ');
	}

	function getPhaseEstimate(phase: string | null): string {
		const estimates: Record<string, string> = {
			decomposition: '~30s',
			persona_selection: '~1min',
			initial_round: '~2min',
			discussion: '~3-5min',
			voting: '~1min',
			synthesis: '~30s',
			complete: 'Done',
		};
		return phase ? estimates[phase] || 'Processing...' : 'Starting...';
	}
</script>

<div class="sticky top-16 z-20 bg-white/95 dark:bg-neutral-800/95 backdrop-blur-sm border-b border-neutral-200 dark:border-neutral-700 shadow-sm">
	<div class="mx-auto px-4 sm:px-6 lg:px-8 xl:px-12 py-2.5">
		<div class="flex items-center justify-between gap-4">
			<!-- Current Phase -->
			<div class="flex items-center gap-2.5 min-w-0">
				<div class="min-w-0">
					<p class="text-sm font-semibold text-neutral-900 dark:text-white truncate">
						{formatPhase(currentPhase)}
					</p>
					<p class="text-xs text-neutral-600 dark:text-neutral-400 flex items-center gap-1.5 flex-wrap">
						{#if currentRound}
							<span class="inline-flex items-center gap-1">
								<span class="inline-block w-1 h-1 bg-neutral-400 rounded-full"></span>
								<span>Round {currentRound}/{maxRounds}</span>
							</span>
						{/if}
						{#if subProblemProgress && subProblemProgress.total > 1 && subProblemProgress.current > 0}
							<span class="inline-flex items-center gap-1">
								<span class="inline-block w-1 h-1 bg-neutral-400 rounded-full"></span>
								<span>Focus area {subProblemProgress.current}/{subProblemProgress.total}</span>
							</span>
						{/if}
					</p>
				</div>
			</div>

			<!-- Phase Estimate -->
			<div class="text-xs text-neutral-600 dark:text-neutral-400 font-medium hidden md:block flex-shrink-0">
				{getPhaseEstimate(currentPhase)}
			</div>
		</div>
	</div>
</div>
