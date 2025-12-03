<script lang="ts">
	import WorkingStatus from '$lib/components/ui/WorkingStatus.svelte';

	interface Props {
		currentWorkingPhase: string | null;
		workingElapsedSeconds: number;
		estimatedDuration: string | undefined;
		isStale: boolean;
		staleSinceSeconds: number;
		sessionStatus: string | undefined;
	}

	let {
		currentWorkingPhase,
		workingElapsedSeconds,
		estimatedDuration,
		isStale,
		staleSinceSeconds,
		sessionStatus
	}: Props = $props();
</script>

<!-- AUDIT FIX (Issue #4): Prominent working status indicator -->
<!-- Shows either:
     1. Backend working_status phase (from currentWorkingPhase)
     2. Client-side staleness banner (when no events for 8+ seconds) -->
{#if currentWorkingPhase}
	<WorkingStatus
		currentPhase={currentWorkingPhase}
		elapsedSeconds={workingElapsedSeconds}
		{estimatedDuration}
	/>
{:else if isStale && sessionStatus === 'active'}
	<WorkingStatus
		currentPhase="Still working..."
		elapsedSeconds={staleSinceSeconds}
	/>
{/if}
