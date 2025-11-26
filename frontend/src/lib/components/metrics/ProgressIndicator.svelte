<script lang="ts">
	import type { SSEEvent } from '$lib/api/sse-events';
	import { MessageSquare } from 'lucide-svelte';

	interface Props {
		events: SSEEvent[];
		currentPhase: string | null;
		currentRound: number | null;
	}

	let { events, currentPhase, currentRound }: Props = $props();

	// Calculate contribution count
	const totalContributions = $derived(events.filter((e) => e.event_type === 'contribution').length);
</script>

<div class="bg-white dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700 p-4">
	<!-- Header -->
	<h3 class="text-sm font-semibold text-slate-900 dark:text-white mb-3 flex items-center gap-2">
		<MessageSquare size={16} class="text-neutral-500" />
		Deliberation Progress
	</h3>

	<!-- Simplified Metrics - Only Expert Contributions -->
	<div class="text-center py-2">
		<p class="text-xs text-slate-500 dark:text-slate-400 mb-2">Expert Contributions</p>
		<p class="text-3xl font-bold text-slate-900 dark:text-white">
			{totalContributions}
		</p>
	</div>
</div>
