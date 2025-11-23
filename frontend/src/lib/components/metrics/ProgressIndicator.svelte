<script lang="ts">
	import { eventTokens } from '$lib/design/tokens';
	import type { SSEEvent } from '$lib/api/sse-events';
	import { Search, Users, MessageSquare, Target, TrendingUp, CheckCircle } from 'lucide-svelte';
	import type { ComponentType } from 'svelte';

	interface Props {
		events: SSEEvent[];
		currentPhase: string | null;
		currentRound: number | null;
	}

	let { events, currentPhase, currentRound }: Props = $props();

	// Calculate overall progress metrics
	const progressMetrics = $derived.by(() => {
		// Extract key milestones
		const hasDecomposition = events.some((e) => e.event_type === 'decomposition_complete');
		const hasPersonaSelection = events.some((e) => e.event_type === 'persona_selection_complete');
		const hasInitialRound = events.some((e) => e.event_type === 'initial_round_started');
		const hasVoting = events.some((e) => e.event_type === 'voting_complete');
		const hasSynthesis = events.some((e) => e.event_type === 'synthesis_complete');
		const hasMetaSynthesis = events.some((e) => e.event_type === 'meta_synthesis_complete');
		const isComplete = events.some((e) => e.event_type === 'complete');

		// Sub-problem tracking
		const subProblemStartedEvents = events.filter((e) => e.event_type === 'subproblem_started');
		const subProblemCompleteEvents = events.filter((e) => e.event_type === 'subproblem_complete');
		const totalSubProblems = subProblemStartedEvents.length > 0
			? (subProblemStartedEvents[0].data.total_sub_problems as number)
			: 1;
		const completedSubProblems = subProblemCompleteEvents.length;

		// Round tracking
		const totalRounds = currentRound || 0;

		// Contribution tracking
		const totalContributions = events.filter((e) => e.event_type === 'contribution').length;

		return {
			hasDecomposition,
			hasPersonaSelection,
			hasInitialRound,
			hasVoting,
			hasSynthesis,
			hasMetaSynthesis,
			isComplete,
			totalSubProblems,
			completedSubProblems,
			totalRounds,
			totalContributions,
		};
	});

	// Define phase milestones
	const phaseMilestones = $derived([
		{
			name: 'Problem Analysis',
			icon: Search,
			completed: progressMetrics.hasDecomposition,
			current: currentPhase === 'decomposition',
		},
		{
			name: 'Expert Selection',
			icon: Users,
			completed: progressMetrics.hasPersonaSelection,
			current: currentPhase === 'persona_selection',
		},
		{
			name: 'Discussion',
			icon: MessageSquare,
			completed: progressMetrics.hasVoting,
			current: currentPhase === 'initial_round' || currentPhase === 'discussion',
		},
		{
			name: 'Recommendations',
			icon: Target,
			completed: progressMetrics.hasSynthesis,
			current: currentPhase === 'voting',
		},
		{
			name: 'Synthesis',
			icon: TrendingUp,
			completed: progressMetrics.hasMetaSynthesis || progressMetrics.isComplete,
			current: currentPhase === 'synthesis' || currentPhase === 'meta_synthesis',
		},
	]);

	function getPhaseStatus(milestone: typeof phaseMilestones[0]): 'complete' | 'current' | 'pending' {
		if (milestone.completed) return 'complete';
		if (milestone.current) return 'current';
		return 'pending';
	}

	function getStatusColor(status: 'complete' | 'current' | 'pending'): string {
		switch (status) {
			case 'complete':
				return eventTokens.charts.progress.complete;
			case 'current':
				return eventTokens.charts.progress.current;
			default:
				return eventTokens.charts.progress.pending;
		}
	}
</script>

<div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
	<!-- Header -->
	<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
		<TrendingUp size={16} class="text-neutral-500" />
		Deliberation Progress
	</h3>

	<!-- Phase Timeline -->
	<div class="space-y-3 mb-4">
		{#each phaseMilestones as milestone, index (milestone.name)}
			{@const status = getPhaseStatus(milestone)}
			{@const color = getStatusColor(status)}
			<div class="flex items-center gap-3">
				<!-- Icon -->
				<div
					class="flex items-center justify-center w-8 h-8 rounded-full border-2 transition-all"
					style="border-color: {color}; background-color: {status === 'complete' ? color : 'transparent'}"
				>
					{#if status === 'complete'}
						<CheckCircle size={16} class="text-white" />
					{:else if status === 'current'}
						{@const Icon = milestone.icon}
						<Icon size={16} class="animate-pulse" style="color: {color}" />
					{:else}
						{@const Icon = milestone.icon}
						<Icon size={16} class="opacity-50" style="color: {color}" />
					{/if}
				</div>

				<!-- Phase Name -->
				<div class="flex-1">
					<p
						class="text-sm font-medium"
						class:text-slate-900={status !== 'pending'}
						class:dark:text-white={status !== 'pending'}
						class:text-slate-400={status === 'pending'}
						class:dark:text-slate-600={status === 'pending'}
					>
						{milestone.name}
					</p>
					{#if status === 'current'}
						<p class="text-xs text-slate-500 dark:text-slate-400">In progress...</p>
					{/if}
				</div>

				<!-- Status Badge -->
				{#if status === 'complete'}
					<span class="text-xs px-2 py-0.5 rounded bg-green-100 text-green-700 dark:bg-green-900/50 dark:text-green-300">
						Complete
					</span>
				{:else if status === 'current'}
					<span class="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700 dark:bg-blue-900/50 dark:text-blue-300 animate-pulse">
						Active
					</span>
				{/if}
			</div>

			<!-- Connector Line -->
			{#if index < phaseMilestones.length - 1}
				<div class="ml-4 h-4 w-0.5 bg-slate-200 dark:bg-slate-700"></div>
			{/if}
		{/each}
	</div>

	<!-- Metrics Grid -->
	<div class="grid grid-cols-2 gap-3 pt-3 border-t border-slate-200 dark:border-slate-700">
		<!-- Sub-problems -->
		<div class="text-center">
			<p class="text-xs text-slate-500 dark:text-slate-400 mb-1">Sub-problems</p>
			<p class="text-lg font-bold text-slate-900 dark:text-white">
				{progressMetrics.completedSubProblems}/{progressMetrics.totalSubProblems}
			</p>
		</div>

		<!-- Rounds -->
		<div class="text-center">
			<p class="text-xs text-slate-500 dark:text-slate-400 mb-1">Rounds</p>
			<p class="text-lg font-bold text-slate-900 dark:text-white">
				{progressMetrics.totalRounds}
			</p>
		</div>

		<!-- Contributions -->
		<div class="text-center col-span-2">
			<p class="text-xs text-slate-500 dark:text-slate-400 mb-1">Expert Contributions</p>
			<p class="text-lg font-bold text-slate-900 dark:text-white">
				{progressMetrics.totalContributions}
			</p>
		</div>
	</div>
</div>
