<script lang="ts">
	/**
	 * PhaseTimeline Component
	 * Displays horizontal stepper showing deliberation phases with completion status
	 */
	import { Search, Users, MessageSquare, Target, TrendingUp, CheckCircle } from 'lucide-svelte';
	import type { ComponentType } from 'svelte';

	interface Phase {
		id: string;
		label: string;
		icon: ComponentType;
	}

	interface Props {
		currentPhase: string | null;
	}

	let { currentPhase = null }: Props = $props();

	const phases: Phase[] = [
		{ id: 'decomposition', label: 'Analysis', icon: Search },
		{ id: 'persona_selection', label: 'Experts', icon: Users },
		{ id: 'initial_round', label: 'Discussion', icon: MessageSquare },
		{ id: 'voting', label: 'Voting', icon: Target },
		{ id: 'synthesis', label: 'Synthesis', icon: TrendingUp },
		{ id: 'complete', label: 'Complete', icon: CheckCircle },
	];

	function getPhaseStatus(
		phaseId: string,
		currentPhase: string | null
	): 'complete' | 'current' | 'pending' {
		if (!currentPhase) return 'pending';

		const currentIndex = phases.findIndex((p) => p.id === currentPhase);
		const phaseIndex = phases.findIndex((p) => p.id === phaseId);

		if (phaseIndex < currentIndex) return 'complete';
		if (phaseIndex === currentIndex) return 'current';
		return 'pending';
	}

	function getPhaseClasses(status: string): string {
		if (status === 'complete') {
			return 'bg-green-500 text-white border-green-500';
		}
		if (status === 'current') {
			return 'bg-blue-500 text-white border-blue-500 ring-4 ring-blue-200 dark:ring-blue-800';
		}
		return 'bg-slate-200 dark:bg-slate-700 text-slate-400 dark:text-slate-500 border-slate-300 dark:border-slate-600';
	}

	function getConnectorClasses(index: number): string {
		if (!currentPhase) return 'bg-slate-300 dark:bg-slate-600';

		const currentIndex = phases.findIndex((p) => p.id === currentPhase);
		if (index < currentIndex) {
			return 'bg-green-500';
		}
		return 'bg-slate-300 dark:bg-slate-600';
	}
</script>

<div class="w-full py-6">
	<div class="flex items-center justify-between">
		{#each phases as phase, index (phase.id)}
			<!-- Phase Step -->
			<div class="flex flex-col items-center gap-2 relative">
				<div
					class="w-12 h-12 rounded-full border-2 flex items-center justify-center transition-all duration-300 {getPhaseClasses(
						getPhaseStatus(phase.id, currentPhase)
					)}"
				>
					{#if getPhaseStatus(phase.id, currentPhase) === 'complete'}
						<CheckCircle size={24} class="text-current" />
					{:else}
						{@const Icon = phase.icon}
						<Icon size={24} class="text-current" />
					{/if}
				</div>
				<span class="text-xs font-medium text-slate-700 dark:text-slate-300 text-center">
					{phase.label}
				</span>
			</div>

			<!-- Connector Line -->
			{#if index < phases.length - 1}
				<div
					class="flex-1 h-1 mx-2 rounded transition-all duration-500 {getConnectorClasses(
						index
					)}"
				></div>
			{/if}
		{/each}
	</div>
</div>
