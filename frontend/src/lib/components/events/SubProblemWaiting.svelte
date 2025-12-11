<script lang="ts">
	/**
	 * SubProblemWaiting - Displays user-friendly waiting message for sub-problem dependencies
	 */
	import type { SSEEvent } from '$lib/api/sse-events';
	import { Clock } from 'lucide-svelte';

	interface Props {
		event: SSEEvent;
	}

	let { event }: Props = $props();

	const waitingFor = $derived((event.data.waiting_for as number[]) ?? []);
	const subProblemIndex = $derived((event.data.sub_problem_index as number) ?? 0);

	// Format waiting list as "Focus Areas 1, 2, 3"
	const waitingForText = $derived.by(() => {
		if (waitingFor.length === 0) return 'other focus areas';
		const areas = waitingFor.map((i) => i + 1).join(', ');
		return waitingFor.length === 1 ? `Focus Area ${areas}` : `Focus Areas ${areas}`;
	});
</script>

<div class="flex items-center gap-3 py-2">
	<div class="flex-shrink-0">
		<div
			class="w-8 h-8 rounded-full bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center"
		>
			<Clock size={16} class="text-blue-600 dark:text-blue-400 animate-pulse" />
		</div>
	</div>
	<div class="flex-1 min-w-0">
		<p class="text-sm text-slate-600 dark:text-slate-400">
			Focus Area {subProblemIndex + 1} is waiting for {waitingForText} to provide initial context...
		</p>
	</div>
</div>
