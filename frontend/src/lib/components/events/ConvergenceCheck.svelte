<script lang="ts">
	/**
	 * ConvergenceCheck Event Component
	 * Displays convergence status and progress towards consensus
	 */
	import type { ConvergenceEvent } from '$lib/api/sse-events';
	import Badge from '$lib/components/ui/Badge.svelte';

	interface Props {
		event: ConvergenceEvent;
	}

	let { event }: Props = $props();

	// Default threshold to 0.85 if not provided
	const threshold = $derived(event.data.threshold ?? 0.85);
	const percentage = $derived(Math.round((event.data.score / threshold) * 100));
	const progressWidth = $derived(Math.min(percentage, 100));
</script>

<div class="space-y-3">
	<div class="flex items-center justify-between">
		<div class="flex items-center gap-2">
			<h3 class="text-base font-semibold text-neutral-900 dark:text-neutral-100">
				Convergence Check
			</h3>
			<Badge variant={event.data.converged ? 'success' : 'info'}>
				{event.data.converged ? 'Converged' : 'In Progress'}
			</Badge>
		</div>
		<div class="text-sm text-neutral-600 dark:text-neutral-400">
			Round {event.data.round}{event.data.max_rounds ? ` / ${event.data.max_rounds}` : ''}
		</div>
	</div>

	<!-- Progress Bar -->
	<div class="space-y-2">
		<div class="flex items-center justify-between text-sm">
			<span class="text-neutral-600 dark:text-neutral-400">Consensus Score</span>
			<span class="font-semibold text-neutral-900 dark:text-neutral-100">
				{event.data.score.toFixed(2)} / {threshold.toFixed(2)}
			</span>
		</div>
		<div class="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-3 overflow-hidden">
			<div
				class="h-full transition-all duration-500 ease-out rounded-full"
				class:bg-success-500={event.data.converged}
				class:bg-info-500={!event.data.converged && percentage >= 70}
				class:bg-warning-500={!event.data.converged && percentage >= 50 && percentage < 70}
				class:bg-neutral-400={!event.data.converged && percentage < 50}
				style="width: {progressWidth}%"
			></div>
		</div>
		<div class="text-xs text-center text-neutral-500 dark:text-neutral-400">
			{percentage}% of threshold
		</div>
	</div>

	{#if event.data.should_stop && event.data.stop_reason}
		<div
			class="bg-success-50 dark:bg-success-900/20 border border-success-200 dark:border-success-700 rounded-lg p-3"
		>
			<p class="text-sm text-success-800 dark:text-success-200">
				<span class="font-semibold">Ready to proceed:</span>
				{event.data.stop_reason}
			</p>
		</div>
	{/if}
</div>
