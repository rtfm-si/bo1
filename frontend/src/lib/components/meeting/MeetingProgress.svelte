<script lang="ts">
	import { PHASE_PROGRESS_MAP } from '$lib/design/tokens';
	import type { SessionData } from '../../../routes/(app)/meeting/[id]/lib/sessionStore.svelte';

	interface Props {
		session: SessionData | null;
	}

	let { session }: Props = $props();

	function calculateProgress(session: SessionData | null): number {
		if (!session) return 0;

		// Handle completed meetings (either by status or phase)
		if (session.status === 'completed' || session.phase === 'complete') {
			return 100;
		}

		// Handle synthesis phase
		if (session.phase === 'synthesis') {
			return 95;
		}

		const baseProgress = PHASE_PROGRESS_MAP[session.phase as keyof typeof PHASE_PROGRESS_MAP] || 0;

		// Add round-based progress within discussion phase
		if (session.phase === 'discussion' && session.round_number) {
			const roundProgress = Math.min((session.round_number / 10) * 25, 25);
			return Math.min(baseProgress + roundProgress, 100);
		}

		return baseProgress;
	}

	const progress = $derived(calculateProgress(session));
</script>

{#if session}
	<div class="px-4 pb-3">
		<div class="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
			<div
				class="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
				style="width: {progress}%"
			></div>
		</div>
	</div>
{/if}
